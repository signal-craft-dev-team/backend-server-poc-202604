---
description: "Task list for Signal Craft Backend POC implementation"
---

# Tasks: Signal Craft Backend POC

**Input**: Design documents from `specs/001-backend-2026-04-15/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/mqtt-topics.md ✅, research.md ✅

**Organization**: Tasks are grouped by phase. Phase 3+ will be defined incrementally.

---

## Phase 1: Setup

**Purpose**: 의존성 및 프로젝트 초기 구조 준비

- [x] T001 `requirements.txt`에 전체 의존성 추가: `aiomqtt`, `google-cloud-storage`, `cloud-sql-python-connector[asyncpg]`, `sqlalchemy[asyncio]`, `asyncpg`, `motor`, `pydantic-settings`, `python-dotenv`

---

## Phase 2: Completed — 인프라 및 기본 통신 구성

**Purpose**: 핵심 인프라 + MQTT 통신 기반 + DB 모델 + 핸들러 스켈레톤까지 구현 완료

**Checkpoint ✅**: DB 연결, MQTT 브로커 연결/구독(6개 토픽), `/health` 엔드포인트, 핸들러 dispatch 등록 모두 확인 완료 (2026-04-23)

### 환경 설정 및 DB 연결

- [x] T002 `app/config.py` 생성 — `pydantic-settings BaseSettings`로 환경변수 정의 (MQTT, DB, GCS)
- [x] T003 [P] `app/db/sql.py` 생성 — Cloud SQL Connector + asyncpg + SQLAlchemy async 엔진/세션 팩토리
- [x] T004 [P] `app/db/mongo.py` 생성 — `motor.AsyncIOMotorClient` 초기화 및 DB 접근 헬퍼

### MQTT 기반 통신

- [x] T005 [P] `app/mqtt/topics.py` 생성 — 구독 6개 / 발행 5개 토픽 상수 정의
- [x] T006 `app/mqtt/client.py` 생성 — `aiomqtt` 래퍼: 브로커 연결, 6개 토픽 구독, 자동 재연결, dispatch 루프
- [x] T007 `app/mqtt/handlers.py` 생성 — dispatch 라우터 (topic split 방식) + 6개 subscribe 콜백 스텁 + 5개 publish 헬퍼

### 앱 진입점 및 모델

- [x] T008 `app/main.py` 구현 — `lifespan`: DB 초기화/종료 + MQTT 백그라운드 태스크 + 핸들러 dispatcher 주입
- [x] T009 `app/main.py` — `GET /health` 엔드포인트: MQTT/DB 연결 상태 JSON 반환
- [x] T010 [P] `app/models/customer.py` 생성 — `Customer` SQLAlchemy 모델
- [x] T011 [P] `app/models/place.py` 생성 — `Place` SQLAlchemy 모델
- [x] T012 [P] `app/models/edge_server.py` 생성 — `EdgeServer` SQLAlchemy 모델
- [x] T013 [P] `app/models/edge_sensor.py` 생성 — `EdgeSensor` SQLAlchemy 모델
- [x] T014 [P] `app/models/schemas.py` 생성 — NEW 시나리오 Pydantic 페이로드 스키마 (NEW-001/002/004/005)

---

## Phase 3: 서버 등록 (NEW-001 → NEW-002)

**Goal**: 엣지 서버 등록 메시지를 수신하고 Cloud SQL에 기록, 결과를 발행한다. 실패 시 3회 재시도 후 MongoDB에 실패 로그를 남긴다.

**흐름**:
```
[엣지] PUBLISH server_init/{id}/cloud
  → handle_server_init (payload 파싱 + server_id 추출)
    → register_edge_server() → SQL upsert (3회 재시도)
      → publish_register_server(success)
      └── 실패 시 publish_register_server(failed) + MongoDB fail_log 기록
