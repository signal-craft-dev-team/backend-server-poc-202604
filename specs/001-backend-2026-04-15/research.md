# Research: Signal Craft Backend POC

**Branch**: `001-backend-2026-04-15` | **Date**: 2026-04-15

## 1. MQTT 클라이언트 라이브러리

**Decision**: `aiomqtt` (v2.x) 사용

**Rationale**:
- Python async/await 네이티브 지원 — `async with`, `async for` 패턴
- FastAPI의 `lifespan` 컨텍스트 매니저와 자연스럽게 통합
- paho-mqtt 위에서 동작하므로 안정성 확보

**Alternatives considered**:
- `paho-mqtt` (동기 기반 — asyncio와 함께 쓰려면 스레드 격리 필요, 복잡도 증가)
- `gmqtt` (async 지원하나 유지보수 빈도 낮음)

**Usage pattern**:
```python
# lifespan에서 MQTT 클라이언트 기동
async with aiomqtt.Client(host, port, username, password) as client:
    await client.subscribe("signalcraft/#")
    async for message in client.messages:
        await dispatch(message)
```

---

## 2. GCS Signed URL (Presigned URL) 생성

**Decision**: `google-cloud-storage` SDK의 `generate_signed_url` (v4) 사용

**Rationale**:
- GCP VM에 서비스 계정이 직접 연결되어 있으므로 별도 키 파일 불필요
- `google.auth.compute_engine.credentials`를 통해 자동 인증
- v4 서명은 최대 7일까지 유효 (POC에서는 5분 사용)

**Alternatives considered**:
- v2 Signed URL (deprecated, v4로 대체)
- Firebase Storage (불필요한 추가 서비스)

**주의사항**: Compute Engine 기본 서비스 계정은 `iam.serviceAccounts.signBlob` 권한이 필요.
VM 서비스 계정에 `Service Account Token Creator` 역할 부여 필요.

---

## 3. Cloud SQL Async 연결

**Decision**: `cloud-sql-python-connector[asyncpg]` + `SQLAlchemy (async)` 사용

**Rationale**:
- `cloud-sql-python-connector`가 IAM 인증 및 SSL 처리를 자동화
- `asyncpg` 드라이버로 완전 비동기 DB 접근
- SQLAlchemy async session으로 표준 ORM 패턴 유지

**Alternatives considered**:
- 직접 PostgreSQL 연결 (SSL/IAM 설정 수동 관리 필요 — 복잡도 증가)
- `databases` 라이브러리 (SQLAlchemy 없이 raw async — ORM 이점 없음)

**Connection pattern**:
```python
from google.cloud.sql.connector import AsyncConnector

connector = AsyncConnector()
engine = create_async_engine(
    "postgresql+asyncpg://",
    async_creator=connector.connect_async(instance, "asyncpg", user, db)
)
```

---

## 4. MongoDB Async 클라이언트

**Decision**: `motor` (공식 MongoDB async 드라이언트) 사용

**Rationale**:
- MongoDB 공식 지원 async 라이브러리
- asyncio 네이티브 지원
- pymongo와 동일한 API 패턴으로 학습 비용 낮음

**Alternatives considered**:
- `pymongo` (동기 기반 — asyncio에서 executor 필요)
- `beanie` (ODM 추가 레이어 — POC에서 불필요한 추상화)

---

## 5. FastAPI Lifespan + MQTT 통합 패턴

**Decision**: FastAPI `lifespan` 컨텍스트 매니저에서 MQTT 클라이언트와 DB 연결 초기화

**Rationale**:
- `@app.on_event("startup")` deprecated → lifespan 권장
- MQTT 클라이언트를 백그라운드 태스크로 실행하여 메시지 루프 유지
- app.state에 클라이언트 저장으로 핸들러에서 접근 가능

**Pattern**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    mqtt_task = asyncio.create_task(run_mqtt_client(app))
    yield
    # shutdown
    mqtt_task.cancel()
```
