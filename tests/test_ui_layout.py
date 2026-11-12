"""Live Tk UI contract tests; run on the Windows desktop test host."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.ui_redesign import build_window  # noqa: E402
from fila_bot.ui_model import MODES, UiModel  # noqa: E402


def ok(name: str) -> None:
    print(f"[PASS] {name}")


root = tk.Tk()
root.withdraw()
model = UiModel(threaded=False)
ui = build_window(root, model)
root.update_idletasks()

assert root.title().startswith("fila-bot v"), root.title()  # title kem version (v1.4.0+)
assert tuple(ui["mode_buttons"].keys()) == MODES
assert ui["safety_summary"].get() == "SIM: no EVE connection · DRY: read-only"
assert ui["estop_button"]["state"] == "disabled"
assert ui["estop_button"].winfo_rooty() + ui["estop_button"].winfo_height() <= (
    ui["operate_panel"].winfo_rooty() + ui["operate_panel"].winfo_height()
)
assert ui["heading_title"].cget("text") == "Run control"
assert ui["footer_hint"].cget("text") == "Kill switch: Ctrl+Shift+Space"
assert ui["sim_button"].cget("selectcolor") == "#355d54"
ok("new window uses the operator-console title, all modes, and truthful idle safety copy")

ui["mode_var"].set("security")
root.update_idletasks()
assert "disabled" in ui["filament_entry"].state()
assert "disabled" in ui["max_runs_entry"].state()
assert "disabled" in ui["engine_combo"].state()
assert "disabled" not in ui["max_missions_entry"].state()
assert ui["mode_summary"].get() == "Security mission"
ok("security mode only enables its applicable run settings")

ui["mode_var"].set("abyss")
root.update_idletasks()
assert "disabled" not in ui["filament_entry"].state()
assert "disabled" not in ui["max_runs_entry"].state()
assert "disabled" not in ui["engine_combo"].state()
assert "disabled" in ui["max_missions_entry"].state()
ok("Abyss mode only enables its applicable run settings")

ui["sim_var"].set(False)
ui["dry_var"].set(False)
root.update_idletasks()
assert "LIVE INPUT" in ui["safety_summary"].get()
assert "real input" in ui["safety_detail"].get().lower()
assert ui["live_warning"].grid_info()
ok("turning SIM and DRY off exposes a visible live-input warning")

root.destroy()
print("ALL OK test_ui_layout")
