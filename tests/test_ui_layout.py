"""Live Tk UI contract tests; run on the Windows desktop test host."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.ui_redesign import build_window  # noqa: E402
from fila_bot.ui_model import UiModel  # noqa: E402


def ok(name: str) -> None:
    print(f"[PASS] {name}")


root = tk.Tk()
root.withdraw()
model = UiModel(threaded=False)
model.mode = "security"  # the public GUI surface must normalize to its single supported activity
model.engine = "bt"     # preserve the Abyss engine choice
ui = build_window(root, model)
root.update_idletasks()

geometry = root.geometry().split("+", 1)[0]
assert geometry == "870x600", geometry
assert root.minsize() == (870, 600), root.minsize()
ok("operator console opens at the 870x600 compact layout")
root.geometry("870x600+2200+100")
root.deiconify()
root.update()
assert (root.winfo_width(), root.winfo_height()) == (870, 600)
root_bottom = root.winfo_rooty() + root.winfo_height()
root_right = root.winfo_rootx() + root.winfo_width()
assert ui["phase_value_label"].winfo_width() > 0
assert ui["phase_value_label"].winfo_rootx() + ui["phase_value_label"].winfo_width() <= root_right
trace_text = next(item for item in ui["trace_canvas"].find_all() if ui["trace_canvas"].type(item) == "text")
trace_bounds = ui["trace_canvas"].bbox(trace_text)
assert trace_bounds[3] <= ui["trace_canvas"].winfo_height(), trace_bounds
assert ui["estop_button"].winfo_rooty() + ui["estop_button"].winfo_height() <= root_bottom
operate_bottom = ui["operate_panel"].winfo_rooty() + ui["operate_panel"].winfo_height()
assert ui["estop_hint"].winfo_rooty() + ui["estop_hint"].winfo_height() <= operate_bottom
assert ui["footer_hint"].winfo_rooty() + ui["footer_hint"].winfo_height() <= root_bottom
ok("mapped UI keeps phase, E-STOP, and footer inside the 870x600 minimum viewport")

assert root.title().startswith("fila-bot v"), root.title()  # title kem version (v1.4.0+)
assert model.mode == "abyss", model.mode
assert model.engine == "bt", model.engine
assert ui["heading_title"].cget("text") == "Abyssal Deadspace"
assert not ui["mode_buttons"]
assert "mode_var" not in ui
assert "max_missions_entry" not in ui
assert ui["engine_combo"]["values"] == ("fsm", "bt")
assert ui["engine_combo"].get() == "bt"
assert ui["safety_summary"].get() == "SIM: no EVE connection · DRY: read-only"
assert ui["estop_button"]["state"] == "disabled"
assert ui["estop_button"].winfo_rooty() + ui["estop_button"].winfo_height() <= (
    ui["operate_panel"].winfo_rooty() + ui["operate_panel"].winfo_height()
)
assert ui["heading_title"].cget("text") == "Abyssal Deadspace"
assert ui["footer_hint"].cget("text") == "Kill switch: Ctrl+Shift+Space"
assert ui["sim_button"].cget("selectcolor") == "#355d54"
ok("Abyssal-only UI normalizes modes, removes extra selectors, and preserves safe controls")

ui["sim_var"].set(False)
ui["dry_var"].set(True)
root.update_idletasks()
ui["refresh"]()
root.update()
assert "DRY requested" in ui["safety_summary"].get()
assert "blocked" in ui["safety_summary"].get().lower()
assert "DRY requested" in ui["status_copy"].get()
ok("DRY mode states that GUI client reads are unavailable")
ui["dry_var"].set(False)
root.update_idletasks()
ui["refresh"]()
root.update()
assert "LIVE INPUT" in ui["safety_summary"].get()
assert "blocked" in ui["safety_summary"].get().lower()
assert "cli" in ui["safety_detail"].get().lower()
assert not root.grid_slaves(row=1)
assert "LIVE INPUT" in ui["status_copy"].get()
root_bottom = root.winfo_rooty() + root.winfo_height()
assert ui["estop_button"].winfo_rooty() + ui["estop_button"].winfo_height() <= root_bottom
operate_bottom = ui["operate_panel"].winfo_rooty() + ui["operate_panel"].winfo_height()
assert ui["estop_hint"].winfo_rooty() + ui["estop_hint"].winfo_height() <= operate_bottom
with mock.patch("tkinter.messagebox.showwarning") as showwarning:
    ui["start_button"].invoke()
showwarning.assert_called_once()
assert model.sup is None
ok("GUI reports and refuses unsupported client/live modes instead of implying they can run")

model.state = "RUNNING"
ui["refresh"]()
root.update_idletasks()
assert not ui["mode_buttons"]
assert ui["sim_button"]["state"] == "disabled"
assert ui["dry_button"]["state"] == "disabled"
assert "disabled" in ui["hours_entry"].state()
assert "disabled" in ui["engine_combo"].state()
assert ui["start_button"]["state"] == "disabled"
assert ui["estop_button"]["state"] == "normal"
ok("configuration locks during a session while stop and E-STOP remain available")

model.state = "IDLE"
ui["refresh"]()
root.update_idletasks()
assert not ui["mode_buttons"]
assert ui["sim_button"]["state"] == "normal"
assert "readonly" in ui["engine_combo"].state()
assert ui["start_button"]["state"] == "normal"
ok("configuration unlocks again after the session returns to idle")

root.destroy()
print("ALL OK test_ui_layout")
