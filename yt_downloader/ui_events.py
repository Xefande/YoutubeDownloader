"""Thread-safe UI mailbox and pure progress presentation.

Only the latest progress sample is retained. Terminal events are never dropped.
Workers use this module without importing or calling Tk.
"""
from __future__ import annotations

import math
import threading
from typing import Any


class WorkerEvents:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._progress: dict[str, Any] | None = None
        self._finished: list[tuple[str, tuple[str, str, str]]] = []

    def progress(self, event: dict[str, Any]) -> None:
        # Do not keep entire yt-dlp info_dict objects (large playlists).
        sample = {key: event.get(key) for key in (
            "status", "downloaded_bytes", "total_bytes", "total_bytes_estimate", "speed", "eta"
        )}
        with self._lock:
            self._progress = sample

    def finish(self, operation: str, status: str, label: str, detail: str) -> None:
        with self._lock:
            self._finished.append((operation, (status, label, detail)))

    def drain(self) -> tuple[dict[str, Any] | None, list[tuple[str, tuple[str, str, str]]]]:
        with self._lock:
            progress, finished = self._progress, self._finished
            self._progress, self._finished = None, []
        return progress, finished


def _number(value: Any) -> float | None:
    if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value):
        return max(0.0, float(value))
    return None


def format_progress(event: dict[str, Any]) -> tuple[float | None, str]:
    if event.get("status") == "finished":
        return None, "Transfer finished. Merging / processing media…"
    total = _number(event.get("total_bytes")) or _number(event.get("total_bytes_estimate"))
    downloaded = _number(event.get("downloaded_bytes"))
    if downloaded is None:
        return None, "Preparing media…"
    percent = min(100.0, downloaded / total * 100) if total else None
    size = f"{downloaded / 1048576:.1f} MB"
    detail = f"{percent:.1f}% · {size} / {total / 1048576:.1f} MB" if percent is not None else size
    speed, eta = _number(event.get("speed")), _number(event.get("eta"))
    if speed:
        detail += f" · {speed / 1048576:.1f} MB/s"
    if eta is not None:
        detail += f" · {int(eta)}s left"
    return percent, detail
