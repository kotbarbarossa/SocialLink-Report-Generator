from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import httpx
import asyncio
from typing import Union, Any
import logging
from config import (kafka_bootstrap_servers, kafka_topic_consumer,
                    group_id, vk_token, kafka_topic_producer)


async def process_message(message: Any) -> None:
    """
    Обрабатывает полученное сообщение из Apache Kafka.
    Аргументы:
    - message: сообщение из Kafka.
    Преобразует данные из сообщения в формат JSON
    и обрабатывает данные, отправляя сообщения в Kafka.
    """
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

        user_id = user.get('id')
        if user_id is None:
            logging.error('ID пользователя не найден.')
            return

        logger.info(f'Извлечен id пользователя: {user_id}.')

        friends_ids = await get_user_friends(user_id)
        if friends_ids is None:
            logging.error('В user friends содержится недопустимое значение.')
            return

        logger.info(f'Получен список друзей: {friends_ids}.')

        all_users = friends_ids + [user_id]
        logger.info(
            f'Создан список друзей пользователей '
            f'+ сам пользователь: {all_users}.'
        )

        producer = await start_producer()

        for user in all_users:
            logger.info(f'Получение групп пользователя: {user}.')
            user_groups = await get_user_groups(user)
            logger.info(f'Получен ответ {user_groups}.')

            if user_groups is not None and 'error' not in user_groups:
                data = {
                    'user': user,
                    'groups': user_groups['response']['items']
                    }
            else:
                data = {'user': user, 'groups': []}

            await send_message_to_kafka(
                producer,
                kafka_topic_producer,
                action='user_groups',
                data=data)
            logger.info(f'Отправлено сообщение {data}.')

        data = {user_id: friends_ids}
        await send_message_to_kafka(
            producer,
            kafka_topic_producer,
            action='user_friends',
            data=data)
        logger.info(f'Отправлено сообщение со списком друзей {data}.')

    except Exception as e:
        logging.error(f'Ошибка отправки сообщений: {e}.')


async def get_response(url: str) -> Union[dict, Any]:
    """
    Получает ответ от стороннего API.
    Аргументы:
    - url: URL для запроса.
    Возвращает ответ в формате JSON или None при ошибке запроса.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            return response.json()
    except httpx.RequestError as e:
        logging.error(f'Ошибка при выполнении HTTP-запроса: {e}')
        return None
    except httpx.HTTPStatusError as e:
        logging.error(f'Ошибка HTTP-статуса: {e}')
        return None


async def get_user_id(username: str) -> Union[str, None]:
    """
    Получает идентификатор пользователя
    по его имени пользователя в социальной сети.
    Аргументы:
    - username: имя пользователя в социальной сети.
    Возвращает идентификатор пользователя или None при ошибке запроса.
    """
    try:
        url = ('https://api.vk.com/method/'
               f'users.get?user_ids={username}&'
               'v=5.131&'
               f'access_token={vk_token}')
        response = await get_response(url=url)
        return response['response'][0]
    except Exception as e:
        logging.error(f'Ошибка получения user ID: {e}')
        return None


async def get_user_friends(user_id: str) -> Union[list, None]:
    """
    Получает список друзей пользователя
    по его идентификатору в социальной сети.
    Аргументы:
    - user_id: идентификатор пользователя в социальной сети.
    Возвращает список друзей пользователя или None при ошибке запроса.
    """
    try:
        url = ('https://api.vk.com/method/'
               f'friends.get?user_id={user_id}&'
               'v=5.131&'
               f'access_token={vk_token}')
        response = await get_response(url=url)
        return response['response']['items']
    except Exception as e:
        logging.error(f'Ошибка получения user friends: {e}')
        return None


async def get_user_groups(user_id: str) -> Union[dict, None]:
    """
    Получает группы пользователя
    по его идентификатору в социальной сети.
    Аргументы:
    - user_id: идентификатор пользователя в социальной сети.
    Возвращает список групп пользователя или None при ошибке запроса.
    """
    try:
        url = ('https://api.vk.com/method/'
               f'groups.get?user_id={user_id}&'
               'extended=1&'
               'v=5.131&'
               f'access_token={vk_token}')
        return await get_response(url=url)
    except Exception as e:
        logging.error(f'Ошибка получения user groups: {e}')
        return None


async def consume() -> None:
    """
    Читает сообщения из Apache Kafka и обрабатывает их.
    Запускает асинхронный процесс чтения сообщений из Kafka
    и вызова функции process_message для обработки полученных данных.
    """
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

    logger = logging.getLogger('vk_api_service_logger')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('vk_api_service.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    asyncio.run(consume())
