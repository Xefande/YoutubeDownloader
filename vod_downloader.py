\

# ----------------------------
# Created for VOD editor guys and for lokalization teams to allow
# easy downloading of VODs and subitles from YouTube.
# by Xefande
# ----------------------------

#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import queue
import shutil
import sys
import threading
import urllib.request
import zipfile
from dataclasses import dataclass, asdict, fields
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except Exception as e:
    print("Tkinter is not available on this Python installation.")
    print("On Windows it is usually included by default. Error:", e)
    sys.exit(1)

try:
    import yt_dlp
except ImportError:
    print("Missing dependency: yt-dlp")
    print("Install: python -m pip install -U yt-dlp")
    sys.exit(1)


# ----------------------------
# Paths (work both in script and PyInstaller builds)
# ----------------------------
def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
DEFAULT_CONFIG_PATH = APP_DIR / "vod_downloader.config.json"

DENO_EXE = APP_DIR / "deno.exe"
FFMPEG_EXE = APP_DIR / "ffmpeg.exe"
FFPROBE_EXE = APP_DIR / "ffprobe.exe"
FFPLAY_EXE = APP_DIR / "ffplay.exe"

# One-click updater sources (Windows x64)
DENO_WIN64_ZIP_URL = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
FFMPEG_ESSENTIALS_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# Subtitles in UI (label, yt-dlp lang code)
SUB_LANGS_UI: list[tuple[str, str]] = [
    ("Hungarian (HU)", "hu"),
    ("German (DE)", "de"),
    ("English (EN)", "en"),
    ("Slovak (SK)", "sk"),
    ("Czech (CS)", "cs"),
    ("Polish (PL)", "pl"),
    ("Spanish (ES)", "es"),
    ("French (FR)", "fr"),
    ("Italian (IT)", "it"),
]

QUALITY_PRESETS: dict[str, str] = {
    "Best (H.264+AAC MP4 recommended)": "bv*[vcodec^=avc1]+ba[acodec^=mp4a]/bv*+ba/b",
    "Up to 1080p": "bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=1080]/bv*+ba/b",
    "Up to 720p": "bv*[height<=720][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=720]/bv*+ba/b",
    "Up to 480p": "bv*[height<=480][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=480]/bv*+ba/b",
}

AUDIO_PRESETS: dict[str, dict[str, Any]] = {
    "Audio only (m4a – fast, no conversion)": {
        "format": "bestaudio[ext=m4a]/bestaudio/b",
        "extract_audio": False,
        "codec": None,
    },
    "Audio only (mp3 – requires ffmpeg)": {
        "format": "bestaudio/b",
        "extract_audio": True,
        "codec": "mp3",
    },
}


# ----------------------------
# Config
# ----------------------------
@dataclass
class AppConfig:
    out_dir: str = "downloads"
    after: str | None = None

    subs: bool = False
    subs_langs: list[str] = None  # type: ignore[assignment]

    open_folder_after: bool = False

    quality_label: str = "Best (H.264+AAC MP4 recommended)"
    audio_only: bool = False
    audio_label: str = "Audio only (m4a – fast, no conversion)"

    concurrent_fragments: int = 4
    retries: int = 10
    fragment_retries: int = 10

    folder_template: str = "%(upload_date>%Y-%m-%d)s+%(title).120B"
    file_template: str = "%(id)s.%(ext)s"  # video/audio: just the ID
    merge_output_format: str = "mp4"

    def __post_init__(self):
        if self.subs_langs is None:
            self.subs_langs = ["hu", "en"]


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_or_create_config(config_path: Path) -> AppConfig:
    default_cfg = AppConfig()

    if not config_path.exists():
        _write_json(config_path, asdict(default_cfg))
        return default_cfg

    raw = _read_json(config_path)

    # --- migrations from older builds (safe / best effort) ---
    # 1) old key name
    if "output_template" in raw and "file_template" not in raw:
        raw["file_template"] = raw["output_template"]

    # 2) old Hungarian preset labels -> new English ones
    quality_migration = {
        "Best (H.264+AAC MP4 ajánlott)": "Best (H.264+AAC MP4 recommended)",
        "1080p max": "Up to 1080p",
        "720p max": "Up to 720p",
        "480p max": "Up to 480p",
    }
    audio_migration = {
        "Csak hang (m4a – gyors, konverzió nélkül)": "Audio only (m4a – fast, no conversion)",
        "Csak hang (mp3 – ffmpeg kell)": "Audio only (mp3 – requires ffmpeg)",
    }
    if isinstance(raw.get("quality_label"), str):
        raw["quality_label"] = quality_migration.get(raw["quality_label"], raw["quality_label"])
    if isinstance(raw.get("audio_label"), str):
        raw["audio_label"] = audio_migration.get(raw["audio_label"], raw["audio_label"])

    # drop unknown keys
    allowed = {f.name for f in fields(AppConfig)}
    cleaned = {k: v for k, v in raw.items() if k in allowed}

    merged = {**asdict(default_cfg), **cleaned}

    # Ensure list type for subs_langs
    subs_langs = merged.get("subs_langs")
    if not isinstance(subs_langs, list):
        merged["subs_langs"] = default_cfg.subs_langs

    return AppConfig(**merged)


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
    raise ValueError("After date must be YYYY-MM-DD or YYYYMMDD")


