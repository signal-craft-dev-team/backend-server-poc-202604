from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

connector = Connector()


async def _get_conn():
    return await connector.connect_async(
        settings.sql_instance_connection_name,
        "asyncpg",
        user=settings.db_user,
        password=settings.db_pwd,
        db=settings.db_name,
    )


engine = create_async_engine(
    "postgresql+asyncpg://",
    async_creator=_get_conn,
    echo=False,
)

AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_engine() -> None:
    await engine.dispose()
    await connector.close_async()
