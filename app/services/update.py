import uuid

from sqlalchemy import select
from enum import Enum

from app.db.mongo import insert_sensor_status_log, insert_server_status_log
from app.db.sql import AsyncSessionFactory
from app.models.edge_sensor import EdgeSensor, SensorType
from app.models.edge_server import EdgeServer, EdgeServerStatus
from app.utils.timezone import kst_now

def _to_log_value(v: object) -> int | str | None:
    if v is None:
        return None
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, uuid.UUID):
        return str(v)
    return v

async def update_edge_server(
    server_id: str,
    *,
    place_id: uuid.UUID | None = None,
    server_status: EdgeServerStatus | None = None,
    capture_duration_ms: int | None = None,
    timezone: str | None = None,
    installation_machine: str | None = None,
    upload_interval_ms: int | None = None,
    active_hours_start: str | None = None,
    active_hours_end: str | None = None,
) -> EdgeServer | None:
    """EdgeServer 설정을 업데이트한다.

    기존 값이 이미 있는 필드는 변경하지 않는다.
    변경된 필드가 하나라도 있으면 updated_at을 갱신한다.
    """
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(EdgeServer).where(EdgeServer.server_id == server_id)
        )
        server = result.scalar_one_or_none()
        if server is None:
            return None

        candidates = {
            "place_id": place_id,
            "server_status": server_status,
            "capture_duration_ms": capture_duration_ms,
            "timezone": timezone,
            "installation_machine": installation_machine,
            "upload_interval_ms": upload_interval_ms,
            "active_hours_start": active_hours_start,
            "active_hours_end": active_hours_end,
        }

        actual_changes: dict = {}
        for field, value in candidates.items():
            if value is not None and getattr(server, field) != value:
                setattr(server, field, value)
                actual_changes[field] = value

        if actual_changes:
            server.updated_at = kst_now()
            await session.commit()
            await insert_server_status_log(
                server_id=server_id,
                **{k: _to_log_value(v) for k, v in actual_changes.items()},
            )

        return server


async def update_edge_sensor(
    server_id: str,
    device_name: str,
    *,
    sensor_type: SensorType | None = None,
    sensor_position: str | None = None,
    installation_machine: str | None = None,
) -> EdgeSensor | None:
    async with AsyncSessionFactory() as session:
        server_result = await session.execute(
            select(EdgeServer).where(EdgeServer.server_id == server_id)
        )
        server = server_result.scalar_one_or_none()
        if server is None:
            return None

        sensor_result = await session.execute(
            select(EdgeSensor).where(
                EdgeSensor.edge_server_id == server.id,
                EdgeSensor.device_name == device_name,
            )
        )
        sensor = sensor_result.scalar_one_or_none()
        if sensor is None:
            return None

        candidates = {
            "sensor_type": sensor_type,
            "sensor_position": sensor_position,
            "installation_machine": installation_machine,
        }

        actual_changes: dict = {}
        for field, value in candidates.items():
            if value is not None and getattr(sensor, field) != value:
                setattr(sensor, field, value)
                actual_changes[field] = value

        if actual_changes:
            sensor.updated_at = kst_now()
            await session.commit()
            await insert_sensor_status_log(
                server_id=server_id,
                device_name=device_name,
                sensor_type=_to_log_value(sensor.sensor_type),
                sensor_position=sensor.sensor_position,
                installation_machine=sensor.installation_machine,
            )

        return sensor
