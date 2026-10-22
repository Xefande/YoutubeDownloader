"""Tk widget tree and rendering, separated from application orchestration.

App supplies the event handlers referenced while building the view.
This presentation base never imports the downloader or performs I/O.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import __version__
from .branding import APP_NAME
from .presets import AUDIO_PRESETS, AUDIO_TRACK_LANGS_UI, BITRATE_PRESETS_UI, QUALITY_PRESETS, SUB_LANGS_UI, SUB_LANG_SHORT_LABELS
from .ui_theme import COLORS, configure_styles

MODE_VIDEO = "video"
MODE_AUDIO = "audio"


class AppView(tk.Tk):
    def _build_ui(self) -> None:
        configure_styles(self)

        root = ttk.Frame(self, padding=16, style="App.TFrame")
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        self._build_header(root)
        main = ttk.Frame(root, style="App.TFrame")
        main.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        main.columnconfigure(0, weight=3, minsize=470)
        main.columnconfigure(1, weight=2, minsize=390)

        left = ttk.Frame(main, style="App.TFrame")
        right = ttk.Frame(main, style="App.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self._build_source(left)
        self._build_destination(left)
        self._build_status(left)
        self._build_middle(right)
        self._build_details(root)
        self._bind_shortcuts()

        self.after_idle(self.txt_urls.focus_set)


    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)

        title_block = ttk.Frame(header, style="App.TFrame")
        title_block.grid(row=0, column=0, sticky="w")
        self.lbl_logo = ttk.Label(title_block, image=self.header_logo, style="Title.TLabel")
        self.lbl_logo.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        self.lbl_title = ttk.Label(title_block, text=APP_NAME, style="Title.TLabel")
        self.lbl_title.grid(row=0, column=1, sticky="sw")
        ttk.Label(title_block, text=f"Video, audio & subtitles · v{__version__}", style="AppMuted.TLabel").grid(
            row=1, column=1, sticky="nw")

        tools = ttk.Frame(header, style="App.TFrame")
        tools.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.var_tool_status = tk.StringVar()
        self.lbl_tool_status = tk.Label(
            tools,
            textvariable=self.var_tool_status,
            bg=COLORS["surface_subtle"],
            fg=COLORS["muted"],
            padx=10,
            pady=5,
            bd=0,
            relief="flat",
            highlightthickness=1,
            font=("Segoe UI", 9),
        )
        self.lbl_tool_status.grid(row=1, column=0, sticky="e", pady=(5, 0))
        self.btn_update = ttk.Button(tools, text="Update tools", command=self._start_update_tools, style="Secondary.TButton")
        self.btn_update.grid(row=0, column=0, sticky="e")
        self._refresh_tool_status()

        # The long product name and native font scaling must not overlap the
        # status badge. Stack the tools below the title when space is limited.
        stacked = None

        def arrange_header(event) -> None:
            nonlocal stacked
            tools_width = max(self.lbl_tool_status.winfo_reqwidth(), self.btn_update.winfo_reqwidth())
            needs_stack = event.width < title_block.winfo_reqwidth() + tools_width + 12
            if needs_stack == stacked:
                return
            stacked = needs_stack
            if stacked:
                title_block.grid_configure(columnspan=2)
                tools.grid_configure(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=(8, 0))
                tools.columnconfigure(0, weight=1)
                self.lbl_tool_status.grid_configure(row=0, column=0, sticky="w", pady=0)
                self.btn_update.grid_configure(row=0, column=1, padx=(12, 0))
            else:
                title_block.grid_configure(columnspan=1)
                tools.grid_configure(row=0, column=1, columnspan=1, sticky="e", padx=(12, 0), pady=0)
                tools.columnconfigure(0, weight=0)
                self.lbl_tool_status.grid_configure(row=1, column=0, sticky="e", pady=(5, 0))
                self.btn_update.grid_configure(row=0, column=0, padx=0)

        header.bind("<Configure>", arrange_header)


    def _build_source(self, parent: ttk.Frame) -> None:
        source = self._make_section(parent, "YouTube links · one per line", "")
        source.pack(fill="x", pady=(0, 8))
        source.columnconfigure(0, weight=1)

        self.txt_urls = tk.Text(
            source,
            height=3,
            wrap="word",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["selection"],
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["primary"],
            font=("Segoe UI", 10),
        )
        self.txt_urls.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.txt_urls.bind("<<Modified>>", self._on_urls_modified)
        self.txt_urls.bind("<<Paste>>", lambda _event: self.after_idle(self._refresh_ready_state))

        self.var_link_count = tk.StringVar(value="No links detected")
        ttk.Label(source, textvariable=self.var_link_count, style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.btn_clear_urls = ttk.Button(source, text="Clear links", command=self._clear_urls, style="Secondary.TButton")
        self.btn_clear_urls.grid(row=2, column=1, sticky="e", pady=(8, 0))


    def _build_destination(self, parent: ttk.Frame) -> None:
        dest = self._make_section(parent, "Destination", "")
        dest.pack(fill="x", pady=(0, 8))
        dest.columnconfigure(0, weight=0)
        dest.columnconfigure(1, weight=1)

        ttk.Label(dest, text="Output folder").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.var_out = tk.StringVar()
        self.ent_out = ttk.Entry(dest, textvariable=self.var_out)
        self.ent_out.grid(row=1, column=1, sticky="ew", padx=(12, 8), pady=(10, 0))
        self.btn_browse = ttk.Button(dest, text="Browse", command=self._browse_out, style="Secondary.TButton")
        self.btn_browse.grid(row=1, column=2, sticky="e", pady=(10, 0))
        ttk.Label(dest, text="Relative folders use the app location.", style="Muted.TLabel").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )


    def _build_middle(self, parent: ttk.Frame) -> None:
        self.middle = ttk.Frame(parent, style="App.TFrame")
        self.middle.pack(fill="both", expand=True)

        tab_bar = tk.Frame(self.middle, bg=COLORS["bg"], bd=0, highlightthickness=0)
        tab_bar.pack(fill="x", pady=(0, 8))
        self.btn_tab_setup = self._make_tab_button(tab_bar, "Setup", lambda: self._select_middle_tab("setup"))
        self.btn_tab_options = self._make_tab_button(tab_bar, "Options", lambda: self._select_middle_tab("options"))
        self.btn_tab_setup.pack(side="left")
        self.btn_tab_options.pack(side="left", padx=(6, 0))

        self.middle_body = ttk.Frame(self.middle, style="App.TFrame")
        self.middle_body.pack(fill="both", expand=True)
        self.middle_body.columnconfigure(0, weight=1)
        self.middle_body.rowconfigure(0, weight=1)

        self.setup_section = self._make_section(self.middle_body, "Download setup", "Choose your format and quality.")
        self.options_section = self._make_section(self.middle_body, "Options", "Subtitles and advanced preferences.")
        self.setup_section.grid(row=0, column=0, sticky="nsew")
        self.options_section.grid(row=0, column=0, sticky="nsew")

        self._build_setup_content(self.setup_section)
        self._build_options_content(self.options_section)
        self._select_middle_tab("setup")


    def _make_tab_button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=COLORS["surface_subtle"],
            fg=COLORS["text"],
            activebackground=COLORS["border"],
            activeforeground=COLORS["text"],
            disabledforeground=COLORS["muted"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["primary"],
            padx=14,
            pady=6,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        return button


    def _select_middle_tab(self, tab: str) -> None:
        self._middle_tab = tab
        tabs = {
            "setup": (self.btn_tab_setup, self.setup_section),
            "options": (self.btn_tab_options, self.options_section),
        }
        for name, (button, frame) in tabs.items():
            selected = name == tab
            if selected:
                frame.grid()
                frame.tkraise()
                button.configure(bg=COLORS["selection"], fg=COLORS["text"], highlightbackground=COLORS["primary"])
            else:
                frame.grid_remove()
                button.configure(bg=COLORS["surface_subtle"], fg=COLORS["text"], highlightbackground=COLORS["border"])


    def _build_setup_content(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        mode_line = ttk.Frame(parent, style="CardBody.TFrame")
        mode_line.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        mode_line.columnconfigure(2, weight=1)

        ttk.Label(mode_line, text="Mode").grid(row=0, column=0, sticky="w")
        self.var_mode = tk.StringVar(value=MODE_VIDEO)
        self.var_audio_only = tk.BooleanVar(value=False)
        self.rdo_video = ttk.Radiobutton(mode_line, text="Video", variable=self.var_mode, value=MODE_VIDEO, command=self._refresh_mode_ui)
        self.rdo_audio = ttk.Radiobutton(mode_line, text="Audio", variable=self.var_mode, value=MODE_AUDIO, command=self._refresh_mode_ui)
        self.rdo_video.grid(row=0, column=1, sticky="w", padx=(14, 8))
        self.rdo_audio.grid(row=0, column=2, sticky="w")

        self.video_settings = ttk.Frame(parent, style="CardBody.TFrame")
        self.video_settings.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.video_settings.columnconfigure(1, weight=1)

        ttk.Label(self.video_settings, text="Quality").grid(row=0, column=0, sticky="w")
        self.var_quality = tk.StringVar()
        self.cmb_quality = ttk.Combobox(
            self.video_settings,
            textvariable=self.var_quality,
            values=list(QUALITY_PRESETS.keys()),
            state="readonly",
            width=26,
        )
        self.cmb_quality.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        ttk.Label(self.video_settings, text="Max bitrate").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.var_bitrate = tk.StringVar(value=list(BITRATE_PRESETS_UI.keys())[0])
        self.cmb_bitrate = ttk.Combobox(
            self.video_settings,
            textvariable=self.var_bitrate,
            values=list(BITRATE_PRESETS_UI.keys()),
            state="readonly",
            width=26,
        )
        self.cmb_bitrate.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))

        self.audio_settings = ttk.Frame(parent, style="CardBody.TFrame")
        self.audio_settings.columnconfigure(1, weight=1)

        ttk.Label(self.audio_settings, text="Audio format").grid(row=0, column=0, sticky="w")
        self.var_audio_label = tk.StringVar()
        self.cmb_audio = ttk.Combobox(
            self.audio_settings,
            textvariable=self.var_audio_label,
            values=list(AUDIO_PRESETS.keys()),
            state="readonly",
            width=26,
        )
        self.cmb_audio.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        self.track_settings = ttk.Frame(parent, style="CardBody.TFrame")
        self.track_settings.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self.track_settings.columnconfigure(1, weight=1)

        ttk.Label(self.track_settings, text="Audio track").grid(row=0, column=0, sticky="w")
        self.var_audio_track = tk.StringVar(value=AUDIO_TRACK_LANGS_UI[0][0])
        self.cmb_audio_track = ttk.Combobox(
            self.track_settings,
            textvariable=self.var_audio_track,
            values=[item[0] for item in AUDIO_TRACK_LANGS_UI],
            state="readonly",
            width=26,
        )
        self.cmb_audio_track.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        ttk.Label(parent, text="Each video gets its own dated folder.", style="Muted.TLabel").grid(
            row=4, column=0, sticky="w", pady=(12, 0)
        )


    def _build_options_content(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        self.var_subs = tk.BooleanVar()
        self.var_dry = tk.BooleanVar()
        self.var_open_folder = tk.BooleanVar()

        self.chk_subs = ttk.Checkbutton(parent, text="Download subtitles", variable=self.var_subs, command=self._refresh_subs_ui)
        self.chk_subs.grid(row=1, column=0, sticky="w", pady=(10, 0))

        self.subs_lang_frame = ttk.Frame(parent, style="CardBody.TFrame")
        self.subs_lang_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.sub_lang_vars: dict[str, tk.BooleanVar] = {}
        self.sub_lang_buttons: list[ttk.Checkbutton] = []
        for index, (_label, code) in enumerate(SUB_LANGS_UI):
            var = tk.BooleanVar()
            self.sub_lang_vars[code] = var
            button = ttk.Checkbutton(self.subs_lang_frame, text=SUB_LANG_SHORT_LABELS[code], variable=var)
            button.grid(row=index // 5, column=index % 5, sticky="w", padx=(0, 10), pady=2)
            self.sub_lang_buttons.append(button)

        self.chk_open_folder = ttk.Checkbutton(parent, text="Open output folder when finished", variable=self.var_open_folder)
        self.chk_open_folder.grid(row=3, column=0, sticky="w", pady=(12, 0))

        advanced = ttk.Frame(parent, style="CardBody.TFrame")
        advanced.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        advanced.columnconfigure(1, weight=1)
        ttk.Label(advanced, text="Advanced", style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(advanced, text="After date").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.var_after = tk.StringVar()
        self.ent_after = ttk.Entry(advanced, textvariable=self.var_after)
        self.ent_after.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))
        ttk.Label(advanced, text="YYYY-MM-DD or YYYYMMDD", style="Muted.TLabel").grid(
            row=2, column=1, sticky="w", padx=(12, 0), pady=(4, 0)
        )
        self.chk_dry = ttk.Checkbutton(advanced, text="Dry-run (do not download)", variable=self.var_dry)
        self.chk_dry.grid(row=3, column=1, sticky="w", padx=(12, 0), pady=(10, 0))


    def _build_status(self, parent: ttk.Frame) -> None:
        status = self._make_section(parent, "Download", "")
        status.pack(fill="x")
        status.columnconfigure(0, weight=1)

        row = ttk.Frame(status, style="CardBody.TFrame")
        row.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        row.columnconfigure(0, weight=1)

        self.lbl_status_badge = tk.Label(
            row,
            text="Ready",
            padx=10,
            pady=5,
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_status_badge.grid(row=0, column=0, sticky="w")
        self.var_status_detail = tk.StringVar(value="Paste at least one YouTube link.")
        self.lbl_status_detail = ttk.Label(row, textvariable=self.var_status_detail, style="Muted.TLabel", wraplength=440)
        self.lbl_status_detail.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        row.bind("<Configure>", lambda event: self.lbl_status_detail.configure(wraplength=max(100, event.width - 4)))

        self.progress = ttk.Progressbar(status, mode="determinate")
        self.progress.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        actions = ttk.Frame(status, style="CardBody.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        self.btn_start = ttk.Button(actions, text="Start download", command=self._start_download, style="Primary.TButton")
        self.btn_start.grid(row=0, column=0, sticky="w")
        self.btn_cancel = ttk.Button(actions, text="Cancel", command=self._cancel_download, state="disabled", style="Secondary.TButton")
        self.btn_cancel.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.btn_save = ttk.Button(actions, text="Save settings", command=self._save_config_from_ui, style="Secondary.TButton")
        self.btn_save.grid(row=0, column=2, sticky="w", padx=(8, 0))

        self._set_status("idle", "Ready", "Paste at least one YouTube link.")


    def _build_details(self, parent: ttk.Frame) -> None:
        details = self._make_section(parent, "Activity log", "")
        details.grid(row=2, column=0, sticky="nsew")
        details.columnconfigure(0, weight=1)
        details.rowconfigure(1, weight=1)
        self.btn_clear_log = ttk.Button(details, text="Clear log", command=self._clear_log, style="Secondary.TButton")
        self.btn_clear_log.grid(row=0, column=0, sticky="e")

        log_shell = ttk.Frame(details, style="CardBody.TFrame")
        log_shell.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        log_shell.columnconfigure(0, weight=1)
        log_shell.rowconfigure(0, weight=1)

        self.txt_log = tk.Text(
            log_shell,
            height=4,
            wrap="word",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["selection"],
            bd=0,
            highlightthickness=0,
            font=("Consolas", 9),
        )
        self.txt_log.grid(row=0, column=0, sticky="nsew")

        scr = ttk.Scrollbar(log_shell, orient="vertical", command=self.txt_log.yview)
        scr.grid(row=0, column=1, sticky="ns")
        self.txt_log.configure(yscrollcommand=scr.set)

        self._log(f"Config: {self.config_path}")


    def _make_section(self, parent: tk.Widget, title: str, subtitle: str) -> tk.Frame:
        frame = tk.Frame(
            parent,
            padx=10,
            pady=8,
            bg=COLORS["surface"],
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["surface_subtle"],
            highlightcolor=COLORS["primary"],
        )
        frame.columnconfigure(0, weight=1)
        header = ttk.Frame(frame, style="CardBody.TFrame")
        header.grid(row=0, column=0, sticky="ew", columnspan=3)
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=title, style="SectionTitle.TLabel").grid(row=0, column=0, sticky="w")
        if subtitle:
            ttk.Label(header, text=subtitle, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        return frame


    def _set_status(self, kind: str, label: str, detail: str) -> None:
        status_colors = {
            "idle": (COLORS["surface_subtle"], COLORS["muted"]),
            "ready": (COLORS["surface_subtle"], COLORS["text"]),
            "running": ("#123A35", COLORS["primary"]),
            "success": (COLORS["success_bg"], COLORS["success_text"]),
            "warning": (COLORS["warning_bg"], COLORS["warning_text"]),
            "cancelled": (COLORS["warning_bg"], COLORS["warning_text"]),
            "error": (COLORS["danger_bg"], COLORS["danger_text"]),
        }
        bg, fg = status_colors.get(kind, status_colors["idle"])
        self.lbl_status_badge.configure(text=label, bg=bg, fg=fg)
        if len(detail) > 180 and hasattr(self, "txt_log"):
            self._log(detail)
        self.var_status_detail.set(detail if len(detail) <= 180 else detail[:177] + "…")
