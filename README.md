# 백엔드 서버 시나리오

## 기기 정의
| 기기명 | 설치위치 | 담당업무 |
|---|---|---|
| 백엔드 | 클라우드 | 1. 엣지 서버와 통신<br>2. 사용자 요구 처리<br>3. 서비스 DB 제어(CRUD) |
| 클라우드 브로커 | 클라우드 | 엣지 서버와 백엔드 사이의 통신 연결(MQTT) |
| 엣지 서버 | 현장 | 1. 백엔드와 통신<br>2. 엣지 센서 제어<br>3. 엣지 브로커 생성<br>4. 로컬 DB 제어(CRUD) |
| 엣지 브로커 | 현장 | 엣지 서버와 엣지 센서 사이의 통신 연결(MQTT) |
| 엣지 센서 | 현장 | 1. 기기 소리 수집<br>2. 엣지 서버로 오디오 데이터 전송 |


## 상태별 분류(신규 설치)

| 상태 번호 | 시나리오 | 통신방식 | 송신자 | 수신자 | HTTP Methods |
|---|---|---|---|---|---|
| NEW-001 | 엣지 서버 등록 요청 | MQTT | 엣지 서버 | 백엔드 | X |
| NEW-002 | 엣지 서버 등록 결과 전달 | MQTT | 백엔드 | 엣지 서버 | X |
| NEW-003 | 엣지 센서 등록 요청 1 | MQTT | 엣지 센서 | 엣지 서버 | X |
| NEW-004 | 엣지 센서 등록 요청 2 | MQTT | 엣지 서버 | 백엔드 | X |
| NEW-005 | 엣지 센서 등록 결과 전달 | MQTT | 백엔드 | 엣지 서버 | X |
| NEW-006 | 엣지 센서 등록 결과 수신 | MQTT | 엣지 서버 | 엣지 센서 | X |

## 상태별 분류(오디오 수집)

| 상태 번호 | 시나리오 | 통신방식 | 송신자 | 수신자 | HTTP Methods |
|---|---|---|---|---|---|
| AUDIO-000 | 엣지 서버 트리거 실행(스케쥴 기반) | X | X | X | X |
| AUDIO-001 | 오디오 업로드 URL 발급 | 엣지 서버 내부 | X | X | X |
| AUDIO-002 | 오디오 데이터 요청(업로드 URL 포함) | MQTT | 엣지 서버 | 엣지 센서 | X |
| AUDIO-003 | 오디오 데이터 송신 | HTTP | 엣지 센서 | 엣지 서버 | POST(Request) |
| AUDIO-004 | 송신 결과 전달 | HTTP | 엣지 서버 | 엣지 센서 | POST(Response) |
| AUDIO-005 | 오디오 데이터 업로드 요청 | MQTT | 엣지 서버 | 백엔드 | X |
| AUDIO-006 | 오디오 Presigned URL 발급 | 백엔드 내부 | X | X | X |
| AUDIO-007 | 오디오 Presigned URL 전달 | MQTT | 백엔드 | 엣지 서버 | X |
| AUDIO-008 | 오디오 Presigned URL 송신 | HTTP | 엣지 서버 | GCP | PUT(Request) |
| AUDIO-009 | 송신 결과 전달 | HTTP | GCP | 엣지 서버 | PUT(Response) |
| AUDIO-010 | 전체 업로드 결과 전달 | MQTT | 엣지 서버 | 백엔드 | X |
| AUDIO-011 | 업로드 결과 기록 | 백엔드 내부 | X | X | X |

## 상태별 분류(파라미터 제어 - 서버)
제어 커맨드에 따라서 파라미터 최종 수신자가 달라짐
| 상태 번호 | 시나리오 | 통신방식 | 송신자 | 수신자 | HTTP Methods |
|---|---|---|---|---|---|
| CTRL-SERVER-001 | 파라미터 값 송신 | MQTT | 백엔드 | 엣지 서버 | X |
| CTRL-SERVER-002 | 송신 결과 전달 | MQTT | 엣지 서버 | 백엔드 | X |

