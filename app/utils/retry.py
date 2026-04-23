import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def async_retry(
    fn: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 5.0,
) -> T:
    """비동기 함수를 최대 max_attempts번 재시도한다.

    모든 시도가 실패하면 마지막 예외를 raise한다.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts:
                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                    attempt, max_attempts, exc, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "All %d attempts failed: %s",
                    max_attempts, exc,
                )
    raise last_exc  # type: ignore[misc]