```

**Checkpoint**: MQTT 클라이언트로 `signalcraft/server_init/{id}/cloud`에 등록 요청 발행 →
`signalcraft/register_server/cloud/{id}`에서 `{"status": "success"}` 수신 + SQL `edgeserver` 테이블에 레코드 확인

### Implementation

- [x] T301 `app/utils/retry.py` 생성 — `async_retry(fn, max_attempts=3, delay=1.0)`: 비동기 함수를 최대 `max_attempts`번 재시도, 각 실패 사이 `delay`초 대기, 모두 실패 시 마지막 예외를 raise
- [x] T302 `app/db/mongo.py` 업데이트 — `insert_error_log(event, server_id, error, attempts)` 헬퍼 추가: `{"event", "server_id", "error", "attempts", "timestamp"}` 형태로 MongoDB `error_logs` 컬렉션에 삽입
- [x] T303 `app/services/registration.py` 생성 — `register_edge_server(server_id, installation_place, timezone)`: `EdgeServer` upsert (server_id 기준, 이미 존재하면 `server_status=ONLINE`, `updated_at` 갱신), 성공 시 `EdgeServer` 객체 반환
- [x] T304 `app/mqtt/handlers.py` 업데이트 — `handle_server_init` 구현:
  1. `parts[2]`에서 `server_id` 추출, payload를 `EdgeServerRegisterRequest`로 파싱
  2. `async_retry`로 `register_edge_server()` 호출 (3회)
  3. 성공: `publish_register_server(server_id, {"status": "success"})` 호출
  4. 실패: `publish_register_server(server_id, {"status": "failed", "message": str(e)})` + `insert_fail_log("server_registration", {...})` 호출

---

## Phase 4: 서버 파라미터 원격 업데이트 (Web API → MQTT Publish)

**Goal**: 외부 API 호출로 엣지 서버 설정을 DB에 갱신하고, 변경된 파라미터를 MQTT로 해당 서버에 전달한다.

**흐름**:
```
[외부] POST /api/v1/update-server-parameters
  → update_edge_server() → SQL 갱신 (변경값만, 동일값 스킵)
    → publish_ctrl_parameters_server({server_id}, {변경된 파라미터})
      → 엣지 서버 수신 확인 (MQTTX 목업 테스트)
```

**Checkpoint**: POST 요청 → `{"status": "updated", "mqtt_published": true}` 응답 +
MQTTX에서 `signalcraft/control_parameters_server/cloud/{id}` 수신 확인

### Implementation

- [x] T401 `app/services/update.py` 생성 — `update_edge_server(server_id, *, place_id, server_status, capture_duration_ms, timezone, installation_machine, upload_interval_ms, active_hours_start, active_hours_end)`: 변경값이 기존값과 다를 때만 갱신, 변경 시 `updated_at` 자동 갱신, 서버 미존재 시 `None` 반환
- [x] T402 `app/api/web_api.py` 생성 — `POST /api/v1/update-server-parameters`: `UpdateServerParametersRequest` (server_id 필수, 나머지 선택), `update_edge_server()` 호출 → 서버 미존재 시 404 → 변경 파라미터 `publish_ctrl_parameters_server()` 발행 → `UpdateServerParametersResponse` 반환
- [x] T403 `app/main.py` 업데이트 — `app.include_router(web_router)` 등록

---

## Phase 5: 센서 등록 (NEW-004 → NEW-005)

**Goal**: 엣지 서버로부터 센서 등록 요청을 수신하고, 등록된 서버 DB id를 FK로 삼아 센서를 Cloud SQL에 기록한 뒤 결과를 발행한다.

**서버 등록과의 차이점**:
1. 토픽의 `server_id`(str)로 SQL에서 `EdgeServer.id`(UUID)를 먼저 조회 — 미등록 서버면 에러 로그 기록 후 중단
2. 조회한 `EdgeServer.id`를 `EdgeSensor.edge_server_id` FK로 등록 (나중에 서버 기준 센서 검색 가능)

**흐름**:
```
[엣지] PUBLISH forward_sensor_init/{server_id}/cloud
  → handle_sensor_init (payload 파싱 + server_id 추출)
    → register_edge_sensor()
        → SQL: EdgeServer WHERE server_id = {server_id} → EdgeServer.id(UUID) 획득
        → 미등록 서버 → ValueError raise → error_log + return
        → EdgeSensor upsert (edge_server_id=EdgeServer.id, device_name 기준)
      → publish_register_sensor(success)
      └── 실패 시 error_log + return
