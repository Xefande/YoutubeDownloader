"""Tool updates with verified staging, recoverable replacement and explicit results."""
from __future__ import annotations

import hashlib
import json
import ntpath
import os
import queue
import shutil
import stat
import tempfile
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .app_paths import reload_yt_dlp

DENO_WIN64_ZIP_URL = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
YTDLP_PYPI_JSON_URL = "https://pypi.org/pypi/yt-dlp/json"
FFMPEG_ESSENTIALS_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


@dataclass(frozen=True)
class ToolUpdateResult:
    name: str
    updated: bool
    detail: str
    restart_required: bool = False


@dataclass(frozen=True)
class UpdateResult:
    components: tuple[ToolUpdateResult, ...]

    @property
    def success(self) -> bool:
        return bool(self.components) and all(item.updated and not item.restart_required for item in self.components)

    @property
    def status(self) -> str:
        if self.success:
            return "success"
        return "warning" if any(item.updated for item in self.components) else "error"

    @property
    def label(self) -> str:
        return {"success": "Tools updated", "warning": "Update needs attention", "error": "Update failed"}[self.status]

    @property
    def detail(self) -> str:
        if self.success:
            return "yt-dlp, Deno and FFmpeg tools updated successfully."
        return "; ".join(f"{item.name}: {item.detail}" for item in self.components
                         if not item.updated or item.restart_required)


@dataclass(frozen=True)
class WheelInfo:
    version: str
    url: str
    filename: str
    sha256: str


