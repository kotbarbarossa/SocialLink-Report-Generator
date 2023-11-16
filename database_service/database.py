from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
import asyncpg

DB_URL = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


async def create_entity(data, table):
    connection = await asyncpg.connect(dsn=DB_URL)
    try:
        await connection.execute(table.__table__.insert().values(data))
    finally:
        await connection.close()
