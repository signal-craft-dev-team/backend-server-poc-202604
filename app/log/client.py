"""MongoDB AsyncIOMotorClient 싱글톤."""
import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None


def get_db() -> AsyncIOMotorDatabase:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    return _client[os.environ["MONGODB_DB_NAME"]]
