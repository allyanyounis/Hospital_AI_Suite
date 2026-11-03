from datetime import datetime, timedelta
import threading
from typing import Dict, List


class InMemoryRateLimiter:
    """Thread-safe in-memory sliding window rate limiter with automatic bounded memory cleanup."""

    def __init__(self, cleanup_interval: int = 100):
        self._lock = threading.Lock()
        self._records: Dict[str, List[datetime]] = {}
        self._check_counter = 0
        self._cleanup_interval = cleanup_interval

    def is_rate_limited(
        self,
        key: str,
        max_requests: int = 20,
        window_seconds: int = 600
    ) -> bool:
        """Check if request for key exceeds max_requests within window_seconds.
        
        Returns True if rate limited, False if allowed (and records the request).
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        with self._lock:
            self._check_counter += 1
            if self._check_counter >= self._cleanup_interval:
                self._cleanup(cutoff)
                self._check_counter = 0

            timestamps = self._records.get(key, [])
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            if len(valid_timestamps) >= max_requests:
                self._records[key] = valid_timestamps
                return True

            valid_timestamps.append(now)
            self._records[key] = valid_timestamps
            return False

    def _cleanup(self, cutoff: datetime) -> None:
        """Prune keys whose timestamps have all expired to keep memory bounded."""
        keys_to_remove = []
        for k, ts_list in self._records.items():
            valid = [ts for ts in ts_list if ts > cutoff]
            if not valid:
                keys_to_remove.append(k)
            else:
                self._records[k] = valid

        for k in keys_to_remove:
            self._records.pop(k, None)

    def reset(self) -> None:
        """Clear all stored rate limit records (useful for test isolation)."""
        with self._lock:
            self._records.clear()
            self._check_counter = 0


# Shared singleton instance for AI chat rate limiting
ai_chat_limiter = InMemoryRateLimiter()