def make_match_filter(after_yyyymmdd: str | None):
    def _match_filter(info, *, incomplete):
        if after_yyyymmdd:
            upload_date = info.get("upload_date")  # "YYYYMMDD"
            if upload_date and upload_date < after_yyyymmdd:
                return f"SKIP: too old (upload_date={upload_date} < {after_yyyymmdd})"
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


# ----------------------------
# Logging helpers
# ----------------------------
class TkLogger:
    """
    yt-dlp logger adapter -> pushes lines to Tk queue.
    Also suppresses very repetitive warnings.
    """

    def __init__(self, q: queue.Queue[str]):
        self.q = q
        self._seen: set[str] = set()

    def debug(self, msg: str) -> None:
        # keep log cleaner; enable if you want
        pass

    def info(self, msg: str) -> None:
        self.q.put(msg)

    def warning(self, msg: str) -> None:
        # de-dup spammy warnings
        key = ("W:" + msg).strip()
        if key in self._seen:
            return
        self._seen.add(key)
        self.q.put("WARNING: " + msg)

    def error(self, msg: str) -> None:
        self.q.put("ERROR: " + msg)


# ----------------------------
# Updater (deno / ffmpeg)
# ----------------------------
def _download_with_progress(url: str, dest: Path, logq: queue.Queue[str], label: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "YTDownloader/1.0 (+https://example.invalid)",
            "Accept": "*/*",
        },
    )

    with urllib.request.urlopen(req) as resp, dest.open("wb") as f:
        total = resp.headers.get("Content-Length")
        total_bytes = int(total) if total and total.isdigit() else None
        downloaded = 0

        chunk = 1024 * 256
        while True:
            buf = resp.read(chunk)
            if not buf:
                break
            f.write(buf)
            downloaded += len(buf)
            if total_bytes:
                pct = downloaded / total_bytes * 100.0
                logq.put(f"⬇ {label}: {pct:5.1f}% ({downloaded/1024/1024:.1f}MB / {total_bytes/1024/1024:.1f}MB)")
            else:
                logq.put(f"⬇ {label}: {downloaded/1024/1024:.1f}MB")


def _extract_exe_from_zip(zip_path: Path, exe_name: str, out_path: Path) -> bool:
    """
    Extracts the first matching exe_name found in the zip and writes it to out_path.
    Returns True if extracted.
    """
    with zipfile.ZipFile(zip_path, "r") as z:
        candidates = [n for n in z.namelist() if n.lower().endswith("/" + exe_name.lower()) or n.lower().endswith("\\" + exe_name.lower()) or n.lower().endswith(exe_name.lower())]
        # Prefer bin/ paths if available
        candidates.sort(key=lambda n: ("/bin/" not in n.replace("\\", "/").lower(), len(n)))
        if not candidates:
            return False

        member = candidates[0]
        with z.open(member) as src, out_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    return True


