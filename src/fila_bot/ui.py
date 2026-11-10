"""Cua so dieu khien fila-bot (tkinter, stdlib).

    python -m fila_bot.ui                # mo cua so
    python -m fila_bot.ui --smoke 40     # khong mo cua so: chay sim N poll, in trang thai
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fila_bot.ui_model import MODE_LABELS, MODES, UiModel  # noqa: E402


def smoke(n: int) -> int:
    m = UiModel(tick=0.05)
    m.start()
    for _ in range(n):
        time.sleep(0.05)
        m.poll()
    v = m.view()
    m.close()
    print(f"state={v['state']} phase={v['phase']} runs={v['runs']} banner={v['banner']!r}")
    for line in v["log"][-10:]:
        print("  " + line)
    return 0 if v["state"] != "IDLE" or v["runs"] else 1


def run_window(auto_close_ms: int = 0) -> int:
    import tkinter as tk
    from tkinter import messagebox, ttk

    m = UiModel()
    root = tk.Tk()
    root.title("fila-bot — Control Center")
    root.geometry("780x600")

    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")
    mode_var = tk.StringVar(value=m.mode)
    ttk.Label(top, text="Mode:").pack(side="left")
    for key in MODES:
        ttk.Radiobutton(top, text=MODE_LABELS[key], value=key, variable=mode_var).pack(side="left")

    opt = ttk.Frame(root, padding=(8, 0))
    opt.pack(fill="x")
    sim_var, dry_var = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
    hours_var = tk.StringVar(value="4")
    ttk.Checkbutton(opt, text="SIM (khong can client)", variable=sim_var).pack(side="left")
    ttk.Checkbutton(opt, text="DRY (chi log phim)", variable=dry_var).pack(side="left")
    ttk.Label(opt, text="  Max gio:").pack(side="left")
    ttk.Entry(opt, textvariable=hours_var, width=4).pack(side="left")

    opt2 = ttk.Frame(root, padding=(8, 6))
    opt2.pack(fill="x")
    fila_var = tk.StringVar(value=m.filament)
    miss_var, runs_var = tk.StringVar(value=""), tk.StringVar(value="")
    engine_var = tk.StringVar(value=m.engine)
    ttk.Label(opt2, text="Filament:").pack(side="left")
    e_fila = ttk.Entry(opt2, textvariable=fila_var, width=32)
    e_fila.pack(side="left")
    ttk.Label(opt2, text=" So mission:").pack(side="left")
    e_miss = ttk.Entry(opt2, textvariable=miss_var, width=5)
    e_miss.pack(side="left")
    ttk.Label(opt2, text=" So run:").pack(side="left")
    e_runs = ttk.Entry(opt2, textvariable=runs_var, width=5)
    e_runs.pack(side="left")
    ttk.Label(opt2, text=" Engine:").pack(side="left")
    cb_engine = ttk.Combobox(opt2, textvariable=engine_var, values=("fsm", "bt"),
                             width=5, state="readonly")
    cb_engine.pack(side="left")

    def sync_mode(*_a):
        """Chi bat o nhap dung mode: Abyss = filament + run + engine, Dist = so mission."""
        abyss = mode_var.get() == "abyss"
        e_fila.state(["!disabled"] if abyss else ["disabled"])
        e_runs.state(["!disabled"] if abyss else ["disabled"])
        cb_engine.state(["readonly"] if abyss else ["disabled"])
        e_miss.state(["disabled" if abyss else "!disabled"])

    mode_var.trace_add("write", sync_mode)

    btns = ttk.Frame(root, padding=8)
    btns.pack(fill="x")

    def _int_or_none(s: str) -> int | None:
        s = (s or "").strip()
        return int(s) if s.isdigit() else None

    def do_start():
        m.mode, m.sim, m.dry = mode_var.get(), sim_var.get(), dry_var.get()
        try:
            m.max_hours = float(hours_var.get()) or None
        except ValueError:
            m.max_hours = 4.0
        m.filament = fila_var.get().strip() or "Tranquil Exotic Filament"
        m.engine = engine_var.get() or "fsm"
        m.max_missions = _int_or_none(miss_var.get())
        m.max_runs = _int_or_none(runs_var.get())
        if not m.sim and not m.dry:
            if not messagebox.askyesno(
                    "XAC NHAN THAO TAC THAT",
                    f"Mode: {MODE_LABELS[m.mode]}\n\n"
                    "SIM dang TAT va DRY dang TAT:\n"
                    "bot se CLICK CHUOT va BAM PHIM THAT vao cua so EVE.\n\n"
                    "Tau co the bi mat, mission co the bi huy. Tiep tuc?"):
                return
        m.start()

    b_start = ttk.Button(btns, text="START", command=do_start)
    b_pause = ttk.Button(btns, text="PAUSE", command=m.pause)
    b_stop = ttk.Button(btns, text="STOP an toan", command=m.stop)
    b_estop = tk.Button(btns, text="E-STOP", bg="#c0392b", fg="white", command=m.estop)
    for b in (b_start, b_pause, b_stop, b_estop):
        b.pack(side="left", padx=4)

    info = tk.StringVar()
    banner = tk.StringVar()
    ttk.Label(root, textvariable=info, padding=8, font=("Consolas", 10),
              justify="left").pack(fill="x")
    tk.Label(root, textvariable=banner, fg="#c0392b", wraplength=740,
             justify="left").pack(fill="x", padx=8)
    log = tk.Text(root, height=16, font=("Consolas", 9))
    log.pack(fill="both", expand=True, padx=8, pady=8)
    ttk.Label(root, text="Kill-switch: Ctrl+Shift+Space | E-STOP nha phim ngay",
              padding=(8, 0, 8, 6)).pack(anchor="w")

    shown_last = [""]           # dong log cuoi da ve -> chi APPEND, khong xoa/ve lai

    def apply_log(lines: list[str]) -> None:
        if not lines:
            return
        if shown_last[0] not in lines:      # log bi cat (deque maxlen) -> ve lai tu dau
            log.delete("1.0", "end")
            start = max(0, len(lines) - 60)
        else:
            start = lines.index(shown_last[0]) + 1
        new = lines[start:]
        if new:
            log.insert("end", "\n".join(new) + "\n")
            log.see("end")
            shown_last[0] = new[-1]

    def refresh():
        m.poll()
        v = m.view()
        stats = v.get("stats") or {}
        tail = (f"Tong: {stats.get('sessions', 0)} phien / {stats.get('completed', 0)} run, "
                f"{stats.get('crashes', 0)} crash"
                + (f"   Lan cuoi: {stats.get('last_reason')}" if stats.get("last_reason") else ""))
        if m.mode == "abyss":
            body = (f"Trang thai: {v['state']}   Phase: {v['phase']}   Room: {v['room']}\n"
                    f"Run xong: {v['runs']}   HP: {v['hp']}   Filament: {v['filaments']}   "
                    f"Thoi gian: {v['elapsed']}\n")
        else:
            body = (f"Trang thai: {v['state']}   Phase: {v['phase']}\n"
                    f"Mission xong: {v['runs']}   Tu choi: {v.get('declined', 0)}   "
                    f"Thoi gian: {v['elapsed']}\n")
        info.set(body + tail)
        banner.set(v["banner"])
        b_start.state(["!disabled"] if v["can_start"] else ["disabled"])
        b_pause.config(text=v["pause_label"])
        b_pause.state(["!disabled"] if v["can_pause"] else ["disabled"])
        b_stop.state(["!disabled"] if v["can_stop"] else ["disabled"])
        b_estop.config(state="normal" if v["state"] != "IDLE" else "disabled")
        apply_log(v["log"])
        root.after(300, refresh)

    def on_close():
        m.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    if auto_close_ms:
        root.after(auto_close_ms, on_close)     # CI: mo cua so that roi tu dong dong
    sync_mode()
    refresh()
    root.mainloop()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="fila-bot UI")
    ap.add_argument("--smoke", type=int, default=0, help="khong mo cua so, chay sim N poll")
    ap.add_argument("--window-ms", type=int, default=0,
                    help="mo cua so that roi tu dong dong sau N ms (test GUI)")
    a = ap.parse_args()
    if a.smoke:
        return smoke(a.smoke)
    return run_window(auto_close_ms=a.window_ms)


if __name__ == "__main__":
    raise SystemExit(main())
