from __future__ import annotations

import queue
import threading
import traceback
from dataclasses import asdict
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

from .app_paths import APP_DIR, DEFAULT_CONFIG_PATH, DENO_EXE, FFMPEG_EXE, get_yt_dlp
from .branding import APP_NAME, apply_window_branding, set_process_identity
from .config import AppConfig, load_or_create_config, parse_after_date, write_json
from .download_service import DownloadService
from .diagnostics import write_error_report
from .downloader import resolve_output_dir
from .platforms import open_folder
from .presets import AUDIO_PRESETS, AUDIO_TRACK_LANGS_UI, BITRATE_PRESETS_UI, QUALITY_PRESETS, SUB_LANGS_UI, SUB_LANG_SHORT_LABELS
from .ui_theme import COLORS, enable_dark_title_bar
from .ui_view import AppView, MODE_VIDEO, MODE_AUDIO
from .updater import update_tools
from .ui_events import WorkerEvents, format_progress


class App(AppView):
    def __init__(self, *, config_path: Path | None = None):
        set_process_identity()
        super().__init__()
        self.withdraw()
        apply_window_branding(self)
        self.geometry("1040x760")
        self.minsize(920, 660)
        self.configure(bg=COLORS["bg"])

        self.config_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
        self.cfg = load_or_create_config(self.config_path)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.downloading = False
        self.updating = False
        self.worker_events = WorkerEvents()
        self.cancel_event = threading.Event()
        self._close_when_idle = False
        self._middle_tab: str | None = None
        self.sub_lang_vars: dict[str, tk.BooleanVar] = {}
        self.sub_lang_buttons = []
        self._log_poll_after_id: str | None = None
        self._is_destroying = False

        self._build_ui()
        self._load_cfg_into_ui()
        self.protocol("WM_DELETE_WINDOW", self._request_close)
        self._poll_log_queue()
        # Realize the native wrapper while hidden, then style it before the
        # first visible frame. Mapping may recreate a wrapper, so handle that
        # synchronously too instead of waiting for a timer or focus change.
        self.update_idletasks()
        self._apply_native_theme()
        self.bind("<Map>", self._apply_native_theme, add="+")
        self.deiconify()


    def _apply_native_theme(self, event=None) -> None:
        if event is None or event.widget is self:
            self._native_theme = enable_dark_title_bar(self)


    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-Return>", self._shortcut_start)
        self.bind_all("<Control-l>", self._shortcut_focus_urls)
        self.bind_all("<Control-L>", self._shortcut_focus_urls)
        self.bind_all("<Control-o>", self._shortcut_browse)
        self.bind_all("<Control-O>", self._shortcut_browse)
        self.bind("<Escape>", lambda _event: self._cancel_download())


    def _shortcut_start(self, _event: tk.Event) -> str:
        if str(self.btn_start.cget("state")) != "disabled":
            self._start_download()
        return "break"


    def _shortcut_focus_urls(self, _event: tk.Event) -> str:
        self.txt_urls.focus_set()
        return "break"


    def _shortcut_browse(self, _event: tk.Event) -> str:
        if not (self.downloading or self.updating):
            self._browse_out()
        return "break"


    def _refresh_tool_status(self) -> None:
        try:
            yt_dlp = get_yt_dlp()
            version = getattr(getattr(yt_dlp, "version", None), "__version__", "OK")
            ytdlp_status = f"yt-dlp {version}"
        except Exception:
            ytdlp_status = "yt-dlp missing"

        deno_status = "Deno OK" if DENO_EXE.exists() else "Deno missing"
        ffmpeg_status = "FFmpeg OK" if FFMPEG_EXE.exists() else "FFmpeg missing"
        self.var_tool_status.set(f"{ytdlp_status} | {ffmpeg_status} | {deno_status}")

        missing = "missing" in self.var_tool_status.get().lower()
        self.lbl_tool_status.configure(
            bg=COLORS["warning_bg"] if missing else COLORS["success_bg"],
            fg=COLORS["warning_text"] if missing else COLORS["success_text"],
            highlightbackground=COLORS["border"],
        )


    def _on_urls_modified(self, _event: tk.Event | None = None) -> None:
        if self.txt_urls.edit_modified():
            self.txt_urls.edit_modified(False)
            self._refresh_ready_state()


    def _clear_urls(self) -> None:
        if self.downloading or self.updating:
            return
        self.txt_urls.delete("1.0", "end")
        self._refresh_ready_state()


    def _refresh_ready_state(self) -> None:
        urls = self._get_urls()
        count = len(urls)
        self.var_link_count.set("No links detected" if count == 0 else f"{count} link{'s' if count != 1 else ''} detected")
        self._update_start_button()

        if self.downloading or self.updating:
            return
        if count:
            self._set_status("ready", "Ready", f"Ready to download {count} link{'s' if count != 1 else ''}.")
        else:
            self._set_status("idle", "Ready", "Paste at least one YouTube link.")


    def _refresh_subs_ui(self) -> None:
        enabled = bool(self.var_subs.get())
        busy = self.downloading or self.updating
        if enabled:
            self.subs_lang_frame.grid()
        else:
            self.subs_lang_frame.grid_remove()
        state = "normal" if enabled and not busy else "disabled"
        for child in self.sub_lang_buttons:
            child.configure(state=state)


    def _refresh_mode_ui(self) -> None:
        audio_only = self.var_mode.get() == MODE_AUDIO
        self.var_audio_only.set(audio_only)
        busy = self.downloading or self.updating

        if audio_only:
            self.video_settings.grid_remove()
            self.audio_settings.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        else:
            self.audio_settings.grid_remove()
            self.video_settings.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        mode_state = "disabled" if busy else "normal"
        combo_state = "disabled" if busy else "readonly"
        self.rdo_video.configure(state=mode_state)
        self.rdo_audio.configure(state=mode_state)
        self.cmb_quality.configure(state=combo_state)
        self.cmb_audio.configure(state=combo_state)
        self.cmb_bitrate.configure(state=combo_state)
        self.cmb_audio_track.configure(state=combo_state)


    def _browse_out(self) -> None:
        initial = str(resolve_output_dir(self.var_out.get().strip() or "downloads", APP_DIR))
        selected = filedialog.askdirectory(initialdir=initial, title="Select output folder")
        if selected:
            self.var_out.set(selected)


    def _clear_log(self) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")


    def _log(self, msg: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        # Bound widget memory during long playlists, without starving UI events.
        excess = int(self.txt_log.index("end-1c").split(".")[0]) - 2000
        if excess > 0:
            self.txt_log.delete("1.0", f"{excess + 1}.0")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")


    def _poll_log_queue(self) -> None:
        if self._is_destroying:
            return
        if self._log_poll_after_id is not None:
            self.after_cancel(self._log_poll_after_id)
            self._log_poll_after_id = None
        try:
            for _ in range(100):
                self._log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        progress, finished = self.worker_events.drain()
        if progress is not None and self.downloading and not self.cancel_event.is_set():
            percent, detail = format_progress(progress)
            if percent is not None:
                self.progress.stop()
                self.progress.configure(mode="determinate", value=percent)
            self.var_status_detail.set(detail)
        for operation, outcome in finished:
            if operation == "download":
                self._download_finished(*outcome)
            else:
                self._update_finished(*outcome)
        if self._close_when_idle and not (self.downloading or self.updating):
            self.destroy()
            return
        self._log_poll_after_id = self.after(100, self._poll_log_queue)


    def destroy(self) -> None:
        if self._is_destroying:
            return
        self._is_destroying = True
        self.cancel_event.set()
        if self._log_poll_after_id is not None:
            try:
                self.after_cancel(self._log_poll_after_id)
            except Exception:
                pass
            self._log_poll_after_id = None
        super().destroy()

    def _request_close(self) -> None:
        if self.updating:
            self._set_status("running", "Updating", "Please wait for the tool update to finish before closing.")
            return
        if self.downloading:
            if messagebox.askyesno(APP_NAME, "Stop the download and close when the current operation releases?", parent=self):
                self._close_when_idle = True
                self._cancel_download()
            return
        self.destroy()

    def report_callback_exception(self, exc_type, exc_value, exc_traceback) -> None:
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log_path = write_error_report(details, APP_DIR)
        self._log(details)
        self._set_status("error", "Interface error", str(exc_value))
        messagebox.showerror("Unexpected error", f"{exc_value}\n\nDetails: {log_path or 'see log'}", parent=self)

    def _cancel_download(self) -> None:
        if not self.downloading or self.cancel_event.is_set():
            return
        self.cancel_event.set()
        self.btn_cancel.configure(state="disabled")
        self._set_status("warning", "Stopping", "Stopping at the next safe point; network or conversion work may take a moment.")


    def _load_cfg_into_ui(self) -> None:
        self.var_out.set(self.cfg.out_dir)
        self.var_after.set(self.cfg.after or "")
        self.var_subs.set(self.cfg.subs)
        self.var_open_folder.set(self.cfg.open_folder_after)
        self.var_mode.set(MODE_AUDIO if self.cfg.audio_only else MODE_VIDEO)
        self.var_audio_only.set(self.cfg.audio_only)
        self.var_quality.set(
            self.cfg.quality_label if self.cfg.quality_label in QUALITY_PRESETS else list(QUALITY_PRESETS.keys())[0]
        )

        bitrate_label = next(
            (key for key, value in BITRATE_PRESETS_UI.items() if value == self.cfg.max_video_bitrate_kbps),
            list(BITRATE_PRESETS_UI.keys())[0],
        )
        self.var_bitrate.set(bitrate_label)

        audio_track_label = next(
            (name for name, code in AUDIO_TRACK_LANGS_UI if code == self.cfg.audio_track_lang),
            AUDIO_TRACK_LANGS_UI[0][0],
        )
        self.var_audio_track.set(audio_track_label)
        self.var_audio_label.set(self.cfg.audio_label if self.cfg.audio_label in AUDIO_PRESETS else list(AUDIO_PRESETS.keys())[0])

        for _, code in SUB_LANGS_UI:
            self.sub_lang_vars[code].set(code in set(self.cfg.subs_langs or []))

        self._refresh_mode_ui()
        self._refresh_subs_ui()
        self._refresh_ready_state()


    def _save_config_from_ui(self) -> None:
        try:
            cfg = self._collect_cfg_from_ui()
            write_json(self.config_path, asdict(cfg))
        except Exception as exc:
            messagebox.showerror("Settings could not be saved", str(exc), parent=self)
            self._set_status("error", "Not saved", str(exc))
            return
        self.cfg = cfg
        self._log(f"Settings saved: {self.config_path}")
        self._set_status("success", "Saved", "Settings saved.")


    def _collect_cfg_from_ui(self) -> AppConfig:
        out_dir = self.var_out.get().strip()
        if not out_dir:
            raise ValueError("Please select an output folder.")

        after = self.var_after.get().strip() or None
        parse_after_date(after)

        quality_label = self.var_quality.get().strip() or list(QUALITY_PRESETS.keys())[0]
        audio_label = self.var_audio_label.get().strip() or list(AUDIO_PRESETS.keys())[0]

        if quality_label not in QUALITY_PRESETS:
            quality_label = list(QUALITY_PRESETS.keys())[0]
        if audio_label not in AUDIO_PRESETS:
            audio_label = list(AUDIO_PRESETS.keys())[0]

        subs_enabled = bool(self.var_subs.get())
        subs_langs = [code for _, code in SUB_LANGS_UI if self.sub_lang_vars[code].get()]
        if subs_enabled and not subs_langs:
            raise ValueError("Select at least one subtitle language in Options.")

        bitrate_label = (self.var_bitrate.get() or "").strip()
        if bitrate_label not in BITRATE_PRESETS_UI:
            bitrate_label = list(BITRATE_PRESETS_UI.keys())[0]

        label_to_code = {name: code for name, code in AUDIO_TRACK_LANGS_UI}

        return AppConfig(
            out_dir=out_dir,
            after=after,
            subs=subs_enabled,
            subs_langs=subs_langs,
            open_folder_after=bool(self.var_open_folder.get()),
            quality_label=quality_label,
            audio_only=self.var_mode.get() == MODE_AUDIO,
            audio_label=audio_label,
            max_video_bitrate_kbps=BITRATE_PRESETS_UI.get(bitrate_label),
            audio_track_lang=label_to_code.get(self.var_audio_track.get(), "default"),
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
        return [line.strip() for line in raw.splitlines() if line.strip()]


    def _update_start_button(self) -> None:
        state = "normal" if self._get_urls() and not (self.downloading or self.updating) else "disabled"
        self.btn_start.configure(state=state)


    def _set_busy(self, busy: bool, *, refresh_status: bool = True) -> None:
        state = "disabled" if busy else "normal"
        text_state = "disabled" if busy else "normal"

        self.txt_urls.configure(state=text_state)
        self.ent_out.configure(state=state)
        self.ent_after.configure(state=state)
        self.btn_browse.configure(state=state)
        self.btn_save.configure(state=state)
        self.btn_update.configure(state=state)
        self.btn_clear_urls.configure(state=state)
        self.chk_subs.configure(state=state)
        self.chk_open_folder.configure(state=state)
        self.chk_dry.configure(state=state)

        self._refresh_mode_ui()
        self._refresh_subs_ui()
        if busy:
            self.btn_start.configure(state="disabled")
        else:
            self._update_start_button()
        self.btn_cancel.configure(state="normal" if self.downloading and not self.cancel_event.is_set() else "disabled")

        if refresh_status:
            self._refresh_ready_state()


    def _start_download(self) -> None:
        if self.downloading or self.updating:
            return

        urls = self._get_urls()
        if not urls:
            messagebox.showwarning("Missing URL", "Paste at least one YouTube link (one per line).")
            self._refresh_ready_state()
            return

        try:
            cfg = self._collect_cfg_from_ui()
            write_json(self.config_path, asdict(cfg))
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self._set_status("error", "Invalid", str(exc))
            return

        self.cfg = cfg
        self.downloading = True
        self.cancel_event.clear()
        self._set_busy(True, refresh_status=False)
        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(12)
        self._set_status("running", "Downloading", f"Downloading {len(urls)} link{'s' if len(urls) != 1 else ''}.")

        subs_txt = "no"
        if cfg.subs:
            subs_txt = ", ".join(SUB_LANG_SHORT_LABELS.get(code, code.upper()) for code in cfg.subs_langs)

        self._log("========================================")
        self._log("Download started...")
        self._log(f"URLs: {len(urls)}")
        self._log(f"Output: {cfg.out_dir}")
        self._log(f"Mode: {'audio only' if cfg.audio_only else 'video'}")

        audio_track_label = next(
            (name for name, code in AUDIO_TRACK_LANGS_UI if code == cfg.audio_track_lang),
            AUDIO_TRACK_LANGS_UI[0][0],
        )
        self._log(f"Audio track: {audio_track_label}")

        if cfg.audio_only:
            self._log(f"Audio preset: {cfg.audio_label}")
        else:
            self._log(f"Quality preset: {cfg.quality_label}")
            bitrate_label = next(
                (key for key, value in BITRATE_PRESETS_UI.items() if value == cfg.max_video_bitrate_kbps),
                list(BITRATE_PRESETS_UI.keys())[0],
            )
            self._log(f"Max bitrate: {bitrate_label}")
        if cfg.after:
            self._log(f"Filter: upload_date >= {parse_after_date(cfg.after)}")
        else:
            self._log("Filter: none")
        self._log(f"Subtitles: {subs_txt}")
        self._log(f"Dry-run: {'yes' if self.var_dry.get() else 'no'}")

        if not DENO_EXE.exists():
            self._log("WARNING: deno.exe not found; formats may be missing on YouTube.")
        if not FFMPEG_EXE.exists():
            self._log("WARNING: ffmpeg.exe not found; merging/conversions may fail.")
        if DENO_EXE.exists():
            self._log("EJS solver: enabled.")
        self._log("========================================")

        thread = threading.Thread(target=self._download_thread, args=(cfg, urls, bool(self.var_dry.get())), daemon=False, name="media-download")
        thread.start()


    def _download_thread(self, cfg: AppConfig, urls: list[str], dry_run: bool) -> None:
        # This method runs on a worker; only Python mailboxes cross the UI boundary.
        try:
            result = DownloadService(APP_DIR, self.log_queue).run(
                cfg, urls, dry_run=dry_run,
                cancel_event=self.cancel_event, progress_hook=self.worker_events.progress,
            )
            if (cfg.open_folder_after and result.out_dir is not None
                    and result.completed_media > 0 and result.status in ("success", "warning")):
                try:
                    open_folder(result.out_dir)
                except OSError as exc:
                    self.log_queue.put(f"Could not open output folder: {exc}")
            self.worker_events.finish("download", result.status, result.label, result.detail)
        except Exception as exc:
            self.log_queue.put(f"Error: {exc}")
            self.worker_events.finish("download", "error", "Failed", str(exc))


    def _download_finished(self, kind: str, label: str, detail: str) -> None:
        self.downloading = False
        self.progress.stop()
        self.progress.configure(mode="determinate", value=100 if kind == "success" else 0)
        self._set_status(kind, label, detail)
        self._set_busy(False, refresh_status=False)


    def _start_update_tools(self) -> None:
        if self.downloading or self.updating:
            return

        if not messagebox.askyesno(
            "Update tools",
            "This will update yt-dlp and replace deno/ffmpeg tools in the app folder.\n\nContinue?",
        ):
            return

        self.updating = True
        self._set_busy(True, refresh_status=False)
        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(12)
        self._set_status("running", "Updating", "Updating yt-dlp, Deno and FFmpeg tools.")
        self._log("========================================")
        self._log("Updating tools...")
        self._log(f"App folder: {APP_DIR}")
        self._log("========================================")

        thread = threading.Thread(target=self._update_tools_thread, daemon=False, name="tool-update")
        thread.start()


    def _update_tools_thread(self) -> None:
        try:
            result = update_tools(APP_DIR, self.log_queue)
            self.worker_events.finish("update", result.status, result.label, result.detail)
        except Exception as exc:
            self.log_queue.put(f"Update failed: {exc}")
            self.worker_events.finish("update", "error", "Update failed", str(exc))


    def _update_finished(self, kind: str, label: str, detail: str) -> None:
        self.updating = False
        self.progress.stop()
        self.progress.configure(mode="determinate", value=100 if kind == "success" else 0)
        self._refresh_tool_status()
        self._set_status(kind, label, detail)
        self._set_busy(False, refresh_status=False)
        self._log("========================================")
