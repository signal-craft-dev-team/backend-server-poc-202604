import asyncio
from datetime import timedelta

import google.auth
import google.auth.transport.requests
from google.cloud import storage

from app.config import settings
from app.utils.timezone import kst_now


def _generate_presigned_url_sync(gcs_path: str) -> tuple[str, str]:
    """동기 함수 — asyncio.to_thread()로 호출한다."""
    credentials, _ = google.auth.default()

    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)

    client = storage.Client(credentials=credentials)
    blob = client.bucket(settings.gcs_bucket_name).blob(gcs_path)

    expiry = timedelta(minutes=settings.gcs_signed_url_expiry_minutes)
    url = blob.generate_signed_url(
        version="v4",
        expiration=expiry,
        method="PUT",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )
    expires_at = (kst_now() + expiry).isoformat()
    return url, expires_at


async def generate_presigned_url(gcs_path: str) -> tuple[str, str]:
    """GCS PUT Presigned URL을 발급한다.

    Returns:
        (presigned_url, expires_at_iso8601)
    """
    return await asyncio.to_thread(_generate_presigned_url_sync, gcs_path)
