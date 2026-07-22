"""
Rate Limiter — Simple in-memory per-user rate limiting.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW

_user_timestamps: dict[int, deque] = defaultdict(deque)


def is_rate_limited(user_id: int) -> bool:
    """
    Returns True if the user has exceeded the rate limit.
    Sliding window algorithm.
    """
    now = time.monotonic()
    window = _user_timestamps[user_id]

    # Remove timestamps outside the window
    while window and now - window[0] > RATE_LIMIT_WINDOW:
        window.popleft()

    if len(window) >= RATE_LIMIT_MESSAGES:
        return True

    window.append(now)
    return False


def reset_rate_limit(user_id: int) -> None:
    _user_timestamps.pop(user_id, None)
