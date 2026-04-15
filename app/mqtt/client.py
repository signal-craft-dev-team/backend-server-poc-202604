import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import aiomqtt

from app.config import settings
from app.mqtt.topics import ALL_SUBSCRIBE_TOPICS

logger = logging.getLogger(__name__)

# 런타임에 핸들러 등록 후 세팅됨 (handlers.py에서 주입)
_dispatch: Callable[[aiomqtt.Message], Coroutine[Any, Any, None]] | None = None
_mqtt_connected: bool = False


def set_dispatcher(fn: Callable[[aiomqtt.Message], Coroutine[Any, Any, None]]) -> None:
    global _dispatch
    _dispatch = fn


def is_connected() -> bool:
    return _mqtt_connected


async def publish(topic: str, payload: dict) -> None:
    """현재 실행 중인 클라이언트를 통해 메시지를 발행한다."""
    if _client is None:
        raise RuntimeError("MQTT client is not running")
    await _client.publish(topic, json.dumps(payload), qos=1)


_client: aiomqtt.Client | None = None


async def run(stop_event: asyncio.Event) -> None:
    """MQTT 클라이언트 메인 루프. lifespan에서 create_task로 실행된다."""
    global _mqtt_connected, _client

    reconnect_interval = 5

    while not stop_event.is_set():
        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_user,
                password=settings.mqtt_pwd,
            ) as client:
                _client = client
                _mqtt_connected = True

                for topic in ALL_SUBSCRIBE_TOPICS:
                    await client.subscribe(topic, qos=1)
                    logger.info("[MQTT] Subscribed to %s", topic)

                logger.info("[MQTT] Connected to %s:%s", settings.mqtt_host, settings.mqtt_port)

                async for message in client.messages:
                    if stop_event.is_set():
                        break
                    if _dispatch is not None:
                        try:
                            await _dispatch(message)
                        except Exception:
                            logger.exception("[MQTT] Handler error for topic %s", message.topic)

        except aiomqtt.MqttError as exc:
            _mqtt_connected = False
            _client = None
            logger.warning("[MQTT] Connection lost (%s). Reconnecting in %ds...", exc, reconnect_interval)
            await asyncio.sleep(reconnect_interval)
        except asyncio.CancelledError:
            break

    _mqtt_connected = False
    _client = None
    logger.info("[MQTT] Client stopped")
