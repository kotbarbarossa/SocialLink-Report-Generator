import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from database import create_entity
from config import kafka_bootstrap_servers, kafka_topic, group_id
from models import User, VKUser, VKGroup


async def process_message(message):
    data = json.loads(message.value)
    logger.info(f'Получены данные {message}.')
    logger.info(f'Преобразованы в {data}.')
    pass


async def create_vk_user(data):
    await create_entity(data, VKUser)


async def create_vk_group(data):
    await create_entity(data, VKGroup)


async def create_user(data):
    await create_entity(data, User)


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
