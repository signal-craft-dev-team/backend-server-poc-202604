#!/usr/bin/env bash
# MQTT 통신 방식 통합 테스트
# 사전 조건: mosquitto-clients 설치 (brew install mosquitto / apt install mosquitto-clients)

set -euo pipefail

# ── 설정 (직접 수정) ──────────────────────────────────────────────────────────
MQTT_HOST="34.9.5.247"          # 예: "34.xx.xx.xx"
MQTT_PORT="1883"
MQTT_USER="signalcraft"
MQTT_PWD="s1357924680"
BACKEND_URL="http://34.173.212.20:8000"        # 예: "http://34.xx.xx.xx:8000"
SERVER_ID="27f5bd10-c235-52a8-9f94-75c3004f26b5"          # 예: "27f5bd10-c235-52a8-9f94-75c3004f26b5"
SENSOR_ID="test-sensor-01"
# ─────────────────────────────────────────────────────────────────────────────

PASS=0
FAIL=0
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
FILE_NAME="test_$(date +%s).wav"

# ── 색상 ──────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAIL=$((FAIL + 1)); }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
section() { echo -e "\n${YELLOW}── $1 ──────────────────────────────${NC}"; }

# ── 인증 옵션 빌드 ────────────────────────────────────────────────────────────
AUTH_OPTS=""
if [[ -n "$MQTT_USER" ]]; then
  AUTH_OPTS="-u $MQTT_USER -P $MQTT_PWD"
fi

# ── 헬퍼: MQTT publish ────────────────────────────────────────────────────────
mqtt_pub() {
  local topic="$1"
  local payload="$2"
  mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" $AUTH_OPTS \
    -t "$topic" -m "$payload" -q 1
}

# ── 헬퍼: MQTT subscribe (최대 N초 대기, 1개 수신 후 종료) ───────────────────
mqtt_sub_once() {
  local topic="$1"
  local wait_sec="${2:-10}"
  timeout "$wait_sec" mosquitto_sub \
    -h "$MQTT_HOST" -p "$MQTT_PORT" $AUTH_OPTS \
    -t "$topic" -C 1 -q 1 2>/dev/null || true
}

# ── 사전 검사 ─────────────────────────────────────────────────────────────────
section "사전 검사"

for cmd in mosquitto_pub mosquitto_sub curl; do
  if command -v "$cmd" &>/dev/null; then
    pass "$cmd 존재"
  else
    fail "$cmd 없음 — brew install mosquitto / apt install mosquitto-clients"
    exit 1
  fi
done

if [[ -z "$MQTT_HOST" || -z "$BACKEND_URL" || -z "$SERVER_ID" ]]; then
  fail "MQTT_HOST / BACKEND_URL / SERVER_ID 가 비어있습니다. 스크립트 상단을 수정하세요."
  exit 1
fi

# ── TEST 1: 백엔드 헬스 체크 ──────────────────────────────────────────────────
section "TEST 1: 백엔드 헬스 체크"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health")
if [[ "$STATUS" == "200" ]]; then
  pass "GET /health → 200"
else
  fail "GET /health → $STATUS"
fi

# ── TEST 2: MQTT 브로커 연결 ──────────────────────────────────────────────────
section "TEST 2: MQTT 브로커 연결"

mqtt_pub "signalcraft/test/ping" '{"ping":"test"}' && pass "MQTT publish 성공" || fail "MQTT publish 실패"

# ── TEST 3: UPLOAD_AUDIO → SEND_URL 수신 ─────────────────────────────────────
section "TEST 3: UPLOAD_AUDIO → SEND_URL"

SEND_URL_TOPIC="signalcraft/send_url/$SERVER_ID"

info "SEND_URL 구독 시작 (백그라운드)"
SEND_URL_RESULT=$(
  mqtt_sub_once "$SEND_URL_TOPIC" 15 &
  SUB_PID=$!

  sleep 1  # 구독 준비 대기

  mqtt_pub "signalcraft/upload_audio/$SERVER_ID" \
    "{\"server_id\":\"$SERVER_ID\",\"sensor_id\":\"$SENSOR_ID\",\"file_name\":\"$FILE_NAME\",\"recorded_at\":\"$NOW\",\"duration_ms\":5000,\"file_size_bytes\":102400,\"timestamp\":\"$NOW\"}"

  wait $SUB_PID
)

if echo "$SEND_URL_RESULT" | grep -q "signed_url"; then
  pass "SEND_URL 수신 확인 (signed_url 포함)"
  SIGNED_URL=$(echo "$SEND_URL_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('signed_url',''))" 2>/dev/null || echo "")
  info "signed_url: ${SIGNED_URL:0:80}..."

  # COMPLETE_UPLOAD 발행 (플로우 정리)
  sleep 1
  mqtt_pub "signalcraft/complete_upload/$SERVER_ID" \
    "{\"server_id\":\"$SERVER_ID\",\"sensor_id\":\"$SENSOR_ID\",\"file_name\":\"$FILE_NAME\",\"recorded_at\":\"$NOW\",\"duration_ms\":5000,\"file_size_bytes\":102400,\"timestamp\":\"$NOW\"}"
  info "COMPLETE_UPLOAD 발행 완료"
else
  fail "SEND_URL 미수신 (15초 타임아웃)"
fi