def _download_with_progress(url: str, dest: Path, logq: queue.Queue[str], label: str, *,
                            timeout: int = 60, sha256: str | None = None) -> None:
    """Do not expose incomplete downloads under the destination filename."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "YTDownloader", "Accept": "*/*"})
    staged: Path | None = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = resp.headers.get("Content-Length")
            total_bytes = int(total) if total and total.isdigit() else None
            downloaded = 0
            next_report = 0
            digest = hashlib.sha256()
            with tempfile.NamedTemporaryFile(mode="wb", dir=dest.parent, prefix=".download-", delete=False) as file:
                staged = Path(file.name)
                while buf := resp.read(1024 * 256):
                    file.write(buf)
                    digest.update(buf)
                    downloaded += len(buf)
                    if downloaded >= next_report:
                        size = f"{downloaded / 1024 / 1024:.1f}MB"
                        if total_bytes:
                            size = f"{downloaded / total_bytes * 100:5.1f}% ({size} / {total_bytes / 1024 / 1024:.1f}MB)"
                        logq.put(f"Downloading {label}: {size}")
                        next_report = downloaded + 4 * 1024 * 1024
                file.flush()
                os.fsync(file.fileno())
            if total_bytes is not None and downloaded != total_bytes:
                raise RuntimeError(f"Incomplete {label} download: expected {total_bytes} bytes, received {downloaded}.")
            if not downloaded:
                raise RuntimeError(f"The {label} download was empty.")
            if sha256 and digest.hexdigest().lower() != sha256.lower():
                raise RuntimeError(f"The {label} download does not match its published SHA-256 digest.")
            os.replace(staged, dest)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def _extract_exe_from_zip(zip_path: Path, exe_name: str, out_path: Path) -> bool:
    with zipfile.ZipFile(zip_path, "r") as archive:
        candidates = [name for name in archive.namelist()
                      if PurePosixPath(name.replace("\\", "/")).name.lower() == exe_name.lower()]
        candidates.sort(key=lambda name: ("/bin/" not in ("/" + name.replace("\\", "/")).lower(), len(name)))
        if not candidates:
            return False
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(candidates[0]) as src, out_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        if out_path.stat().st_size == 0:
            raise RuntimeError(f"Downloaded archive contains an empty {exe_name}.")
    return True


def _safe_extract_all(archive: zipfile.ZipFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.infolist():
        name = member.filename.replace("\\", "/")
        if (ntpath.splitdrive(name)[0] or PurePosixPath(name).is_absolute()
                or ".." in PurePosixPath(name).parts or ":" in name
                or stat.S_ISLNK(member.external_attr >> 16)):
            raise RuntimeError(f"Unsafe zip member path: {member.filename}")
        target = (destination / name).resolve()
        try:
            target.relative_to(destination)
        except ValueError as exc:
            raise RuntimeError(f"Unsafe zip member path: {member.filename}") from exc
    archive.extractall(destination)


def _install_pydeps_from_wheel(wheel_path: Path, pydeps_dir: Path, *,
                              validate: Callable[[], Any] | None = None) -> Any:
    pydeps_dir.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".pydeps-update-", dir=pydeps_dir.parent))
    staged, backup = work / "new", work / "backup"
    staged.mkdir()
    preserve_backup = False
    try:
        with zipfile.ZipFile(wheel_path, "r") as archive:
            _safe_extract_all(archive, staged)
        if not (staged / "yt_dlp" / "__init__.py").is_file():
            raise RuntimeError("Downloaded wheel does not contain the yt_dlp package.")
        if pydeps_dir.exists():
            pydeps_dir.rename(backup)
        try:
            staged.rename(pydeps_dir)
            return validate() if validate is not None else None
        except Exception as install_error:
            try:
                if pydeps_dir.exists():
                    pydeps_dir.rename(staged)
                if backup.exists():
                    backup.rename(pydeps_dir)
            except OSError as rollback_error:
                preserve_backup = True
                raise RuntimeError(f"Update and restore failed. Previous installation preserved at {backup}: {rollback_error}") from install_error
            raise
    finally:
        if not preserve_backup:
            shutil.rmtree(work, ignore_errors=True)


def _replace_tool_files(staged_files: list[Path], app_dir: Path) -> None:
    """Commit a tool family together, restoring every old file on failure."""
    backup = Path(tempfile.mkdtemp(prefix=".tools-backup-", dir=app_dir))
    moved: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    preserve_backup = False
    try:
        for source in staged_files:
            target = app_dir / source.name
            if target.exists():
                old = backup / source.name
                os.replace(target, old)
                moved.append((old, target))
            os.replace(source, target)
            installed.append(target)
    except OSError as install_error:
        rollback_errors: list[str] = []
        for target in reversed(installed):
            try:
                target.unlink(missing_ok=True)
            except OSError as exc:
                rollback_errors.append(str(exc))
        for old, target in reversed(moved):
            try:
                os.replace(old, target)
            except OSError as exc:
                rollback_errors.append(str(exc))
        if rollback_errors:
            preserve_backup = True
            raise RuntimeError(f"Update and restore failed. Backups preserved at {backup}: {'; '.join(rollback_errors)}") from install_error
        raise
    finally:
        if not preserve_backup:
            shutil.rmtree(backup, ignore_errors=True)


def _get_latest_ytdlp_wheel_info() -> WheelInfo:
    with urllib.request.urlopen(YTDLP_PYPI_JSON_URL, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("info"), dict):
        raise RuntimeError("Invalid yt-dlp release metadata from PyPI.")
    version = data["info"].get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError("Could not determine latest yt-dlp version from PyPI JSON.")
    releases = data.get("releases")
    candidates = (releases.get(version) if isinstance(releases, dict) else None) or data.get("urls") or []
    for item in candidates if isinstance(candidates, list) else []:
        if not isinstance(item, dict) or item.get("packagetype") != "bdist_wheel":
            continue
        filename = str(item.get("filename") or "")
        url = str(item.get("url") or "")
        digests = item.get("digests")
        digest = str(digests.get("sha256") or "") if isinstance(digests, dict) else ""
        parsed = urllib.parse.urlparse(url)
        if (filename.endswith("py3-none-any.whl") and "/" not in filename and "\\" not in filename
                and ":" not in filename and parsed.scheme == "https" and parsed.hostname == "files.pythonhosted.org"
                and len(digest) == 64 and all(c in "0123456789abcdefABCDEF" for c in digest)
                and not item.get("yanked")):
            return WheelInfo(version, url, filename, digest)
    raise RuntimeError(f"No supported yt-dlp wheel with a SHA-256 digest found for {version}.")


def update_tools(app_dir: Path, logq: queue.Queue[str]) -> UpdateResult:
    app_dir.mkdir(parents=True, exist_ok=True)
    results: list[ToolUpdateResult] = []
    with tempfile.TemporaryDirectory(prefix=".update-", dir=app_dir) as tmp_name:
        tmp = Path(tmp_name)
        try:
            logq.put("Updating yt-dlp...")
            wheel = _get_latest_ytdlp_wheel_info()
            wheel_path = tmp / wheel.filename
            _download_with_progress(wheel.url, wheel_path, logq, "yt-dlp", sha256=wheel.sha256)
            active = _install_pydeps_from_wheel(
                wheel_path, app_dir / "_pydeps", validate=lambda: reload_yt_dlp(app_dir / "_pydeps"))
            active_version = getattr(getattr(active, "version", None), "__version__", "unknown")
            results.append(ToolUpdateResult("yt-dlp", True, f"Active version: {active_version}"))
        except Exception as exc:
            results.append(ToolUpdateResult("yt-dlp", False, str(exc)))

        for name, url, files in (
            ("Deno", DENO_WIN64_ZIP_URL, ("deno.exe",)),
            ("FFmpeg", FFMPEG_ESSENTIALS_ZIP_URL, ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe")),
        ):
            try:
                logq.put(f"Updating {name}...")
                archive_path = tmp / f"{name}.zip"
                _download_with_progress(url, archive_path, logq, name)
                staged_files = []
                for exe in files:
                    staged = tmp / exe
                    if not _extract_exe_from_zip(archive_path, exe, staged):
                        raise RuntimeError(f"Could not find {exe} in the downloaded archive.")
                    staged_files.append(staged)
                _replace_tool_files(staged_files, app_dir)
                results.append(ToolUpdateResult(name, True, "Updated."))
            except Exception as exc:
                results.append(ToolUpdateResult(name, False, str(exc)))

    for item in results:
        prefix = "WARNING: " if not item.updated or item.restart_required else ""
        logq.put(f"{prefix}{item.name}: {item.detail}")
    outcome = UpdateResult(tuple(results))
    logq.put(outcome.detail)
    return outcome
