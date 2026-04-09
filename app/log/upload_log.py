"""MongoDB 로그 기록 함수.

컬렉션:
  - audio_upload_logs : 오디오 업로드 완료/추론 로그
  - upload_error_logs : 업로드 에러 로그
  - server_comm_logs  : 서버 통신 로그
  - sensor_comm_logs  : 센서 통신 로그
"""
import logging

from app.log.client import get_db
from app.log.models import AudioUploadLog, SensorCommLog, ServerCommLog, UploadErrorLog

logger = logging.getLogger(__name__)

_AUDIO_UPLOAD_COLLECTION = "audio_upload_logs"
_ERROR_COLLECTION = "upload_error_logs"
_SERVER_COMM_COLLECTION = "server_comm_logs"
_SENSOR_COMM_COLLECTION = "sensor_comm_logs"


async def write_audio_upload_log(log: AudioUploadLog) -> None:
    """오디오 업로드 완료 로그 기록 (정상 및 추론)."""
    try:
        await get_db()[_AUDIO_UPLOAD_COLLECTION].insert_one(log.model_dump())
        logger.info(f"[Log] audio_upload saved | file={log.file_name} inferred={log.inferred}")
    except Exception as exc:
        logger.error(f"[Log] failed to save audio_upload log | file={log.file_name} error={exc}")


async def write_error_log(log: UploadErrorLog) -> None:
    """업로드 에러 로그 기록."""
    try:
        await get_db()[_ERROR_COLLECTION].insert_one(log.model_dump())
        logger.error(f"[Log] error saved | reason={log.reason}")
    except Exception as exc:
        logger.error(f"[Log] failed to save error log | reason={log.reason} error={exc}")


async def write_server_comm_log(log: ServerCommLog) -> None:
    """서버 통신 로그 기록."""
    try:
        await get_db()[_SERVER_COMM_COLLECTION].insert_one(log.model_dump())
        logger.info(f"[Log] server_comm saved | server={log.server_id} event={log.event_type}")
    except Exception as exc:
        logger.error(f"[Log] failed to save server_comm log | server={log.server_id} error={exc}")


async def write_sensor_comm_log(log: SensorCommLog) -> None:
    """센서 통신 로그 기록."""
    try:
        await get_db()[_SENSOR_COMM_COLLECTION].insert_one(log.model_dump())
        logger.info(f"[Log] sensor_comm saved | sensor={log.sensor_id} event={log.event_type}")
    except Exception as exc:
        logger.error(f"[Log] failed to save sensor_comm log | sensor={log.sensor_id} error={exc}")
