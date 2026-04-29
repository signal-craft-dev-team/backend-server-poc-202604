from sqlalchemy import select

from app.db.mongo import insert_server_status_log
from app.db.sql import AsyncSessionFactory
from app.models.edge_sensor import EdgeSensor, SensorType
from app.models.edge_server import EdgeServer, EdgeServerStatus
from app.utils.timezone import kst_now


async def register_edge_server(server_id: str, timezone: str | None, installation_machine: str | None) -> EdgeServer:
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(EdgeServer).where(EdgeServer.server_id == server_id)
        )
        server = result.scalar_one_or_none()

        if server is None:
            server = EdgeServer(
                server_id=server_id,
                server_status=EdgeServerStatus.ONLINE,
                timezone=timezone,
                installation_machine=installation_machine,
                capture_duration_ms=5000,
                upload_interval_ms=1000 * 60,  # 1분
                created_at=kst_now(),
                updated_at=kst_now(),
                active_hours_start="00:00",
                active_hours_end="23:59",
            )
            session.add(server)
            await session.commit()
            await insert_server_status_log(server_id=server_id, server_status=EdgeServerStatus.ONLINE.value)
        else:
            prev_status = server.server_status
            server.server_status = EdgeServerStatus.ONLINE
            server.updated_at = kst_now()
            await session.commit()
            if prev_status != EdgeServerStatus.ONLINE:
                await insert_server_status_log(server_id=server_id, server_status=EdgeServerStatus.ONLINE.value)

        return server


async def register_edge_sensor(
    server_id_str: str,
    device_name: str | None,
    sensor_type: str | None,
    sensor_position: str | None,
    installation_machine: str | None = None,
) -> EdgeSensor:
    async with AsyncSessionFactory() as session:
        server_result = await session.execute(
            select(EdgeServer).where(EdgeServer.server_id == server_id_str)
        )
        server = server_result.scalar_one_or_none()
        if server is None:
            raise ValueError(f"Server not registered: {server_id_str}")

        sensor_result = await session.execute(
            select(EdgeSensor).where(
                EdgeSensor.edge_server_id == server.id,
                EdgeSensor.device_name == device_name,
            )
        )
        sensor = sensor_result.scalar_one_or_none()

        if sensor is None:
            sensor = EdgeSensor(
                edge_server_id=server.id,
                device_name=device_name,
                sensor_type=SensorType(sensor_type.upper()) if sensor_type else None,
                sensor_position=sensor_position,
                installation_machine=installation_machine,
                created_at=kst_now(),
                updated_at=kst_now(),
            )
            session.add(sensor)
        else:
            if sensor_position is not None:
                sensor.sensor_position = sensor_position
            sensor.updated_at = kst_now()

        await session.commit()
        return sensor
    