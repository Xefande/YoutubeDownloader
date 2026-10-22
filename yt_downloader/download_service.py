"""Download execution boundary: no Tk objects, event loop, or widget access."""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from .app_paths import get_yt_dlp
from .config import AppConfig
from .downloader import ProgressHook, build_download_plan
from .logging_adapter import QueueLogger

DownloadStatus = Literal["success", "warning", "error", "cancelled"]


@dataclass(frozen=True)
class DownloadResult:
    status: DownloadStatus
    label: str
    detail: str
    out_dir: Path | None = None
    return_code: int | None = None
    completed_media: int = 0
    warnings: int = 0
    errors: int = 0


class DownloadCancelled(Exception):
    """Cooperative cancellation raised at yt-dlp hook boundaries."""


class DownloadService:
    def __init__(self, app_dir: Path, log_queue: queue.Queue[str], *,
                 engine_factory: Callable[[dict[str, Any]], Any] | None = None):
        self.app_dir = app_dir
        self.log_queue = log_queue
        self.engine_factory = engine_factory

    def run(self, cfg: AppConfig, urls: list[str], *, dry_run: bool = False,
            cancel_event: threading.Event | None = None,
            progress_hook: ProgressHook | None = None) -> DownloadResult:
        """Run one request and report actual engine outcome, including partial errors.

        Cancel is cooperative: active socket/subprocess operations must return to
        a progress, extraction filter, or postprocessor hook before they stop.
        """
        cancel_event = cancel_event or threading.Event()
        logger = QueueLogger(self.log_queue)
        completed: set[str] = set()
        out_dir: Path | None = None
        return_code: int | None = None

        def check_cancelled() -> None:
            if cancel_event.is_set():
                raise DownloadCancelled("Download cancelled.")

        def on_progress(event: dict[str, Any]) -> None:
            check_cancelled()
            if progress_hook is not None:
                progress_hook(event)

        def on_postprocess(event: dict[str, Any]) -> None:
            check_cancelled()
            # A downloaded fragment or intermediate audio stream is not a
            # completed media item; count only the final file move.
            if (not dry_run and event.get("status") == "finished"
                    and event.get("postprocessor") == "MoveFiles"):
                info = event.get("info_dict") or {}
                key = info.get("filepath")
                if key:
                    completed.add(str(key))

        def result(status: DownloadStatus, label: str, detail: str) -> DownloadResult:
            self.log_queue.put(detail)
            return DownloadResult(status, label, detail, out_dir, return_code,
                                  len(completed), logger.warning_count, logger.error_count)

        try:
            check_cancelled()
            if not urls or any(not isinstance(url, str) or not url.strip() for url in urls):
                raise ValueError("Provide at least one non-empty URL.")
            plan = build_download_plan(
                cfg=cfg, app_dir=self.app_dir, deno_exe=self.app_dir / "deno.exe",
                ffmpeg_exe=self.app_dir / "ffmpeg.exe", logger=logger,
                progress_hooks=[on_progress], dry_run=dry_run,
            )
            out_dir = plan.out_dir
            if not dry_run:
                out_dir.mkdir(parents=True, exist_ok=True)
            options = dict(plan.ydl_opts)
            options["postprocessor_hooks"] = [on_postprocess, *options.get("postprocessor_hooks", [])]
            original_filter = options["match_filter"]

            def match_filter(info: dict[str, Any], *, incomplete: bool):
                check_cancelled()
                return original_filter(info, incomplete=incomplete)

            options["match_filter"] = match_filter
            factory = self.engine_factory or get_yt_dlp(self.app_dir / "_pydeps").YoutubeDL
            check_cancelled()
            with factory(options) as engine:
                return_code = engine.download(list(urls))
            check_cancelled()
            if return_code or logger.error_count:
                return result("warning" if completed else "error", "Completed with errors" if completed else "Failed",
                              f"{len(completed)} media item(s) completed; yt-dlp reported errors. See details.")
            if dry_run:
                detail = "Dry run finished. No media files were downloaded."
            elif completed:
                detail = f"{len(completed)} media item(s) completed."
            else:
                detail = "No new media completed. Archive or date filters may have skipped items."
            if logger.warning_count:
                return result("warning", "Finished with warnings", detail + " See details for warnings.")
            return result("success", "Dry run complete" if dry_run else "Completed", detail)
        except DownloadCancelled:
            return result("cancelled", "Cancelled", f"Download cancelled. {len(completed)} media item(s) completed.")
        except Exception as exc:
            if cancel_event.is_set():
                return result("cancelled", "Cancelled", f"Download cancelled. {len(completed)} media item(s) completed.")
            return result("warning" if completed else "error", "Completed with errors" if completed else "Failed", str(exc))
