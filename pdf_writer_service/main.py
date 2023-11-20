from aiokafka import AIOKafkaConsumer
import json
import asyncio
import logging
from typing import Any, Dict, List
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from config import (kafka_bootstrap_servers, kafka_topic_consumer,
                    group_id)


async def process_message(message: Any) -> None:
    """
    Обрабатывает полученное сообщение из Apache Kafka.
    Аргументы:
    - message: сообщение из Kafka.
    Преобразует данные из сообщения в формат JSON,
    и вызывает функцию write_pdf с этими данными.
    """
    json_data = json.loads(message.value)
    data = json_data['data']
    logger.info(f'\nПолучены данные {message}.')
    await write_pdf(data)


async def write_pdf(data: Dict[str, Any]) -> None:
    """
    Создает PDF-файл на основе полученных данных.
    Аргументы:
    - data: данные из Kafka.
    Готовит и форматирует данные для создания PDF-файла,
    содержащего информацию о пользователе из Kafka.
    """
    username = data.get('username')

    logger.info(
        '\nПодготовка данных для PDF.'
        f'\nПользователь: {data.get("username")}.'
        f'\nVK id: {data.get("vk_user_id")}.'
        f'\nСписок друзей VK: {data.get("friends_ids")[:100]}...'
        f'\nСписок групп друзей VK: {data.get("group_names")[:100]}...'
        )

    pdf_filename = f'{username}.pdf'
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)

    styles = getSampleStyleSheet()

    pdfmetrics.registerFont(
        TTFont('CascadiaCode',
               '/usr/share/fonts/truetype/CascadiaCode/ttf/CascadiaCode.ttf'))
    styles['Normal'].fontName = 'CascadiaCode'

    flowables: List = []

    for key, value in data.items():
        logger.info(f'key = {key}')
        logger.info(f'value = {type(value)}')
        if key == 'group_names':
            value = json.loads(value)
            p = Paragraph(
                f'Общее количество групп: {len(value)}',
                styles['Normal'])
            flowables.append(p)
            p = Paragraph('Group names:', styles['Normal'])
            flowables.append(p)
            for index, group in enumerate(value, start=1):
                text = f"{index}. {group['name']}"
                p = Paragraph(text, styles['Normal'])
                flowables.append(p)
        elif key == 'friends_ids':
            value = json.loads(value)
            p = Paragraph(
                f'Общее количество друзей: {len(value)}',
                styles['Normal'])
            flowables.append(p)
            text = (f'{key.capitalize()}: '
                    f'{", ".join(str(item["id"]) for item in value)}')
            p = Paragraph(text, styles['Normal'])
            flowables.append(p)
        else:
            p = Paragraph(f'{key.capitalize()}: {value}', styles['Normal'])
            flowables.append(p)

    doc.build(flowables)
    logger.info(f'Файл {pdf_filename} сохранен.')


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


if __name__ == '__main__':
    logger = logging.getLogger('pdf_writer_service_logger')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('pdf_writer_service.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    asyncio.run(consume())