def update_tools(app_dir: Path, logq: queue.Queue[str]) -> None:
    """
    Updates deno.exe, ffmpeg.exe, ffprobe.exe, ffplay.exe in app_dir.
    Downloads archives to a temp folder, then overwrites exes.
    """
    tmp = app_dir / "_update_tmp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)

    try:
        # --- deno ---
        logq.put("▶ Updating deno…")
        deno_zip = tmp / "deno.zip"
        _download_with_progress(DENO_WIN64_ZIP_URL, deno_zip, logq, "deno")
        deno_out = tmp / "deno.exe"
        if not _extract_exe_from_zip(deno_zip, "deno.exe", deno_out):
            raise RuntimeError("Could not find deno.exe in the downloaded zip.")
        shutil.copy2(deno_out, app_dir / "deno.exe")
        logq.put("✅ deno.exe updated.")

        # --- ffmpeg bundle ---
        logq.put("▶ Updating ffmpeg (ffmpeg/ffprobe/ffplay)…")
        ff_zip = tmp / "ffmpeg.zip"
        _download_with_progress(FFMPEG_ESSENTIALS_ZIP_URL, ff_zip, logq, "ffmpeg")
        for exe in ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]:
            out = tmp / exe
            if _extract_exe_from_zip(ff_zip, exe, out):
                shutil.copy2(out, app_dir / exe)
                logq.put(f"✅ {exe} updated.")
            else:
                logq.put(f"⚠ {exe} not found in ffmpeg zip (skipped).")

        logq.put("🎉 Tools updated successfully.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------
# Tk App
# ----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Xefande's VOD Downloader")
        self.geometry("1020x730")
        self.minsize(880, 610)

        self.config_path = DEFAULT_CONFIG_PATH
        self.cfg = load_or_create_config(self.config_path)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.downloading = False
        self.updating = False
        self._last_finished_media: str | None = None

        self._build_ui()
        self._load_cfg_into_ui()
        self._poll_log_queue()

    # ---------- UI ----------
    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        url_frame = ttk.LabelFrame(root, text="YouTube links", padding=10)
        url_frame.pack(fill="x")

        ttk.Label(url_frame, text="Paste one link per line.").pack(anchor="w")
        self.txt_urls = tk.Text(url_frame, height=4, wrap="word")
        self.txt_urls.pack(fill="x", pady=(6, 0))

        settings = ttk.LabelFrame(root, text="Settings", padding=10)
        settings.pack(fill="x", pady=(10, 0))

        grid = ttk.Frame(settings)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        ttk.Label(grid, text="Output folder:").grid(row=0, column=0, sticky="w")
        self.var_out = tk.StringVar()
        ttk.Entry(grid, textvariable=self.var_out).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(grid, text="Browse…", command=self._browse_out).grid(row=0, column=2, sticky="e")

        ttk.Label(grid, text="After date (optional):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.var_after = tk.StringVar()
        ttk.Entry(grid, textvariable=self.var_after).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(8, 0))
        ttk.Label(grid, text="YYYY-MM-DD or YYYYMMDD").grid(row=1, column=2, sticky="e", pady=(8, 0))

        mode = ttk.Frame(settings)
        mode.pack(fill="x", pady=(10, 0))
        mode.columnconfigure(2, weight=1)

        self.var_audio_only = tk.BooleanVar()
        ttk.Checkbutton(mode, text="Audio only", variable=self.var_audio_only, command=self._refresh_mode_ui).grid(row=0, column=0, sticky="w")

        ttk.Label(mode, text="Audio mode:").grid(row=0, column=1, sticky="e", padx=(14, 6))
        self.var_audio_label = tk.StringVar()
        self.cmb_audio = ttk.Combobox(mode, textvariable=self.var_audio_label, values=list(AUDIO_PRESETS.keys()), state="readonly", width=44)
        self.cmb_audio.grid(row=0, column=2, sticky="w")

        ttk.Label(mode, text="Quality:").grid(row=1, column=1, sticky="e", padx=(14, 6), pady=(8, 0))
        self.var_quality = tk.StringVar()
        self.cmb_quality = ttk.Combobox(mode, textvariable=self.var_quality, values=list(QUALITY_PRESETS.keys()), state="readonly", width=44)
        self.cmb_quality.grid(row=1, column=2, sticky="w", pady=(8, 0))

        self.var_subs = tk.BooleanVar()
        self.var_dry = tk.BooleanVar()
        self.var_open_folder = tk.BooleanVar()

        checks = ttk.Frame(settings)
        checks.pack(fill="x", pady=(10, 0))

        ttk.Checkbutton(checks, text="Download subtitles", variable=self.var_subs, command=self._refresh_subs_ui).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(checks, text="Dry-run (do not download)", variable=self.var_dry).grid(row=0, column=1, sticky="w", padx=(14, 0))
        ttk.Checkbutton(checks, text="Open output folder when finished", variable=self.var_open_folder).grid(row=0, column=2, sticky="w", padx=(14, 0))

        # Subtitles selection
        self.subs_frame = ttk.LabelFrame(settings, text="Subtitle languages", padding=10)
        self.subs_frame.pack(fill="x", pady=(10, 0))

        self.sub_lang_vars: dict[str, tk.BooleanVar] = {}
        row = 0
        col = 0
        for label, code in SUB_LANGS_UI:
            v = tk.BooleanVar()
            self.sub_lang_vars[code] = v
            ttk.Checkbutton(self.subs_frame, text=label, variable=v).grid(row=row, column=col, sticky="w", padx=(0, 16), pady=2)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        ttk.Label(
            settings,
            text="Each video goes into its own subfolder: yyyy-mm-dd+video title",
        ).pack(anchor="w", pady=(10, 0))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(10, 0))

        self.btn_start = ttk.Button(btns, text="Start download", command=self._start_download)
        self.btn_start.pack(side="left")

        self.btn_save = ttk.Button(btns, text="Save settings", command=self._save_config_from_ui)
        self.btn_save.pack(side="left", padx=(10, 0))

        self.btn_update = ttk.Button(btns, text="Update tools (deno/ffmpeg)", command=self._start_update_tools)
        self.btn_update.pack(side="left", padx=(10, 0))

        ttk.Button(btns, text="Clear log", command=self._clear_log).pack(side="left", padx=(10, 0))

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
        state = "normal" if enabled else "disabled"
        for v in self.sub_lang_vars.values():
            # checkbox widgets are bound to vars; disable frame by toggling children state
            pass
        for child in self.subs_frame.winfo_children():
            try:
                child.configure(state=state)
            except Exception:
                pass

    def _refresh_mode_ui(self):
        audio_only = bool(self.var_audio_only.get())
        if audio_only:
            self.cmb_quality.configure(state="disabled")
            self.cmb_audio.configure(state="readonly")
        else:
            self.cmb_quality.configure(state="readonly")
            self.cmb_audio.configure(state="disabled")

    def _browse_out(self):
        initial = self.var_out.get().strip() or str(APP_DIR)
        selected = filedialog.askdirectory(initialdir=initial, title="Select output folder")
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

        self.var_subs.set(self.cfg.subs)
        self.var_open_folder.set(self.cfg.open_folder_after)

        self.var_audio_only.set(self.cfg.audio_only)
        self.var_quality.set(self.cfg.quality_label if self.cfg.quality_label in QUALITY_PRESETS else list(QUALITY_PRESETS.keys())[0])
        self.var_audio_label.set(self.cfg.audio_label if self.cfg.audio_label in AUDIO_PRESETS else list(AUDIO_PRESETS.keys())[0])

        # subtitle checkboxes
        for _, code in SUB_LANGS_UI:
            self.sub_lang_vars[code].set(code in set(self.cfg.subs_langs or []))

        self._refresh_mode_ui()
        self._refresh_subs_ui()

        # If subtitles enabled, re-apply selection after frame enablement
        if self.var_subs.get():
            for _, code in SUB_LANGS_UI:
                self.sub_lang_vars[code].set(code in set(self.cfg.subs_langs or []))

    def _save_config_from_ui(self):
        try:
            cfg = self._collect_cfg_from_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        _write_json(self.config_path, asdict(cfg))
        self.cfg = cfg
        self._log(f"✅ Settings saved: {self.config_path}")

    def _collect_cfg_from_ui(self) -> AppConfig:
        out_dir = self.var_out.get().strip()
        if not out_dir:
            raise ValueError("Please select an output folder.")

        after = self.var_after.get().strip() or None
        _ = parse_after_date(after)

        audio_only = bool(self.var_audio_only.get())
        quality_label = (self.var_quality.get().strip() or list(QUALITY_PRESETS.keys())[0])
        audio_label = (self.var_audio_label.get().strip() or list(AUDIO_PRESETS.keys())[0])

        if quality_label not in QUALITY_PRESETS:
            quality_label = list(QUALITY_PRESETS.keys())[0]
        if audio_label not in AUDIO_PRESETS:
            audio_label = list(AUDIO_PRESETS.keys())[0]

        subs_enabled = bool(self.var_subs.get())
        subs_langs: list[str] = []
        if subs_enabled:
            subs_langs = [code for _, code in SUB_LANGS_UI if self.sub_lang_vars[code].get()]
            if not subs_langs:
                # sane fallback
                subs_langs = ["en"]

        return AppConfig(
            out_dir=out_dir,
            after=after,
            subs=subs_enabled,
            subs_langs=subs_langs,
            open_folder_after=bool(self.var_open_folder.get()),
            quality_label=quality_label,
            audio_only=audio_only,
            audio_label=audio_label,
            concurrent_fragments=self.cfg.concurrent_fragments,
            retries=self.cfg.retries,
            fragment_retries=self.cfg.fragment_retries,
            folder_template=self.cfg.folder_template,
            file_template=self.cfg.file_template,
            merge_output_format=self.cfg.merge_output_format,
        )

    def _get_urls(self) -> list[str]:
        raw = self.txt_urls.get("1.0", "end").strip()
        if not raw:
            return []
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.btn_start.configure(state=state)
        self.btn_save.configure(state=state)
        self.btn_update.configure(state=state)

    # ---------- Download ----------
    def _start_download(self):
        if self.downloading or self.updating:
            return

        urls = self._get_urls()
        if not urls:
            messagebox.showwarning("Missing URL", "Paste at least one YouTube link (one per line).")
            return

        try:
            cfg = self._collect_cfg_from_ui()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        _write_json(self.config_path, asdict(cfg))
        self.cfg = cfg

        self.downloading = True
        self._last_finished_media = None
        self._set_busy(True)

        subs_txt = "no"
        if cfg.subs:
            subs_txt = ", ".join([code.upper() for code in cfg.subs_langs])

        self._log("========================================")
        self._log("▶ Download started…")
        self._log(f"URLs: {len(urls)}")
        self._log(f"Output: {cfg.out_dir}")
        self._log(f"Mode: {'audio only' if cfg.audio_only else 'video'}")
        if cfg.audio_only:
            self._log(f"Audio preset: {cfg.audio_label}")
        else:
            self._log(f"Quality preset: {cfg.quality_label}")
        if cfg.after:
            self._log(f"Filter: upload_date >= {parse_after_date(cfg.after)}")
        else:
            self._log("Filter: none")
        self._log(f"Subtitles: {subs_txt}")
        self._log(f"Dry-run: {'yes' if self.var_dry.get() else 'no'}")

        # tool hints
        if not DENO_EXE.exists():
            self._log("⚠ Tip: deno.exe not found → formats may be missing on YouTube.")
        if not FFMPEG_EXE.exists():
            self._log("⚠ Tip: ffmpeg.exe not found → merging/conversions may fail (audio-only mp3 definitely needs ffmpeg).")

        if DENO_EXE.exists():
            self._log("ℹ EJS solver: enabled (downloads from GitHub if needed).")
        self._log("========================================")

        t = threading.Thread(target=self._download_thread, args=(cfg, urls, bool(self.var_dry.get())), daemon=True)
        t.start()

    def _download_thread(self, cfg: AppConfig, urls: list[str], dry_run: bool):
        try:
            out_dir = Path(cfg.out_dir).expanduser()
            if not out_dir.is_absolute():
                out_dir = (APP_DIR / out_dir).resolve()
            out_dir.mkdir(parents=True, exist_ok=True)

            archive_file = out_dir / ".ytdlp_archive.txt"
            after_yyyymmdd = parse_after_date(cfg.after)

            # Ensure yt-dlp creates subfolders by using the "default" template with folder + filename
            outtmpl_default = f"{cfg.folder_template}/{cfg.file_template}"

            def progress_hook(d: dict[str, Any]):
                status = d.get("status")
                filename = (d.get("filename") or "").lower()

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
                    media_exts = (".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".aac", ".opus")
                    if filename.endswith(media_exts):
                        if filename != (self._last_finished_media or ""):
                            self._last_finished_media = filename
                            self.log_queue.put("✅ Media download finished, merging/post-processing…")

            # format selection
            if cfg.audio_only:
                a = AUDIO_PRESETS.get(cfg.audio_label, list(AUDIO_PRESETS.values())[0])
                fmt = a["format"]
            else:
                fmt = QUALITY_PRESETS.get(cfg.quality_label, list(QUALITY_PRESETS.values())[0])

            ydl_opts: dict[str, Any] = {
                "paths": {"home": str(out_dir)},
                "outtmpl": {
                    "default": outtmpl_default,
                    # Subtitles: ID-LANGCODE (uppercase)
                    "subtitle": f"{cfg.folder_template}/%(id)s-%(language)s.%(ext)s",
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
                "logger": TkLogger(self.log_queue),
                "progress_hooks": [progress_hook],
            }

            # Prefer tools shipped next to the EXE
            if FFMPEG_EXE.exists():
                ydl_opts["ffmpeg_location"] = str(APP_DIR)

            # JS runtime (deno) + EJS solver (remote)
            if DENO_EXE.exists():
                ydl_opts["js_runtimes"] = {"deno": {"path": str(DENO_EXE)}}
                # Enables automatic download of remote EJS solver script (recommended by yt-dlp)
                ydl_opts["remote_components"] = ["ejs:github"]

            # Video mode: prefer mp4 merge
            if not cfg.audio_only:
                ydl_opts["merge_output_format"] = cfg.merge_output_format

            # Subtitles
            if cfg.subs:
                langs = list(dict.fromkeys((cfg.subs_langs or [])))  # de-dup preserving order

                # Small delays reduce 429 risk when requesting multiple subtitle tracks
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
                a = AUDIO_PRESETS.get(cfg.audio_label, None)
                if a and a.get("extract_audio"):
                    ydl_opts["postprocessors"] = [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": a.get("codec", "mp3"),
                            "preferredquality": "0",
                        }
                    ]

            # Rename subtitle files to uppercase language code (ID-EN etc.)
            def _subtitle_renamer(d: dict[str, Any]):
                if d.get("status") != "finished":
                    return
                fn = d.get("filename")
                if not fn:
                    return
                p = Path(fn)
                if p.suffix.lower() not in (".vtt", ".srt", ".ass", ".ttml"):
                    return
                # Expect: <id>-<language>.vtt
                parts = p.stem.split("-")
                if len(parts) < 2:
                    return
                lang = parts[-1]
                new_name = p.with_name(p.stem[:-len(lang)] + lang.upper() + p.suffix)
                try:
                    if new_name != p and p.exists():
                        p.rename(new_name)
                except Exception:
                    pass

            ydl_opts["progress_hooks"].append(_subtitle_renamer)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)

            self.log_queue.put("🎉 Done!")
            if cfg.open_folder_after:
                open_folder(out_dir)

        except Exception as e:
            self.log_queue.put(f"❌ Error: {e}")
        finally:
            self.after(0, self._download_finished)

    def _download_finished(self):
        self.downloading = False
        self._set_busy(False)

    # ---------- Tools updater ----------
    def _start_update_tools(self):
        if self.downloading or self.updating:
            return

        if not messagebox.askyesno(
            "Update tools",
            "This will download and replace deno/ffmpeg tools in the app folder.\n\nContinue?",
        ):
            return

        self.updating = True
        self._set_busy(True)
        self._log("========================================")
        self._log("▶ Updating tools…")
        self._log(f"App folder: {APP_DIR}")
        self._log("========================================")

        t = threading.Thread(target=self._update_tools_thread, daemon=True)
        t.start()

    def _update_tools_thread(self):
        try:
            update_tools(APP_DIR, self.log_queue)
        except Exception as e:
            self.log_queue.put(f"❌ Update failed: {e}")
        finally:
            self.after(0, self._update_finished)

    def _update_finished(self):
        self.updating = False
        self._set_busy(False)
        self._log("========================================")


if __name__ == "__main__":
    import traceback

    try:
        App().mainloop()
    except Exception:
        tb = traceback.format_exc()
        log_path = (APP_DIR / "vod_gui_error.log")
        log_path.write_text(tb, encoding="utf-8")
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("Startup error", f"The program crashed during startup.\n\nDetails:\n{log_path}")
            r.destroy()
        except Exception:
            pass
        raise
