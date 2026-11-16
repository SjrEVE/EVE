"""Abyssal operator console UI for fila-bot (tkinter, stdlib).

Public GUI surface is Abyssal-only and SIM-only. UiModel remains the
source of truth; this module is presentation and dispatch only.

    python -m fila_bot.ui        -> mo cua so nay
"""
from __future__ import annotations

from typing import Any

from .ui_model import UiModel

PALETTE = {
    "navy": "#173044",
    "navy_hover": "#24485d",
    "ink": "#1f2b31",
    "muted": "#65757a",
    "paper": "#f1f3ef",
    "white": "#ffffff",
    "line": "#d3dad5",
    "blue": "#225c7a",
    "green": "#3f675d",
    "green_bg": "#e4eee8",
    "red": "#a93f39",
    "red_bg": "#fae8e5",
    "amber": "#7f5c24",
    "amber_bg": "#f6eddc",
    "disabled": "#e7ebe7",
    "panel_alt": "#fbfcfa",
    "chip_on": "#355d54",
    "chip_off": "#294352",
}
FONT = "Segoe UI"
DATA_FONT = "Consolas"


def _int_or_none(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value.lstrip("-").isdigit() else None


def build_window(root: Any, model: UiModel, auto_close_ms: int = 0) -> dict[str, Any]:
    """Build the Abyssal operator UI on ``root`` and return testable controls."""
    import tkinter as tk
    from tkinter import messagebox, ttk

    from fila_bot.version import short

    # Public GUI surface: Abyssal-only. Preserve chosen engine.
    model.mode = "abyss"

    root.title(f"fila-bot {short()} — Abyssal Control")
    root.geometry("870x600")
    root.minsize(870, 600)
    root.configure(background=PALETTE["paper"])

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Fila.TEntry", padding=(6, 4), fieldbackground=PALETTE["panel_alt"],
        foreground=PALETTE["ink"], bordercolor=PALETTE["line"],
    )
    style.map(
        "Fila.TEntry",
        fieldbackground=[("disabled", PALETTE["disabled"]), ("!disabled", PALETTE["panel_alt"])],
        foreground=[("disabled", PALETTE["muted"]), ("!disabled", PALETTE["ink"])],
    )
    style.configure(
        "Fila.TCombobox", padding=(6, 4), fieldbackground=PALETTE["panel_alt"],
        background=PALETTE["panel_alt"], foreground=PALETTE["ink"], arrowcolor=PALETTE["navy"],
    )
    style.map(
        "Fila.TCombobox",
        fieldbackground=[("disabled", PALETTE["disabled"]), ("readonly", PALETTE["panel_alt"])],
        foreground=[("disabled", PALETTE["muted"]), ("readonly", PALETTE["ink"])],
    )
    style.configure(
        "Fila.Vertical.TScrollbar", background="#d6ded8", troughcolor=PALETTE["paper"],
        bordercolor=PALETTE["paper"], arrowcolor=PALETTE["muted"],
    )

    # Rows: 0 header, 1 status strip (removable), 2 main, 3 log, 4 footer
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(2, weight=1)
    root.grid_rowconfigure(3, weight=1)

    # ---- state vars ----
    sim_var = tk.BooleanVar(value=True)
    dry_var = tk.BooleanVar(value=True)
    hours_var = tk.StringVar(value="4")
    filament_var = tk.StringVar(value=model.filament)
    engine_var = tk.StringVar(value=model.engine if model.engine in ("fsm", "bt") else "fsm")
    run_limit_var = tk.StringVar(value="")

    safety_summary = tk.StringVar(value="SIM: no EVE connection · DRY: read-only")
    safety_detail = tk.StringVar(value="Safe default: simulation only, no game input will be sent.")
    state_var = tk.StringVar(value="IDLE")
    status_copy = tk.StringVar(value="Ready. Configure Abyss run and press Start.")
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

    # ---- header ----
    header = tk.Frame(root, bg=PALETTE["navy"], height=50)
    header.grid(row=0, column=0, sticky="ew")
    header.grid_propagate(False)
    header.grid_columnconfigure(1, weight=1)

    brand = tk.Frame(header, bg=PALETTE["navy"])
    brand.grid(row=0, column=0, sticky="nsw", padx=(14, 10))
    tk.Label(brand, text="FILA / BOT", bg=PALETTE["navy"], fg="#f5f7f2",
             font=(FONT, 11, "bold")).pack(anchor="w", pady=(8, 0))
    tk.Label(brand, text="Abyssal operator console", bg=PALETTE["navy"], fg="#b9c8ce",
             font=(FONT, 8)).pack(anchor="w")

    safety_controls = tk.Frame(header, bg=PALETTE["navy"])
    safety_controls.grid(row=0, column=1, sticky="e", padx=(8, 14))
    sim_label = tk.StringVar(value="SIM  ON")
    dry_label = tk.StringVar(value="DRY  ON")

    def style_safety_button(button: Any, active: bool) -> None:
        chip = PALETTE["chip_on"] if active else PALETTE["chip_off"]
        button.configure(
            bg=chip, selectcolor=chip,
            fg="#f2f7f3" if active else "#becbd0",
            activebackground="#477366" if active else PALETTE["navy_hover"],
            highlightbackground="#59717e",
        )

    def update_safety(*_args: Any) -> None:
        sim = bool(sim_var.get())
        dry = bool(dry_var.get())
        sim_label.set(f"SIM  {'ON' if sim else 'OFF'}")
        dry_label.set(f"DRY  {'ON' if dry else 'OFF'}")
        style_safety_button(sim_button, sim)
        style_safety_button(dry_button, dry)

        if sim and dry:
            safety_summary.set("SIM: no EVE connection · DRY: read-only")
            safety_detail.set("Safe default: simulation only, no game input will be sent.")
            safety_bar.configure(bg=PALETTE["green"])
        elif sim:
            safety_summary.set("SIM: no EVE connection · DRY off")
            safety_detail.set("Simulation still prevents real EVE input.")
            safety_bar.configure(bg=PALETTE["green"])
        elif dry:
            safety_summary.set("DRY requested · GUI client access blocked")
            safety_detail.set("This GUI runs SIM only. Use fila_bot.cli for client read-only runs.")
            safety_bar.configure(bg=PALETTE["blue"])
        else:
            # LIVE INPUT requested: block live GUI path and hide status strip row.
            safety_summary.set("LIVE INPUT requested · GUI live path blocked")
            safety_detail.set("This GUI cannot access EVE. Use fila_bot.cli with its client ownership lock for live access.")
            safety_bar.configure(bg=PALETTE["red"])

        # Row-1 visibility contract: no grid-managed widget on root row 1 in LIVE INPUT blocked state.
        if (not sim) and (not dry):
            status_strip.grid_remove()
        else:
            if not root.grid_slaves(row=1):
                status_strip.grid(row=1, column=0, sticky="ew", padx=14, pady=(8, 4))

        # Keep idle status text in sync with current safety mode for clarity.
        if state_var.get() == "IDLE" and model.state == "IDLE":
            refresh_status_copy_for_idle()

    sim_button = tk.Checkbutton(
        safety_controls, textvariable=sim_label, variable=sim_var,
        command=update_safety, indicatoron=False, relief="flat", bd=0,
        padx=10, pady=6, font=(FONT, 8, "bold"), takefocus=True,
        highlightthickness=1, highlightbackground="#59717e", highlightcolor=PALETTE["blue"],
    )
    dry_button = tk.Checkbutton(
        safety_controls, textvariable=dry_label, variable=dry_var,
        command=update_safety, indicatoron=False, relief="flat", bd=0,
        padx=10, pady=6, font=(FONT, 8, "bold"), takefocus=True,
        highlightthickness=1, highlightbackground="#59717e", highlightcolor=PALETTE["blue"],
    )
    sim_button.pack(side="left", padx=(0, 8), pady=10)
    dry_button.pack(side="left", pady=10)

    # ---- status strip ----
    status_strip = tk.Frame(root, bg=PALETTE["paper"])
    status_strip.grid(row=1, column=0, sticky="ew", padx=14, pady=(8, 4))
    status_strip.grid_columnconfigure(1, weight=1)

    state_badge = tk.Label(
        status_strip, textvariable=state_var, bg="#e1e7e3", fg=PALETTE["green"],
        font=(FONT, 10, "bold"), padx=10, pady=5,
    )
    state_badge.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 10))

    status_label = tk.Label(
        status_strip, textvariable=status_copy, bg=PALETTE["paper"], fg=PALETTE["ink"],
        font=(FONT, 10), anchor="w", justify="left", wraplength=520,
    )
    status_label.grid(row=0, column=1, sticky="ew")

    meta_row = tk.Frame(status_strip, bg=PALETTE["paper"])
    meta_row.grid(row=1, column=1, sticky="w", pady=(1, 0))
    tk.Label(meta_row, text="Phase", bg=PALETTE["paper"], fg=PALETTE["muted"],
             font=(FONT, 8)).pack(side="left")
    phase_value_label = tk.Label(meta_row, textvariable=phase_var, bg=PALETTE["paper"],
                                 fg=PALETTE["ink"], font=(DATA_FONT, 9, "bold"))
    phase_value_label.pack(side="left", padx=(6, 14))
    tk.Label(meta_row, text="Elapsed", bg=PALETTE["paper"], fg=PALETTE["muted"],
             font=(FONT, 8)).pack(side="left")
    tk.Label(meta_row, textvariable=elapsed_var, bg=PALETTE["paper"], fg=PALETTE["ink"],
             font=(DATA_FONT, 9, "bold")).pack(side="left", padx=(6, 0))

    # ---- main panels ----
    work = tk.Frame(root, bg=PALETTE["paper"])
    work.grid(row=2, column=0, sticky="nsew", padx=14, pady=(2, 6))
    work.grid_columnconfigure(0, weight=3, minsize=390)
    work.grid_columnconfigure(1, weight=2, minsize=330)
    work.grid_rowconfigure(0, weight=1)

    def panel(parent: Any, column: int, title: str, subtitle_var: Any | None = None) -> Any:
        outer = tk.Frame(parent, bg=PALETTE["line"], padx=1, pady=1)
        outer.grid(row=0, column=column, sticky="nsew", padx=(0, 5) if column == 0 else (5, 0))
        inner = tk.Frame(outer, bg=PALETTE["white"], padx=12, pady=10)
        inner.pack(fill="both", expand=True)
        inner.grid_columnconfigure(0, weight=1)
        head = tk.Frame(inner, bg=PALETTE["white"])
        head.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        head.grid_columnconfigure(0, weight=1)
        tk.Label(head, text=title, bg=PALETTE["white"], fg=PALETTE["ink"],
                 font=(FONT, 10, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
        if subtitle_var is not None:
            tk.Label(head, textvariable=subtitle_var, bg=PALETTE["white"], fg=PALETTE["muted"],
                     font=(FONT, 8), anchor="e").grid(row=0, column=1, sticky="e")
        tk.Frame(inner, bg=PALETTE["line"], height=1).grid(row=1, column=0, sticky="ew", pady=(0, 8))
        return inner

    settings = panel(work, 0, "Run setup")
    operate = panel(work, 1, "Operate", stats_summary)

    # ---- setup panel ----
    settings.grid_columnconfigure(0, weight=1)
    settings.grid_columnconfigure(1, weight=1)

    heading_title = tk.Label(
        settings, text="Abyssal Deadspace", bg=PALETTE["white"],
        fg=PALETTE["ink"], font=(FONT, 13, "bold"), anchor="w",
    )
    heading_title.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 6))

    tk.Label(
        settings,
        text="Simple safe run: keep SIM on, choose limits if needed, then press Start.",
        bg=PALETTE["white"], fg=PALETTE["muted"], font=(FONT, 8),
        anchor="w", justify="left", wraplength=360,
    ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))

    tk.Label(settings, text="Filament", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="w").grid(row=4, column=0, sticky="w")
    tk.Label(settings, text="Engine", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="w").grid(row=4, column=1, sticky="w")

    filament_entry = ttk.Entry(settings, textvariable=filament_var, style="Fila.TEntry")
    filament_entry.grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(2, 8))
    engine_combo = ttk.Combobox(
        settings, textvariable=engine_var, values=("fsm", "bt"),
        state="readonly", style="Fila.TCombobox",
    )
    engine_combo.grid(row=5, column=1, sticky="ew", pady=(2, 8))

    tk.Label(settings, text="Max Abyss runs (optional)", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="w").grid(row=6, column=0, sticky="w")
    tk.Label(settings, text="Max session hours", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="w").grid(row=6, column=1, sticky="w")

    max_runs_entry = ttk.Entry(settings, textvariable=run_limit_var, style="Fila.TEntry")
    max_runs_entry.grid(row=7, column=0, sticky="ew", padx=(0, 8), pady=(2, 2))
    hours_entry = ttk.Entry(settings, textvariable=hours_var, style="Fila.TEntry")
    hours_entry.grid(row=7, column=1, sticky="ew", pady=(2, 2))

    tk.Label(settings, text="Blank = no cap", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="w").grid(row=8, column=0, sticky="w")
    tk.Label(settings, text="Blank = no time limit", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="w").grid(row=8, column=1, sticky="w")

    tk.Frame(settings, bg=PALETTE["line"], height=1).grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 8))
    tk.Label(settings, text="Safety status", bg=PALETTE["white"], fg=PALETTE["ink"],
             font=(FONT, 9, "bold"), anchor="w").grid(row=10, column=0, columnspan=2, sticky="w")

    safety_detail_label = tk.Label(
        settings, textvariable=safety_detail, bg=PALETTE["white"],
        fg=PALETTE["muted"], font=(FONT, 9), anchor="w",
        justify="left", wraplength=360,
    )
    safety_detail_label.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(3, 0))
    safety_bar = tk.Frame(settings, bg=PALETTE["green"], height=4)
    safety_bar.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    # ---- operate panel ----
    operate.grid_columnconfigure(0, weight=1)

    run_summary = tk.Frame(operate, bg=PALETTE["white"])
    run_summary.grid(row=2, column=0, sticky="ew", pady=(0, 8))
    run_summary.grid_columnconfigure(0, weight=1)
    run_summary.grid_columnconfigure(1, weight=1)

    tk.Label(run_summary, text="State", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8)).grid(row=0, column=0, sticky="w")
    tk.Label(run_summary, textvariable=state_var, bg=PALETTE["white"], fg=PALETTE["ink"],
             font=(FONT, 16, "bold"), anchor="w").grid(row=1, column=0, sticky="w")
    tk.Label(run_summary, text="Safety", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8)).grid(row=0, column=1, sticky="w")
    tk.Label(run_summary, textvariable=safety_summary, bg=PALETTE["white"], fg=PALETTE["ink"],
             font=(FONT, 8), anchor="w", justify="left", wraplength=220).grid(row=1, column=1, sticky="nw")

    stats_row = tk.Frame(operate, bg=PALETTE["white"])
    stats_row.grid(row=3, column=0, sticky="ew", pady=(0, 6))
    for col in range(3):
        stats_row.grid_columnconfigure(col, weight=1)

    for col, (lv, vv) in enumerate(((stat1_label, stat1_value), (stat2_label, stat2_value), (stat3_label, stat3_value))):
        cell = tk.Frame(stats_row, bg=PALETTE["panel_alt"], padx=6, pady=6,
                        highlightbackground=PALETTE["line"], highlightthickness=1)
        cell.grid(row=0, column=col, sticky="ew", padx=(0, 4) if col < 2 else 0)
        tk.Label(cell, textvariable=lv, bg=PALETTE["panel_alt"], fg=PALETTE["muted"],
                 font=(FONT, 8), anchor="w").pack(anchor="w")
        tk.Label(cell, textvariable=vv, bg=PALETTE["panel_alt"], fg=PALETTE["ink"],
                 font=(FONT, 11, "bold"), anchor="w").pack(anchor="w")

    trace_head = tk.Frame(operate, bg=PALETTE["white"])
    trace_head.grid(row=4, column=0, sticky="ew")
    tk.Label(trace_head, text="Recent phases", bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="w").pack(side="left")
    tk.Label(trace_head, textvariable=history_note, bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="e").pack(side="right")

    trace_canvas = tk.Canvas(operate, height=40, bg="#eef2ef", highlightthickness=1,
                             highlightbackground="#dce3de", bd=0)
    trace_canvas.grid(row=5, column=0, sticky="ew", pady=(2, 8))

    controls = tk.Frame(operate, bg=PALETTE["white"])
    controls.grid(row=6, column=0, sticky="ew")
    controls.grid_columnconfigure(0, weight=1)

    def action_button(parent: Any, text: str, kind: str = "secondary", command: Any = None) -> Any:
        if kind == "primary":
            bg, fg, hover = PALETTE["navy"], "#ffffff", PALETTE["navy_hover"]
        elif kind == "danger":
            bg, fg, hover = PALETTE["red"], "#ffffff", "#8f332e"
        else:
            bg, fg, hover = PALETTE["white"], PALETTE["navy"], "#e6edf0"
        button = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground=hover, activeforeground=fg, disabledforeground="#9aa4a0",
            relief="flat", bd=0, padx=10, pady=7, font=(FONT, 9, "bold"),
            takefocus=True, cursor="hand2", highlightthickness=1,
            highlightbackground=PALETTE["line"] if kind != "danger" else PALETTE["red"],
            highlightcolor=PALETTE["blue"],
        )

        def on_enter(_e: Any) -> None:
            if str(button["state"]) != "disabled":
                button.configure(bg=hover)

        def on_leave(_e: Any) -> None:
            if str(button["state"]) != "disabled":
                button.configure(bg=bg)

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        return button

    def refresh_status_copy_for_idle() -> None:
        """Keep idle status message aligned with current safety toggles."""
        sim = bool(sim_var.get())
        dry = bool(dry_var.get())
        if not sim and not dry:
            status_copy.set("LIVE INPUT requested · GUI live path blocked")
        elif not sim and dry:
            status_copy.set("DRY requested · GUI client access blocked")
        else:
            # SIM on (dry on/off) is a valid safe GUI state.
            status_copy.set("Ready. Configure Abyss run and press Start.")

    def do_start() -> None:
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
                    "Invalid limit",
                    "Maximum session must be a positive number of hours.",
                    parent=root,
                )
                hours_entry.focus_set()
                return
        else:
            model.max_hours = None

        model.filament = filament_var.get().strip() or "Tranquil Exotic Filament"
        model.engine = engine_var.get() or "fsm"
        model.max_runs = _int_or_none(run_limit_var.get())
        model.max_missions = None

        if not model.sim:
            messagebox.showwarning(
                "Client mode unavailable in GUI",
                "This GUI runs in SIM only and will not read or control EVE.\n\n"
                "For client access use: python -m fila_bot.cli (enforces ownership lock).\n"
                "Keep SIM on for safe simulation here.",
                parent=root,
            )
            # Reflect the specific blocked safety state (do not collapse DRY-requested into LIVE).
            refresh_status_copy_for_idle()
            return

        model.start()

    main_actions = tk.Frame(controls, bg=PALETTE["white"])
    main_actions.pack(fill="x", pady=(0, 4))

    start_button = action_button(main_actions, "Start", "primary", do_start)
    pause_button = action_button(main_actions, "Pause", "secondary", model.pause)
    stop_button = action_button(main_actions, "Stop", "secondary", model.stop)
    start_button.pack(side="left", padx=(0, 6))
    pause_button.pack(side="left", padx=(0, 6))
    stop_button.pack(side="left")

    danger_row = tk.Frame(controls, bg=PALETTE["white"])
    danger_row.pack(fill="x", pady=(2, 0))
    estop_button = action_button(danger_row, "E-STOP", "danger", model.estop)
    estop_button.pack(side="left")
    estop_hint = tk.Label(
        danger_row,
        text="Emergency stop. Immediate halt of bot actions in this session.",
        bg=PALETTE["white"], fg=PALETTE["muted"], font=(FONT, 8),
        anchor="w", justify="left", wraplength=260,
    )
    estop_hint.pack(side="left", padx=(8, 0))

    # ---- activity log ----
    log_outer = tk.Frame(root, bg=PALETTE["line"], padx=1, pady=1)
    log_outer.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 4))
    log_outer.grid_columnconfigure(0, weight=1)
    log_outer.grid_rowconfigure(1, weight=1)

    log_head = tk.Frame(log_outer, bg=PALETTE["white"], padx=10, pady=6)
    log_head.grid(row=0, column=0, sticky="ew")
    log_head.grid_columnconfigure(0, weight=1)
    tk.Label(log_head, text="Activity log", bg=PALETTE["white"], fg=PALETTE["ink"],
             font=(FONT, 10, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
    tk.Label(log_head, textvariable=log_summary, bg=PALETTE["white"], fg=PALETTE["muted"],
             font=(FONT, 8), anchor="e").grid(row=0, column=1, sticky="e")

    log_text = tk.Text(
        log_outer, height=6, wrap="word", relief="flat", bd=0,
        bg=PALETTE["panel_alt"], fg=PALETTE["ink"], insertbackground=PALETTE["blue"],
        selectbackground="#d8e5e1", selectforeground=PALETTE["ink"],
        font=(DATA_FONT, 9), padx=8, pady=6, takefocus=True,
        highlightthickness=0, state="disabled",
    )
    log_text.grid(row=1, column=0, sticky="nsew")
    log_scroll = ttk.Scrollbar(
        log_outer, orient="vertical", command=log_text.yview,
        style="Fila.Vertical.TScrollbar",
    )
    log_scroll.grid(row=1, column=1, sticky="ns")
    log_text.configure(yscrollcommand=log_scroll.set)
    log_text.tag_configure("time", foreground="#68767b")
    log_text.tag_configure("live", foreground=PALETTE["blue"])
    log_text.tag_configure("danger", foreground=PALETTE["red"])
    log_text.tag_configure("success", foreground=PALETTE["green"])
    log_text.tag_configure("empty", foreground=PALETTE["muted"], font=(FONT, 9))
    log_text.configure(state="normal")
    log_text.insert("end", "No events yet. Keep SIM on for safety, then press Start.", "empty")
    log_text.configure(state="disabled")

    # ---- footer ----
    footer = tk.Frame(root, bg=PALETTE["paper"])
    footer.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 6))
    footer_hint = tk.Label(
        footer, text="Kill switch: Ctrl+Shift+Space",
        bg=PALETTE["paper"], fg=PALETTE["muted"], font=(FONT, 8), anchor="w",
    )
    footer_hint.pack(side="left")

    # ---- dynamic behavior ----
    configuration_enabled: list[bool | None] = [None]
    shown_last: list[str] = [""]
    log_has_placeholder = [True]

    def set_configuration_enabled(enabled: bool) -> None:
        if configuration_enabled[0] == enabled:
            return
        configuration_enabled[0] = enabled
        state = "normal" if enabled else "disabled"
        sim_button.configure(state=state)
        dry_button.configure(state=state)
        for entry in (hours_entry, filament_entry, max_runs_entry):
            try:
                entry.state(["!disabled"] if enabled else ["disabled"])
            except Exception:
                entry.configure(state=state)
        engine_combo.configure(state="readonly" if enabled else "disabled")

    def insert_log_line(line: str) -> None:
        tag = "live" if "[LIVE]" in line else "time"
        upper = line.upper()
        if any(term in upper for term in ("BLOCKED", "CRASH", "ERROR", "ESTOP", "FATAL")):
            tag = "danger"
        elif any(term in upper for term in ("COMPLETE", "SUCCESS", "[OK]", "DONE")):
            tag = "success"
        log_text.insert("end", line + "\n", tag)

    def apply_log(lines: list[str]) -> None:
        if not lines:
            log_summary.set("No events yet")
            return
        if log_has_placeholder[0]:
            log_text.configure(state="normal")
            log_text.delete("1.0", "end")
            log_has_placeholder[0] = False
            start = max(0, len(lines) - 180)
        elif shown_last[0] not in lines:
            log_text.configure(state="normal")
            log_text.delete("1.0", "end")
            start = max(0, len(lines) - 180)
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
        log_summary.set(f"{len(lines)} events")

    def draw_phase_trace(lines: list[str]) -> None:
        trace_canvas.delete("all")
        width = max(trace_canvas.winfo_width(), 320)
        height = max(trace_canvas.winfo_height(), 40)
        left, right, y = 18, width - 18, 12
        trace_canvas.create_line(left, y, right, y, fill="#b8c7c0", width=2)

        events: list[str] = []
        for line in lines:
            if "Phase:" not in line or "→" not in line:
                continue
            phase = line.rsplit("→", 1)[-1].strip()
            if phase and (not events or events[-1] != phase):
                events.append(phase)
        events = events[-5:]

        if not events:
            trace_canvas.create_oval(left - 4, y - 4, left + 4, y + 4, fill="#d5a64a", outline="")
            trace_canvas.create_text(
                (left + right) // 2, y + 14,
                text="Phase history appears after first state change",
                fill=PALETTE["muted"], font=(FONT, 8), anchor="center",
            )
            history_note.set("Waiting for phase events")
            return

        span = max(right - left, 1)
        count = len(events)
        for index, phase in enumerate(events):
            x = left if count == 1 else left + (span * index / (count - 1))
            is_last = index == count - 1
            color = PALETTE["blue"]
            up = phase.upper()
            if any(t in up for t in ("BLOCK", "ERROR", "ESTOP", "CRASH", "FATAL")):
                color = PALETTE["red"]
            elif any(t in up for t in ("DONE", "COMPLETE", "DOCKED", "IDLE")):
                color = PALETTE["green"]
            radius = 5 if is_last else 3
            trace_canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=color, outline=PALETTE["white"] if is_last else color, width=1,
            )
            trace_canvas.create_text(
                x, y + 14, text=phase[:14],
                fill=PALETTE["ink"] if is_last else PALETTE["muted"],
                font=(FONT, 7, "bold" if is_last else "normal"), anchor="n",
            )
        history_note.set(f"{count} recent")

    sim_var.trace_add("write", update_safety)
    dry_var.trace_add("write", update_safety)
    update_safety()

    def refresh_ui() -> None:
        try:
            model.poll()
            view = model.view()
        except tk.TclError:
            return

        state = str(view.get("state") or "IDLE")
        phase = str(view.get("phase") or "—")
        set_configuration_enabled(state == "IDLE")

        state_var.set(state.upper())
        phase_var.set(phase)
        elapsed_var.set(str(view.get("elapsed") or "0:00:00"))

        banner = str(view.get("banner") or "").strip()
        detail = str(view.get("detail") or "").strip()
        sim = bool(sim_var.get())
        dry = bool(dry_var.get())

        # Status precedence: show GUI safety-block messaging in idle when applicable,
        # then explicit model banner, then sensible defaults/details.
        if state == "IDLE" and not sim and not dry:
            status_copy.set("LIVE INPUT requested · GUI live path blocked")
        elif state == "IDLE" and not sim and dry:
            status_copy.set("DRY requested · GUI client access blocked")
        elif banner:
            status_copy.set(banner)
        elif state == "IDLE":
            status_copy.set("Ready. Configure Abyss run and press Start.")
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

        stat1_label.set("Runs")
        stat1_value.set(str(view.get("runs", 0)))
        stat2_label.set("Room")
        stat2_value.set(str(view.get("room", 0)))
        stat3_label.set("Filaments")
        stat3_value.set(str(view.get("filaments", "—")))

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
        "sim_var": sim_var,
        "dry_var": dry_var,
        "safety_summary": safety_summary,
        "safety_detail": safety_detail,
        "safety_detail_label": safety_detail_label,
        "status_copy": status_copy,
        "estop_button": estop_button,
        "filament_entry": filament_entry,
        "max_runs_entry": max_runs_entry,
        "hours_entry": hours_entry,
        "start_button": start_button,
        "pause_button": pause_button,
        "stop_button": stop_button,
        "engine_combo": engine_combo,
        "operate_panel": operate,
        "trace_canvas": trace_canvas,
        "estop_hint": estop_hint,
        "heading_title": heading_title,
        "footer_hint": footer_hint,
        "phase_value_label": phase_value_label,
        "sim_button": sim_button,
        "dry_button": dry_button,
        "refresh": refresh_ui,
    }


def run_window(auto_close_ms: int = 0) -> int:
    """Entry point: open the UI. Returns 0."""
    import tkinter as tk

    model = UiModel()
    root = tk.Tk()
    build_window(root, model, auto_close_ms=auto_close_ms)
    root.mainloop()
    return 0


def main() -> int:
    """CLI entry point for ``python -m fila_bot.ui``."""
    try:
        return run_window()
    except Exception as exc:  # pragma: no cover - UI startup guard
        import traceback

        traceback.print_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "fila-bot UI failed to start",
                f"{exc!r}\n\n"
                "If you see 'No module named _tkinter', install Python with Tk/Tcl support.\n"
                "On Windows, the standard python.org installer includes it by default.",
            )
            root.destroy()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
