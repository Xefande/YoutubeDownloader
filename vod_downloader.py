#!/usr/bin/env python3
#
# Welcome to Xefande's VOD Downloader 
# Best friend of VOD editor guy.
#

from __future__ import annotations

import json
import os
import queue
import re
import sys
import threading
from dataclasses import dataclass, asdict, fields, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except Exception as e:
    print("Tkinter nincs telepítve / elérhető ezen a Pythonon.")
    print("Windows-on általában alapból van. Hiba:", e)
    sys.exit(1)

try:
    import yt_dlp
except ImportError:
    print("Hiányzik a yt-dlp. Telepítés: python -m pip install -U yt-dlp")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "vod_downloader.config.json"

DENO_EXE = SCRIPT_DIR / "deno.exe"  # ha ide teszed, automatikusan használjuk

QUALITY_PRESETS: dict[str, str] = {
    "Best (H.264+AAC MP4 ajánlott)": "bv*[vcodec^=avc1]+ba[acodec^=mp4a]/bv*+ba/b",
    "1080p max": "bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=1080]/bv*+ba/b",
    "720p max": "bv*[height<=720][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=720]/bv*+ba/b",
    "480p max": "bv*[height<=480][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=480]/bv*+ba/b",
}

AUDIO_PRESETS: dict[str, dict[str, Any]] = {
    "Csak hang (m4a – gyors, konverzió nélkül)": {
        "format": "bestaudio[ext=m4a]/bestaudio/b",
        "extract_audio": False,
        "codec": None,
    },
    "Csak hang (mp3 – ffmpeg kell)": {
        "format": "bestaudio/b",
        "extract_audio": True,
        "codec": "mp3",
    },
}

# UI feliratnyelvek
SUB_LANGS_UI = [
    ("Magyar (HU)", "hu"),
    ("Angol (EN)", "en"),
    ("Német (DE)", "de"),
    ("Szlovák (SK)", "sk"),
    ("Cseh (CS)", "cs"),
    ("Lengyel (PL)", "pl"),
    ("Spanyol (ES)", "es"),
    ("Francia (FR)", "fr"),
]

# Felirat ext-ek, amiket átnevezünk
SUB_EXTS = {".vtt", ".srt", ".ass", ".ttml", ".srv1", ".srv2", ".srv3", ".json"}


@dataclass
class AppConfig:
    out_dir: str = "downloads"
    vod_only: bool = True
    after: str | None = None

    subs: bool = False
    subs_langs: list[str] = field(default_factory=lambda: ["hu", "en"])

    open_folder_after: bool = False

    quality_label: str = "Best (H.264+AAC MP4 ajánlott)"
    audio_only: bool = False
    audio_label: str = "Csak hang (m4a – gyors, konverzió nélkül)"

    concurrent_fragments: int = 4
    retries: int = 10
    fragment_retries: int = 10

    # Rövid, Windows path-biztos defaultok:
    # Almappa marad: yyyy-mm-dd + title (rövidítve)
    folder_template: str = "%(upload_date>%Y-%m-%d)s+%(title).50B"
    # Fájl: CSAK ID
    file_template: str = "%(id)s.%(ext)s"
    merge_output_format: str = "mp4"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_or_create_config(config_path: Path) -> AppConfig:
    default_cfg = AppConfig()

    # HA NINCS CONFIG -> ALAPBÓL A JÓ BEÁLLÍTÁSOKKAL HOZZUK LÉTRE
    if not config_path.exists():
        _write_json(config_path, asdict(default_cfg))
        return default_cfg

    raw = _read_json(config_path)

    # régi kulcsok migrálása / tisztítása
    if "output_template" in raw and "file_template" not in raw:
        raw["file_template"] = raw["output_template"]

    # régi, már nem használt opciót kidobjuk
    raw.pop("subs_all_languages", None)

    # subs_langs ha véletlen string volt
    if isinstance(raw.get("subs_langs"), str):
        raw["subs_langs"] = [x.strip() for x in raw["subs_langs"].split(",") if x.strip()]

    # Ha régi hosszú sablon volt, cseréljük le a mostani, path-biztosra
    ft = str(raw.get("file_template") or "")
    if (not ft) or ("%(title)" in ft) or ("%(upload_date" in ft) or ("[%(id)s]" in ft):
        raw["file_template"] = default_cfg.file_template

    fld = str(raw.get("folder_template") or "")
    if (not fld) or (".120B" in fld) or (".60B" in fld and "%(title)" in fld and "%(upload_date" in fld):
        # nem erőltetjük, de ha gyanúsan régi/hosszú, akkor rövidítjük
        raw["folder_template"] = default_cfg.folder_template

    # ismeretlen kulcsok eldobása
    allowed = {f.name for f in fields(AppConfig)}
    cleaned = {k: v for k, v in raw.items() if k in allowed}

    merged = {**asdict(default_cfg), **cleaned}
    cfg = AppConfig(**merged)

    if not cfg.subs_langs:
        cfg.subs_langs = ["hu", "en"]

    return cfg