```

**Checkpoint**: MQTT 클라이언트로 `signalcraft/forward_sensor_init/{server_id}/cloud` 발행 →
`signalcraft/register_sensor/cloud/{server_id}`에서 `{"status": "success", "device_name": "..."}` 수신 +
SQL `edgesensor` 테이블에 레코드 확인 (`edge_server_id` FK 정상 연결)

### Implementation

- [x] T501 `app/models/schemas.py` 업데이트 — `EdgeSensorRegisterRequest`에서 `edge_server_id` 필드 제거: server DB id는 토픽의 `server_id`로 DB 조회해서 획득하므로 payload 불필요. `device_name`, `sensor_type`, `sensor_position`만 유지
- [x] T502 `app/services/registration.py` 업데이트 — `register_edge_sensor(server_id_str, device_name, sensor_type, sensor_position)` 추가:
  1. `EdgeServer WHERE server_id = server_id_str` 조회 → 없으면 `ValueError("Server not registered: {server_id_str}")` raise
  2. `EdgeSensor WHERE edge_server_id = EdgeServer.id AND device_name = device_name` 조회
  3. 없으면 신규 생성 (`edge_server_id=EdgeServer.id`, `sensor_type`, `sensor_position`, `created_at`, `updated_at`)
  4. 있으면 `sensor_position`, `updated_at` 갱신
  5. `EdgeSensor` 반환
- [x] T503 `app/mqtt/subscribe.py` 업데이트 ✅ 2026-04-23 검증 완료 — `handle_sensor_init` 구현 (서버 등록과 동일한 try 2단계 구조):
  1. `parts[2]`에서 `server_id_str` 추출, payload → `EdgeSensorRegisterRequest` 파싱
  2. try 1: `async_retry`로 `register_edge_sensor()` 호출 → 실패 시 `error_log` 기록 + return
  3. try 2: `publish_register_sensor(server_id_str, {"status": "success", "device_name": sensor.device_name})` → 실패 시 warning 로그

---

## Phase 6: 서버 파라미터 적용 결과 수신 (CTRL-SERVER-002)

**Goal**: 엣지 서버가 파라미터를 적용한 뒤 전송하는 결과 메시지를 수신하고, 성공/실패 여부를 MongoDB에 기록한다.

**MQTT QoS ACK와의 차이**:
- QoS ACK: 브로커까지 전달 여부만 확인 (엣지 수신/적용 여부 불명)
- CTRL-SERVER-002: 엣지가 실제로 파라미터를 적용했는지 application-level 확인

**흐름**:
```
[엣지] 파라미터 적용 후 PUBLISH result_parameters_server/{server_id}/cloud
  → handle_result_parameters_server (payload 파싱)
    → MongoDB ctrl_result_logs에 결과 기록 (server_id, status, message, timestamp)
```

**Checkpoint**: Web API로 서버 파라미터 업데이트 후 MQTTX에서
`signalcraft/result_parameters_server/{id}/cloud`로 결과 publish →
MongoDB `ctrl_result_logs`에 레코드 확인

### Implementation

- [x] T602 `app/models/schemas.py` 업데이트 — `CtrlServerResultPayload` Pydantic 스키마 추가 (CTRL-SERVER-002): `status: str`, `message: str | None`
- [x] T603 `app/mqtt/subscribe.py` 업데이트 — `handle_result_parameters_server` 구현:
  1. `parts[2]`에서 `server_id_str` 추출, payload → `CtrlServerResultPayload` 파싱
  2. `insert_ctrl_result_log(server_id_str, status, message)` 호출
  3. 성공/실패 여부를 INFO/WARNING 레벨로 로그 출력

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: 운영 및 개발 환경 완성도 향상

- [ ] TP01 [P] `.env.example` 생성 — 전체 환경변수 키 목록 (값은 placeholder)
- [ ] TP02 [P] `app/main.py` 업데이트 — 서버 기동 시 MQTT 연결 상태, DB 연결 상태, 구독 토픽 목록을 INFO 레벨 로그로 출력
- [ ] TP03 전체 흐름 수동 검증 — quickstart.md 시나리오 기준

---

## Notes

- `[P]` 태스크 = 병렬 실행 가능
- `app/mqtt/handlers.py` — 각 Phase 완성 시마다 콜백 함수 구현이 추가됨
- GCS Signed URL 생성은 VM 서비스 계정의 `iam.serviceAccounts.signBlob` 권한 필요
