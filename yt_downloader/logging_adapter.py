from __future__ import annotations

import queue
import threading


class QueueLogger:
    """Thread-safe yt-dlp logging with bounded warning deduplication and counts."""

    def __init__(self, q: queue.Queue[str]):
        self.q = q
        self._seen: dict[str, None] = {}
        self._lock = threading.Lock()
        self.warning_count = 0
        self.error_count = 0

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        self.q.put(msg)

    def warning(self, msg: str) -> None:
        key = ("W:" + msg).strip()
        with self._lock:
            if key in self._seen:
                return
            if len(self._seen) >= 512:
                del self._seen[next(iter(self._seen))]
            self._seen[key] = None
            self.warning_count += 1
        self.q.put("WARNING: " + msg)

    def error(self, msg: str) -> None:
        with self._lock:
            self.error_count += 1
        self.q.put("ERROR: " + msg)


# Retained for integrations that imported the original UI-named adapter.
TkLogger = QueueLogger