# ── TEST 4: CONTROL_SERVER → ACK 플로우 ──────────────────────────────────────
section "TEST 4: CONTROL_SERVER → ACK"

CONTROL_TOPIC="signalcraft/control_server/$SERVER_ID"
ACK_TOPIC="signalcraft/control_server/$SERVER_ID/ack"
MSG_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")

info "제어 명령 구독 시작 (백그라운드)"
CTRL_TMP=$(mktemp)
HTTP_TMP=$(mktemp)

# 제어 명령 구독 (백그라운드, 임시 파일에 저장)
timeout 12 mosquitto_sub \
  -h "$MQTT_HOST" -p "$MQTT_PORT" $AUTH_OPTS \
  -t "$CONTROL_TOPIC" -C 1 -q 1 > "$CTRL_TMP" 2>/dev/null &
SUB_PID=$!

sleep 1

# HTTP 요청 (백그라운드, 응답을 임시 파일에 저장)
curl -s -X POST "$BACKEND_URL/mqtt/control_server" \
  -H "Content-Type: application/json" \
  -d "{\"command\":\"CHANGE_CAPTURE_DURATION\",\"server_id\":\"$SERVER_ID\",\"params\":{\"capture_duration_ms\":5000},\"timestamp\":\"$NOW\"}" \
  --max-time 35 > "$HTTP_TMP" &
HTTP_PID=$!

# 구독 결과 대기
wait $SUB_PID || true
CONTROL_RESULT=$(cat "$CTRL_TMP")
rm -f "$CTRL_TMP"

info "CONTROL_RESULT raw: $CONTROL_RESULT"

if echo "$CONTROL_RESULT" | grep -q "message_id"; then
  RECV_MSG_ID=$(echo "$CONTROL_RESULT" | grep -o '"message_id":"[^"]*"' | cut -d'"' -f4)
  pass "CONTROL_SERVER 메시지 수신 (message_id=$RECV_MSG_ID)"

  # ACK 발행
  mqtt_pub "$ACK_TOPIC" \
    "{\"message_id\":\"$RECV_MSG_ID\",\"server_id\":\"$SERVER_ID\",\"command\":\"CHANGE_CAPTURE_DURATION\",\"status\":\"APPLIED\",\"timestamp\":\"$NOW\"}"

  # HTTP 응답 대기 및 확인
  wait $HTTP_PID || true
  HTTP_BODY=$(cat "$HTTP_TMP")
  if echo "$HTTP_BODY" | grep -q '"status":"APPLIED"'; then
    pass "HTTP 응답 확인 (status=APPLIED)"
  else
    fail "HTTP 응답 이상: $HTTP_BODY"
  fi
else
  fail "CONTROL_SERVER 메시지 미수신"
  kill $HTTP_PID 2>/dev/null || true
fi
rm -f "$HTTP_TMP"

# ── TEST 5: ABNORMAL 이벤트 ───────────────────────────────────────────────────
section "TEST 5: ABNORMAL 이벤트"

mqtt_pub "signalcraft/cloud/$SERVER_ID/abnormal" \
  "{\"server_id\":\"$SERVER_ID\",\"sensor_id\":\"$SENSOR_ID\",\"event_type\":\"SENSOR_OFFLINE\",\"detail\":\"bash test\",\"timestamp\":\"$NOW\"}" \
  && pass "ABNORMAL 발행 성공" || fail "ABNORMAL 발행 실패"

# ── TEST 6: DISK_ALERT 이벤트 ─────────────────────────────────────────────────
section "TEST 6: DISK_ALERT 이벤트"

mqtt_pub "signalcraft/cloud/$SERVER_ID/disk_alert" \
  "{\"server_id\":\"$SERVER_ID\",\"disk_usage_percent\":92.5,\"threshold_percent\":90.0,\"timestamp\":\"$NOW\"}" \
  && pass "DISK_ALERT 발행 성공" || fail "DISK_ALERT 발행 실패"

# ── TEST 7: UPLOAD_FAILED 이벤트 ─────────────────────────────────────────────
section "TEST 7: UPLOAD_FAILED 이벤트"

mqtt_pub "signalcraft/cloud/$SERVER_ID/upload_failed" \
  "{\"server_id\":\"$SERVER_ID\",\"sensor_id\":\"$SENSOR_ID\",\"file_name\":\"$FILE_NAME\",\"reason\":\"bash test failure\",\"timestamp\":\"$NOW\"}" \
  && pass "UPLOAD_FAILED 발행 성공" || fail "UPLOAD_FAILED 발행 실패"

# ── MongoDB 로그 확인 (선택) ──────────────────────────────────────────────────
section "TEST 8: MongoDB 로그 기록 확인"

sleep 2
LOG_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/log/health-check")
if [[ "$LOG_STATUS" == "200" ]]; then
  LOG_BODY=$(curl -s "$BACKEND_URL/log/health-check")
  if echo "$LOG_BODY" | grep -q '"status":"ok"'; then
    pass "MongoDB 연결 정상"
  else
    fail "MongoDB 응답 이상: $LOG_BODY"
  fi
else
  fail "GET /log/health-check → $LOG_STATUS"
fi

# ── 결과 요약 ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}════════════════════════════════════${NC}"
echo -e "  PASS: ${GREEN}${PASS}${NC}  |  FAIL: ${RED}${FAIL}${NC}"
echo -e "${YELLOW}════════════════════════════════════${NC}"

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
