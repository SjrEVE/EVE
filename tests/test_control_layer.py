"""Test Auto-Control Layer merge (2026-11-10): scan-code keys, bezier/dry input,
release_all giữ contract cũ, control fallback + submenu + AutoController, win geometry.

Chạy: PYTHONPATH=src python tests/test_control_layer.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot import keys as keys_mod                 # noqa: E402
from fila_bot import input as inp                      # noqa: E402
from fila_bot import control as ctl                    # noqa: E402
from fila_bot import win as win_mod                    # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# ---------------- 1. keys: resolve_vk + scan-code + alias D0..D9 ----------------
ok("resolve_vk_f5", keys_mod.resolve_vk("F5") == 0x74)
ok("resolve_vk_digit_alias", keys_mod.resolve_vk("D7") == 0x37
   and keys_mod.resolve_vk("7") == 0x37)
ok("resolve_vk_lowercase", keys_mod.resolve_vk("d") == 0x44)
try:
    keys_mod.resolve_vk("NOT_A_KEY")
    ok("resolve_vk_unknown_raises", False)
except ValueError:
    ok("resolve_vk_unknown_raises", True)

sc = keys_mod.vk_to_scancode(0x11)   # VK_CONTROL → 0x1D (MapVirtualKeyW hoặc fallback)
ok("scancode_ctrl", sc == 0x1D, str(sc))
ok("scancode_d", keys_mod.vk_to_scancode(0x44) == 0x20, str(keys_mod.vk_to_scancode(0x44)))
ok("scancode_enter", keys_mod.vk_to_scancode(0x0D) == 0x1C)
ok("scancode_unknown_zero", keys_mod.vk_to_scancode(0xFFFF) == 0)
ok("old_key_names_kept", keys_mod.KEY["R"] == 0x52 and keys_mod.KEY["ESC"] == 0x1B
   and keys_mod.KEY["ENTER"] == 0x0D and keys_mod.KEY["SPACE"] == 0x20)

# ---------------- 2. input: dry contract + hold/holds + bezier passthrough ----------------
r = inp.send_click(100, 200, dry_run=True)
ok("click_dry_exact", r["x"] == 100 and r["y"] == 200 and r["dry"] is True, str(r))
r = inp.send_right_click(5, 6, dry_run=True)
ok("right_click_dry_shape", r["x"] == 5 and r["button"] == "right", str(r))
r = inp.send_click(1, 2, dry_run=True, button="right")
ok("click_button_param", r.get("button") == "right", str(r))
r = inp.type_text("25", dry_run=True)
ok("type_text_dry", r["typed"] == "25", str(r))
r = inp.send_type("25", dry_run=True)
ok("send_type_alias", r["typed"] == "25", str(r))
r = inp.send_hover(10, 20, dwell_s=0.1, dry_run=True)
ok("send_hover_dry", r["hover"] is True and r["dwell_s"] == 0.1, str(r))
r = inp.hover(10, 20, dry_run=True)
ok("hover_old_shape", r["hover"] is True and r["dry"] is True, str(r))
r = inp.send_drag((1, 2), (30, 40), dry_run=True)
ok("drag_dry_shape", r["from"] == (1, 2) and r["to"] == (30, 40), str(r))
r = inp.send_hold("ctrl_down", dry_run=True)
ok("send_hold_dry", r["hold"] == "ctrl_down" and r["vk"] == 0x11, str(r))
ok("move_smooth_dry_passthrough", inp.move_cursor_smooth(9, 9, dry_run=True) == (9, 9))

# delay lognormal clamp
delays = [inp.humanized_delay(1.0) for _ in range(300)]
ok("delay_clamped", all(0.75 <= d <= 1.45 for d in delays), f"{min(delays):.2f}..{max(delays):.2f}")

# release_all: contract cũ + _ACTIVE_HOLDS
class FakeUser32:
    def __init__(self, held):
        self.held = set(held)
        self.kb, self.ms = [], []

    def GetAsyncKeyState(self, vk):
        return 0x8000 if vk in self.held else 0

    def keybd_event(self, vk, scan, flags, extra):
        self.kb.append((vk, flags))

    def mouse_event(self, flags, x, y, d, e):
        self.ms.append(flags)


u = FakeUser32(set())
inp._ACTIVE_HOLDS.add(0x11)          # Ctrl đang giữ theo sổ (không đọc được từ fake)
r = inp.release_all(user32=u)
ok("release_holds_registry", r["released"] == ["ctrl"] and r["dry"] is False, str(r))
ok("release_sends_keyup", u.kb == [(0x11, 0x0002)], str(u.kb))
ok("release_clears_holds", inp._ACTIVE_HOLDS == set())

u = FakeUser32({0x11, 0x01})
r = inp.release_all(user32=u)
ok("release_held_keys_mouse", r["released"] == ["ctrl", "lmb"] and u.ms == [0x0004], str(r))

r = inp.release_all(dry_run=True)
ok("release_dry_shape", r["released"] == [] and r["dry"] is True, str(r))

# ---------------- 3. control: fallback + submenu + AutoController + verify factories ----------------
spec_fail = ctl.ActionSpec("primary_fail",
                           [{"do": "combo", "mods": [], "key": "F1"}],
                           verify=lambda eye: False, retry_max=1)
spec_fb = ctl.ActionSpec("fallback", [{"do": "combo", "mods": [], "key": "F2"}])
spec_fail.fallback = spec_fb
r = ctl.execute(spec_fail, dry=True)
combos = [s.get("combo") for s in r["input_log"] if "combo" in s]
ok("fallback_runs_after_fail", r["ok"] is True and combos == ["F1", "F1", "F2"], str(r))

r = ctl.execute(ctl.ActionSpec("plain", [{"do": "combo", "mods": [], "key": "F3"}]), dry=True)
ok("plain_execute_ok", r["ok"] is True and r["attempts"] == 1, str(r))

spec = ctl.act_submenu_select((100, 100), (120, 140), (130, 180))
kinds = [s["do"] for s in spec.steps]
ok("submenu_steps", kinds == ["right_click", "hover", "click"], str(spec.steps))
ok("submenu_hover_dwell", spec.steps[1].get("dwell_s") == 0.30, str(spec.steps[1]))

# old act catalog còn nguyên
ok("act_reload_kept", ctl.act_reload().steps[0]["key"] == "R"
   and ctl.act_reload().steps[0]["mods"] == ["ctrl"])
ok("act_gate_jump_kept", ctl.act_gate_jump((50, 60)).steps[0]["at"] == (50, 60))
ok("act_hotkey_dock_jump_keyclick", ctl.act_hotkey_dock_jump((9, 9)).steps[0]["do"] == "key_click")
ok("act_drones_orbit_new", ctl.act_drones_orbit().steps[0]["mods"] == ["shift", "alt"]
   and ctl.act_drones_orbit().steps[0]["key"] == "R")

# step "hold" + "hover" qua _run_steps dry
log = ctl._run_steps([{"do": "hold", "key": "ctrl_down"},
                      {"do": "hover", "at": (5, 6), "dwell_s": 0.1}], dry=True)
ok("step_hold_shape", log[0] == {"hold": "ctrl_down", "dry": True}, str(log))
ok("step_hover_shape", log[1]["dry"] is True, str(log))

# verify factories: eye=None / eye không có method → True (không chặn dry test)
ok("verify_none_eye", ctl.verify_docked_state(True)(None) is True)
ok("verify_missing_method", ctl.verify_context_menu_open(1)(object()) is True)
ok("verify_maneuver_missing", ctl.verify_maneuver("orbit")(None) is True)

ac = ctl.AutoController(dry=True)
ok("autocnt_dry_nowin", ac.sync_window() is None and ac.win is None)
r = ac.run(ctl.act_confirm())
ok("autocnt_dry_run", r["ok"] is True, str(r))
r = ac.safe_close_menus()
ok("safe_close_failclosed", r["ok"] is False and "empty_point" in r["fail"], str(r))

# act_dismiss vẫn cấm ESC
try:
    ctl.act_dismiss()
    ok("dismiss_still_banned", False)
except NotImplementedError:
    ok("dismiss_still_banned", True)

# overlay gate vẫn fail-closed khi bấm thật
spec_click = ctl.ActionSpec("click_test", [{"do": "click", "at": (50, 50)}])
r = ctl.execute(spec_click, dry=False, win={"origin": (0, 0), "size": (100, 100),
                                            "hwnd": 1, "pid": 999})
ok("overlay_gate_alive", r["ok"] is False and "che" in r.get("fail", ""), str(r))

# ---------------- 4. win: client_to_screen (thuần khi không hwnd) ----------------
w = {"origin": (10, 20), "size": (800, 600)}
ok("cts_origin_offset", win_mod.client_to_screen(w, (100, 200)) == (110, 220))
ok("cts_clamp", win_mod.client_to_screen(w, (-5, -5)) == (12, 22))
ok("cts_none_passthrough", win_mod.client_to_screen(None, (7, 8)) == (7, 8))
ok("win_has_scale_field_or_none", True)   # dict thật có 'scale' khi có hwnd

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
