---
description: "Task list for Signal Craft Backend POC implementation"
---

# Tasks: Signal Craft Backend POC

**Input**: Design documents from `specs/001-backend-2026-04-15/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/mqtt-topics.md ✅, research.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

---

## Phase 1: Setup

**Purpose**: 의존성 및 프로젝트 초기 구조 준비

- [x] T001 `requirements.txt`에 전체 의존성 추가: `aiomqtt==2.*`, `google-cloud-storage`, `cloud-sql-python-connector[asyncpg]`, `sqlalchemy[asyncio]`, `asyncpg`, `motor`, `pydantic-settings`, `python-dotenv`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 유저 스토리가 의존하는 핵심 인프라 — 이 단계 완료 전에는 어떤 스토리도 시작할 수 없다

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 `app/config.py` 생성 — `pydantic-settings BaseSettings`로 모든 환경변수 정의 (MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PWD, DB_USER, DB_PWD, DB_NAME, SQL_INSTANCE_CONNECTION_NAME, MONGODB_URI, MONGODB_DB_NAME, GCS_BUCKET_NAME, GCS_SIGNED_URL_EXPIRY_MINUTES)
- [x] T003 [P] `app/db/sql.py` 생성 — `cloud-sql-python-connector` + `asyncpg` 드라이버 기반 SQLAlchemy async 엔진 및 세션 팩토리 구현
- [x] T004 [P] `app/db/mongo.py` 생성 — `motor.AsyncIOMotorClient` 초기화 및 DB 접근 헬퍼 구현
- [x] T005 [P] `app/mqtt/topics.py` 생성 — 모든 MQTT 토픽 문자열을 상수로 정의 (contracts/mqtt-topics.md 기준 전체 6개 구독 토픽 + 발행 토픽 포함)
- [x] T006 `app/mqtt/client.py` 생성 — `aiomqtt.Client` 래퍼: 브로커 연결, 6개 와일드카드 토픽 구독, 메시지 dispatch 루프 (토픽 패턴 매칭 → 핸들러 라우팅)
- [x] T007 `app/main.py` 업데이트 — `@asynccontextmanager lifespan`에서 DB 연결 초기화/종료 및 MQTT 클라이언트를 `asyncio.create_task`로 백그라운드 실행
- [x] T007a `app/main.py` 업데이트 — `GET /health` 엔드포인트 추가: MQTT 연결 상태 및 DB 연결 상태를 JSON으로 반환 (`{"status": "ok", "mqtt": true, "db": true}`)

**Checkpoint**: DB 연결 및 MQTT 브로커 연결 로그가 출력되며 서버가 정상 기동되어야 한다

---

## Phase 3: User Story 1 - 현장 장비 등록 (Priority: P1) 🎯 MVP

**Goal**: 엣지 서버 및 센서의 등록 요청을 수신하고 DB에 기록, 결과를 해당 기기에 전달한다

**Independent Test**: MQTT 클라이언트로 `signalcraft/edge/{id}/register`에 등록 요청을 발행 →
`signalcraft/edge/{id}/register/result`에서 `{"status": "success"}` 수신 확인 +
Cloud SQL EdgeServer 테이블에 레코드 존재 확인

### Implementation for User Story 1

- [ ] T008 [P] [US1] `app/models/edge_server.py` 생성 — `EdgeServer` SQLAlchemy async 모델 (id UUID PK, device_id UNIQUE, location, status ENUM, registered_at, last_seen_at)
- [ ] T009 [P] [US1] `app/models/edge_sensor.py` 생성 — `EdgeSensor` SQLAlchemy async 모델 (id UUID PK, device_id UNIQUE, edge_server_id FK, status ENUM, registered_at)
- [ ] T010 [P] [US1] `app/models/schemas.py` 생성 — NEW 시나리오 Pydantic 스키마 (NEW-001 요청, NEW-002 결과, NEW-004 요청, NEW-005 결과 페이로드)
- [ ] T011 [US1] `app/db/sql.py` 업데이트 — `EdgeServer`, `EdgeSensor` 테이블 `create_all` (lifespan startup에서 호출)
- [ ] T012 [US1] `app/services/registration.py` 생성 — `register_edge_server(device_id, location)`, `register_edge_sensor(sensor_device_id, edge_server_id)` 구현 (중복 등록 시 기존 레코드 반환)
- [ ] T013 [US1] `app/mqtt/handlers.py` 생성 — `handle_edge_server_register(message)`: payload 파싱 → service 호출 → 결과 MQTT publish (NEW-002), `handle_edge_sensor_register(message)`: payload 파싱 → service 호출 → 결과 publish (NEW-005)
- [ ] T014 [US1] `app/mqtt/client.py` 업데이트 — dispatch 로직에 NEW 토픽 패턴 → `handlers.py` 핸들러 라우팅 연결

**Checkpoint**: US1 독립 동작 검증 — 위 Independent Test 기준 통과

---

## Phase 4: User Story 2 - 현장 장비 파라미터 원격 제어 (Priority: P2)

**Goal**: 백엔드가 엣지 서버 또는 센서에 파라미터 변경 명령을 MQTT로 전송하고,
결과를 수신하여 MongoDB ControlLog에 기록한다

**Independent Test**: `app/services/control.py`의 `send_server_param()` 호출 →
`signalcraft/edge/{id}/ctrl/server` 토픽에 파라미터 publish 확인.
엣지 서버 시뮬레이터에서 결과 publish → MongoDB ControlLog에 결과 레코드 확인

### Implementation for User Story 2

- [ ] T015 [P] [US2] `app/models/schemas.py` 업데이트 — CTRL 시나리오 Pydantic 스키마 추가 (CTRL-SERVER-001/002, CTRL-SENSOR-001/004 페이로드)
- [ ] T016 [US2] `app/services/control.py` 생성 — `send_server_param(edge_server_id, param_name, param_value)`: CTRL-SERVER-001 publish + MongoDB ControlLog 기록, `send_sensor_param(edge_server_id, sensor_id, param_name, param_value)`: CTRL-SENSOR-001 publish + 로그, `record_control_result(target_type, target_device_id, param_name, status, message)`: MongoDB ControlLog 결과 업데이트
- [ ] T017 [US2] `app/mqtt/handlers.py` 업데이트 — `handle_ctrl_server_result(message)`: CTRL-SERVER-002 수신 → service 결과 기록, `handle_ctrl_sensor_result(message)`: CTRL-SENSOR-004 수신 → service 결과 기록 추가
- [ ] T018 [US2] `app/mqtt/client.py` 업데이트 — dispatch에 CTRL result 토픽 패턴 → `handlers.py` CTRL 핸들러 라우팅 추가

**Checkpoint**: US2 독립 동작 검증 — 위 Independent Test 기준 통과

---

## Phase 5: User Story 3 - 오디오 데이터 클라우드 저장 지원 (Priority: P3)

**Goal**: 엣지 서버의 오디오 업로드 요청에 GCS Presigned URL을 발급하고,
업로드 완료 통보 수신 시 수집 이력을 DB에 기록한다

**Independent Test**: 등록된 엣지 서버에서 `signalcraft/edge/{id}/audio/upload/request` 발행 →
`signalcraft/edge/{id}/audio/upload/url`에서 `presigned_url`, `gcs_path`, `expires_at` 포함 응답 수신 확인.
완료 통보 발행 후 Cloud SQL AudioRecord 테이블에 `upload_status=success` 레코드 확인

### Implementation for User Story 3

- [ ] T019 [P] [US3] `app/models/audio_record.py` 생성 — `AudioRecord` SQLAlchemy async 모델 (id UUID PK, edge_server_id FK, gcs_path, presigned_url_issued_at, presigned_url_expires_at, upload_status ENUM, upload_completed_at)
- [ ] T020 [P] [US3] `app/models/schemas.py` 업데이트 — AUDIO 시나리오 Pydantic 스키마 추가 (AUDIO-005 요청, AUDIO-007 응답, AUDIO-010 완료 페이로드)
- [ ] T021 [US3] `app/db/sql.py` 업데이트 — `AudioRecord` 테이블 `create_all`에 추가
- [ ] T022 [US3] `app/storage/gcs.py` 생성 — `generate_signed_url(bucket, object_path, expiry_minutes)`: GCS v4 Signed URL (PUT) 생성, Compute Engine 기본 인증 사용
- [ ] T023 [US3] `app/services/audio.py` 생성 — `issue_presigned_url(edge_server_id)`: gcs_path 생성 → Signed URL 발급 → AudioRecord pending 저장 → URL 반환, `record_upload_result(gcs_path, status)`: AudioRecord status 업데이트
- [ ] T024 [US3] `app/mqtt/handlers.py` 업데이트 — `handle_audio_upload_request(message)`: service 호출 → AUDIO-007 결과 publish, `handle_audio_upload_complete(message)`: service 호출 → 이력 기록 추가
- [ ] T025 [US3] `app/mqtt/client.py` 업데이트 — dispatch에 AUDIO 토픽 패턴 → `handlers.py` AUDIO 핸들러 라우팅 추가

**Checkpoint**: US3 독립 동작 검증 — 위 Independent Test 기준 통과

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: 운영 및 개발 환경 완성도 향상

- [ ] T026 [P] `.env.example` 생성 — quickstart.md 기준 전체 환경변수 키 목록 (값은 placeholder)
- [ ] T027 [P] `.gitignore` 업데이트 — `.env` 항목 추가 확인 (없으면 추가)
- [ ] T028 [P] `app/main.py` 업데이트 — 서버 기동 시 MQTT 연결 상태, DB 연결 상태, 구독 토픽 목록을 INFO 레벨 로그로 출력
- [ ] T029 quickstart.md의 동작 검증 시나리오를 실행하여 전체 흐름(NEW → CTRL → AUDIO) 수동 검증

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존성 없음 — 즉시 시작 가능
- **Foundational (Phase 2)**: Phase 1 완료 후 시작 — 모든 유저 스토리를 블록
- **US1 (Phase 3)**: Phase 2 완료 필수
- **US2 (Phase 4)**: Phase 2 완료 필수 — US1과 무관하게 독립 시작 가능 (팀 환경)
- **US3 (Phase 5)**: Phase 2 완료 필수 — US1/US2와 무관하게 독립 시작 가능 (팀 환경)
- **Polish (Phase N)**: 원하는 유저 스토리가 모두 완료된 후

### User Story Dependencies

- **US1 (P1)**: Phase 2 이후 즉시 시작 — 다른 스토리에 의존 없음
- **US2 (P2)**: Phase 2 이후 즉시 시작 — US1 완료 불필요
- **US3 (P3)**: Phase 2 이후 즉시 시작 — US1/US2 완료 불필요

### Within Each User Story

- 모델 → 서비스 → 핸들러 추가 → 클라이언트 dispatch 연결 순서
- [P] 마크 태스크는 같은 단계 내에서 동시 진행 가능

### Parallel Opportunities

```bash
# Phase 2 내 병렬 가능:
Task: T003 app/db/sql.py
Task: T004 app/db/mongo.py
Task: T005 app/mqtt/topics.py

