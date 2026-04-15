from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("MongoDB client is not initialized")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_db_name]


def connect() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_uri)


def disconnect() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
