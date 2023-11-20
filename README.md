# SocialLink Report Generator

Добро пожаловать в SocialLink Report Generator - ваш инструмент для генерации отчетов на основе данных из социальных сетей.

## О проекте

SocialLink Report Generator - это инструмент для автоматической генерации отчетов по данным из различных социальных сетей, таких как VK, Telegram, Instagram и других. Проект основан на асинхронных методах и микросервисной архитектуре.

### Особенности

- **Множество поддерживаемых социальных сетей:** Мы поддерживаем различные платформы, что позволяет собирать разнообразную информацию.
- **Гибкий генератор отчетов:** Создавайте настраиваемые отчеты с различными параметрами и данными.
- **Асинхронные методы:** Использование асинхронности для эффективного обращения к API социальных сетей и обработки данных.
- **Микросервисная архитектура:** Разделение функционала на отдельные сервисы для улучшения масштабируемости и обслуживаемости.

### Сервисы

- **api_gateway_service:** Принимает имя пользователя через FastAPI.
- **vk_api_service:** Запрашивает информацию у VK API при помощи библиотеки httpx.
- **database_service:** Осуществляет запись и формирование информации для PDF с использованием SQLAlchemy и PostgreSQL.
- **pdf_writer_service:** Создает PDF файл с информацией о пользователе, связанных контактах и их группах, используя библиотеку reportlab.

### Используемые технологии

- **Docker Compose:** Инструмент для определения и запуска многоконтейнерных Docker приложений.
- **PostgreSQL:** Мощная реляционная база данных, используемая для хранения и управления данными в проекте.
- **Kafka:** Распределенная система обмена сообщениями, обеспечивает асинхронную связь между микросервисами.
- **FastAPI (версия 0.104.1):** Легкий и быстрый веб-фреймворк для создания API на Python с поддержкой асинхронности.
- **Asyncio и AnyIO:** Библиотеки для асинхронного программирования, используемые для эффективного управления асинхронными задачами.
- **Aiokafka (версия 0.8.1):** Асинхронный клиент для работы с Apache Kafka, обеспечивает эффективную интеграцию с микросервисами.
- **SQLAlchemy (версия 2.0.23):** Мощный инструмент для работы с базами данных в Python, поддерживает асинхронные запросы и взаимодействие с различными СУБД.
- **Alembic (версия 1.12.1):** Инструмент для управления базой данных в Python, обеспечивает миграции и версионирование структуры БД.
- **Asyncpg (версия 0.29.0):** Асинхронный драйвер PostgreSQL для Python, обеспечивает эффективное взаимодействие с базой данных.
- **Httpx (версия 0.25.1):** Асинхронный HTTP-клиент для Python, предоставляющий удобные средства для выполнения HTTP-запросов.
- **Uvicorn (версия 0.24.0.post1):** ASGI-сервер, предназначенный для запуска и обслуживания веб-приложений на основе ASGI-фреймворков, таких как FastAPI.
- **Pydantic (версия 2.5.0):** Библиотека для валидации данных и создания схем на основе аннотаций типов Python.

Эти технологии обеспечивают эффективное взаимодействие между сервисами, асинхронное выполнение задач, управление базой данных, обработку HTTP-запросов и другие важные аспекты в вашем проекте SocialLink Report Generator.

## Установка и запуск
Для установки проекта выполните клонирование репозитория:

```bash
git clone https://github.com/kotbarbarossa/SocialLink-Report-Generator.git
```

Требуется установить ```Docker```, если он еще не установлен.

В каждой папке микросервисов создайте файл ```.env``` на основе указанных шаблонов:

####  api_gateway_service

```plaintext
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_VK=vk_api_service
KAFKA_TOPIC_INSTAGRAM=instagram_api_service
KAFKA_TOPIC_TELEGRAM=telegram_api_service
KAFKA_GROUP_ID=user_processing_group
```

####  database_service

```plaintext
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres

KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_CONSUMER=database_service
KAFKA_TOPIC_PRODUCER=pdf_writer_service
KAFKA_GROUP_ID=user_processing_group
```

####  pdf_writer_service

```plaintext
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_CONSUMER=pdf_writer_service
KAFKA_GROUP_ID=user_processing_group
```

####  vk_api_service

```plaintext
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_CONSUMER=vk_api_service
KAFKA_TOPIC_PRODUCER=database_service
KAFKA_TOPIC_INSTAGRAM=instagram_api_service
KAFKA_TOPIC_TELEGRAM=telegram_api_service
KAFKA_GROUP_ID=user_processing_group
VK_TOKEN="токен"
```

####  infra

```plaintext
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres

KAFKA_GROUP_ID='user_processing_group'
KAFKA_ADVERTISED_LISTENERS='INSIDE://kafka:9093,OUTSIDE://kafka:9092'
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP='INSIDE:PLAINTEXT,OUTSIDE:PLAINTEXT'
KAFKA_LISTENERS='INSIDE://0.0.0.0:9093,OUTSIDE://0.0.0.0:9092'
KAFKA_INTER_BROKER_LISTENER_NAME='INSIDE'
KAFKA_ZOOKEEPER_CONNECT='zookeeper:2181'
KAFKA_CREATE_TOPICS="vk_api_service:1:1"
```

Запустите сборку образа командой:

```bash
docker-compose up -d
```

После сборки образа выполните миграции. Зайдите в контейнер:

```bash
docker exec -it infra-database_service-1 bash
```

Запустите миграции:

```bash
alembic upgrade head
```

Сервис будет доступен по адресу:

```bash
http://localhost:8000/docs/
```

Для создания отчета отправьте ```POST```-запрос на:

```bash
/post_user/{social_network}/{username}/
```

Используйте параметры:

```json
{
  "social_network": "vk",
  "username": "username"
}
```

PDF файл будет доступен в контейнере ```infra-pdf_writer_service-1```

Для быстрого извлечения файла из контейнера используйте команду:

```bash
docker cp infra-pdf_writer_service-1:/app/имя_файла.pdf /tmp/
```

Где ```/tmp/``` - путь к локальной директории.

Посмотреть имя файла можно используя команды:

```bash
docker exec -it infra-pdf_writer_service-1 bash
ls
```