"""Build the portable Windows application with the pinned dependencies."""
from __future__ import annotations

import importlib.metadata
import platform
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def build() -> Path:
    if (sys.platform != "win32" or sys.version_info[:2] != (3, 12)
            or struct.calcsize("P") != 8 or platform.machine().lower() not in {"amd64", "x86_64"}):
        raise ValueError("Build requires Windows x64 and Python 3.12 x64.")
    for filename in ("requirements.txt", "requirements-build.txt"):
        for line in (ROOT / filename).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith(("#", "-r ")):
                continue
            name, expected = line.strip().split("==", 1)
            actual = importlib.metadata.version(name.split("[", 1)[0])
            if actual != expected:
                raise ValueError(f"{name}: expected {expected}, found {actual}. Run Build.cmd.")

    from yt_downloader import __version__
    from yt_downloader.branding import APP_NAME

    assets = ROOT / "yt_downloader" / "assets"
    for name in ("app.ico", "logo-32.png", "logo-48.png", "logo-256.png"):
        if not (assets / name).is_file():
            raise ValueError(f"Missing application artwork: {name}")
    work = ROOT / "build"
    work.mkdir(exist_ok=True)
    version_file = work / "version.txt"
    numbers = tuple(int(part) for part in __version__.split(".")) + (0,)
    version_file.write_text(
        f"VSVersionInfo(ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r}, "
        "mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)), kids=["
        "StringFileInfo([StringTable('040904B0', ["
        f"StringStruct('CompanyName', 'Xefandez'), StringStruct('FileDescription', {APP_NAME!r}), "
        f"StringStruct('FileVersion', '{__version__}'), StringStruct('ProductVersion', '{__version__}'), "
        f"StringStruct('ProductName', {APP_NAME!r}), StringStruct('OriginalFilename', 'YTDownloader.exe')])]), "
        "VarFileInfo([VarStruct('Translation', [1033, 1200])])])\n",
        encoding="utf-8",
    )
    subprocess.run([
        sys.executable, "-B", "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "YTDownloader", "--version-file", str(version_file),
        "--icon", str(assets / "app.ico"), "--add-data", f"{assets};yt_downloader/assets",
        "--distpath", str(ROOT / "dist"), "--workpath", str(work / "pyinstaller"),
        "--specpath", str(work), str(ROOT / "vod_downloader.py"),
    ], check=True, cwd=ROOT)
    executable = ROOT / "dist" / "YTDownloader.exe"
    if not executable.is_file():
        raise FileNotFoundError(f"Build did not produce {executable}")
    return executable


if __name__ == "__main__":
    try:
        result = build()
    except (OSError, ValueError, subprocess.SubprocessError, importlib.metadata.PackageNotFoundError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Build complete: {result}")
    print("Deno and FFmpeg are not included. Use Update tools in the app before the first download.")
