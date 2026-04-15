# ─── 구독 토픽 (백엔드 Subscribe) ────────────────────────────────────────────
# + : 단일 레벨 와일드카드

SUBSCRIBE_EDGE_SERVER_REGISTER   = "signalcraft/edge/+/register"
SUBSCRIBE_EDGE_SENSOR_REGISTER   = "signalcraft/edge/+/sensor/+/register"
SUBSCRIBE_AUDIO_UPLOAD_REQUEST   = "signalcraft/edge/+/audio/upload/request"
SUBSCRIBE_AUDIO_UPLOAD_COMPLETE  = "signalcraft/edge/+/audio/upload/complete"
SUBSCRIBE_CTRL_SERVER_RESULT     = "signalcraft/edge/+/ctrl/server/result"
SUBSCRIBE_CTRL_SENSOR_RESULT     = "signalcraft/edge/+/ctrl/sensor/+/result"

ALL_SUBSCRIBE_TOPICS = [
    SUBSCRIBE_EDGE_SERVER_REGISTER,
    SUBSCRIBE_EDGE_SENSOR_REGISTER,
    SUBSCRIBE_AUDIO_UPLOAD_REQUEST,
    SUBSCRIBE_AUDIO_UPLOAD_COMPLETE,
    SUBSCRIBE_CTRL_SERVER_RESULT,
    SUBSCRIBE_CTRL_SENSOR_RESULT,
]

# ─── 발행 토픽 템플릿 (백엔드 Publish) ───────────────────────────────────────
# 사용 예: PUBLISH_EDGE_SERVER_REGISTER_RESULT.format(edge_server_id="abc")

PUBLISH_EDGE_SERVER_REGISTER_RESULT  = "signalcraft/edge/{edge_server_id}/register/result"
PUBLISH_EDGE_SENSOR_REGISTER_RESULT  = "signalcraft/edge/{edge_server_id}/sensor/{sensor_id}/register/result"
PUBLISH_AUDIO_UPLOAD_URL             = "signalcraft/edge/{edge_server_id}/audio/upload/url"
PUBLISH_CTRL_SERVER                  = "signalcraft/edge/{edge_server_id}/ctrl/server"
PUBLISH_CTRL_SENSOR                  = "signalcraft/edge/{edge_server_id}/ctrl/sensor/{sensor_id}"
