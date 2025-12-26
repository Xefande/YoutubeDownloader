#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("Missing yt-dlp. Install: python -m pip install -U yt-dlp")
    sys.exit(1)


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "vod_downloader.config.json"


@dataclass
class AppConfig:
    out_dir: str = "downloads"
    vod_only: bool = True               # download only streams
    after: str | None = None            # "YYYY-MM-DD" or "YYYYMMDD"
    subs: bool = False
    concurrent_fragments: int = 4
    retries: int = 10
    fragment_retries: int = 10
    open_folder_after: bool = False     # open folder after download
    output_template: str = "%(upload_date>%Y-%m-%d)s - %(title).150B [%(id)s].%(ext)s"
    format: str = "bv*[vcodec^=avc1]+ba[acodec^=mp4a]/bv*+ba/b"
    merge_output_format: str = "mp4"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_or_create_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        cfg = AppConfig()
        _write_json(config_path, asdict(cfg))
        print(f"📝 Config created: {config_path}")
        print("   Edit config (out_dir stb.), and restart.")
        return cfg

    try:
        raw = _read_json(config_path)
        cfg = AppConfig(**{**asdict(AppConfig()), **raw})
        return cfg
    except Exception as e:
        print(f"❌ Cant read config file: {config_path}")
        print(f"   Error: {e}")
        sys.exit(2)


def parse_after_date(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    if "-" in s:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.strftime("%Y%m%d")
    if len(s) == 8 and s.isdigit():
        return s
    raise ValueError(" --after / config.after format YYYY-MM-DD or YYYYMMDD")


def make_match_filter(vod_only: bool, after_yyyymmdd: str | None):
    allowed_live_status = {"was_live", "post_live"}

    def _match_filter(info, *, incomplete):
        # upcoming / élő videókat ne
        if vod_only:
            live_status = info.get("live_status")
            if live_status not in allowed_live_status:
                return f"SKIP: nem befejezett stream VOD (live_status={live_status})"

        if after_yyyymmdd:
            upload_date = info.get("upload_date")  # "YYYYMMDD"
            if upload_date and upload_date < after_yyyymmdd:
                return f"SKIP: túl régi (upload_date={upload_date} < {after_yyyymmdd})"

        return None

    return _match_filter


def open_folder(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')  # noqa: S605
        else:
            os.system(f'xdg-open "{path}"')  # noqa: S605
    except Exception:
        pass


def prompt_urls() -> list[str]:
    print("")
    print("🔗 Illeszd be a letöltendő YouTube linket (üres Enter = kilépés).")
    print("   Tipp: csatorna stream oldal pl.: https://www.youtube.com/@NEV/streams")
    urls: list[str] = []
    while True:
        url = input("URL> ").strip()
        if not url:
            break
        urls.append(url)
    return urls


def build_ydl_opts(cfg: AppConfig, out_dir: Path, after_yyyymmdd: str | None, dry_run: bool) -> dict:
    archive_file = out_dir / ".ytdlp_archive.txt"

    ydl_opts = {
        "paths": {"home": str(out_dir)},
        "outtmpl": cfg.output_template,
        "windowsfilenames": True,

        "format": cfg.format,
        "merge_output_format": cfg.merge_output_format,

        "download_archive": str(archive_file),
        "ignoreerrors": True,
        "retries": cfg.retries,
        "fragment_retries": cfg.fragment_retries,
        "concurrent_fragment_downloads": int(cfg.concurrent_fragments),

        "noplaylist": False,
        "match_filter": make_match_filter(vod_only=cfg.vod_only, after_yyyymmdd=after_yyyymmdd),
    }

    if cfg.subs:
        ydl_opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["hu", "en", "all"],
        })

    if dry_run:
        ydl_opts["simulate"] = True

    return ydl_opts


def main():
    ap = argparse.ArgumentParser(
        description="YouTube stream VOD-ok letöltése (yt-dlp). Config + interaktív mód."
    )
    ap.add_argument("url", nargs="?", default=None, help="Videó / playlist / csatorna URL (opcionális, interaktív módban bekéri).")

    ap.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Config fájl útvonala (default: a script mellett).")
    ap.add_argument("-o", "--out", default=None, help="Kimeneti mappa (felülírja a config out_dir-t).")

    ap.add_argument("--include-non-live", action="store_true",
                    help="Ne szűrje ki a nem-stream videókat (alapból csak stream VOD).")
    ap.add_argument("--after", default=None, help="Csak ez UTÁN (YYYY-MM-DD vagy YYYYMMDD).")
    ap.add_argument("--subs", action="store_true", help="Feliratok mentése is (ha vannak).")
    ap.add_argument("--dry-run", action="store_true", help="Csak listáz, nem tölt le.")
    ap.add_argument("--open-folder", action="store_true", help="Letöltés után nyissa meg a kimeneti mappát.")
    ap.add_argument("--interactive", action="store_true", help="Mindig kérje be az URL-t konzolon.")
    args = ap.parse_args()

    cfg_path = Path(args.config).expanduser().resolve()
    cfg = load_or_create_config(cfg_path)

    # CLI felülírja configot, ha meg van adva
    if args.out is not None:
        cfg.out_dir = args.out
    if args.after is not None:
        cfg.after = args.after
    if args.subs:
        cfg.subs = True
    if args.include_non_live:
        cfg.vod_only = False
    if args.open_folder:
        cfg.open_folder_after = True

    out_dir = Path(cfg.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (SCRIPT_DIR / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        after_yyyymmdd = parse_after_date(cfg.after)
    except ValueError as e:
        print(str(e))
        sys.exit(2)

    urls: list[str] = []
    if args.interactive or not args.url:
        urls = prompt_urls()
        if not urls:
            print("Kilépés.")
            return
    else:
        urls = [args.url]

    ydl_opts = build_ydl_opts(cfg, out_dir, after_yyyymmdd, dry_run=args.dry_run)

    print("")
    print(f"📁 Kimenet mappa: {out_dir}")
    print(f"🗃️ Archív (ne töltse le újra): {out_dir / '.ytdlp_archive.txt'}")
    print(f"🎯 Szűrés: {'csak stream VOD' if cfg.vod_only else 'minden videó'}")
    if after_yyyymmdd:
        print(f"📅 Dátum szűrés: csak {after_yyyymmdd} után")
    print(f"🧩 Feliratok: {'igen' if cfg.subs else 'nem'}")
    print("")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(urls)

    if cfg.open_folder_after:
        open_folder(out_dir)


if __name__ == "__main__":
    main()
