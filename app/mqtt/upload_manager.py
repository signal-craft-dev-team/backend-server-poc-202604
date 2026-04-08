"""COMPLETE_UPLOAD 수신 대기 관리.

AckManager와 동일한 패턴 — paho 콜백 스레드에서 asyncio 루프로 결과를 전달.
상관관계 키는 file_name (server_id_sensor_id_timestamp.wav 형식으로 사실상 유니크).
"""
import asyncio
import logging
from typing import Callable, Coroutine, Dict, Optional

logger = logging.getLogger(__name__)


class UploadManager:
    def __init__(self) -> None:
        self._pending: Dict[str, asyncio.Queue] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def schedule(self, coro: Coroutine) -> None:
        """paho 콜백 스레드에서 asyncio 코루틴을 이벤트 루프에 예약."""
        if self._loop is None:
            logger.error("[UploadManager] event loop not set")
            return
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def register(self, file_name: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._pending[file_name] = q
        return q

    def resolve(self, file_name: str, payload: dict) -> None:
        """paho 스레드에서 호출 — COMPLETE_UPLOAD 페이로드를 대기 중인 코루틴에 전달."""
        q = self._pending.get(file_name)
        if q is None:
            logger.warning(f"[UploadManager] no waiter for file_name={file_name}")
            return
        if self._loop is None:
            logger.error("[UploadManager] event loop not set")
            return
        self._loop.call_soon_threadsafe(q.put_nowait, payload)

    def unregister(self, file_name: str) -> None:
        self._pending.pop(file_name, None)


upload_manager = UploadManager()
