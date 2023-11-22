import asyncio
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from sqlalchemy.future import select
from config import (kafka_bootstrap_servers, kafka_topic_consumer,
                    kafka_topic_producer, group_id)
from models import User, VKUser, VKGroup, user_groups, user_friends
from database import async_session
from sqlalchemy.orm import selectinload
from sqlalchemy import and_


async def process_message(message: Any) -> None:
    """
    Обрабатывает полученное сообщение из Apache Kafka.
    Аргументы:
    - message: сообщение из Kafka.
    Допустимые действия:
    - 'user_groups': обрабатывает данные о группах пользователя.
    - 'user_friends': обрабатывает данные о друзьях пользователя.
    """
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
        logger.warning(f'Неизвестное действие: {action}')


async def handle_user_groups(data: Dict[str, Any]) -> None:
    """
    Обрабатывает данные о группах пользователя.
    Аргументы:
    - data: данные о группах пользователя в формате JSON.
    """
    user_id = data.get('user')
    groups = data.get('groups', [])

    user = await get_or_create_user(user_id)

    for group_data in groups:
        await process_group(user, group_data)


async def handle_user_friends(data: Dict[str, List[int]]) -> None:
    """
    Обрабатывает данные о друзьях пользователя.
    Аргументы:
    - data: данные о друзьях пользователя в формате JSON.
    """
    for user_id, friends in data.items():
        username = f'vk_{user_id}'
        vk_user, user = await get_or_create_vk_user_and_user(
            int(user_id),
            username)

        for friend_id in friends:
            friend_user = await get_or_create_user(friend_id)
            await create_user_relation(vk_user, friend_user)
    logger.info(f'Создание записи для {user_id} окончено.')


async def get_or_create_vk_user_and_user(
        user_id: int,
        username: str) -> Tuple[Optional[VKUser], Optional[User]]:
    async with async_session() as session:
        vk_user = await session.execute(
            select(VKUser).filter_by(vk_user_id=user_id))
        vk_user = vk_user.scalar_one_or_none()

        if not vk_user:
            vk_user = VKUser(vk_user_id=user_id)
            session.add(vk_user)
            await session.commit()

        user = await session.execute(
            select(User).filter_by(vk_user=vk_user))
        user = user.scalar_one_or_none()

        if not user:
            user = await session.execute(
                select(User).filter_by(username=username))
            user = user.scalar_one_or_none()
            if not user:
                user = User(username=username, vk_user=vk_user)
                session.add(user)
                await session.commit()
            else:
                user.vk_user = vk_user
                session.add(user)
                await session.commit()

    return vk_user, user


async def get_or_create_user(user_id: int) -> Optional[VKUser]:
    """
    Получает пользователя VK по его идентификатору
    или создает нового, если отсутствует.
    Аргументы:
    - user_id: идентификатор пользователя VK.
    Возвращает объект пользователя VK.
    """
    async with async_session() as session:
        user = await session.execute(
            select(VKUser).filter_by(vk_user_id=user_id))
        user = user.scalar_one_or_none()

        if not user:
            user = VKUser(vk_user_id=user_id)
            session.add(user)
            await session.commit()

    return user


async def process_group(
        user: VKUser, group_data: Dict[str, Any]) -> None:
    """
    Обрабатывает данные о группе VK.
    Аргументы:
    - user: объект пользователя VK.
    - group_data: данные о группе VK в формате JSON.
    """
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


async def create_user_relation(user: VKUser, friend_user: VKUser) -> None:
    """
    Создает связь между двумя пользователями VK.
    Аргументы:
    - user: объект пользователя VK.
    - friend_user: объект другого пользователя VK.
    """
    user_id = user.id
    friend_user_id = friend_user.id

    async with async_session() as session:
        existing_relation = await session.execute(
            select(user_friends).filter(
                and_(
                    user_friends.c.vk_user_id == user_id,
                    user_friends.c.friend_vk_user_id == friend_user_id
                )
            )
        )
        existing_relation = existing_relation.scalar_one_or_none()

        if not existing_relation:
            user_friend_data = {
                'vk_user_id': user_id,
                'friend_vk_user_id': friend_user_id
            }
            await session.execute(
                user_friends.insert().values(user_friend_data))
            await session.commit()

    return None


async def get_user_info(data: Dict[str, Any]) -> None:
    """
    Получает информацию о пользователе VK и его друзьях и группах.
    Аргументы:
    - data: данные о пользователе VK в формате JSON.
    """
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


async def consume() -> None:
    """
    Читает сообщения из Apache Kafka и обрабатывает их.
    Запускает асинхронный процесс чтения сообщений из Kafka
    и вызова функции process_message для обработки полученных данных.
    """
    consumer = AIOKafkaConsumer(
        kafka_topic_consumer,
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


async def start_producer() -> AIOKafkaProducer:
    """
    Запускает Kafka Producer для отправки сообщений в Kafka.
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    return producer


async def send_message_to_kafka(
        producer: AIOKafkaProducer,
        topic: str,
        action: str,
        data: str) -> None:
    """
    Отправляет сообщение в Kafka.
    Аргументы:
    - producer: экземпляр Kafka Producer.
    - topic: тема Kafka, в которую будет отправлено сообщение.
    - action: действие для сообщения.
    - data: данные сообщения.
    """
    await producer.send(topic, value={"action": action, "data": data})


async def stop_producer(producer: AIOKafkaProducer) -> None:
    """
    Останавливает Kafka Producer.
    Аргументы:
    - producer: экземпляр Kafka Producer.
    """
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
