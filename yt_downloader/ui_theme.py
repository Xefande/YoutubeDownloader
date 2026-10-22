"""Shared visual tokens and native window styling; no application state."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from tkinter import TclError, ttk

COLORS = {
    "bg": "#0E0F12",
    "surface": "#181B20",
    "surface_subtle": "#232831",
    "border": "#38414D",
    "text": "#F4F7FB",
    "muted": "#A8B3C2",
    "primary": "#28E6B8",
    "primary_pressed": "#13B890",
    "primary_text": "#031613",
    "selection": "#126B5F",
    "success_text": "#9AF0B3",
    "success_bg": "#123822",
    "warning_text": "#F5C84C",
    "warning_bg": "#3A2A0E",
    "danger_text": "#FF8A98",
    "danger_bg": "#3C171F",
}


def configure_styles(window) -> None:
    style = ttk.Style(window)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    style.configure(".", font=("Segoe UI", 10), background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("App.TFrame", background=COLORS["bg"])
    style.configure(
        "Card.TFrame",
        background=COLORS["surface"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        borderwidth=0,
        relief="flat",
    )
    style.configure("CardBody.TFrame", background=COLORS["surface"])
    style.configure("Subtle.TFrame", background=COLORS["surface_subtle"])
    style.configure("TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("AppMuted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
    style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 14, "bold"))
    style.configure("SectionTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 11, "bold"))
    style.configure("Header.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
    # Clam inherits light active/disabled backgrounds from its root state map.
    # Define the whole control state palette, including its indicator, locally.
    for control in ("TCheckbutton", "TRadiobutton"):
        style.configure(
            control,
            background=COLORS["surface"], foreground=COLORS["text"],
            indicatorbackground=COLORS["surface_subtle"], indicatorforeground=COLORS["text"],
            upperbordercolor=COLORS["muted"], lowerbordercolor=COLORS["muted"],
            focuscolor=COLORS["primary"],
        )
        indicator_border = [
            ("disabled", COLORS["border"]), ("focus", COLORS["primary"]),
            ("active", COLORS["primary"]), ("!disabled", COLORS["muted"]),
        ]
        style.map(
            control,
            background=[
                ("disabled", COLORS["surface"]), ("pressed", COLORS["selection"]),
                ("active", COLORS["surface_subtle"]), ("!disabled", COLORS["surface"]),
            ],
            foreground=[("disabled", COLORS["muted"]), ("!disabled", COLORS["text"])],
            indicatorbackground=[
                ("disabled", "selected", COLORS["border"]),
                ("disabled", "alternate", COLORS["border"]),
                ("disabled", COLORS["surface_subtle"]),
                ("pressed", "selected", COLORS["primary_pressed"]),
                ("pressed", "alternate", COLORS["primary_pressed"]),
                ("selected", COLORS["primary"]), ("alternate", COLORS["primary"]),
                ("!disabled", COLORS["surface_subtle"]),
            ],
            indicatorforeground=[
                ("disabled", COLORS["muted"]), ("selected", COLORS["primary_text"]),
                ("alternate", COLORS["primary_text"]), ("!disabled", COLORS["text"]),
            ],
            upperbordercolor=indicator_border, lowerbordercolor=indicator_border,
        )
    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        insertcolor=COLORS["text"],
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", COLORS["surface_subtle"]), ("!disabled", COLORS["surface"])],
        foreground=[("disabled", COLORS["muted"]), ("!disabled", COLORS["text"])],
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["surface_subtle"],
        background=COLORS["surface_subtle"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        arrowcolor=COLORS["text"],
        selectbackground=COLORS["selection"],
        selectforeground=COLORS["text"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", COLORS["surface_subtle"]),
            ("disabled", COLORS["surface_subtle"]),
            ("!disabled", COLORS["surface"]),
        ],
        background=[
            ("readonly", COLORS["surface_subtle"]),
            ("disabled", COLORS["surface_subtle"]),
            ("active", COLORS["border"]),
            ("!disabled", COLORS["surface"]),
        ],
        foreground=[("disabled", COLORS["muted"]), ("!disabled", COLORS["text"])],
        arrowcolor=[("disabled", COLORS["muted"]), ("!disabled", COLORS["text"])],
    )
    window.option_add("*TCombobox*Listbox.background", COLORS["surface"])
    window.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    window.option_add("*TCombobox*Listbox.selectBackground", COLORS["selection"])
    window.option_add("*TCombobox*Listbox.selectForeground", COLORS["text"])
    style.configure("TNotebook", background=COLORS["bg"], bordercolor=COLORS["border"])
    style.configure(
        "TNotebook.Tab",
        background=COLORS["surface_subtle"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=(10, 5),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["surface"]), ("active", COLORS["surface_subtle"])],
        foreground=[("selected", COLORS["text"]), ("active", COLORS["text"])],
    )
    style.configure("Horizontal.TProgressbar", troughcolor=COLORS["surface_subtle"], background=COLORS["primary"])
    style.configure(
        "TButton",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        relief="flat",
        borderwidth=1,
        focusthickness=1,
        focuscolor=COLORS["primary"],
        padding=(10, 6),
    )
    style.map(
        "TButton",
        background=[("disabled", COLORS["surface_subtle"]), ("active", COLORS["border"]), ("!disabled", COLORS["surface"])],
        foreground=[("disabled", COLORS["muted"]), ("!disabled", COLORS["text"])],
    )
    style.configure(
        "Secondary.TButton",
        background=COLORS["surface_subtle"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        relief="flat",
        borderwidth=1,
        padding=(10, 6),
    )
    style.map(
        "Secondary.TButton",
        background=[
            ("disabled", COLORS["surface_subtle"]),
            ("active", COLORS["border"]),
            ("!disabled", COLORS["surface_subtle"]),
        ],
        foreground=[("disabled", COLORS["muted"]), ("!disabled", COLORS["text"])],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=COLORS["surface_subtle"],
        troughcolor=COLORS["bg"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        arrowcolor=COLORS["text"],
        relief="flat",
        borderwidth=0,
        width=12,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", COLORS["border"]), ("!active", COLORS["surface_subtle"])],
        arrowcolor=[("disabled", COLORS["muted"]), ("!disabled", COLORS["text"])],
    )
    style.configure(
        "Primary.TButton",
        background=COLORS["primary"],
        foreground=COLORS["primary_text"],
        bordercolor=COLORS["primary"],
        relief="flat",
        borderwidth=0,
        focusthickness=2,
        focuscolor=COLORS["primary"],
        padding=(14, 7),
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", COLORS["primary_pressed"]), ("active", COLORS["primary_pressed"]), ("disabled", COLORS["border"])],
        foreground=[("disabled", COLORS["muted"])],
    )


@dataclass(frozen=True)
class TitleBarStyleResult:
    hwnd: int | None = None
    dark_mode_hresult: int | None = None
    caption_color_hresult: int | None = None
    text_color_hresult: int | None = None
    frame_refreshed: bool = False
    error: str | None = None

    @property
    def dark_mode_applied(self) -> bool:
        return self.dark_mode_hresult is not None and self.dark_mode_hresult >= 0


def _colorref(color: str) -> int:
    """Convert a Tk #RRGGBB color into Win32's 0x00BBGGRR COLORREF."""
    red, green, blue = (int(color[index:index + 2], 16) for index in (1, 3, 5))
    return red | green << 8 | blue << 16


