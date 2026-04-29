# MQTT Topic Contracts

**Branch**: `001-backend-2026-04-15` | **Date**: 2026-04-15

모든 MQTT 토픽은 클라우드 브로커를 경유한다.
README.md 시나리오 테이블의 각 MQTT 단계에 1:1 대응한다.

## 토픽 네임스페이스 규칙

```
signalcraft/{action}/{server_id}/cloud        # Subscribe (엣지 → 백엔드)
signalcraft/{action}/cloud/{server_id}        # Publish  (백엔드 → 엣지)
```

- `{server_id}`: 엣지 서버의 device_id (URL-safe string)
- `+`: MQTT 단일 레벨 와일드카드 (구독 시 사용)

---

## 신규 설치 (NEW)

### NEW-001 — 엣지 서버 등록 요청

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/server_init/{server_id}/cloud` |
| 방향 | 엣지 서버 → **백엔드** (Subscribe) |
| QoS | 1 |

**Payload**:
```json
{
  "device_id": "string",
  "location": "string (optional)"
}
```

---

### NEW-002 — 엣지 서버 등록 결과 전달

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/register_server/cloud/{server_id}` |
| 방향 | **백엔드** (Publish) → 엣지 서버 |
| QoS | 1 |

**Payload**:
```json
{
  "status": "success | failed",
  "message": "string (optional)"
}
```

---

### NEW-004 — 엣지 센서 등록 요청 (중계)

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/forward_sensor_init/{server_id}/cloud` |
| 방향 | 엣지 서버 → **백엔드** (Subscribe) |
| QoS | 1 |

**Payload**:
```json
{
  "sensor_device_id": "string",
  "edge_server_id": "string"
}
```

---

### NEW-005 — 엣지 센서 등록 결과 전달

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/register_sensor/cloud/{server_id}` |
| 방향 | **백엔드** (Publish) → 엣지 서버 |
| QoS | 1 |

**Payload**:
```json
{
  "status": "success | failed",
  "sensor_device_id": "string",
  "message": "string (optional)"
}
```

---

## 오디오 수집 (AUDIO)

### AUDIO-005 — 오디오 데이터 업로드 요청

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/request_upload_audio/{server_id}/cloud` |
| 방향 | 엣지 서버 → **백엔드** (Subscribe) |
| QoS | 1 |

**Payload**:
```json
{
  "edge_server_id": "string",
  "file_name": "string (optional, 백엔드가 생성 가능)"
}
```

---

### AUDIO-007 — Presigned URL 전달

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/upload_audio_url/cloud/{server_id}` |
| 방향 | **백엔드** (Publish) → 엣지 서버 |
| QoS | 1 |

**Payload**:
```json
{
  "presigned_url": "string (PUT URL)",
  "gcs_path": "string",
  "expires_at": "ISO8601"
}
```

---

### AUDIO-010 — 전체 업로드 결과 전달

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/upload_result/{server_id}/cloud` |
| 방향 | 엣지 서버 → **백엔드** (Subscribe) |
| QoS | 1 |

**Payload**:
```json
{
  "gcs_path": "string",
  "status": "success | failed",
  "message": "string (optional)"
}
```

---

## 파라미터 제어 — 서버 (CTRL-SERVER)

### CTRL-SERVER-001 — 파라미터 값 송신

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/control_parameters_server/cloud/{server_id}` |
| 방향 | **백엔드** (Publish) → 엣지 서버 |
| QoS | 1 |

**Payload**:
```json
{
  "parameter_name": "string",
  "parameter_value": "any"
}
```

---

### CTRL-SERVER-002 — 송신 결과 전달

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/result_parameters_server/{server_id}/cloud` |
| 방향 | 엣지 서버 → **백엔드** (Subscribe) |
| QoS | 1 |

**Payload**:
```json
{
  "parameter_name": "string",
  "status": "success | failed",
  "message": "string (optional)"
}
```

---

## 파라미터 제어 — 센서 (CTRL-SENSOR)

### CTRL-SENSOR-001 — 파라미터 값 송신 (백엔드 → 엣지 서버)

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/control_parameters_sensor/cloud/{server_id}` |
| 방향 | **백엔드** (Publish) → 엣지 서버 |
| QoS | 1 |

**Payload**:
```json
{
  "sensor_device_id": "string",
  "parameter_name": "string",
  "parameter_value": "any"
}
```

---

### CTRL-SENSOR-004 — 최종 결과 전달 (엣지 서버 → 백엔드)

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/result_parameters_sensor/{server_id}/cloud` |
| 방향 | 엣지 서버 → **백엔드** (Subscribe) |
| QoS | 1 |

**Payload**:
```json
{
  "sensor_device_id": "string",
  "parameter_name": "string",
  "status": "success | failed",
  "message": "string (optional)"
}
```

---

## 연결 상태 (LWT)

### LWT-001/002 — 엣지 서버 연결 상태

| 항목 | 값 |
|---|---|
| 토픽 | `signalcraft/lwt/{server_id}/cloud` |
| 방향 | 엣지 서버 → **백엔드** (Subscribe) |
| QoS | 1 |

**Payload**:
```json
{ "status": "OFFLINE" }
```
> LWT-001: 비정상 종료 시 브로커가 자동 발행 (`status: OFFLINE`)<br>
> LWT-002: 재연결 후 엣지 서버가 직접 발행 (`status: ONLINE`, Birth Message)

---

## 백엔드 구독 토픽 요약

백엔드가 클라우드 브로커에 Subscribe하는 토픽 목록:

```
signalcraft/server_init/+/cloud
signalcraft/forward_sensor_init/+/cloud
signalcraft/request_upload_audio/+/cloud
signalcraft/upload_result/+/cloud
signalcraft/result_parameters_server/+/cloud
signalcraft/result_parameters_sensor/+/cloud
signalcraft/lwt/+/cloud
```

(`+`는 MQTT 단일 레벨 와일드카드)
