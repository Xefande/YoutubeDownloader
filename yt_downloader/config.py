from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path

from .presets import AUDIO_PRESETS, AUDIO_TRACK_LANGS_UI, BITRATE_PRESETS_UI, QUALITY_PRESETS, SUB_LANGS_UI


@dataclass
class AppConfig:
    out_dir: str = "downloads"
    after: str | None = None

    subs: bool = False
    subs_langs: list[str] = field(default_factory=lambda: ["hu", "en"])

    open_folder_after: bool = False

    quality_label: str = "Best available (H.264+AAC MP4 preferred)"
    max_video_bitrate_kbps: int | None = None
    audio_track_lang: str = "default"
    audio_only: bool = False
    audio_label: str = "Audio only (m4a - fast, no conversion)"

    concurrent_fragments: int = 4
    retries: int = 10
    fragment_retries: int = 10

    folder_template: str = "%(upload_date>%Y-%m-%d)s+%(title).120B"
    file_template: str = "%(id)s.%(ext)s"
    merge_output_format: str = "mp4"

    def __post_init__(self) -> None:
        if self.subs_langs is None:
            self.subs_langs = ["hu", "en"]


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("Settings must contain a JSON object.")
    return data


def write_json(path: Path, data: dict) -> None:
    """Replace settings only after a complete UTF-8 document has reached disk."""
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as file:
            staged = Path(file.name)
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


_write_json = write_json


def _as_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _positive_int(value: object, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return default
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        return default
    if parsed <= 0:
        return default
    return parsed


def load_or_create_config(config_path: Path) -> AppConfig:
    default_cfg = AppConfig()

    if not config_path.exists():
        write_json(config_path, asdict(default_cfg))
        return default_cfg

    return normalize_config(read_json(config_path))


def normalize_config(raw: dict) -> AppConfig:
    """Migrate persisted settings without mutating the supplied dictionary.

    Invalid field types fall back to defaults; an invalid date *string* stays
    visible so the user can correct it before starting a download.
    """
    if not isinstance(raw, dict):
        raise ValueError("Settings must contain a JSON object.")
    raw = dict(raw)
    default_cfg = AppConfig()

    if "output_template" in raw and "file_template" not in raw:
        raw["file_template"] = raw["output_template"]

    quality_migration = {
        "Best (H.264+AAC MP4 recommended)": "Best available (H.264+AAC MP4 preferred)",
        "Best (H.264+AAC MP4 aj\u0103\u02c7nlott)": "Best available (H.264+AAC MP4 preferred)",
        "Up to 2160p": "2160p max (4K)",
        "2160p max": "2160p max (4K)",
        "Up to 1440p": "1440p max (2K)",
        "1440p max": "1440p max (2K)",
        "Up to 1080p": "1080p max",
        "1080p max": "1080p max",
        "Up to 720p": "720p max",
        "720p max": "720p max",
        "Up to 480p": "480p max",
        "480p max": "480p max",
    }
    audio_migration = {
        "Csak hang (m4a \u00e2\u20ac\u201c gyors, konverzi\u0103\u0142 n\u0103\u00a9lk\u0103\u013dl)": "Audio only (m4a - fast, no conversion)",
        "Csak hang (mp3 \u00e2\u20ac\u201c ffmpeg kell)": "Audio only (mp3 - requires ffmpeg)",
        "Audio only (m4a – fast, no conversion)": "Audio only (m4a - fast, no conversion)",
        "Audio only (mp3 – requires ffmpeg)": "Audio only (mp3 - requires ffmpeg)",
        "Audio only (m4a \u00e2\u20ac\u201c fast, no conversion)": "Audio only (m4a - fast, no conversion)",
        "Audio only (mp3 \u00e2\u20ac\u201c requires ffmpeg)": "Audio only (mp3 - requires ffmpeg)",
    }
    if isinstance(raw.get("quality_label"), str):
        raw["quality_label"] = quality_migration.get(raw["quality_label"], raw["quality_label"])
    if isinstance(raw.get("audio_label"), str):
        raw["audio_label"] = audio_migration.get(raw["audio_label"], raw["audio_label"])

    if not isinstance(raw.get("quality_label"), str) or raw["quality_label"] not in QUALITY_PRESETS:
        raw["quality_label"] = default_cfg.quality_label
    if not isinstance(raw.get("audio_label"), str) or raw["audio_label"] not in AUDIO_PRESETS:
        raw["audio_label"] = default_cfg.audio_label

    label_to_code = {name: code for name, code in AUDIO_TRACK_LANGS_UI}
    codes = set(label_to_code.values())
    if isinstance(raw.get("audio_track_lang"), str):
        value = raw["audio_track_lang"].strip()
        if value in label_to_code:
            value = label_to_code[value]
        if value not in codes:
            value = "default"
        raw["audio_track_lang"] = value
    else:
        raw["audio_track_lang"] = default_cfg.audio_track_lang

    if "max_video_bitrate_kbps" in raw:
        value = raw.get("max_video_bitrate_kbps")
        if isinstance(value, str):
            value = value.strip()
            if value in BITRATE_PRESETS_UI:
                value = BITRATE_PRESETS_UI[value]
        raw["max_video_bitrate_kbps"] = _positive_int(value, 0) or None

    for name in ("out_dir", "folder_template", "file_template", "merge_output_format"):
        value = raw.get(name)
        raw[name] = value.strip() if isinstance(value, str) and value.strip() else getattr(default_cfg, name)
    if not isinstance(raw.get("after"), str):
        raw["after"] = None

    raw["subs"] = _as_bool(raw.get("subs"), default_cfg.subs)
    raw["open_folder_after"] = _as_bool(raw.get("open_folder_after"), default_cfg.open_folder_after)
    raw["audio_only"] = _as_bool(raw.get("audio_only"), default_cfg.audio_only)
    raw["concurrent_fragments"] = _positive_int(raw.get("concurrent_fragments"), default_cfg.concurrent_fragments)
    raw["retries"] = _positive_int(raw.get("retries"), default_cfg.retries)
    raw["fragment_retries"] = _positive_int(raw.get("fragment_retries"), default_cfg.fragment_retries)

    valid_sub_langs = {code for _, code in SUB_LANGS_UI}
    if isinstance(raw.get("subs_langs"), list):
        raw["subs_langs"] = [
            code
            for code in dict.fromkeys(str(item).strip() for item in raw["subs_langs"])
            if code in valid_sub_langs
        ]

    allowed = {field.name for field in fields(AppConfig)}
    cleaned = {key: value for key, value in raw.items() if key in allowed}
    merged = {**asdict(default_cfg), **cleaned}

    if not isinstance(merged.get("subs_langs"), list):
        merged["subs_langs"] = default_cfg.subs_langs

    return AppConfig(**merged)


def parse_after_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if "-" in value:
        date_value = datetime.strptime(value, "%Y-%m-%d")
        return date_value.strftime("%Y%m%d")
    if len(value) == 8 and value.isdigit():
        date_value = datetime.strptime(value, "%Y%m%d")
        return date_value.strftime("%Y%m%d")
    raise ValueError("After date must be YYYY-MM-DD or YYYYMMDD")


def make_match_filter(after_yyyymmdd: str | None):
    def _match_filter(info, *, incomplete):
        if after_yyyymmdd:
            upload_date = info.get("upload_date")
            if upload_date and upload_date < after_yyyymmdd:
                return f"SKIP: too old (upload_date={upload_date} < {after_yyyymmdd})"
        return None

    return _match_filter