def enable_dark_title_bar(window) -> TitleBarStyleResult:
    """Style the actual Tk wrapper synchronously, without activating the window.

    At startup the caller must withdraw, build and update_idletasks first, then
    call this before deiconify. Tk's wrapper HWND does not exist reliably before
    that idle geometry pass. A root <Map> callback can also call this when a
    wrapper is recreated. No delayed timer or focus change is needed to repaint.
    """
    if sys.platform != "win32":
        return TitleBarStyleResult()
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.RedrawWindow.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT),
                                       wintypes.HRGN, wintypes.UINT]
        user32.RedrawWindow.restype = wintypes.BOOL
        dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                               ctypes.c_void_p, wintypes.DWORD]
        dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long  # HRESULT, not a pointer

        # winfo_id identifies Tk's client window; DWM owns its top-level wrapper.
        hwnd = user32.GetAncestor(window.winfo_id(), 2)  # GA_ROOT
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        def set_attribute(attribute: int, value: int) -> int:
            data = wintypes.DWORD(value)  # BOOL and COLORREF are both 32 bits
            return int(dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data)))

        dark_result = set_attribute(20, 1)  # DWMWA_USE_IMMERSIVE_DARK_MODE
        if dark_result < 0:
            dark_result = set_attribute(19, 1)  # compatibility with older Windows 10
        # Explicit colors also keep active/inactive captions aligned on Windows
        # 11. Windows 10 rejects these with E_INVALIDARG; dark mode still works.
        caption_result = set_attribute(35, _colorref(COLORS["bg"]))
        text_result = set_attribute(36, _colorref(COLORS["text"]))
        flags = 0x0020 | 0x0001 | 0x0002 | 0x0004 | 0x0010
        # SWP_FRAMECHANGED | NOSIZE | NOMOVE | NOZORDER | NOACTIVATE
        positioned = bool(user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, flags))
        # RDW_INVALIDATE | RDW_FRAME | RDW_UPDATENOW: repaint non-client chrome
        # immediately instead of waiting for a later activation message.
        redrawn = bool(user32.RedrawWindow(hwnd, None, None, 0x0001 | 0x0400 | 0x0100))
        return TitleBarStyleResult(int(hwnd), dark_result, caption_result, text_result, positioned and redrawn)
    except (OSError, TclError) as exc:
        return TitleBarStyleResult(error=str(exc))
