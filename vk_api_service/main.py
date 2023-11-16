from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import httpx
import asyncio
from typing import Union, Any
import logging
from config import (kafka_bootstrap_servers, kafka_topic_consumer,
                    group_id, vk_token, kafka_topic_producer)


async def process_message(message):
    data = json.loads(message.value)
    username = data.get('username')
    logger.info(f'Получены данные {message}.')

    if not username:
        logging.error('В сообщении отсутствует username.')
        return

    try:
        user = await get_user_id(username)
        if user is None:
            logging.error('В user ID содержится недопустимое значение.')
            return
        logger.info(f'Получен ответ с пользователем {user}.')

        user_id = user['id']
        logger.info(f'Извелечен id пользователя: {user_id}.')
        friends_ids = await get_user_friends(user_id)
        if friends_ids is None:
            logging.error('В user friends содержится недопустимое значение.')
            return
        logger.info(f'Получен список друзей: {friends_ids}.')

        all_users = friends_ids + [user_id]
        logger.info(
            'Создан список друзей пользователей'
            f' + сам пользователь: {all_users}.')
        producer = await start_producer()

        for user in all_users:
            logger.info(f'Получение групп пользователя: {user}.')
            user_groups = await get_user_groups(user)
            logger.info(f'Получен ответ {user_groups}.')
            if 'error' not in user_groups and user_groups is not None:
                data = {'user': user,
                        'groups': user_groups['response']['items']}
                await send_message_to_kafka(
                    producer,
                    kafka_topic_producer,
                    action='user_groups', data=data)
                logger.info(f'Отпарлено сообщение {data}.')
            else:
                data = {'user': user,
                        'groups': []}
                await send_message_to_kafka(
                    producer,
                    kafka_topic_producer,
                    action='user_groups', data=data)
                logger.info(f'Отпарлено сообщение {data}.')

        data = {user_id: friends_ids}
        await send_message_to_kafka(
            producer,
            kafka_topic_producer,
            action='user_friends', data=data)
        logger.info(f'Отпарлено сообщение cо списком друзей {data}.')

    except Exception as e:
        logging.error(f'Ошибка отправки сообщений: {e}.')


async def get_response(url: str) -> Union[dict, Any]:
    """Получение ответа от стороннего API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            return response.json()
    except httpx.RequestError as e:
        logging.error('Ошибка при выполнении HTTP-запроса: %s', e)
        return None
    except httpx.HTTPStatusError as e:
        logging.error('Ошибка HTTP-статуса: %s', e)
        return None


async def get_user_id(username):
    try:
        url = ('https://api.vk.com/method/'
               f'users.get?user_ids={username}&'
               'v=5.131&'
               f'access_token={vk_token}')
        response = await get_response(url=url)
        return response['response'][0]
    except Exception as e:
        logging.error('Ошибка получения user ID: %s', e)
        return None


async def get_user_friends(user_id):
    try:
        url = ('https://api.vk.com/method/'
               f'friends.get?user_id={user_id}&'
               'v=5.131&'
               f'access_token={vk_token}')
        response = await get_response(url=url)
        return response['response']['items']
    except Exception as e:
        logging.error('Ошибка получения user friends: %s', e)
        return None


async def get_user_groups(user_id):
    try:
        url = ('https://api.vk.com/method/'
               f'groups.get?user_id={user_id}&'
               'extended=1&'
               'v=5.131&'
               f'access_token={vk_token}')
        return await get_response(url=url)
    except Exception as e:
        logging.error('Ошибка получения user groups: %s', e)
        return None


async def consume():
    try:
        consumer = AIOKafkaConsumer(
            kafka_topic_consumer,
            bootstrap_servers=kafka_bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=True,
            auto_offset_reset='earliest'
        )
        await consumer.start()

        async for message in consumer:
            try:
                await process_message(message)
            except Exception as e:
                logging.error(f'Ошибка обработки сообщения: {e}')
    except Exception as e:
        logging.error(f'Ошибка консьюмера: {e}')
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

    logger = logging.getLogger('vk_api_service_logger')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('vk_api_service.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    asyncio.run(consume())
