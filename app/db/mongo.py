from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings
from app.utils.timezone import kst_now

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


async def insert_error_log(event: str, server_id: str, error: str, attempts: int) -> None:
    doc = {
        "event": event,
        "server_id": server_id,
        "error": error,
        "attempts": attempts,
        "timestamp": kst_now(),
    }
    await get_db()["error_logs"].insert_one(doc)


async def insert_server_status_log(
    server_id: str,
    server_status: str | None = None,
    place_id: str | None = None,
    capture_duration_ms: int | None = None,
    timezone: str | None = None,
    installation_machine: str | None = None,
    upload_interval_ms: int | None = None,
    active_hours_start: str | None = None,
    active_hours_end: str | None = None,
) -> None:
    doc = {
        "server_id": server_id,
        "timestamp": kst_now(),
        "changes": {
            k: v for k, v in {
                "server_status": server_status,
                "place_id": place_id,
                "capture_duration_ms": capture_duration_ms,
                "timezone": timezone,
                "installation_machine": installation_machine,
                "upload_interval_ms": upload_interval_ms,
                "active_hours_start": active_hours_start,
                "active_hours_end": active_hours_end,
            }.items() if v is not None
        },
    }
    await get_db()["server_status_logs"].insert_one(doc)


async def insert_sensor_status_log(
    server_id: str,
    device_name: str | None,
    sensor_type: str | None,
    sensor_position: str | None,
    installation_machine: str | None = None,
) -> None:
    doc = {
        "server_id": server_id,
        "device_name": device_name,
        "sensor_type": sensor_type,
        "sensor_position": sensor_position,
        "installation_machine": installation_machine,
        "timestamp": kst_now(),
    }
    await get_db()["sensor_status_logs"].insert_one(doc)