## 상태별 분류(파라미터 제어 - 센서)
제어 커맨드에 따라서 파라미터 최종 수신자가 달라짐
| 상태 번호 | 시나리오 | 통신방식 | 송신자 | 수신자 | HTTP Methods |
|---|---|---|---|---|---|
| CTRL-SENSOR-001 | 파라미터 값 송신 | MQTT | 백엔드 | 엣지 서버 | X |
| CTRL-SENSOR-002 | 센서로 값 송신 | MQTT | 엣지 서버 | 엣지 센서 | X |
| CTRL-SENSOR-003 | 송신 결과 전달 | MQTT | 엣지 센서 | 엣지 서버 | X |
| CTRL-SENSOR-004 | 송신 결과 전달 | MQTT | 엣지 서버 | 백엔드 | X |

## MQTT 토픽 정리

## 기본구조
```
signalcraft/{토픽내용}/{송신위치}/{수신위치}
```
---
예시<br>
| 방향 | 토픽 예시 |
|---|---|
|엣지 센서 -> 엣지 서버| signalcraft/status_check/edge-sensor-1/edge-server-1
|엣지 서버 -> 엣지 센서| signalcraft/status_check/edge-server-1/edge-sensor-1
|클라우드 -> 엣지 서버| signalcraft/status_check/cloud/edge-server-1
|엣지 서버 -> 클라우드| signalcraft/status_check/edge-server-1/cloud

## 엣지 서버 브로커 토픽

| 시나리오 | 방향 | 토픽 | QoS |
|---|---|---|---|
| NEW-003 센서 등록 요청 | 엣지 센서 → 엣지 서버 | `signalcraft/sensor_init/{sensor_id}/{server_id}` | 1 |
| NEW-006 센서 등록 결과 수신 | 엣지 서버 → 엣지 센서 | `signalcraft/register_sensor/{server_id}/{sensor_id}` | 1 |
| AUDIO-002 오디오 데이터 요청 | 엣지 서버 → 엣지 센서 | `signalcraft/request_audio/{server_id}/{sensor_id}` | 1 |
| CTRL-SENSOR-002 센서로 파라미터 송신 | 엣지 서버 → 엣지 센서 | `signalcraft/control_parameters/{server_id}/{sensor_id}` | 1 |
| CTRL-SENSOR-003 센서 제어 결과 전달 | 엣지 센서 → 엣지 서버 | `signalcraft/result_parameters/{sensor_id}/{server_id}` | 1 |

> AUDIO-003/004 (오디오 데이터 송수신)는 HTTP로 처리 — MQTT 토픽 없음

---

## 클라우드 브로커 토픽

| 시나리오 | 방향 | 토픽 | QoS |
|---|---|---|---|
| NEW-001 엣지 서버 등록 요청 | 엣지 서버 → 백엔드 | `signalcraft/server_init/{server_id}/cloud` | 1 |
| NEW-002 엣지 서버 등록 결과 전달 | 백엔드 → 엣지 서버 | `signalcraft/register_server/cloud/{server_id}` | 1 |
| NEW-004 엣지 센서 등록 요청 | 엣지 서버 → 백엔드 | `signalcraft/forward_sensor_init/{server_id}/cloud` | 1 |
| NEW-005 엣지 센서 등록 결과 전달 | 백엔드 → 엣지 서버 | `signalcraft/register_sensor/cloud/{server_id}` | 1 |
| AUDIO-005 오디오 업로드 요청 | 엣지 서버 → 백엔드 | `signalcraft/request_upload_audio/{server_id}/cloud` | 1 |
| AUDIO-007 Presigned URL 전달 | 백엔드 → 엣지 서버 | `signalcraft/upload_audio_url/cloud/{server_id}` | 1 |
| AUDIO-010 전체 업로드 결과 전달 | 엣지 서버 → 백엔드 | `signalcraft/upload_result/{server_id}/cloud` | 1 |
| CTRL-SERVER-001 서버 파라미터 송신 | 백엔드 → 엣지 서버 | `signalcraft/control_parameters_server/cloud/{server_id}` | 1 |
| CTRL-SERVER-002 서버 제어 결과 전달 | 엣지 서버 → 백엔드 | `signalcraft/result_parameters_server/{server_id}/cloud` | 1 |
| CTRL-SENSOR-001 센서 파라미터 송신 | 백엔드 → 엣지 서버 | `signalcraft/control_parameters_sensor/cloud/{server_id}` | 1 |
| CTRL-SENSOR-004 센서 제어 결과 전달 | 엣지 서버 → 백엔드 | `signalcraft/result_parameters_sensor/{server_id}/cloud` | 1 |

---