from __future__ import annotations

from typing import Any


SUB_LANGS_UI: list[tuple[str, str]] = [
    ("English (EN)", "en"),
    ("German (DE)", "de"),
    ("Hungarian (HU)", "hu"),
    ("Italian (IT)", "it"),
    ("French (FR)", "fr"),
    ("Spanish (ES)", "es"),
    ("Slovak (SK)", "sk"),
    ("Czech (CZ)", "cs"),
    ("Polish (PL)", "pl"),
]

# Display abbreviations can differ from the language codes used by yt-dlp.
SUB_LANG_SHORT_LABELS: dict[str, str] = {
    code: label.rsplit("(", 1)[-1].removesuffix(")") for label, code in SUB_LANGS_UI
}

QUALITY_PRESETS: dict[str, int | None] = {
    "Best available (H.264+AAC MP4 preferred)": None,
    "2160p max (4K)": 2160,
    "1440p max (2K)": 1440,
    "1080p max": 1080,
    "720p max": 720,
    "480p max": 480,
}

BITRATE_PRESETS_UI: dict[str, int | None] = {
    "No limit": None,
    "2 Mbps": 2000,
    "4 Mbps": 4000,
    "6 Mbps": 6000,
    "8 Mbps": 8000,
    "12 Mbps": 12000,
    "20 Mbps": 20000,
    "40 Mbps": 40000,
}

AUDIO_TRACK_LANGS_UI: list[tuple[str, str]] = [
    ("Default (original)", "default"),
    ("English", "en"),
    ("German", "de"),
    ("Italian", "it"),
    ("French", "fr"),
    ("Spanish", "es"),
    ("Polish", "pl"),
    ("Czech", "cs"),
    ("Slovak", "sk"),
    ("Hungarian", "hu"),
]

AUDIO_PRESETS: dict[str, dict[str, Any]] = {
    "Audio only (m4a - fast, no conversion)": {
        "format": "bestaudio[ext=m4a]/bestaudio/b",
        "extract_audio": False,
        "codec": None,
    },
    "Audio only (mp3 - requires ffmpeg)": {
        "format": "bestaudio/b",
        "extract_audio": True,
        "codec": "mp3",
    },
}

