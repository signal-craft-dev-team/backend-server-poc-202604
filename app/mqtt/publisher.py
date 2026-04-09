import paho.mqtt.client as mqtt
import logging
logger = logging.getLogger(__name__)

def publish(client: mqtt.Client, topic: str, payload: str, qos: int = 0) -> None:
    result = client.publish(topic, payload, qos=qos)
    result.wait_for_publish()
    logger.info(f"[MQTT] published | topic={topic} payload={payload}")
