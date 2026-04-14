import asyncio
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from google.cloud.sql.connector import Connector

load_dotenv()

INSTANCE_CONNECTION_NAME = os.getenv("SQL_INSTANCE_CONNECTION_NAME")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PWD = os.getenv("DB_PWD")
DB_NAME = os.getenv("DB_NAME", "postgres")

_AsyncSessionLocal = None


async def create_connector() -> Connector:
    # loop 인자를 명시적으로 넘겨야 Connector가 새 루프를 만들지 않고 uvicorn 루프를 사용함
    loop = asyncio.get_running_loop()
    return Connector(loop=loop)


def connect(connector: Connector) -> None:
    global _AsyncSessionLocal

    async def _get_conn():
        return await connector.connect_async(
            INSTANCE_CONNECTION_NAME,
            "asyncpg",
            user=DB_USER,
            password=DB_PWD,
            db=DB_NAME,
        )

    engine = create_async_engine(
        "postgresql+asyncpg://",
        async_creator=_get_conn,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    _AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def disconnect(connector: Connector) -> None:
    await connector.close_async()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if _AsyncSessionLocal is None:
        raise RuntimeError("DB session not initialized — connect() must be called at startup")
    async with _AsyncSessionLocal() as session:
        yield session
