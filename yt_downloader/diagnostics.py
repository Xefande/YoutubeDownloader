"""Error reporting that also works from a windowed executable."""
from __future__ import annotations

import tempfile
from pathlib import Path


def write_error_report(details: str, app_dir: Path) -> Path | None:
    for path in (app_dir / "vod_gui_error.log", Path(tempfile.gettempdir()) / "YTDownloader-error.log"):
        try:
            path.write_text(details, encoding="utf-8")
            return path
        except OSError:
            continue
    return None
