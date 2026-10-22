from __future__ import annotations

import sys
import importlib
from pathlib import Path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


APP_DIR = get_app_dir()
YTDLP_PYDEPS_DIR = APP_DIR / "_pydeps"
DEFAULT_CONFIG_PATH = APP_DIR / "vod_downloader.config.json"

DENO_EXE = APP_DIR / "deno.exe"
FFMPEG_EXE = APP_DIR / "ffmpeg.exe"
FFPROBE_EXE = APP_DIR / "ffprobe.exe"
FFPLAY_EXE = APP_DIR / "ffplay.exe"


def ensure_pydeps_first_on_syspath(pydeps_dir: Path = YTDLP_PYDEPS_DIR) -> None:
    if pydeps_dir.is_dir():
        p = str(pydeps_dir)
        sys.path[:] = [entry for entry in sys.path if entry != p]
        sys.path.insert(0, p)


def get_yt_dlp(pydeps_dir: Path = YTDLP_PYDEPS_DIR):
    ensure_pydeps_first_on_syspath(pydeps_dir)
    import yt_dlp  # type: ignore

    return yt_dlp


def reload_yt_dlp(pydeps_dir: Path = YTDLP_PYDEPS_DIR):
    ensure_pydeps_first_on_syspath(pydeps_dir)
    previous = {key: value for key, value in sys.modules.copy().items()
                if key == "yt_dlp" or key.startswith("yt_dlp.")}
    for key in previous:
        del sys.modules[key]
    importlib.invalidate_caches()
    try:
        return importlib.import_module("yt_dlp")
    except Exception:
        # Keep the currently working engine usable if a replacement cannot load.
        for key in list(sys.modules):
            if key == "yt_dlp" or key.startswith("yt_dlp."):
                del sys.modules[key]
        sys.modules.update(previous)
        raise
