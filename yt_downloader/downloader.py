from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config import AppConfig, make_match_filter, parse_after_date
from .formats import build_audio_only_format, build_video_format, choose_merge_output_format
from .presets import AUDIO_PRESETS, QUALITY_PRESETS

ProgressHook = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class DownloadPlan:
    out_dir: Path
    archive_file: Path
    max_height: int | None
    ydl_opts: dict[str, Any]


def resolve_output_dir(out_dir_value: str, app_dir: Path) -> Path:
    out_dir = Path(out_dir_value).expanduser()
    if not out_dir.is_absolute():
        out_dir = (app_dir / out_dir).resolve()
    return out_dir


def make_subtitle_renamer(logger: Any = None) -> ProgressHook:
    """Normalize subtitle names after yt-dlp has finished moving its files.

    Download progress fires too early: renaming there invalidates paths still
    owned by yt-dlp, and splitting a video ID at '-' corrupts hyphenated IDs.
    """
    def _rename_case_aware(path: Path, new_name: Path) -> None:
        if str(path) == str(new_name) or not path.exists():
            return
        if str(path).lower() == str(new_name).lower():
            temp_name = path.with_name(f"{path.name}.tmp-rename")
            counter = 0
            while temp_name.exists():
                counter += 1
                temp_name = path.with_name(f"{path.name}.{counter}.tmp-rename")
            path.rename(temp_name)
            try:
                temp_name.rename(new_name)
            except OSError:
                temp_name.rename(path)
                raise
            return
        path.rename(new_name)

    def _subtitle_renamer(event: dict[str, Any]) -> None:
        if event.get("status") != "finished" or event.get("postprocessor") != "MoveFiles":
            return
        info = event.get("info_dict") or {}
        moves = info.get("__files_to_move") or {}
        for lang, subtitle in (info.get("requested_subtitles") or {}).items():
            filename = subtitle.get("filepath")
            if not filename:
                continue
            moved = moves.get(filename)
            path = Path(moved or filename)
            if not path.exists() and info.get("filepath"):
                path = Path(info["filepath"]).parent / path.name
            language_suffix = "." + lang
            if not path.stem.endswith(language_suffix):
                continue
            base = path.stem[:-len(language_suffix)]
            new_name = path.with_name(f"{base}-{lang.upper()}{path.suffix}")
            try:
                _rename_case_aware(path, new_name)
                if new_name.exists():
                    subtitle["filepath"] = str(new_name)
            except OSError as exc:
                if logger is not None:
                    logger.warning(f"Could not normalize subtitle filename {path.name}: {exc}")

    return _subtitle_renamer


def build_download_plan(
    *,
    cfg: AppConfig,
    app_dir: Path,
    deno_exe: Path,
    ffmpeg_exe: Path,
    logger: Any,
    progress_hooks: list[ProgressHook] | None = None,
    dry_run: bool = False,
) -> DownloadPlan:
    out_dir = resolve_output_dir(cfg.out_dir, app_dir)
    archive_file = out_dir / ".ytdlp_archive.txt"
    after_yyyymmdd = parse_after_date(cfg.after)
    outtmpl_default = f"{cfg.folder_template}/{cfg.file_template}"

    max_height: int | None = None
    if cfg.audio_only:
        fmt = build_audio_only_format(audio_preset_key=cfg.audio_label, audio_lang_code=cfg.audio_track_lang)
    else:
        max_height = QUALITY_PRESETS.get(cfg.quality_label)
        fmt = build_video_format(
            max_height=max_height,
            max_video_bitrate_kbps=cfg.max_video_bitrate_kbps,
            audio_lang_code=cfg.audio_track_lang,
        )

    hooks: list[ProgressHook] = list(progress_hooks or [])

    ydl_opts: dict[str, Any] = {
        "paths": {"home": str(out_dir)},
        "outtmpl": {
            "default": outtmpl_default,
            "subtitle": f"{cfg.folder_template}/%(id)s.%(ext)s",
        },
        "windowsfilenames": True,
        "format": fmt,
        "download_archive": str(archive_file),
        "ignoreerrors": True,
        "retries": cfg.retries,
        "fragment_retries": cfg.fragment_retries,
        "concurrent_fragment_downloads": int(cfg.concurrent_fragments),
        "noplaylist": False,
        "match_filter": make_match_filter(after_yyyymmdd=after_yyyymmdd),
        "logger": logger,
        "progress_hooks": hooks,
    }

    if ffmpeg_exe.exists():
        ydl_opts["ffmpeg_location"] = str(ffmpeg_exe.parent)

    if deno_exe.exists():
        ydl_opts["js_runtimes"] = {"deno": {"path": str(deno_exe)}}
        ydl_opts["remote_components"] = ["ejs:github"]

    if not cfg.audio_only:
        ydl_opts["merge_output_format"] = choose_merge_output_format(cfg.merge_output_format, max_height)

    if cfg.subs:
        langs = list(dict.fromkeys(cfg.subs_langs or []))
        if len(langs) >= 3:
            ydl_opts["sleep_interval"] = 1
            ydl_opts["max_sleep_interval"] = 3
        ydl_opts.update(
            {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": langs,
            }
        )

    if dry_run:
        ydl_opts["simulate"] = True

    if cfg.audio_only:
        audio_preset = AUDIO_PRESETS.get(cfg.audio_label)
        if audio_preset and audio_preset.get("extract_audio"):
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_preset.get("codec", "mp3"),
                    "preferredquality": "0",
                }
            ]

    ydl_opts["postprocessor_hooks"] = [make_subtitle_renamer(logger)]
    return DownloadPlan(out_dir=out_dir, archive_file=archive_file, max_height=max_height, ydl_opts=ydl_opts)
