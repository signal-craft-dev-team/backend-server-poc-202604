"""공통 픽스처 및 EdgeSimulator."""
import asyncio
import json
import os
import uuid
from typing import Optional

import paho.mqtt.client as mqtt
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient

load_dotenv()

# ── 테스트 설정 (직접 수정) ───────────────────────────────────────────────────
BACKEND_URL     = "http://34.173.212.20:8000"   # 예: "http://34.173.212.20:8000"
TEST_SERVER_ID  = "27f5bd10-c235-52a8-9f94-75c3004f26b5"   # 예: "server-001" (DB에 존재하는 server_id)

MQTT_HOST       = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT       = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER       = os.getenv("MQTT_USER")
MQTT_PWD        = os.getenv("MQTT_PWD")


class EdgeSimulator:
    """엣지 디바이스를 모방하는 MQTT 클라이언트.

    - Cloud → Edge 토픽을 구독하고 수신 메시지를 Queue에 저장
    - Edge → Cloud 토픽으로 메시지 발행
    """

    def __init__(self) -> None:
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"edge-simulator-{uuid.uuid4().hex[:8]}",
        )
        if MQTT_USER:
            self._client.username_pw_set(MQTT_USER, MQTT_PWD)
        self._queues: dict[str, asyncio.Queue] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def connect(self) -> None:
        self._client.on_message = self._on_message
        self._client.connect(MQTT_HOST, MQTT_PORT)
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def subscribe(self, topic: str) -> asyncio.Queue:
        # 테스트 코루틴 내부에서 호출되므로 여기서 루프를 캡처해야 올바른 루프를 얻을 수 있음
        self._loop = asyncio.get_event_loop()
        q: asyncio.Queue = asyncio.Queue()
        self._queues[topic] = q
        self._client.subscribe(topic, qos=1)
        return q

    def publish(self, topic: str, payload: dict) -> None:
        self._client.publish(topic, json.dumps(payload), qos=1)

    def _on_message(self, client, userdata, message: mqtt.MQTTMessage) -> None:
        topic = message.topic
        # 와일드카드 구독 처리: 등록된 큐 중 토픽이 매칭되는 것에 전달
        for registered_topic, q in self._queues.items():
            if self._topic_matches(registered_topic, topic):
                payload = json.loads(message.payload.decode())
                if self._loop:
                    try:
                        self._loop.call_soon_threadsafe(q.put_nowait, payload)
                    except RuntimeError:
                        pass  # 이전 테스트의 루프가 닫힌 경우 무시

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """MQTT 와일드카드(+) 매칭."""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")
        if len(pattern_parts) != len(topic_parts):
            return False
        return all(p == t or p == "+" for p, t in zip(pattern_parts, topic_parts))

    async def wait_for(self, queue: asyncio.Queue, timeout: float = 10.0) -> dict:
        """큐에서 메시지를 timeout 초 안에 받아 반환."""
        return await asyncio.wait_for(queue.get(), timeout=timeout)


# ── pytest 픽스처 ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def edge() -> EdgeSimulator:
    sim = EdgeSimulator()
    sim.connect()
    yield sim
    sim.disconnect()


@pytest_asyncio.fixture
async def http() -> AsyncClient:
    async with AsyncClient(base_url=BACKEND_URL) as client:
        yield client
