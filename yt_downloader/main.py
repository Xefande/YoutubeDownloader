from __future__ import annotations

import traceback

from .app_paths import APP_DIR
from .branding import APP_NAME, apply_window_branding
from .diagnostics import write_error_report


def main() -> None:
    try:
        from .ui import App
        App().mainloop()
    except Exception:
        tb = traceback.format_exc()
        log_path = write_error_report(tb, APP_DIR)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            apply_window_branding(root)
            root.withdraw()
            messagebox.showerror(APP_NAME, f"{APP_NAME} could not start.\n\n{tb.splitlines()[-1]}\n\nDetails:\n{log_path or 'Error log could not be written.'}", parent=root)
            root.destroy()
        except Exception:
            pass
        raise
