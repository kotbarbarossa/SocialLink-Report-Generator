from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

DB_URL = (
    'postgresql+asyncpg://'
    f'{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

engine = create_async_engine(DB_URL)

async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession)
