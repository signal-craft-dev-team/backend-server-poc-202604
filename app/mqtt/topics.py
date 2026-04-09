"""MQTT topic helpers."""

# ── CONTROL_SERVER ──────────────────────────────────────────────────────────
_CONTROL_BASE = "signalcraft/control_server"

def control_topic(server_id: str) -> str:
    """Cloud → Edge: 파라미터 제어 명령."""
    return f"{_CONTROL_BASE}/{server_id}"

def control_ack_topic(server_id: str) -> str:
    """Edge → Cloud: 제어 명령 ACK."""
    return f"{_CONTROL_BASE}/{server_id}/ack"


# ── UPLOAD_AUDIO / SEND_URL / COMPLETE_UPLOAD ────────────────────────────────

def upload_audio_topic(server_id: str) -> str:
    """Edge → Cloud: 오디오 업로드 요청."""
    return f"signalcraft/upload_audio/{server_id}"

def send_url_topic(server_id: str) -> str:
    """Cloud → Edge: GCS Presigned URL 전달."""
    return f"signalcraft/send_url/{server_id}"

def complete_upload_topic(server_id: str) -> str:
    """Edge → Cloud: 업로드 완료 알림."""
    return f"signalcraft/complete_upload/{server_id}"

def retry_upload_topic(server_id: str) -> str:
    """Cloud → Edge: 재업로드 요청."""
    return f"signalcraft/retry_upload/{server_id}"


# ── CLOUD INBOUND (Edge → Cloud) ─────────────────────────────────────────────
_CLOUD_BASE = "signalcraft/cloud"

def abnormal_topic(server_id: str) -> str:
    """Edge → Cloud: 비정상 이벤트 / 센서 오프라인."""
    return f"{_CLOUD_BASE}/{server_id}/abnormal"

def disk_alert_topic(server_id: str) -> str:
    """Edge → Cloud: 디스크 용량 경고."""
    return f"{_CLOUD_BASE}/{server_id}/disk_alert"

def upload_failed_topic(server_id: str) -> str:
    """Edge → Cloud: 엣지 측 업로드 실패 알림."""
    return f"{_CLOUD_BASE}/{server_id}/upload_failed"
