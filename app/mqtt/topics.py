# ─── 구독 토픽 (백엔드 Subscribe) ────────────────────────────────────────────
# + : 단일 레벨 와일드카드

SUBSCRIBE_SERVER_INIT                  = "signalcraft/server_init/+/cloud"
SUBSCRIBE_FORWARD_SENSOR_INIT          = "signalcraft/forward_sensor_init/+/cloud"
SUBSCRIBE_REQUEST_UPLOAD_AUDIO         = "signalcraft/request_upload_audio/+/cloud"
SUBSCRIBE_UPLOAD_RESULT                = "signalcraft/upload_result/+/cloud"
SUBSCRIBE_RESULT_PARAMETERS_SERVER     = "signalcraft/result_parameters_server/+/cloud"
SUBSCRIBE_RESULT_PARAMETERS_SENSOR     = "signalcraft/result_parameters_sensor/+/cloud"
SUBSCRIBE_LWT                          = "signalcraft/lwt/+/cloud"

ALL_SUBSCRIBE_TOPICS = [
    SUBSCRIBE_SERVER_INIT,
    SUBSCRIBE_FORWARD_SENSOR_INIT,
    SUBSCRIBE_REQUEST_UPLOAD_AUDIO,
    SUBSCRIBE_UPLOAD_RESULT,
    SUBSCRIBE_RESULT_PARAMETERS_SERVER,
    SUBSCRIBE_RESULT_PARAMETERS_SENSOR,
    SUBSCRIBE_LWT
]

# ─── 발행 토픽 템플릿 (백엔드 Publish) ───────────────────────────────────────
# 사용 예: PUBLISH_REGISTER_SERVER.format(server_id="abc")

PUBLISH_REGISTER_SERVER              = "signalcraft/register_server/cloud/{server_id}"
PUBLISH_REGISTER_SENSOR              = "signalcraft/register_sensor/cloud/{server_id}"
PUBLISH_UPLOAD_AUDIO_URL             = "signalcraft/upload_audio_url/cloud/{server_id}"
PUBLISH_CTRL_PARAMETERS_SERVER       = "signalcraft/control_parameters_server/cloud/{server_id}"
PUBLISH_CTRL_PARAMETERS_SENSOR       = "signalcraft/control_parameters_sensor/cloud/{server_id}"
