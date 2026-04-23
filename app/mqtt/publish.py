from app.mqtt import client as mqtt_client
from app.mqtt.topics import (
    PUBLISH_CTRL_PARAMETERS_SENSOR,
    PUBLISH_CTRL_PARAMETERS_SERVER,
    PUBLISH_REGISTER_SENSOR,
    PUBLISH_REGISTER_SERVER,
    PUBLISH_UPLOAD_AUDIO_URL,
)


async def publish_register_server(server_id: str, payload: dict) -> None:
    """NEW-002 | signalcraft/register_server/cloud/{server_id}"""
    await mqtt_client.publish(PUBLISH_REGISTER_SERVER.format(server_id=server_id), payload)


async def publish_register_sensor(server_id: str, payload: dict) -> None:
    """NEW-005 | signalcraft/register_sensor/cloud/{server_id}"""
    await mqtt_client.publish(PUBLISH_REGISTER_SENSOR.format(server_id=server_id), payload)


async def publish_upload_audio_url(server_id: str, payload: dict) -> None:
    """AUDIO-007 | signalcraft/upload_audio_url/cloud/{server_id}"""
    await mqtt_client.publish(PUBLISH_UPLOAD_AUDIO_URL.format(server_id=server_id), payload)


async def publish_ctrl_parameters_server(server_id: str, payload: dict) -> None:
    """CTRL-SERVER-001 | signalcraft/control_parameters_server/cloud/{server_id}"""
    await mqtt_client.publish(PUBLISH_CTRL_PARAMETERS_SERVER.format(server_id=server_id), payload)


async def publish_ctrl_parameters_sensor(server_id: str, payload: dict) -> None:
    """CTRL-SENSOR-001 | signalcraft/control_parameters_sensor/cloud/{server_id}"""
    await mqtt_client.publish(PUBLISH_CTRL_PARAMETERS_SENSOR.format(server_id=server_id), payload)
