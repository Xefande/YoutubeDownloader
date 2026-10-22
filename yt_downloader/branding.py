"""Application identity and bundled artwork, independent of writable app paths."""
from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "YouTube Downloader"
WINDOW_TITLE = "Xefande's Vod Downloader"
APP_ID = "Xefandez.VODDownloader"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def set_process_identity() -> None:
    """Give Windows the same identity as the installed shortcuts, before Tk starts."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        set_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        set_id.argtypes = [wintypes.LPCWSTR]
        set_id.restype = ctypes.c_long
        result = set_id(APP_ID)
        if result < 0:
            raise OSError(f"Could not set Windows application identity: {result:#x}")


def apply_window_branding(window) -> None:
    """Set the native icon, inherited dialog icon and retained header image."""
    import tkinter as tk

    window.title(WINDOW_TITLE)
    window.header_logo = tk.PhotoImage(master=window, file=str(ASSETS_DIR / "logo-48.png"))
    if sys.platform == "win32":
        window.iconbitmap(default=str(ASSETS_DIR / "app.ico"))
        # A class default covers new dialogs. Assign this window explicitly too:
        # the Shell asks WM_GETICON for taskbar/Alt-Tab before using class icons.
        window.iconbitmap(str(ASSETS_DIR / "app.ico"))
    else:
        window._icon_images = [
            tk.PhotoImage(master=window, file=str(ASSETS_DIR / f"logo-{size}.png"))
            for size in (32, 256)
        ]
        window.iconphoto(True, *window._icon_images)
