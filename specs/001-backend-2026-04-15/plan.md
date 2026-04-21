# Implementation Plan: Signal Craft Backend POC

**Branch**: `001-backend-2026-04-15` | **Date**: 2026-04-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-backend-2026-04-15/spec.md`

## Summary

MQTT 기반 IoT 기기(엣지 서버/센서) 등록, 오디오 수집 지원(GCS Presigned URL),
파라미터 원격 제어를 처리하는 FastAPI + aiomqtt 비동기 백엔드 서버를 구현한다.
모든 외부 통신은 README 시나리오 테이블을 단일 소스로 하며,
클라우드 브로커를 통한 MQTT와 GCS HTTP 경로만 사용한다.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI (헬스체크 엔드포인트 및 미래 관리 API 진입점 보유용), aiomqtt, google-cloud-storage, cloud-sql-python-connector, SQLAlchemy (async), motor (MongoDB async), uvicorn
**Storage**: Cloud SQL / PostgreSQL (엣지 서버·센서 등록, 수집 이력 — 구조화), MongoDB (파라미터 제어 이력 — 비구조화)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux (GCP VM, Docker 컨테이너)
**Project Type**: web-service + MQTT subscriber/publisher
**Performance Goals**: Presigned URL 발급 및 전달 5초 이내 (SC-003)
**Constraints**: 모든 I/O async, 자격증명 환경변수 전용, 기기 계층 준수
**Scale/Scope**: POC — 소수 현장, 단일 배포 인스턴스

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 게이트 | 결과 |
|---|---|---|
| I. 시나리오 기반 통신 설계 | MQTT 토픽 및 HTTP 경로가 README 시나리오 테이블에 정의된 것만 사용 | ✅ |
| II. 계층적 메시지 흐름 | 백엔드는 클라우드 브로커하고만 MQTT 통신, 엣지 브로커와 직접 연결 없음 | ✅ |
| III. 비동기 우선 설계 | FastAPI async def + aiomqtt 기반으로 모든 I/O 구현 | ✅ |
| IV. 단계적 시나리오 구현 | 구현 순서: NEW → CTRL-SERVER/CTRL-SENSOR → AUDIO | ✅ |
| V. 환경변수 기반 설정 | 모든 접속 정보는 환경변수로 주입, 소스 코드 내 하드코딩 없음 | ✅ |

**Post-Phase 1 Re-check**: ✅ 모든 MQTT 토픽 계약이 계층 원칙 준수 확인

## Project Structure

### Documentation (this feature)

```text
specs/001-backend-2026-04-15/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── mqtt-topics.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
app/
├── main.py              # FastAPI app, lifespan (MQTT 클라이언트 기동/종료)
├── config.py            # 환경변수 기반 설정 (pydantic BaseSettings)
├── mqtt/
│   ├── client.py        # aiomqtt 클라이언트 래퍼, 토픽 구독/발행
│   ├── topics.py        # MQTT 토픽 상수 정의
│   └── handlers.py      # 전체 MQTT 핸들러 (NEW / CTRL / AUDIO 시나리오)
├── models/
│   ├── edge_server.py   # EdgeServer SQLAlchemy 모델
│   ├── edge_sensor.py   # EdgeSensor SQLAlchemy 모델
│   ├── audio_record.py  # AudioRecord SQLAlchemy 모델
│   └── schemas.py       # Pydantic 스키마 (MQTT 메시지 직렬화)
├── services/
│   ├── registration.py  # 기기 등록 비즈니스 로직
│   ├── audio.py         # Presigned URL 발급, 수집 이력 기록
│   └── control.py       # 파라미터 제어 명령 전달 및 이력 기록
├── db/
│   ├── sql.py           # Cloud SQL async 세션 팩토리
│   └── mongo.py         # MongoDB motor 클라이언트
└── storage/
    └── gcs.py           # GCS Signed URL 생성
```

**Structure Decision**: 단일 서비스 구조(app/). handlers는 단일 파일(`mqtt/handlers.py`)로 관리,
services/models는 도메인별 분리. 테스트는 추후 `/speckit.tasks`에서 정의.

## Complexity Tracking

> Constitution Check 위반 없음 — 이 섹션은 빈 상태로 유지
