"""GCS 클라이언트 — Presigned URL 생성 및 파일 존재 여부 확인.

인증: Application Default Credentials (ADC) 사용.
  - VM(GCE) / Cloud Run: 서비스 계정 자동 인식
  - 로컬: GOOGLE_APPLICATION_CREDENTIALS 환경변수로 서비스 계정 키 경로 지정

GCE 환경에서는 Compute Engine credentials가 sign_bytes를 직접 지원하지 않으므로
access_token 방식으로 Signed URL을 생성합니다.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import google.auth
import google.auth.transport.requests
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

logger = logging.getLogger(__name__)

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "signalcraft-audio")
GCS_SIGNED_URL_EXPIRY_MINUTES = int(os.getenv("GCS_SIGNED_URL_EXPIRY_MINUTES", "5"))


def _get_refreshed_credentials():
    """ADC로 credentials를 가져온 후 access token을 갱신."""
    credentials, _ = google.auth.default()
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials


def generate_presigned_url(file_name: str) -> tuple[str, datetime]:
    """GCS PUT Signed URL 생성. blocking — asyncio.to_thread로 호출할 것.

    GCE/Cloud Run 환경에서는 service_account_email + access_token 방식 사용.
    로컬(키 파일)에서는 credentials 자체로 서명.
    """
    credentials = _get_refreshed_credentials()
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(file_name)

    expiry = timedelta(minutes=GCS_SIGNED_URL_EXPIRY_MINUTES)
    expires_at = datetime.now(timezone.utc) + expiry

    url = blob.generate_signed_url(
        version="v4",
        expiration=expiry,
        method="PUT",
        content_type="audio/wav",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )
    return url, expires_at


def check_file_exists(file_name: str) -> bool:
    """GCS에 파일이 존재하는지 확인. blocking — asyncio.to_thread로 호출할 것."""
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(file_name)
    return blob.exists()
