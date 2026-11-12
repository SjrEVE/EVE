"""Dispatch-grid redesign for the fila-bot Windows operator console.

This module owns presentation only. UiModel remains the source of truth and
all buttons send the same model events as the previous UI.
"""
from __future__ import annotations

import time
from typing import Any

from .ui_model import MODE_LABELS, MODES, UiModel

PALETTE = {
    "navy": "#173044",
    "navy_hover": "#284b60",
    "ink": "#202b32",
    "muted": "#68767b",
    "paper": "#f0f2ed",
    "white": "#ffffff",
    "line": "#d2d9d3",
    "blue": "#225c7a",
    "gold": "#d5a64a",
    "green": "#486d62",
    "green_bg": "#e4eee8",
    "red": "#a93f39",
    "red_bg": "#fae8e5",
    "amber": "#7f5c24",
    "amber_bg": "#f6eddc",
    "disabled": "#e7ebe7",
}
FONT = "Segoe UI"
DATA_FONT = "Consolas"


def _int_or_none(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


def build_window(root: Any, model: UiModel, auto_close_ms: int = 0) -> dict[str, Any]:
    """Build the dispatch-grid UI on ``root`` and return testable controls."""
    import tkinter as tk
    from tkinter import messagebox, ttk

    from fila_bot.version import short

    root.title(f"fila-bot {short()} — EVE Operations")
    root.geometry("1180x760")
    root.minsize(960, 680)
    root.configure(background=PALETTE["paper"])
    root.resizable(True, True)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Fila.TEntry", padding=(9, 7), fieldbackground="#fbfcfa",
        foreground=PALETTE["ink"], bordercolor=PALETTE["line"],
    )
    style.map(
        "Fila.TEntry",
        fieldbackground=[("disabled", PALETTE["disabled"]), ("!disabled", "#fbfcfa")],
        foreground=[("disabled", PALETTE["muted"]), ("!disabled", PALETTE["ink"])],
    )
    style.configure(
        "Fila.TCombobox", padding=(8, 6), fieldbackground="#fbfcfa",
        background="#fbfcfa", foreground=PALETTE["ink"], arrowcolor=PALETTE["navy"],
    )
    style.map(
        "Fila.TCombobox",
        fieldbackground=[("disabled", PALETTE["disabled"]), ("readonly", "#fbfcfa")],
        foreground=[("disabled", PALETTE["muted"]), ("readonly", PALETTE["ink"])],
    )
    style.configure(
        "Fila.Vertical.TScrollbar", background="#d6ded8", troughcolor=PALETTE["paper"],
        bordercolor=PALETTE["paper"], arrowcolor=PALETTE["muted"],
    )

    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(4, weight=1)

    mode_var = tk.StringVar(value=model.mode)
    sim_var = tk.BooleanVar(value=True)
    dry_var = tk.BooleanVar(value=True)
    hours_var = tk.StringVar(value="4")
    filament_var = tk.StringVar(value=model.filament)
    mission_limit_var = tk.StringVar(value="")
    run_limit_var = tk.StringVar(value="")
    engine_var = tk.StringVar(value=model.engine)
    mode_summary = tk.StringVar(value=MODE_LABELS[model.mode])
    safety_summary = tk.StringVar(value="SIM: no EVE connection · DRY: read-only")
    safety_detail = tk.StringVar(value="No game input will be sent in this setup.")
    state_var = tk.StringVar(value="IDLE")
    status_copy = tk.StringVar(value="No active run")
    phase_var = tk.StringVar(value="—")
    elapsed_var = tk.StringVar(value="0:00:00")
    stat1_label = tk.StringVar(value="Runs")
    stat1_value = tk.StringVar(value="0")
    stat2_label = tk.StringVar(value="Room")
    stat2_value = tk.StringVar(value="—")
    stat3_label = tk.StringVar(value="Filaments")
    stat3_value = tk.StringVar(value="—")
    history_note = tk.StringVar(value="No phase changes yet")
    log_summary = tk.StringVar(value="No events yet")
    stats_summary = tk.StringVar(value="0 sessions · 0 completed · 0 crashes")

    # Header: product identity, mode tabs, and explicit safety controls.
    header = tk.Frame(root, bg=PALETTE["navy"], height=60)
    header.grid(row=0, column=0, sticky="ew")
    header.grid_propagate(False)
    header.grid_columnconfigure(1, weight=1)

    brand = tk.Frame(header, bg=PALETTE["navy"])
    brand.grid(row=0, column=0, sticky="nsw", padx=(24, 22))
    mark = tk.Canvas(brand, width=25, height=25, bg=PALETTE["navy"],
                     highlightthickness=0, bd=0)
    mark.pack(side="left", pady=17, padx=(0, 9))
    mark.create_oval(3, 3, 22, 22, outline="#9bbab1", width=1)
    mark.create_line(1, 18, 23, 7, fill=PALETTE["gold"], width=1)
    mark.create_oval(15, 5, 19, 9, fill=PALETTE["gold"], outline="")
    tk.Label(
        brand, text="FILA / BOT", bg=PALETTE["navy"], fg="#f5f7f2",
        font=(FONT, 12, "bold"),
    ).pack(side="left", pady=17)

    mode_tabs = tk.Frame(header, bg=PALETTE["navy"])
    mode_tabs.grid(row=0, column=1, sticky="w")
    mode_buttons: dict[str, Any] = {}

    safety_controls = tk.Frame(header, bg=PALETTE["navy"])
    safety_controls.grid(row=0, column=2, sticky="e", padx=(12, 22))
    sim_label = tk.StringVar(value="SIM  ON")
    dry_label = tk.StringVar(value="DRY  ON")

    def style_safety_button(button: Any, active: bool) -> None:
        chip = "#355d54" if active else "#294352"
        button.configure(
            bg=chip,
            selectcolor=chip,
            fg="#f2f7f3" if active else "#becbd0",
            activebackground="#477366" if active else PALETTE["navy_hover"],
            highlightbackground="#59717e",
        )

    live_warning = tk.Label(
        root, text="LIVE INPUT: SIM and DRY are both off. Starting can send real clicks and keys to EVE.",
        bg=PALETTE["red_bg"], fg=PALETTE["red"], anchor="w",
        font=(FONT, 9, "bold"), padx=24, pady=8,
        highlightthickness=1, highlightbackground="#efc4bf",
    )
    live_warning.grid(row=1, column=0, sticky="ew")
    live_warning.grid_remove()

    heading = tk.Frame(root, bg=PALETTE["paper"])
    heading.grid(row=2, column=0, sticky="ew", padx=28, pady=(8, 6))
    heading.grid_columnconfigure(0, weight=1)
    heading_title = tk.Label(
        heading, text="Run control", bg=PALETTE["paper"], fg=PALETTE["ink"],
        font=(FONT, 20, "bold"), anchor="w",
    )
    heading_title.grid(row=0, column=0, sticky="w")
    tk.Label(
        heading, text="Configure and supervise the selected mode", bg=PALETTE["paper"],
        fg=PALETTE["muted"], font=(FONT, 9), anchor="e",
    ).grid(row=0, column=1, sticky="e")

    def update_safety(*_args: Any) -> None:
        sim = bool(sim_var.get())
        dry = bool(dry_var.get())
        sim_label.set(f"SIM  {'ON' if sim else 'OFF'}")
        dry_label.set(f"DRY  {'ON' if dry else 'OFF'}")
        style_safety_button(sim_button, sim)
        style_safety_button(dry_button, dry)
        if sim and dry:
            safety_summary.set("SIM: no EVE connection · DRY: read-only")
            safety_detail.set("No game input will be sent in this setup.")
            safety_bar.configure(bg=PALETTE["green"])
            live_warning.grid_remove()
        elif sim:
            safety_summary.set("SIM: no EVE connection · DRY off")
            safety_detail.set("Simulation still prevents real EVE input.")
            safety_bar.configure(bg=PALETTE["green"])
            live_warning.grid_remove()
        elif dry:
            safety_summary.set("Client mode · read-only (DRY)")
            safety_detail.set("EVE may be read, but input is disabled.")
            safety_bar.configure(bg=PALETTE["blue"])
            live_warning.grid_remove()
        else:
            safety_summary.set("LIVE INPUT ENABLED")
            safety_detail.set("Real input to EVE is enabled; confirmation is required.")
            safety_bar.configure(bg=PALETTE["red"])
            live_warning.grid()

    sim_button = tk.Checkbutton(
        safety_controls, textvariable=sim_label, variable=sim_var,
        command=update_safety, indicatoron=False, relief="flat", bd=0,
        padx=10, pady=7, font=(FONT, 8, "bold"), takefocus=True,
        highlightthickness=1, highlightbackground="#59717e", highlightcolor=PALETTE["gold"],
    )
    dry_button = tk.Checkbutton(
        safety_controls, textvariable=dry_label, variable=dry_var,
        command=update_safety, indicatoron=False, relief="flat", bd=0,
        padx=10, pady=7, font=(FONT, 8, "bold"), takefocus=True,
        highlightthickness=1, highlightbackground="#59717e", highlightcolor=PALETTE["gold"],
    )
    sim_button.pack(side="left", padx=(0, 7), pady=11)
    dry_button.pack(side="left", pady=11)

    def sync_mode_fields(*_args: Any) -> None:
        abyss = mode_var.get() == "abyss"
        filament_entry.state(["!disabled"] if abyss else ["disabled"])
        max_runs_entry.state(["!disabled"] if abyss else ["disabled"])
        engine_combo.state(["!disabled", "readonly"] if abyss else ["!readonly", "disabled"])
        max_missions_entry.state(["disabled"] if abyss else ["!disabled"])
        mode_summary.set(MODE_LABELS.get(mode_var.get(), mode_var.get()))

    def update_mode_tabs(*_args: Any) -> None:
        for key, button in mode_buttons.items():
            selected = mode_var.get() == key
            button.configure(
                bg=PALETTE["navy_hover"] if selected else PALETTE["navy"],
                fg="#ffffff" if selected else "#c3d0d3",
                highlightbackground=PALETTE["gold"] if selected else PALETTE["navy"],
                highlightcolor=PALETTE["gold"] if selected else PALETTE["navy"],
            )
        sync_mode_fields()

    for key in MODES:
        button = tk.Radiobutton(
            mode_tabs, text=MODE_LABELS[key], variable=mode_var, value=key,
            indicatoron=False, relief="flat", bd=0, padx=13, pady=8,
            bg=PALETTE["navy"], fg="#c3d0d3", selectcolor=PALETTE["navy_hover"],
            activebackground=PALETTE["navy_hover"], activeforeground="#ffffff",
            font=(FONT, 9, "bold"), takefocus=True,
            highlightthickness=2, highlightbackground=PALETTE["navy"],
            highlightcolor=PALETTE["gold"], command=update_mode_tabs,
        )
        button.pack(side="left", padx=(0, 4), pady=8)
        mode_buttons[key] = button

    # One scan line carries the live run state, actual phase, and safety summary.
    status_row = tk.Frame(root, bg=PALETTE["paper"], height=64)
    status_row.grid(row=3, column=0, sticky="ew", padx=28)
    status_row.grid_propagate(False)
    status_row.grid_columnconfigure(1, weight=1)
    state_badge = tk.Label(
        status_row, textvariable=state_var, bg="#dfe8e2", fg=PALETTE["green"],
        font=(FONT, 9, "bold"), padx=10, pady=6,
    )
    state_badge.grid(row=0, column=0, sticky="w", pady=(9, 0), padx=(0, 13))
    status_label = tk.Label(
        status_row, textvariable=status_copy, bg=PALETTE["paper"], fg=PALETTE["ink"],
        font=(FONT, 10), anchor="w",
    )
    status_label.grid(row=0, column=1, sticky="ew", pady=(8, 0))
    safety_label = tk.Label(
        status_row, textvariable=safety_summary, bg=PALETTE["paper"],
        fg=PALETTE["muted"], font=(FONT, 8), anchor="w",
    )
    safety_label.grid(row=1, column=1, sticky="w", pady=(0, 7))
    tk.Label(
        status_row, text="Phase", bg=PALETTE["paper"], fg=PALETTE["muted"],
        font=(FONT, 8), anchor="e",
    ).grid(row=0, column=2, sticky="e", padx=(16, 2), pady=(8, 0))
    tk.Label(
        status_row, textvariable=phase_var, bg=PALETTE["paper"],
        fg=PALETTE["ink"], font=(DATA_FONT, 9, "bold"), anchor="e",
    ).grid(row=1, column=2, sticky="e", padx=(16, 2), pady=(0, 7))

    work = tk.Frame(root, bg=PALETTE["paper"])
    work.grid(row=4, column=0, sticky="nsew", padx=28, pady=(0, 8))
    work.grid_columnconfigure(0, weight=1, uniform="panels", minsize=400)
    work.grid_columnconfigure(1, weight=1, uniform="panels", minsize=400)
    work.grid_rowconfigure(0, weight=1)

    def panel(parent: Any, column: int, title: str, subtitle_var: Any | None = None) -> Any:
        outer = tk.Frame(parent, bg=PALETTE["line"], padx=1, pady=1)
        outer.grid(row=0, column=column, sticky="nsew", padx=(0, 8) if column == 0 else (8, 0))
        inside = tk.Frame(outer, bg=PALETTE["white"], padx=17, pady=15)
        inside.pack(fill="both", expand=True)
        inside.grid_columnconfigure(0, weight=1)
        head = tk.Frame(inside, bg=PALETTE["white"])
        head.grid(row=0, column=0, sticky="ew", pady=(0, 13))
        head.grid_columnconfigure(0, weight=1)
        tk.Label(
            head, text=title, bg=PALETTE["white"], fg=PALETTE["ink"],
            font=(FONT, 11, "bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w")
        if subtitle_var is not None:
            tk.Label(
                head, textvariable=subtitle_var, bg=PALETTE["white"],
                fg=PALETTE["muted"], font=(FONT, 8), anchor="e",
            ).grid(row=0, column=1, sticky="e")
        tk.Frame(inside, bg=PALETTE["line"], height=1).grid(
            row=1, column=0, sticky="ew", pady=(0, 14)
        )
        return inside

    settings = panel(work, 0, "Configure run", mode_summary)
    settings.grid_columnconfigure(0, weight=1)
    settings.grid_columnconfigure(1, weight=1)

    def field_label(parent: Any, text: str, row: int, column: int) -> None:
        tk.Label(
            parent, text=text, bg=PALETTE["white"], fg=PALETTE["muted"],
            font=(FONT, 8), anchor="w",
        ).grid(row=row, column=column, sticky="w", padx=(0, 10), pady=(0, 4))

    def make_entry(parent: Any, variable: Any, row: int, column: int, width: int = 20) -> Any:
        entry = ttk.Entry(parent, textvariable=variable, style="Fila.TEntry", width=width)
        entry.grid(row=row + 1, column=column, sticky="ew", padx=(0, 10), pady=(0, 12))
        return entry

    field_label(settings, "Filament", 2, 0)
    filament_entry = make_entry(settings, filament_var, 2, 0, 24)
    field_label(settings, "Engine", 2, 1)
    engine_combo = ttk.Combobox(
        settings, textvariable=engine_var, values=("fsm", "bt"),
        state="readonly", style="Fila.TCombobox", width=12,
    )
    engine_combo.grid(row=3, column=1, sticky="ew", padx=(0, 0), pady=(0, 12))

    field_label(settings, "Maximum session", 4, 0)
    hours_entry = make_entry(settings, hours_var, 4, 0, 12)
    field_label(settings, "Maximum missions", 4, 1)
    max_missions_entry = make_entry(settings, mission_limit_var, 4, 1, 12)
    field_label(settings, "Maximum runs", 6, 0)
    max_runs_entry = make_entry(settings, run_limit_var, 6, 0, 12)
    tk.Label(
        settings, text="Set a limit only when this run needs one.",
        bg=PALETTE["white"], fg=PALETTE["muted"], font=(FONT, 8), anchor="w",
    ).grid(row=7, column=1, sticky="w", padx=(0, 4), pady=(0, 12))

    safety_bar = tk.Frame(settings, bg=PALETTE["green"], height=3)
    tk.Frame(settings, bg=PALETTE["line"], height=1).grid(
        row=8, column=0, columnspan=2, sticky="ew", pady=(1, 12)
    )
    tk.Label(
        settings, text="Safety mode", bg=PALETTE["white"], fg=PALETTE["ink"],
        font=(FONT, 9, "bold"), anchor="w",
    ).grid(row=9, column=0, sticky="w")
    tk.Label(
        settings, textvariable=safety_detail, bg=PALETTE["white"],
        fg=PALETTE["muted"], font=(FONT, 8), anchor="e",
    ).grid(row=9, column=1, sticky="e")
    safety_bar.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(9, 0))

    # Operate panel: actual model state and controls, not decorative metrics.
    operate = panel(work, 1, "Operate", stats_summary)
    operate.grid_columnconfigure(0, weight=1)
    run_summary = tk.Frame(operate, bg=PALETTE["white"])
    run_summary.grid(row=2, column=0, sticky="ew", pady=(0, 13))
    run_summary.grid_columnconfigure(0, weight=1)
    tk.Label(
        run_summary, text="Run state", bg=PALETTE["white"], fg=PALETTE["muted"],
        font=(FONT, 8), anchor="w",
    ).grid(row=0, column=0, sticky="w")
    tk.Label(
        run_summary, text="Elapsed", bg=PALETTE["white"], fg=PALETTE["muted"],
        font=(FONT, 8), anchor="e",
    ).grid(row=0, column=1, sticky="e", padx=(12, 0))
    tk.Label(
        run_summary, textvariable=state_var, bg=PALETTE["white"], fg=PALETTE["ink"],
        font=(FONT, 22, "bold"), anchor="w",
    ).grid(row=1, column=0, sticky="w")
    tk.Label(
        run_summary, textvariable=elapsed_var, bg=PALETTE["white"], fg=PALETTE["ink"],
        font=(DATA_FONT, 15, "bold"), anchor="e",
    ).grid(row=1, column=1, sticky="e", padx=(12, 0))

    stats_row = tk.Frame(operate, bg=PALETTE["white"])
    stats_row.grid(row=3, column=0, sticky="ew", pady=(0, 12))
    for col in range(3):
        stats_row.grid_columnconfigure(col, weight=1)
    for col, (label_var, value_var) in enumerate((
        (stat1_label, stat1_value), (stat2_label, stat2_value), (stat3_label, stat3_value),
    )):
        cell = tk.Frame(stats_row, bg="#f6f8f5", padx=9, pady=8)
        cell.grid(row=0, column=col, sticky="ew", padx=(0, 6) if col < 2 else (0, 0))
        tk.Label(cell, textvariable=label_var, bg="#f6f8f5", fg=PALETTE["muted"],
                 font=(FONT, 8), anchor="w").pack(anchor="w")
        tk.Label(cell, textvariable=value_var, bg="#f6f8f5", fg=PALETTE["ink"],
                 font=(FONT, 11, "bold"), anchor="w").pack(anchor="w", pady=(3, 0))

    trace_head = tk.Frame(operate, bg=PALETTE["white"])
    trace_head.grid(row=4, column=0, sticky="ew", pady=(0, 5))
    tk.Label(trace_head, text="Recent phase changes", bg=PALETTE["white"],
             fg=PALETTE["muted"], font=(FONT, 8), anchor="w").pack(side="left")
    tk.Label(trace_head, textvariable=history_note, bg=PALETTE["white"],
             fg=PALETTE["muted"], font=(FONT, 8), anchor="e").pack(side="right")
    trace_canvas = tk.Canvas(
        operate, height=42, bg="#eef2ef", highlightthickness=1,
        highlightbackground="#dce3de", bd=0,
    )
    trace_canvas.grid(row=5, column=0, sticky="ew")

    controls = tk.Frame(operate, bg=PALETTE["white"])
    controls.grid(row=6, column=0, sticky="ew", pady=(13, 0))

    def action_button(parent: Any, text: str, kind: str = "secondary", command: Any = None) -> Any:
        if kind == "primary":
            bg, fg, hover = PALETTE["navy"], "#ffffff", PALETTE["navy_hover"]
        elif kind == "stop":
            bg, fg, hover = PALETTE["white"], PALETTE["red"], PALETTE["red_bg"]
        else:
            bg, fg, hover = PALETTE["white"], PALETTE["navy"], "#e6edf0"
        button = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground=hover, activeforeground=fg, disabledforeground="#9aa4a0",
            relief="flat", bd=0, padx=13, pady=8, font=(FONT, 9, "bold"),
            takefocus=True, cursor="hand2", highlightthickness=1,
            highlightbackground=PALETTE["line"], highlightcolor=PALETTE["blue"],
        )

        def on_enter(_event: Any) -> None:
            if str(button["state"]) != "disabled":
                button.configure(bg=hover)

        def on_leave(_event: Any) -> None:
            if str(button["state"]) != "disabled":
                button.configure(bg=bg)

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        button.pack(side="left", padx=(0, 7))
        return button

    def do_start() -> None:
        model.mode = mode_var.get()
        model.sim = bool(sim_var.get())
        model.dry = bool(dry_var.get())
        raw_hours = hours_var.get().strip()
        if raw_hours:
            try:
                value = float(raw_hours)
                if value < 0:
                    raise ValueError
                model.max_hours = value or None
            except ValueError:
                messagebox.showerror(
                    "Invalid limit", "Maximum session must be a positive number of hours.", parent=root,
                )
                hours_entry.focus_set()
                return
        else:
            model.max_hours = None
        model.filament = filament_var.get().strip() or "Tranquil Exotic Filament"
        model.engine = engine_var.get() or "fsm"
        model.max_missions = _int_or_none(mission_limit_var.get())
        model.max_runs = _int_or_none(run_limit_var.get())
        if not model.sim and not model.dry:
            confirmed = messagebox.askyesno(
                "Confirm live input",
                f"Mode: {MODE_LABELS[model.mode]}\n\n"
                "SIM and DRY are both off. fila-bot can send real clicks and keys to EVE.\n\n"
                "Continue?",
                parent=root,
            )
            if not confirmed:
                return
        model.start()

    start_button = action_button(controls, "Start", "primary", do_start)
    pause_button = action_button(controls, "Pause", "secondary", model.pause)
    stop_button = action_button(controls, "Stop", "secondary", model.stop)
    estop_button = action_button(controls, "E-STOP", "stop", model.estop)
    tk.Label(
        operate, text="E-STOP is available while a session is active.",
        bg=PALETTE["white"], fg=PALETTE["muted"], font=(FONT, 8), anchor="w",
    ).grid(row=7, column=0, sticky="w", pady=(8, 0))

    # Append-only event history, with a scroll bar and a useful empty state.
    log_outer = tk.Frame(root, bg=PALETTE["line"], padx=1, pady=1)
    log_outer.grid(row=5, column=0, sticky="nsew", padx=28, pady=(0, 8))
    log_outer.grid_columnconfigure(0, weight=1)
    log_outer.grid_rowconfigure(1, weight=1)
    log_inside = tk.Frame(log_outer, bg=PALETTE["white"], padx=14, pady=8)
    log_inside.grid(row=0, column=0, sticky="nsew")
    log_inside.grid_columnconfigure(0, weight=1)
    log_header = tk.Frame(log_inside, bg=PALETTE["white"])
    log_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    log_header.grid_columnconfigure(0, weight=1)
    tk.Label(log_header, text="Event log", bg=PALETTE["white"], fg=PALETTE["ink"],
             font=(FONT, 10, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
    tk.Label(log_header, textvariable=log_summary, bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="e").grid(row=0, column=1, sticky="e")
    log_text = tk.Text(
        log_outer, height=5, wrap="none", relief="flat", bd=0,
        bg="#fbfcfa", fg=PALETTE["ink"], insertbackground=PALETTE["blue"],
        selectbackground="#d8e5e1", selectforeground=PALETTE["ink"],
        font=(DATA_FONT, 9), padx=14, pady=10, takefocus=True,
        highlightthickness=0, state="disabled",
    )
    log_text.grid(row=1, column=0, sticky="nsew")
    log_scroll = ttk.Scrollbar(log_outer, orient="vertical", command=log_text.yview,
                               style="Fila.Vertical.TScrollbar")
    log_scroll.grid(row=1, column=1, sticky="ns")
    log_text.configure(yscrollcommand=log_scroll.set)
    log_text.tag_configure("time", foreground="#68767b")
    log_text.tag_configure("live", foreground=PALETTE["blue"])
    log_text.tag_configure("danger", foreground=PALETTE["red"])
    log_text.tag_configure("success", foreground=PALETTE["green"])
    log_text.tag_configure("empty", foreground=PALETTE["muted"], font=(FONT, 9))
    log_text.configure(state="normal")
    log_text.insert("end", "No events yet. Start a SIM or DRY session to see phases and actions.", "empty")
    log_text.configure(state="disabled")

    footer = tk.Frame(root, bg=PALETTE["paper"])
    footer.grid(row=6, column=0, sticky="ew", padx=28, pady=(0, 8))
    footer_hint = tk.Label(
        footer, text="Kill switch: Ctrl+Shift+Space", bg=PALETTE["paper"],
        fg=PALETTE["muted"], font=(FONT, 8), anchor="w",
    )
    footer_hint.pack(side="left")
    tk.Label(
        footer, text="State and history reflect UiModel", bg=PALETTE["paper"],
        fg=PALETTE["muted"], font=(FONT, 8), anchor="e",
    ).pack(side="right")

    shown_last: list[str] = [""]
    log_has_placeholder = [True]

    def insert_log_line(line: str) -> None:
        tag = "live" if "[LIVE]" in line else "time"
        upper = line.upper()
        if any(term in upper for term in ("BLOCKED", "CRASH", "ERROR", "ESTOP", "FATAL")):
            tag = "danger"
        elif any(term in upper for term in ("COMPLETE", "SUCCESS", "[OK]")):
            tag = "success"
        log_text.insert("end", line + "\n", tag)

    def apply_log(lines: list[str]) -> None:
        if not lines:
            return
        if log_has_placeholder[0]:
            log_text.configure(state="normal")
            log_text.delete("1.0", "end")
            log_has_placeholder[0] = False
            start = max(0, len(lines) - 140)
        elif shown_last[0] not in lines:
            log_text.configure(state="normal")
            log_text.delete("1.0", "end")
            start = max(0, len(lines) - 140)
        else:
            start = lines.index(shown_last[0]) + 1
            log_text.configure(state="normal")
        new_lines = lines[start:]
        for line in new_lines:
            insert_log_line(line)
        if new_lines:
            shown_last[0] = new_lines[-1]
            log_text.see("end")
        log_text.configure(state="disabled")
        log_summary.set(f"{len(lines)} recent events")

    def draw_phase_trace(lines: list[str]) -> None:
        trace_canvas.delete("all")
        width = max(trace_canvas.winfo_width(), 420)
        height = max(trace_canvas.winfo_height(), 42)
        left, right, y = 24, width - 24, 15
        trace_canvas.create_line(left, y, right, y, fill="#b8c7c0", width=2)
        events: list[str] = []
        for line in lines:
            if "Phase:" not in line or "→" not in line:
                continue
            phase = line.rsplit("→", 1)[-1].strip()
            if phase and (not events or events[-1] != phase):
                events.append(phase)
        events = events[-4:]
        if not events:
            trace_canvas.create_oval(left - 4, y - 4, left + 4, y + 4,
                                     fill=PALETTE["gold"], outline="")
            trace_canvas.create_text(
                (left + right) // 2, y + 13,
                text="Phase history appears after the first state change",
                fill=PALETTE["muted"], font=(FONT, 8), anchor="center",
            )
            history_note.set("Waiting for first phase event")
            return
        span = max(right - left, 1)
        count = len(events)
        for index, phase in enumerate(events):
            x = left if count == 1 else left + (span * index / (count - 1))
            is_last = index == count - 1
            color = PALETTE["blue"]
            if any(term in phase.upper() for term in ("BLOCK", "ERROR", "ESTOP", "CRASH")):
                color = PALETTE["red"]
            elif any(term in phase.upper() for term in ("DONE", "COMPLETE", "DOCKED")):
                color = PALETTE["green"]
            radius = 5 if is_last else 3
            trace_canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                                     fill=color, outline=PALETTE["white"] if is_last else color,
                                     width=1)
            trace_canvas.create_text(
                x, y + 15, text=phase[:15], fill=PALETTE["ink"] if is_last else PALETTE["muted"],
                font=(FONT, 7, "bold" if is_last else "normal"), anchor="n",
            )
        history_note.set(f"{count} recent changes")

    mode_var.trace_add("write", update_mode_tabs)
    sim_var.trace_add("write", update_safety)
    dry_var.trace_add("write", update_safety)
    update_mode_tabs()
    update_safety()

    def refresh_ui() -> None:
        try:
            model.poll()
            view = model.view()
        except tk.TclError:
            return
        state = str(view.get("state") or "IDLE")
        phase = str(view.get("phase") or "—")
        state_var.set(state.upper())
        phase_var.set(phase)
        elapsed_var.set(str(view.get("elapsed") or "0:00:00"))
        banner = str(view.get("banner") or "").strip()
        detail = str(view.get("detail") or "").strip()
        if banner:
            status_copy.set(banner)
        elif state == "IDLE":
            status_copy.set("No active run")
        elif detail:
            status_copy.set(detail)
        else:
            status_copy.set("Session active")

        if state in ("BLOCKED", "CRASHED", "ERROR") or view.get("danger"):
            state_badge.configure(bg=PALETTE["red_bg"], fg=PALETTE["red"])
        elif state == "PAUSED":
            state_badge.configure(bg=PALETTE["amber_bg"], fg=PALETTE["amber"])
        elif state == "RUNNING":
            state_badge.configure(bg=PALETTE["green_bg"], fg=PALETTE["green"])
        else:
            state_badge.configure(bg="#e1e7e3", fg=PALETTE["green"])

        stats = view.get("stats") or {}
        sessions = stats.get("sessions", 0)
        completed = stats.get("completed", 0)
        crashes = stats.get("crashes", 0)
        last_reason = stats.get("last_reason")
        stats_summary.set(
            f"{sessions} sessions · {completed} completed · {crashes} crashes"
            + (f" · Last: {last_reason}" if last_reason else "")
        )
        if mode_var.get() == "abyss":
            stat1_label.set("Runs")
            stat1_value.set(str(view.get("runs", 0)))
            stat2_label.set("Room")
            stat2_value.set(str(view.get("room", 0)))
            stat3_label.set("Filaments")
            stat3_value.set(str(view.get("filaments", "—")))
        else:
            stat1_label.set("Missions")
            stat1_value.set(str(view.get("runs", 0)))
            stat2_label.set("Declined")
            stat2_value.set(str(view.get("declined", 0)))
            stat3_label.set("Time")
            stat3_value.set(str(view.get("elapsed", "0:00:00")))

        start_button.configure(state="normal" if view.get("can_start") else "disabled")
        pause_button.configure(text=str(view.get("pause_label") or "Pause"))
        pause_button.configure(state="normal" if view.get("can_pause") else "disabled")
        stop_button.configure(state="normal" if view.get("can_stop") else "disabled")
        estop_button.configure(state="normal" if view.get("can_estop") else "disabled")
        apply_log(view.get("log") or [])
        draw_phase_trace(view.get("log") or [])
        root.after(300, refresh_ui)

    def on_close() -> None:
        model.close()
        try:
            root.destroy()
        except tk.TclError:
            pass

    root.protocol("WM_DELETE_WINDOW", on_close)
    refresh_ui()
    if auto_close_ms:
        root.after(auto_close_ms, on_close)

    return {
        "mode_var": mode_var,
        "mode_buttons": mode_buttons,
        "sim_var": sim_var,
        "dry_var": dry_var,
        "safety_summary": safety_summary,
        "safety_detail": safety_detail,
        "live_warning": live_warning,
        "estop_button": estop_button,
        "filament_entry": filament_entry,
        "max_runs_entry": max_runs_entry,
        "engine_combo": engine_combo,
        "max_missions_entry": max_missions_entry,
        "mode_summary": mode_summary,
        "operate_panel": operate,
        "heading_title": heading_title,
        "footer_hint": footer_hint,
        "sim_button": sim_button,
        "refresh": refresh_ui,
    }


def run_window(auto_close_ms: int = 0) -> int:
    import tkinter as tk

    model = UiModel()
    root = tk.Tk()
    build_window(root, model, auto_close_ms=auto_close_ms)
    root.mainloop()
    return 0
