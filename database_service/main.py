import asyncio
import json
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from sqlalchemy.future import select
from config import (kafka_bootstrap_servers, kafka_topic,
                    kafka_topic_producer, group_id)
from models import User, VKUser, VKGroup, user_groups, user_friends
from database import async_session
from sqlalchemy.orm import selectinload


async def process_message(message):
    data = json.loads(message.value)
    logger.info(f'Получены данные {message}.')
    logger.info(f'Преобразованы в {data}.')

    action = data.get('action')
    payload = data.get('data')

    if action == 'user_groups':
        await handle_user_groups(payload)

    elif action == 'user_friends':
        await handle_user_friends(payload)
        await get_user_info(payload)

    else:
        logger.warning('Неизвестное действие: %s', action)


async def handle_user_groups(data):
    user_id = data.get('user')
    groups = data.get('groups', [])

    user = await get_or_create_user(user_id)

    for group_data in groups:
        await process_group(user, group_data)


async def handle_user_friends(data):
    for user_id, friends in data.items():
        user, user_obj = await get_or_create_user_with_user_obj(int(user_id))

        for friend_id in friends:
            friend_user = await get_or_create_user(friend_id)
            await create_user_relation(user, friend_user)
    logger.info(f'Создание записи для {user_id} окончено.')


async def get_or_create_user_with_user_obj(user_id):
    async with async_session() as session:
        user = await session.execute(
            select(VKUser).filter_by(vk_user_id=user_id))
        user = user.scalar_one_or_none()
        user_obj = None

        if not user:
            user = VKUser(vk_user_id=user_id)
            session.add(user)
            await session.commit()

        user_obj = await session.execute(
            select(User).filter_by(vk_user=user))
        user_obj = user_obj.scalar_one_or_none()

        if not user_obj:
            user_obj = User(username=f"vk_{user_id}", vk_user=user)
            session.add(user_obj)
            await session.commit()

    return user, user_obj


async def get_or_create_user(user_id):
    async with async_session() as session:
        user = await session.execute(
            select(VKUser).filter_by(vk_user_id=user_id))
        user = user.scalar_one_or_none()

        if not user:
            user = VKUser(vk_user_id=user_id)
            session.add(user)
            await session.commit()

    return user


async def process_group(user, group_data):
    group_id = group_data.get('id')

    async with async_session() as session:
        group = await session.execute(
            select(VKGroup).filter_by(vk_group_id=group_id))
        group = group.scalar_one_or_none()

        if not group:
            group = VKGroup(
                vk_group_id=group_id,
                name=group_data.get('name'),
                screen_name=group_data.get('screen_name')
            )
            session.add(group)
            await session.commit()

        user_group_data = {'vk_user_id': user.id, 'vk_group_id': group.id}
        await session.execute(user_groups.insert().values(user_group_data))
        await session.commit()


async def create_user_relation(user, friend_user):
    user_friend_data = {
        'vk_user_id': user.id,
        'friend_vk_user_id': friend_user.id}

    async with async_session() as session:
        await session.execute(user_friends.insert().values(user_friend_data))
        await session.commit()

    return None


async def get_user_info(data):
    for user_id, friendz in data.items():
        logger.info(f'Подготовка данных для PDF {user_id}.')
        user_id = int(user_id)
        try:
            async with async_session() as session:

                user_and_friends_query = select(VKUser).options(
                    selectinload(VKUser.user),
                    selectinload(VKUser.friends).selectinload(VKUser.groups)
                ).filter_by(vk_user_id=user_id)

                vk_user = await session.execute(user_and_friends_query)
                vk_user_info = vk_user.scalars().first()

                friends_info_json = json.dumps(
                    [
                        {'id': friend.vk_user_id}
                        for friend in vk_user_info.friends
                    ], ensure_ascii=False)

                groups_info_json = json.dumps([
                    {'name': group.name}
                    for friend in vk_user_info.friends
                    for group in friend.groups
                ], ensure_ascii=False)

                logger.info(f'\nПользователь: {vk_user_info.user.username}.'
                            f'\nVK id: {user_id}.'
                            f'\nСписок друзей VK: {friends_info_json}'
                            f'\nСписок групп друзей VK: {groups_info_json}'
                            )

                data = {
                    'username': vk_user_info.user.username,
                    'vk_user_id': user_id,
                    'friends_ids': friends_info_json,
                    'group_names': groups_info_json,
                    }
                producer = await start_producer()
                await send_message_to_kafka(
                    producer,
                    kafka_topic_producer,
                    action='pdf_user_info',
                    data=data)
                await stop_producer(producer)
                logger.info(f'Отправлено сообщение {data}.')

        except Exception as e:
            logger.error(f'Ошибка сбора данных {e}.')


async def consume():
    consumer = AIOKafkaConsumer(
        kafka_topic,
        bootstrap_servers=kafka_bootstrap_servers,
        group_id=group_id,
        enable_auto_commit=True,
        auto_offset_reset='earliest'
    )
    await consumer.start()

    try:
        async for message in consumer:
            await process_message(message)
    finally:
        await consumer.stop()


async def start_producer():
    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    return producer


async def send_message_to_kafka(producer, topic: str, action: str, data: str):
    await producer.send(topic, value={"action": action, "data": data})


async def stop_producer(producer):
    await producer.stop()


if __name__ == '__main__':

    logger = logging.getLogger('database-service_logger')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('database-service.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    asyncio.run(consume())
