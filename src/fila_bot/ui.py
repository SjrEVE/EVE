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


def run_window() -> int:
    import tkinter as tk
    from tkinter import ttk

    m = UiModel()
    root = tk.Tk()
    root.title("fila-bot")
    root.geometry("620x460")

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

    btns = ttk.Frame(root, padding=8)
    btns.pack(fill="x")

    def do_start():
        m.mode, m.sim, m.dry = mode_var.get(), sim_var.get(), dry_var.get()
        try:
            m.max_hours = float(hours_var.get()) or None
        except ValueError:
            m.max_hours = 4.0
        m.start()

    b_start = ttk.Button(btns, text="START", command=do_start)
    b_pause = ttk.Button(btns, text="PAUSE", command=m.pause)
    b_stop = ttk.Button(btns, text="STOP an toan", command=m.stop)
    b_estop = tk.Button(btns, text="E-STOP", bg="#c0392b", fg="white", command=m.estop)
    for b in (b_start, b_pause, b_stop, b_estop):
        b.pack(side="left", padx=4)

    info = tk.StringVar()
    banner = tk.StringVar()
    ttk.Label(root, textvariable=info, padding=8, font=("Consolas", 10)).pack(fill="x")
    ban_lbl = tk.Label(root, textvariable=banner, fg="#c0392b", wraplength=580, justify="left")
    ban_lbl.pack(fill="x", padx=8)
    log = tk.Text(root, height=14, font=("Consolas", 9))
    log.pack(fill="both", expand=True, padx=8, pady=8)
    ttk.Label(root, text="Kill-switch: Ctrl+Shift+Space", padding=(8, 0, 8, 6)).pack(anchor="w")

    def refresh():
        m.poll()
        v = m.view()
        stats = v.get("stats") or {}
        info.set(f"Trang thai: {v['state']}   Phase: {v['phase']}   Room: {v['room']}\n"
                 f"Run xong: {v['runs']}   HP: {v['hp']}   Filament: {v['filaments']}   "
                 f"Thoi gian: {v['elapsed']}\n"
                 f"Tong: {stats.get('sessions', 0)} phien / {stats.get('completed', 0)} run, "
                 f"{stats.get('crashes', 0)} crash"
                 + (f"   Lan cuoi: {stats.get('last_reason')}" if stats.get("last_reason") else ""))
        banner.set(v["banner"])
        b_start.state(["!disabled"] if v["can_start"] else ["disabled"])
        b_pause.config(text=v["pause_label"])
        b_pause.state(["!disabled"] if v["can_pause"] else ["disabled"])
        b_stop.state(["!disabled"] if v["can_stop"] else ["disabled"])
        log.delete("1.0", "end")
        log.insert("end", "\n".join(v["log"][-60:]))
        log.see("end")
        root.after(300, refresh)

    def on_close():
        m.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    refresh()
    root.mainloop()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="fila-bot UI")
    ap.add_argument("--smoke", type=int, default=0, help="khong mo cua so, chay sim N poll")
    a = ap.parse_args()
    return smoke(a.smoke) if a.smoke else run_window()


if __name__ == "__main__":
    raise SystemExit(main())
