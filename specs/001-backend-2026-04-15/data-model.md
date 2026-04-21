# Data Model: Signal Craft Backend POC

**Branch**: `001-backend-2026-04-15` | **Date**: 2026-04-15

## Cloud SQL (PostgreSQL) — 구조화 데이터

### EdgeServer

엣지 서버 기기 등록 정보.

| 필드 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID | PK, auto | 내부 식별자 |
| device_id | VARCHAR(128) | UNIQUE, NOT NULL | 장비 자체 식별자 (MQTT 등록 시 제공) |
| location | VARCHAR(255) | NULL | 설치 위치 설명 |
| status | ENUM | NOT NULL, default='active' | active / inactive |
| registered_at | TIMESTAMPTZ | NOT NULL, default=now() | 최초 등록 시각 |
| last_seen_at | TIMESTAMPTZ | NULL | 마지막 메시지 수신 시각 |

**State transitions**: `inactive` → `active` (등록 성공) → `inactive` (비활성 처리)

---

### EdgeSensor

엣지 센서 기기 등록 정보. 반드시 특정 엣지 서버에 귀속된다.

| 필드 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID | PK, auto | 내부 식별자 |
| device_id | VARCHAR(128) | UNIQUE, NOT NULL | 장비 자체 식별자 |
| edge_server_id | UUID | FK → EdgeServer.id, NOT NULL | 귀속 엣지 서버 |
| status | ENUM | NOT NULL, default='active' | active / inactive |
| registered_at | TIMESTAMPTZ | NOT NULL, default=now() | 최초 등록 시각 |

---

### AudioRecord

수집된 오디오의 메타데이터 및 업로드 이력.

| 필드 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID | PK, auto | 내부 식별자 |
| edge_server_id | UUID | FK → EdgeServer.id, NOT NULL | 업로드 요청 엣지 서버 |
| gcs_path | VARCHAR(512) | NULL | GCS 저장 경로 (업로드 완료 후 확정) |
| presigned_url_issued_at | TIMESTAMPTZ | NOT NULL | Presigned URL 발급 시각 |
| presigned_url_expires_at | TIMESTAMPTZ | NOT NULL | Presigned URL 만료 시각 |
| upload_status | ENUM | NOT NULL, default='pending' | pending / success / failed |
| upload_completed_at | TIMESTAMPTZ | NULL | 업로드 완료 시각 |

**State transitions**: `pending` → `success` (완료 통보 수신) / `failed` (실패 통보 또는 만료)

---

## MongoDB — 비구조화 데이터

### ControlLog (컬렉션)

파라미터 제어 명령과 결과 이력. 파라미터 스키마가 장비 종류마다 다를 수 있어 MongoDB에 저장.

```json
{
  "_id": "ObjectId",
  "target_type": "server | sensor",
  "target_device_id": "string",
  "edge_server_id": "string",
  "command": {
    "parameter_name": "string",
    "parameter_value": "any"
  },
  "result": {
    "status": "success | failed",
    "message": "string (optional)",
    "applied_at": "ISODate"
  },
  "issued_at": "ISODate",
  "completed_at": "ISODate (null if pending)"
}
```

**Index**: `target_device_id`, `issued_at` (조회 성능)

---

## 엔티티 관계

```
EdgeServer (1) ──── (N) EdgeSensor
EdgeServer (1) ──── (N) AudioRecord
EdgeServer (1) ──── (N) ControlLog [MongoDB, device_id 참조]
EdgeSensor  (1) ──── (N) ControlLog [MongoDB, device_id 참조]
```
