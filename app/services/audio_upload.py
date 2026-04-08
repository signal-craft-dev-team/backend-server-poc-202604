"""UPLOAD_AUDIO 수신 시 전체 업로드 플로우를 처리하는 서비스.

흐름:
  1. UPLOAD_AUDIO 수신 (subscriber → upload_manager.schedule 경유)
  2. GCS Presigned URL 생성 (최대 3회 재시도)
     └─ 전체 실패 → 에러 로그 기록 후 종료
  3. SEND_URL MQTT 발행
  4. COMPLETE_UPLOAD 대기 (30초 타임아웃)
     ├─ 수신 성공 → Firestore 업로드 로그 기록
     └─ 타임아웃 → GCS 파일 존재 여부 확인
         ├─ 존재 → Firestore 로그 기록 (업로드는 완료된 것으로 간주)
         └─ 없음 → retry_upload MQTT 발행
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.gcs.client import check_file_exists, generate_presigned_url
from app.mqtt.publisher import publish
from app.mqtt.schemas import (
    CompleteUploadMessage,
    RetryUploadMessage,
    SendUrlMessage,
    UploadAudioMessage,
)
from app.mqtt.state import get_client
from app.mqtt.topics import retry_upload_topic, send_url_topic
from app.mqtt.upload_manager import upload_manager

logger = logging.getLogger(__name__)

COMPLETE_UPLOAD_TIMEOUT_SEC = 30
GCS_URL_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Firestore / 에러 DB pseudo-code
# ---------------------------------------------------------------------------

async def _write_firestore_upload_log(msg: CompleteUploadMessage) -> None:
    """TODO: Firestore에 업로드 완료 로그 기록.

    예시 문서 구조 (collection: audio_upload_logs):
    {
        "server_id": msg.server_id,
        "sensor_id": msg.sensor_id,
        "file_name": msg.file_name,
        "recorded_at": msg.recorded_at,
        "duration_ms": msg.duration_ms,
        "file_size_bytes": msg.file_size_bytes,
        "uploaded_at": msg.timestamp,
        "created_at": datetime.now(timezone.utc),
    }
    """
    logger.info(f"[Firestore] upload log (pseudo) | file={msg.file_name}")


async def _write_firestore_log_inferred(msg: UploadAudioMessage) -> None:
    """타임아웃 후 GCS에서 파일 확인됐을 때 UPLOAD_AUDIO 정보로 로그 기록.

    TODO: Firestore에 업로드 로그 기록 (COMPLETE_UPLOAD 없이 추론된 완료).
    """
    logger.info(f"[Firestore] inferred upload log (pseudo) | file={msg.file_name}")


async def _write_error_log(context: dict, reason: str) -> None:
    """TODO: 에러 DB(Firestore 별도 컬렉션 또는 Cloud Logging)에 장애 로그 기록.

    예시 문서 구조 (collection: upload_error_logs):
    {
        "server_id": context.get("server_id"),
        "file_name": context.get("file_name"),
        "reason": reason,
        "occurred_at": datetime.now(timezone.utc),
    }
    """
    logger.error(f"[ErrorLog] upload error (pseudo) | reason={reason} context={context}")


# ---------------------------------------------------------------------------
# 메인 핸들러
# ---------------------------------------------------------------------------

async def handle_upload_audio(payload: dict) -> None:
    """UPLOAD_AUDIO 수신 시 진입점. upload_manager.schedule()로 asyncio 루프에서 실행."""
    try:
        msg = UploadAudioMessage(**payload)
    except Exception as exc:
        logger.error(f"[AudioUpload] invalid UPLOAD_AUDIO payload | error={exc}")
        return

    logger.info(f"[AudioUpload] received | server={msg.server_id} file={msg.file_name}")

    # 1. GCS Presigned URL 생성 (최대 3회 재시도)
    signed_url = None
    expires_at = None
    for attempt in range(1, GCS_URL_MAX_RETRIES + 1):
        try:
            signed_url, expires_at = await asyncio.to_thread(
                generate_presigned_url, msg.file_name
            )
            logger.info(f"[AudioUpload] presigned URL generated | attempt={attempt}")
            break
        except Exception as exc:
            logger.warning(f"[AudioUpload] presigned URL failed | attempt={attempt} error={exc}")
            if attempt < GCS_URL_MAX_RETRIES:
                await asyncio.sleep(2 ** (attempt - 1))  # 1s, 2s

    if signed_url is None:
        await _write_error_log(
            {"server_id": msg.server_id, "file_name": msg.file_name},
            reason=f"Presigned URL 생성 {GCS_URL_MAX_RETRIES}회 모두 실패",
        )
        return

    # 2. SEND_URL 발행
    client = get_client()
    if client is None:
        logger.error("[AudioUpload] MQTT client unavailable — cannot send SEND_URL")
        return

    # 3. COMPLETE_UPLOAD 대기 큐를 publish 전에 등록 (race condition 방지)
    #    publish 이후 등록하면 paho 스레드가 COMPLETE_UPLOAD를 먼저 수신할 수 있음
    complete_queue = upload_manager.register(msg.file_name)

    send_url_msg = SendUrlMessage(
        server_id=msg.server_id,
        file_name=msg.file_name,
        signed_url=signed_url,
        expires_at=expires_at,
        timestamp=datetime.now(timezone.utc),
    )
    try:
        publish(client, send_url_topic(msg.server_id), send_url_msg.model_dump_json())
    except Exception as exc:
        upload_manager.unregister(msg.file_name)
        logger.error(f"[AudioUpload] SEND_URL publish failed | error={exc}")
        return
    try:
        complete_payload = await asyncio.wait_for(
            complete_queue.get(), timeout=COMPLETE_UPLOAD_TIMEOUT_SEC
        )
        complete_msg = CompleteUploadMessage(**complete_payload)
        logger.info(f"[AudioUpload] COMPLETE_UPLOAD received | file={msg.file_name}")

        # 4a. Firestore 로그 기록
        await _write_firestore_upload_log(complete_msg)

    except asyncio.TimeoutError:
        logger.warning(
            f"[AudioUpload] COMPLETE_UPLOAD timeout ({COMPLETE_UPLOAD_TIMEOUT_SEC}s) "
            f"| file={msg.file_name}"
        )
        await _handle_complete_timeout(msg, client)

    finally:
        upload_manager.unregister(msg.file_name)


async def _handle_complete_timeout(msg: UploadAudioMessage, client) -> None:
    """COMPLETE_UPLOAD 타임아웃 처리: GCS 확인 → 로그 기록 또는 재업로드 요청."""
    try:
        file_exists = await asyncio.to_thread(check_file_exists, msg.file_name)
    except Exception as exc:
        logger.error(f"[AudioUpload] GCS existence check failed | error={exc}")
        await _write_error_log(
            {"server_id": msg.server_id, "file_name": msg.file_name},
            reason=f"COMPLETE_UPLOAD 타임아웃 후 GCS 확인 실패: {exc}",
        )
        return

    if file_exists:
        logger.info(f"[AudioUpload] file found in GCS after timeout | file={msg.file_name}")
        await _write_firestore_log_inferred(msg)
    else:
        logger.warning(f"[AudioUpload] file not in GCS — requesting re-upload | file={msg.file_name}")
        retry_msg = RetryUploadMessage(
            server_id=msg.server_id,
            file_name=msg.file_name,
            reason="COMPLETE_UPLOAD timeout and file not found in storage",
            timestamp=datetime.now(timezone.utc),
        )
        try:
            publish(client, retry_upload_topic(msg.server_id), retry_msg.model_dump_json())
        except Exception as exc:
            logger.error(f"[AudioUpload] retry_upload publish failed | error={exc}")
            await _write_error_log(
                {"server_id": msg.server_id, "file_name": msg.file_name},
                reason=f"재업로드 요청 발행 실패: {exc}",
            )