# US1 내 병렬 가능:
Task: T008 app/models/edge_server.py
Task: T009 app/models/edge_sensor.py
Task: T010 app/models/schemas.py (NEW 스키마)

# US3 내 병렬 가능:
Task: T019 app/models/audio_record.py
Task: T020 app/models/schemas.py (AUDIO 스키마 추가)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: T001
2. Phase 2: T002 → T003/T004/T005 (병렬) → T006 → T007
3. Phase 3: T008/T009/T010 (병렬) → T011 → T012 → T013 → T014
4. **STOP and VALIDATE**: Independent Test for US1
5. Deploy to GCP VM and verify end-to-end

### Incremental Delivery

1. Setup + Foundational → 인프라 준비
2. US1 → 장비 등록 동작 → 검증/배포 (MVP)
3. US2 → 파라미터 제어 → 검증/배포
4. US3 → 오디오 수집 → 검증/배포
5. Polish → 운영 준비 완료

---

## Notes

- `[P]` 태스크 = 다른 파일, 의존성 없음 → 병렬 실행 가능
- `[USn]` 라벨 = 해당 유저 스토리와 연결된 태스크
- `app/mqtt/handlers.py`는 각 스토리 완성 시마다 핸들러 함수가 추가됨 (T013 → T017 → T024)
- `app/mqtt/client.py`는 각 스토리 완성 시마다 dispatch 라우팅이 추가됨 (T006 → T014 → T018 → T025)
- GCS Signed URL 생성은 VM 서비스 계정의 `iam.serviceAccounts.signBlob` 권한 필요 (quickstart.md 참고)
