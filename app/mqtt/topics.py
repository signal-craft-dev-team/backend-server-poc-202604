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