def parse_after_date(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    if "-" in s:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.strftime("%Y%m%d")
    if len(s) == 8 and s.isdigit():
        return s
    raise ValueError("Az 'after' formátum legyen YYYY-MM-DD vagy YYYYMMDD")


def make_match_filter(vod_only: bool, after_yyyymmdd: str | None):
    allowed_live_status = {"was_live", "post_live"}

    def _match_filter(info, *, incomplete):
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
            os.startfile(str(path))  # noqa
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception:
        pass


class TkLogger:
    def __init__(self, q: queue.Queue[str]):
        self.q = q

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        self.q.put(msg)

    def warning(self, msg: str) -> None:
        self.q.put("WARNING: " + msg)

    def error(self, msg: str) -> None:
        self.q.put("ERROR: " + msg)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube VOD Downloader (GUI)")
        self.geometry("980x760")
        self.minsize(820, 600)

        self.config_path = DEFAULT_CONFIG_PATH
        self.cfg = load_or_create_config(self.config_path)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.downloading = False
        self._last_finished_media: str | None = None

        self._build_ui()
        self._load_cfg_into_ui()
        self._poll_log_queue()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        url_frame = ttk.LabelFrame(root, text="YouTube link(ek)", padding=10)
        url_frame.pack(fill="x")

        ttk.Label(url_frame, text="Több linket is beilleszthetsz (soronként 1).").pack(anchor="w")
        self.txt_urls = tk.Text(url_frame, height=4, wrap="word")
        self.txt_urls.pack(fill="x", pady=(6, 0))

        settings = ttk.LabelFrame(root, text="Beállítások", padding=10)
        settings.pack(fill="x", pady=(10, 0))

        grid = ttk.Frame(settings)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        ttk.Label(grid, text="Letöltési mappa:").grid(row=0, column=0, sticky="w")
        self.var_out = tk.StringVar()
        ttk.Entry(grid, textvariable=self.var_out).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(grid, text="Browse…", command=self._browse_out).grid(row=0, column=2, sticky="e")

        ttk.Label(grid, text="After (opcionális):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.var_after = tk.StringVar()
        ttk.Entry(grid, textvariable=self.var_after).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(8, 0))
        ttk.Label(grid, text="YYYY-MM-DD vagy YYYYMMDD").grid(row=1, column=2, sticky="e", pady=(8, 0))

        mode = ttk.Frame(settings)
        mode.pack(fill="x", pady=(10, 0))
        mode.columnconfigure(2, weight=1)

        self.var_audio_only = tk.BooleanVar()
        ttk.Checkbutton(
            mode,
            text="Csak hang letöltése",
            variable=self.var_audio_only,
            command=self._refresh_mode_ui
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(mode, text="Hang mód:").grid(row=0, column=1, sticky="e", padx=(14, 6))
        self.var_audio_label = tk.StringVar()
        self.cmb_audio = ttk.Combobox(
            mode,
            textvariable=self.var_audio_label,
            values=list(AUDIO_PRESETS.keys()),
            state="readonly",
            width=42
        )
        self.cmb_audio.grid(row=0, column=2, sticky="w")

        ttk.Label(mode, text="Minőség:").grid(row=1, column=1, sticky="e", padx=(14, 6), pady=(8, 0))
        self.var_quality = tk.StringVar()
        self.cmb_quality = ttk.Combobox(
            mode,
            textvariable=self.var_quality,
            values=list(QUALITY_PRESETS.keys()),
            state="readonly",
            width=42
        )
        self.cmb_quality.grid(row=1, column=2, sticky="w", pady=(8, 0))

        self.var_vod_only = tk.BooleanVar()
        self.var_subs = tk.BooleanVar()
        self.var_dry = tk.BooleanVar()
        self.var_open_folder = tk.BooleanVar()

        checks = ttk.Frame(settings)
        checks.pack(fill="x", pady=(10, 0))

        ttk.Checkbutton(checks, text="Csak stream VOD (was_live / post_live)", variable=self.var_vod_only)\
            .grid(row=0, column=0, sticky="w")

        ttk.Checkbutton(
            checks,
            text="Feliratok mentése",
            variable=self.var_subs,
            command=self._refresh_subs_ui
        ).grid(row=0, column=1, sticky="w", padx=(14, 0))

        ttk.Checkbutton(checks, text="Csak teszt (dry-run) – nem tölt le", variable=self.var_dry)\
            .grid(row=1, column=0, sticky="w", pady=(6, 0))

        ttk.Checkbutton(checks, text="Letöltés után nyissa meg a mappát", variable=self.var_open_folder)\
            .grid(row=1, column=1, sticky="w", padx=(14, 0), pady=(6, 0))

        # Felirat nyelvválasztó
        self.sub_lang_vars: dict[str, tk.BooleanVar] = {}
        self.sub_lang_checks: list[ttk.Checkbutton] = []

        self.frm_sub_langs = ttk.LabelFrame(settings, text="Felirat nyelvek", padding=10)
        self.frm_sub_langs.pack(fill="x", pady=(10, 0))

        for i, (label, code) in enumerate(SUB_LANGS_UI):
            var = tk.BooleanVar()
            self.sub_lang_vars[code] = var
            cb = ttk.Checkbutton(self.frm_sub_langs, text=label, variable=var)
            cb.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 18), pady=(0, 6))
            self.sub_lang_checks.append(cb)

        ttk.Label(
            settings,
            text="Minden videó külön almappába kerül: yyyy-mm-dd+videó címe (rövidítve, Windows path-biztosan)."
        ).pack(anchor="w", pady=(10, 0))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(10, 0))

        self.btn_start = ttk.Button(btns, text="Start letöltés", command=self._start_download)
        self.btn_start.pack(side="left")

        self.btn_save = ttk.Button(btns, text="Config mentése", command=self._save_config_from_ui)
        self.btn_save.pack(side="left", padx=(10, 0))

        ttk.Button(btns, text="Log törlése", command=self._clear_log).pack(side="left", padx=(10, 0))

        log_frame = ttk.LabelFrame(root, text="Log / Progress", padding=10)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.txt_log = tk.Text(log_frame, wrap="word")
        self.txt_log.pack(side="left", fill="both", expand=True)

        scr = ttk.Scrollbar(log_frame, orient="vertical", command=self.txt_log.yview)
        scr.pack(side="right", fill="y")
        self.txt_log.configure(yscrollcommand=scr.set)

        self._log(f"Config: {self.config_path}")
        self._refresh_mode_ui()
        self._refresh_subs_ui()

    def _refresh_subs_ui(self):
        enabled = bool(self.var_subs.get())
        for cb in self.sub_lang_checks:
            cb.configure(state=("normal" if enabled else "disabled"))

    def _refresh_mode_ui(self):
        audio_only = bool(self.var_audio_only.get())
        if audio_only:
            self.cmb_quality.configure(state="disabled")
            self.cmb_audio.configure(state="readonly")
        else:
            self.cmb_quality.configure(state="readonly")
            self.cmb_audio.configure(state="disabled")

    def _browse_out(self):
        initial = self.var_out.get().strip() or str(SCRIPT_DIR)
        selected = filedialog.askdirectory(initialdir=initial, title="Válaszd ki a letöltési mappát")
        if selected:
            self.var_out.set(selected)

    def _clear_log(self):
        self.txt_log.delete("1.0", "end")

    def _log(self, msg: str):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._log(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    def _load_cfg_into_ui(self):
        self.var_out.set(self.cfg.out_dir)
        self.var_after.set(self.cfg.after or "")
        self.var_vod_only.set(self.cfg.vod_only)

        self.var_subs.set(self.cfg.subs)
        self.var_open_folder.set(self.cfg.open_folder_after)

        selected = set(self.cfg.subs_langs or [])
        for _, code in SUB_LANGS_UI:
            self.sub_lang_vars[code].set(code in selected)

        # default: ha semmi nincs pipálva, legyen HU+EN
        if not any(v.get() for v in self.sub_lang_vars.values()):
            self.sub_lang_vars["hu"].set(True)
            self.sub_lang_vars["en"].set(True)

        self.var_audio_only.set(self.cfg.audio_only)
        self.var_quality.set(
            self.cfg.quality_label if self.cfg.quality_label in QUALITY_PRESETS else list(QUALITY_PRESETS.keys())[0]
        )
        self.var_audio_label.set(
            self.cfg.audio_label if self.cfg.audio_label in AUDIO_PRESETS else list(AUDIO_PRESETS.keys())[0]
        )

        self._refresh_mode_ui()
        self._refresh_subs_ui()

    def _save_config_from_ui(self):
        try:
            cfg = self._collect_cfg_from_ui()
        except Exception as e:
            messagebox.showerror("Hiba", str(e))
            return
        _write_json(self.config_path, asdict(cfg))
        self.cfg = cfg
        self._log(f"✅ Config mentve: {self.config_path}")

    def _collect_cfg_from_ui(self) -> AppConfig:
        out_dir = self.var_out.get().strip()
        if not out_dir:
            raise ValueError("Adj meg egy letöltési mappát!")

        after = self.var_after.get().strip() or None
        _ = parse_after_date(after)

        audio_only = bool(self.var_audio_only.get())
        quality_label = (self.var_quality.get().strip() or list(QUALITY_PRESETS.keys())[0])
        audio_label = (self.var_audio_label.get().strip() or list(AUDIO_PRESETS.keys())[0])

        if quality_label not in QUALITY_PRESETS:
            quality_label = list(QUALITY_PRESETS.keys())[0]
        if audio_label not in AUDIO_PRESETS:
            audio_label = list(AUDIO_PRESETS.keys())[0]

        subs_langs = [code for _, code in SUB_LANGS_UI if self.sub_lang_vars[code].get()]
        if not subs_langs:
            subs_langs = ["hu", "en"]

        return AppConfig(
            out_dir=out_dir,
            vod_only=bool(self.var_vod_only.get()),
            after=after,

            subs=bool(self.var_subs.get()),
            subs_langs=subs_langs,

            open_folder_after=bool(self.var_open_folder.get()),
            quality_label=quality_label,
            audio_only=audio_only,
            audio_label=audio_label,
            concurrent_fragments=self.cfg.concurrent_fragments,
            retries=self.cfg.retries,
            fragment_retries=self.cfg.fragment_retries,

            # ezek maradnak defaulton (ID alapú fájlnevek)
            folder_template=self.cfg.folder_template,
            file_template=self.cfg.file_template,
            merge_output_format=self.cfg.merge_output_format,
        )

    def _get_urls(self) -> list[str]:
        raw = self.txt_urls.get("1.0", "end").strip()
        if not raw:
            return []
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]

    def _start_download(self):
        if self.downloading:
            return

        urls = self._get_urls()
        if not urls:
            messagebox.showwarning("Hiányzó URL", "Illessz be legalább 1 YouTube linket (soronként 1)!")
            return

        try:
            cfg = self._collect_cfg_from_ui()
        except Exception as e:
            messagebox.showerror("Hiba", str(e))
            return

        # mentjük a configot minden startnál is
        _write_json(self.config_path, asdict(cfg))
        self.cfg = cfg

        self.btn_start.configure(state="disabled")
        self.btn_save.configure(state="disabled")
        self.downloading = True
        self._last_finished_media = None

        self._log("========================================")
        self._log("▶ Letöltés indul…")
        self._log(f"URL-ek száma: {len(urls)}")
        self._log(f"Kimenet: {cfg.out_dir}")
        self._log(f"Mód: {'csak hang' if cfg.audio_only else 'videó'}")
        if cfg.audio_only:
            self._log(f"Hang preset: {cfg.audio_label}")
        else:
            self._log(f"Minőség preset: {cfg.quality_label}")
        self._log(f"Szűrés: {'csak VOD' if cfg.vod_only else 'minden videó'}")

        if cfg.subs:
            self._log("Feliratok: " + ", ".join([c.upper() for c in cfg.subs_langs]))
        else:
            self._log("Feliratok: nem")

        self._log(f"Dry-run: {'igen' if self.var_dry.get() else 'nem'}")
        if not DENO_EXE.exists():
            self._log("⚠ Tipp: nincs deno.exe a mappában → YouTube formátumok hiányozhatnak. (JS runtime warning)")
        self._log("========================================")

        t = threading.Thread(target=self._download_thread, args=(cfg, urls, bool(self.var_dry.get())), daemon=True)
        t.start()

    def _download_thread(self, cfg: AppConfig, urls: list[str], dry_run: bool):
        def _subtitle_uppercase_lang(path: Path) -> None:
            # várható minta: <id>-<lang>.<ext>  pl: dSPc5GHMydw-hu.vtt
            m = re.match(r"^(?P<id>[A-Za-z0-9_-]{6,})-(?P<lang>[^.]+)(?P<ext>\.[^.]+)$", path.name)
            if not m:
                return
            new_name = f"{m.group('id')}-{m.group('lang').upper()}{m.group('ext')}"
            if new_name == path.name:
                return
            dst = path.with_name(new_name)
            try:
                # Windows: case-only rename néha trükkös → kétlépcsős
                if str(path).lower() == str(dst).lower() and str(path) != str(dst):
                    tmp = path.with_name(path.name + ".tmp_case")
                    path.rename(tmp)
                    tmp.rename(dst)
                else:
                    path.rename(dst)
            except Exception:
                pass

        try:
            out_dir = Path(cfg.out_dir).expanduser()
            if not out_dir.is_absolute():
                out_dir = (SCRIPT_DIR / out_dir).resolve()
            out_dir.mkdir(parents=True, exist_ok=True)

            archive_file = out_dir / ".ytdlp_archive.txt"
            after_yyyymmdd = parse_after_date(cfg.after)

            # ID alapú fájlnév + felirat: ID-LANG
            outtmpl_default = f"{cfg.folder_template}/{cfg.file_template}"  # file_template = "%(id)s.%(ext)s"
            outtmpl_subtitle = f"{cfg.folder_template}/%(id)s-%(language)s.%(ext)s"

            def progress_hook(d: dict[str, Any]):
                status = d.get("status")
                fn = d.get("filename") or ""
                p = Path(fn) if fn else None

                if status == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes")
                    speed = d.get("speed")
                    eta = d.get("eta")
                    if total and downloaded:
                        pct = downloaded / total * 100.0
                        msg = f"⬇ {pct:5.1f}%  {downloaded/1024/1024:6.1f}MB / {total/1024/1024:6.1f}MB"
                        if speed:
                            msg += f"  {speed/1024/1024:4.1f}MB/s"
                        if eta:
                            msg += f"  ETA {eta}s"
                        self.log_queue.put(msg)

                elif status == "finished":
                    if p is None:
                        return

                    # Felirat: rename id-hu.vtt -> id-HU.vtt
                    if p.suffix.lower() in SUB_EXTS and "-" in p.name:
                        _subtitle_uppercase_lang(p)
                        return

                    # Média: csak egyszer logoljuk
                    media_exts = (".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".aac", ".opus")
                    if p.name.lower().endswith(media_exts):
                        low = str(p).lower()
                        if low != (self._last_finished_media or ""):
                            self._last_finished_media = low
                            self.log_queue.put("✅ Média letöltés kész, merge/utómunka…")

            # format kiválasztás
            if cfg.audio_only:
                a = AUDIO_PRESETS.get(cfg.audio_label, list(AUDIO_PRESETS.values())[0])
                fmt = a["format"]
            else:
                fmt = QUALITY_PRESETS.get(cfg.quality_label, list(QUALITY_PRESETS.values())[0])

            ydl_opts: dict[str, Any] = {
                "paths": {"home": str(out_dir)},
                "outtmpl": {
                    "default": outtmpl_default,
                    "subtitle": outtmpl_subtitle,
                },
                "windowsfilenames": True,
                "format": fmt,
                "download_archive": str(archive_file),
                "ignoreerrors": True,
                "retries": cfg.retries,
                "fragment_retries": cfg.fragment_retries,
                "concurrent_fragment_downloads": int(cfg.concurrent_fragments),
                "noplaylist": False,
                "match_filter": make_match_filter(vod_only=cfg.vod_only, after_yyyymmdd=after_yyyymmdd),
                "logger": TkLogger(self.log_queue),
                "progress_hooks": [progress_hook],
            }

            # JS runtime (deno) automatikusan
            if DENO_EXE.exists():
                ydl_opts["js_runtimes"] = {"deno": {"path": str(DENO_EXE)}}

            # videó módban mp4 merge prefer
            if not cfg.audio_only:
                ydl_opts["merge_output_format"] = cfg.merge_output_format

            # feliratok: választott nyelvek (nincs "all")
            if cfg.subs:
                langs = list(dict.fromkeys(cfg.subs_langs))  # unique
                # sok nyelvnél óvatos lassítás (429 ellen)
                if len(langs) >= 4:
                    ydl_opts["sleep_interval"] = 1
                    ydl_opts["max_sleep_interval"] = 2

                ydl_opts.update({
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": langs,
                })

            if dry_run:
                ydl_opts["simulate"] = True

            # Audio-only + mp3: ffmpeg postprocess
            if cfg.audio_only:
                a = AUDIO_PRESETS.get(cfg.audio_label, None)
                if a and a.get("extract_audio"):
                    ydl_opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": a.get("codec", "mp3"),
                        "preferredquality": "0",
                    }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ret = ydl.download(urls)

            if ret == 0:
                self.log_queue.put("🎉 Kész!")
            else:
                self.log_queue.put("⚠ Befejezve hibákkal (nézd a WARNING/ERROR sorokat fentebb).")

            if cfg.open_folder_after:
                open_folder(out_dir)

        except Exception as e:
            self.log_queue.put(f"❌ Hiba: {e}")
        finally:
            self.after(0, self._download_finished)

    def _download_finished(self):
        self.downloading = False
        self.btn_start.configure(state="normal")
        self.btn_save.configure(state="normal")


if __name__ == "__main__":
    import traceback
    try:
        App().mainloop()
    except Exception:
        tb = traceback.format_exc()
        log_path = (SCRIPT_DIR / "vod_gui_error.log")
        log_path.write_text(tb, encoding="utf-8")
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("Hiba induláskor", f"A program hibával leállt.\n\nRészletek:\n{log_path}")
            r.destroy()
        except Exception:
            pass
        raise
