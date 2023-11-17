import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from sqlalchemy.future import select
from config import kafka_bootstrap_servers, kafka_topic, group_id
from models import User, VKUser, VKGroup, user_groups, user_friends
from database import async_session


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


if __name__ == '__main__':

    logger = logging.getLogger('database-service_logger')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('database-service.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    asyncio.run(consume())
