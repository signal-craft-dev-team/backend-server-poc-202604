# Quickstart: Signal Craft Backend POC

**Branch**: `001-backend-2026-04-15` | **Date**: 2026-04-15

## 사전 요구사항

- Python 3.12
- Docker (로컬 MQTT 브로커 테스트용)
- GCP 서비스 계정 (VM 환경에서는 자동 인증)

## 로컬 환경 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
# .env 파일에 아래 값 입력
```

`.env` 파일 내용:

```env
# MQTT (클라우드 브로커)
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USER=your_mqtt_user
MQTT_PWD=your_mqtt_password

# Cloud SQL
DB_USER=your_db_user
DB_PWD=your_db_password
DB_NAME=signalcraft
SQL_INSTANCE_CONNECTION_NAME=project:region:instance

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=signalcraft

# GCS
GCS_BUCKET_NAME=your_bucket_name
GCS_SIGNED_URL_EXPIRY_MINUTES=5
```

### 3. 로컬 MQTT 브로커 실행 (개발용)

```bash
docker run -d --name mqtt-broker -p 1883:1883 eclipse-mosquitto
```

### 4. 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 동작 검증

### 엣지 서버 등록 테스트 (NEW-001 ~ NEW-002)

MQTT 클라이언트(예: mosquitto_pub)로 등록 요청 발행:

```bash
mosquitto_pub -h localhost -p 1883 \
  -t "signalcraft/edge/edge-server-001/register" \
  -m '{"device_id": "edge-server-001", "location": "공장 1층"}'
```

결과 수신 확인:

```bash
mosquitto_sub -h localhost -p 1883 \
  -t "signalcraft/edge/edge-server-001/register/result"
```

기대 응답:
```json
{"status": "success", "message": null}
```

### 오디오 업로드 URL 요청 테스트 (AUDIO-005 ~ AUDIO-007)

```bash
mosquitto_pub -h localhost -p 1883 \
  -t "signalcraft/edge/edge-server-001/audio/upload/request" \
  -m '{"edge_server_id": "edge-server-001"}'
```

결과 수신:
```bash
mosquitto_sub -h localhost -p 1883 \
  -t "signalcraft/edge/edge-server-001/audio/upload/url"
```

기대 응답:
```json
{
  "presigned_url": "https://storage.googleapis.com/...",
  "gcs_path": "audio/edge-server-001/2026-04-15T00:00:00.wav",
  "expires_at": "2026-04-15T00:05:00Z"
}
```

## 배포 확인

`main` 브랜치 push 후 GitHub Actions에서 자동 빌드 및 GCP VM 배포.
배포 후 VM에서:

```bash
docker logs signalcraft-backend --tail 50
```

정상 기동 로그:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     [MQTT] Connected to broker
INFO:     [MQTT] Subscribed to signalcraft/edge/+/register
...
INFO:     Application startup complete.
```
