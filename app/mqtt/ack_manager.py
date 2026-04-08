"""Bridges MQTT callback thread → asyncio for CONTROL_ACK correlation.

paho-mqtt fires on_message in its own background thread (loop_start).
AckManager lets the HTTP handler await a Queue that the MQTT thread fills
via loop.call_soon_threadsafe — the only safe way to cross the boundary.
"""
import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AckManager:
    def __init__(self) -> None:
        self._pending: Dict[str, asyncio.Queue] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def register(self, message_id: str) -> asyncio.Queue:
        """Create a Queue for the given message_id and return it to the waiter."""
        q: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._pending[message_id] = q
        return q

    def resolve(self, message_id: str, payload: dict) -> None:
        """Called from the MQTT thread — delivers the ACK payload to the waiter."""
        q = self._pending.get(message_id)
        if q is None:
            logger.warning(f"[AckManager] no waiter for message_id={message_id}")
            return
        if self._loop is None:
            logger.error("[AckManager] event loop not set")
            return
        self._loop.call_soon_threadsafe(q.put_nowait, payload)

    def unregister(self, message_id: str) -> None:
        self._pending.pop(message_id, None)


ack_manager = AckManager()
