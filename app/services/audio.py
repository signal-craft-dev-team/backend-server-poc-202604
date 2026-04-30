from sqlalchemy import select

from app.db.mongo import insert_audio_upload_log, update_audio_upload_log
from app.db.sql import AsyncSessionFactory
from app.models.edge_server import EdgeServer
from app.storage.gcs import generate_presigned_url
from app.utils.timezone import kst_now


async def issue_presigned_url(server_id: str) -> tuple[str, str, str]:
    """GCS 경로 생성 → Presigned URL 발급 → audio_upload_logs pending 저장.

    Returns:
        (gcs_path, presigned_url, expires_at)
    """
    now = kst_now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    gcs_path = f"{server_id}/{date_str}/{timestamp_str}.wav"

    presigned_url, expires_at = await generate_presigned_url(gcs_path)
    await insert_audio_upload_log(server_id=server_id, gcs_path=gcs_path)

    return gcs_path, presigned_url, expires_at


async def check_upload_anomaly(server_id: str) -> bool:
    """가동 시간 중 업로드 누락 여부를 확인한다.

    active_hours 내에서 마지막 success 업로드 이후
    3 × upload_interval_ms 이상 경과했으면 True 반환.
    """
    from app.db.mongo import get_db  # noqa: PLC0415

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(EdgeServer).where(EdgeServer.server_id == server_id)
        )
        server = result.scalar_one_or_none()

    if server is None or server.upload_interval_ms is None:
        return False

    now = kst_now()
    current_time = now.strftime("%H:%M")

    in_active_hours = (
        server.active_hours_start is not None
        and server.active_hours_end is not None
        and server.active_hours_start <= current_time <= server.active_hours_end
    )
    if not in_active_hours:
        return False

    last_record = await get_db()["audio_upload_logs"].find_one(
        {"server_id": server_id, "status": "success"},
        sort=[("upload_completed_at", -1)],
    )
    if last_record is None:
        return False

    last_upload_at = last_record["upload_completed_at"]
    elapsed_ms = (now - last_upload_at).total_seconds() * 1000
    return elapsed_ms > 3 * server.upload_interval_ms


async def record_upload_result(
    server_id: str,
    status: str,
    sensor_map: dict[str, str],
    message: str | None = None,
) -> None:
    """업로드 결과를 audio_upload_logs에 기록한다.

    엣지가 gcs_path를 반환하지 않으므로 server_id로 최신 pending 문서를 조회한다.
    """
    from app.db.mongo import get_db  # noqa: PLC0415

    record = await get_db()["audio_upload_logs"].find_one(
        {"server_id": server_id, "status": "pending"},
        sort=[("presigned_url_issued_at", -1)],
    )
    if record is None:
        raise ValueError(f"No pending upload log found for server_id={server_id}")

    await update_audio_upload_log(
        gcs_path=record["gcs_path"],
        status=status,
        sensor_map=sensor_map,
        message=message,
    )
