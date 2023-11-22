from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel, Field, validator
from aiokafka import AIOKafkaProducer
import logging
import uvicorn
import json

from config import (
    kafka_bootstrap_servers,
    kafka_topic_vk,
    kafka_topic_instagram,
    kafka_topic_telegram
    )

TOPIC = {
    'vk': kafka_topic_vk,
    'telegram': kafka_topic_telegram,
    'instagram': kafka_topic_instagram,
    }

app = FastAPI(
    title='Event-Explorer-Backend',
    debug=True
)


class PostUserRequest(BaseModel):
    """Валидация запроса post_user."""
    name: str = Field(max_length=100)
    social_network: str = Field(max_length=50)
    username: str = Field(max_length=250)

    @validator('social_network')
    def validate_social_network(cls, v: str) -> str:
        allowed_social_networks = {'vk', 'telegram', 'instagram'}
        if v.lower() not in allowed_social_networks:
            raise ValueError('Invalid social network')
        return v.lower()


@app.post('/post_user/{name}/{social_network}/{username}/', tags=['post_user'])
async def get_user_info(request: PostUserRequest) -> Union[dict, str]:
    """Функция добавления информации о пользователе."""
    name = request.name
    social_network = request.social_network
    username = request.username

    data = {
        'username': username,
        'name': name
    }

    producer = await start_producer()
    await send_message_to_kafka(producer, TOPIC[social_network], data)
    await stop_producer(producer)
    logger.info(f'Отправлено сообщение {data}.')

    return {'message': f'Added {social_network} - {username} for {name}.'}


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
        data: dict) -> None:
    """
    Отправляет сообщение в Kafka.
    Аргументы:
    - producer: экземпляр Kafka Producer.
    - topic: тема Kafka, в которую будет отправлено сообщение.
    - action: действие для сообщения.
    - data: данные сообщения.
    """
    await producer.send(topic, value=data)


async def stop_producer(producer: AIOKafkaProducer) -> None:
    """
    Останавливает Kafka Producer.
    Аргументы:
    - producer: экземпляр Kafka Producer.
    """
    await producer.stop()


if __name__ == '__main__':

    logger = logging.getLogger('api_gateway_service')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('api_gateway_service.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    uvicorn.run(app, host="0.0.0.0", port=8000)
