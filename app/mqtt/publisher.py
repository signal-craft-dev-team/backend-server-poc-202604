import asyncio
import logging

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


async def publish(client: mqtt.Client, topic: str, payload: str, qos: int = 0) -> None:
    result = client.publish(topic, payload, qos=qos)
    await asyncio.to_thread(result.wait_for_publish)
    logger.info(f"[MQTT] published | topic={topic} payload={payload}")
