"""Control layer — biến quyết định thành keybind THẬT của EVE + VERIFY kết quả.

Mọi keybind ở đây lấy từ UniWiki "Keyboard controls" (Havoc 21.06, dump 2026-11-07):

Combat:      Q approach · W orbit · E keep-at-range · S warp-to · A align
             D dock/jump/gate · Ctrl+click lock · Ctrl+Shift unlock · Ctrl+Space stop
             Alt+Space focus overview (chơi bàn phím được từ overview)
Modules:     F1-F8 high · Alt-F1..8 mid · Ctrl-F1..8 low · Ctrl+R reload
             Shift+F1..8 overheat high · Ctrl+Shift+F1..8 overheat low
Drones:      Shift+F launch · F engage · Shift+Alt+R return&orbit · Shift+R return bay
Camera/UI:   Ctrl+D tactical overlay · Esc đóng dialog · Enter confirm (unmodifiable)

Mỗi action = 1 ActionSpec: steps(input cần bấm) + verify(cách check game đã nhận
qua eye) + retry policy. VERIFY là khác biệt giữa bot biết nó vừa làm gì và script gà.

Merge 2026-11-10 (Auto-Control Layer — graft lên nền cũ, giữ 100% contract):
  - ActionSpec.fallback: hành động dự phòng chạy tự động khi verify fail hết retry
  - verify factories: verify_maneuver / verify_context_menu_open / verify_docked_state
  - step mới: "hold" (ctrl_down/ctrl_up qua send_hold có scan-code + _ACTIVE_HOLDS),
    "hover" (dwell mở submenu — hover chứ KHÔNG click entry cha, click là menu sập)
  - act_submenu_select: chuỗi chuẩn menu nhiều cấp (right-click → hover cha → click con)
  - act_drones_orbit (Shift+Alt+R), AutoController (eye + win + control binding)
  - execute luôn release_all trong finally — exception không kẹt Ctrl/Shift
GIỮ NGUYÊN: dry=True mặc định, fail-closed gate _blocked_by_overlay (bị che = KHÔNG
bấm), đủ act catalog ground từ client thật, kwarg `win`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from . import input as inp


@dataclass
class ActionSpec:
    name: str
    steps: list[dict[str, Any]]              # {"do":"combo","mods":[...],"key":"F1"} | {"do":"click","at":(x,y)} | {"do":"wait","s":1.0}
    verify: Callable[[Any], bool] | None = None   # eye -> bool; None = trust
    retry_max: int = 1                        # số lần bấm lại nếu verify fail
    verify_wait: float = 1.0                  # đợi bao lâu sau bấm trước khi check
    fallback: "ActionSpec | None" = None      # chạy khi primary fail hết retry (merge 2026-11-10)


def _run_steps(steps: list[dict[str, Any]], dry: bool,
               humanize: bool = True) -> list[dict[str, Any]]:
    log = []
    for st in steps:
        kind = st["do"]
        if kind == "combo":
            log.append(inp.send_combo(st.get("mods", ()), st["key"], dry_run=dry,
                                      humanize=humanize))
        elif kind == "click":
            log.append(inp.send_click(*st["at"], dry_run=dry, humanize=humanize))
        elif kind == "right_click":
            log.append(inp.send_right_click(*st["at"], dry_run=dry, humanize=humanize))
        elif kind == "wait":
            if not dry:
                time.sleep(st["s"])
            log.append({"waited": st["s"], "dry": dry})
        elif kind == "type":
            log.append(inp.type_text(st["text"], dry_run=dry, humanize=humanize))
        elif kind == "key_click":
            log.append(inp.send_key_click(st["key"], *st["at"], dry_run=dry,
                                          humanize=humanize))
        elif kind == "drag":
            log.append(inp.send_drag(st["from"], st["to"], dry_run=dry,
                                     humanize=humanize))
        elif kind == "hold":
            # merge 2026-11-10: token 'ctrl_down'/'ctrl_up'... qua send_hold (scan-code
            # + _ACTIVE_HOLDS); log giữ shape cũ {"hold": token} cho test_issue1
            inp.send_hold(st["key"], dry_run=dry, humanize=humanize)
            log.append({"hold": st["key"], "dry": dry})
        elif kind == "hover":
            inp.send_hover(*st["at"], dwell_s=float(st.get("dwell_s", 0.28)),
                           dry_run=dry, humanize=humanize)
            log.append({"hover": st["at"], "dwell_s": st.get("dwell_s", 0.28), "dry": dry})
        elif kind == "hold_ctrl_down":
            inp.send_hold("ctrl_down", dry_run=dry, humanize=humanize)
            log.append({"hold": "ctrl_down", "dry": dry})
        elif kind == "hold_ctrl_up":
            inp.send_hold("ctrl_up", dry_run=dry, humanize=humanize)
            log.append({"hold": "ctrl_up", "dry": dry})
    return log


def execute(spec: ActionSpec, eye: Any = None, dry: bool = True,
            win: dict[str, Any] | None = None,
            humanize: bool = True) -> dict[str, Any]:
    """Chạy action + verify + retry. dry=True: không bấm phím thật nhưng VẪN chạy
    verify (để test được retry logic và verify functions).

    win: dict từ win.find_client_window(). Có win → toạ độ client được đổi sang
    toạ độ màn hình trước khi click (BẮT BUỘC khi bấm thật, nếu không sẽ lệch
    đúng bằng title bar + viền — ground 2026-11-09).

    humanize: tắt/bật jitter+lognormal (config.humanize của Boss — audit
    2026-11-10: trước đây nút này chết vì không được truyền xuống input).

    Merge 2026-11-10: release_all trong finally (exception không kẹt phím) +
    spec.fallback tự chạy khi primary fail hết retry.
    """
    attempts = 0
    verified = spec.verify is None      # không có verify → coi như ok ngay
    input_log: list[dict[str, Any]] = []
    steps = _to_screen_steps(spec.steps, win, dry)

    if not dry:
        blocked = _blocked_by_overlay(steps, win)
        if blocked:
            # KHÔNG bấm: bấm vào cửa sổ khác = hành động sai + báo ok giả
            return {"ok": False, "attempts": 0, "input_log": [], "verified": False,
                    "fail": blocked}

    try:
        while attempts <= spec.retry_max:
            attempts += 1
            input_log += _run_steps(steps, dry, humanize=humanize)
            if spec.verify is None:
                verified = True
                break
            if not dry:
                time.sleep(spec.verify_wait)
            if eye is not None and spec.verify(eye):
                verified = True
                break
    finally:
        try:
            inp.release_all(dry_run=dry)
        except Exception:      # noqa: BLE001 — nhả phím lỗi không được giết caller
            pass

    if not verified and spec.fallback is not None:
        fb = execute(spec.fallback, eye=eye, dry=dry, win=win, humanize=humanize)
        input_log += fb.get("input_log", [])
        verified = bool(fb.get("ok"))
        attempts += int(fb.get("attempts", 0))

    return {"ok": verified, "attempts": attempts, "input_log": input_log,
            "verified": verified, "executed_steps": len(input_log)}


def _to_screen_steps(steps: list[dict[str, Any]], win: dict[str, Any] | None,
                     dry: bool) -> list[dict[str, Any]]:
    """Đổi mọi toạ độ client trong steps → toạ độ màn hình (nếu có win & bấm thật)."""
    if win is None or dry:
        return steps
    from .win import client_to_screen
    out = []
    for st in steps:
        do = st.get("do")
        if do in ("click", "right_click", "key_click", "hover") and st.get("at"):
            out.append({**st, "at": client_to_screen(win, st["at"])})
        elif do == "drag" and st.get("from") and st.get("to"):
            out.append({**st,
                        "from": client_to_screen(win, st["from"]),
                        "to": client_to_screen(win, st["to"])})
        else:
            out.append(st)
    return out


def _blocked_by_overlay(steps: list[dict[str, Any]], win: dict[str, Any] | None) -> str | None:
    """Điểm click có bị cửa sổ khác che không? Trả lý do hoặc None.

    Ground 2026-11-09: cửa sổ Hermes che nửa phải EVE → click vào nút Undock
    rơi vào Hermes, game không nhận, mà `execute` vẫn trả ok=True (nói dối).
    Fail-closed: bị che → KHÔNG bấm, trả lý do.
    """
    if win is None:
        return None
    from .win import is_reachable
    for st in steps:
        do = st.get("do")
        if do in ("click", "right_click", "key_click", "hover") and st.get("at"):
            if not is_reachable(win, st["at"]):
                return (f"điểm {st['at']} bị cửa sổ khác che (không phải EVE) — "
                        "không bấm; đưa cửa sổ EVE lên trước")
        elif do == "drag" and st.get("from"):
            if not is_reachable(win, st["from"]):
                return (f"điểm kéo {st['from']} bị cửa sổ khác che — đưa EVE lên trước")
    return None


# ---------------- Closed-loop verify factories (merge 2026-11-10) ----------------

def verify_maneuver(expected_prefix: str) -> Callable[[Any], bool]:
    """Verify HUD maneuver indicator (approach/orbit/align...) bắt đầu bằng prefix."""
    exp = str(expected_prefix).strip().lower()

    def _check(eye: Any) -> bool:
        if eye is None or not hasattr(eye, "maneuver"):
            return True
        if hasattr(eye, "refresh"):
            eye.refresh()
        m = eye.maneuver()
        return bool(m and str(m).strip().lower().startswith(exp))

    return _check


def verify_context_menu_open(min_menus: int = 1) -> Callable[[Any], bool]:
    """Verify context menu đang mở (đếm panel menu trong UI tree)."""

    def _check(eye: Any) -> bool:
        if eye is None or not hasattr(eye, "context_menus"):
            return True
        if hasattr(eye, "refresh"):
            eye.refresh()
        menus = eye.context_menus() or []
        return len(menus) >= min_menus

    return _check


def verify_docked_state(want_docked: bool) -> Callable[[Any], bool]:
    """Verify trạng thái dock/undock qua eye (ShipUI có/hay không)."""

    def _check(eye: Any) -> bool:
        if eye is None or not hasattr(eye, "is_docked"):
            return True
        if hasattr(eye, "refresh"):
            eye.refresh()
        return bool(eye.is_docked()) is bool(want_docked)

    return _check


# ---------------- Action catalog (keybind thật) ----------------

def act_approach(target_xy: tuple[int, int] | None = None) -> ActionSpec:
    """Q trên target đang chọn. Nếu có tọa độ overview entry → click chọn trước."""
    steps = []
    if target_xy:
        steps.append({"do": "click", "at": target_xy})
    steps.append({"do": "combo", "mods": [], "key": "Q"})
    return ActionSpec("approach", steps)


def act_orbit(target_xy: tuple[int, int] | None, distance_km: float) -> ActionSpec:
    """W + nhập khoảng cách (dialog km) — orbit thật của EVE là W→gõ số→Enter.
    Chọn target trước nếu có tọa độ."""
    steps = []
    if target_xy:
        steps.append({"do": "click", "at": target_xy})
    steps += [
        {"do": "combo", "mods": [], "key": "W"},
        {"do": "wait", "s": 0.5},
        {"do": "type", "text": str(int(distance_km))},
        {"do": "combo", "mods": [], "key": "ENTER"},
    ]
    return ActionSpec("orbit", steps)


def act_keep_range(target_xy: tuple[int, int] | None, distance_km: float) -> ActionSpec:
    """E + nhập khoảng cách."""
    steps = []
    if target_xy:
        steps.append({"do": "click", "at": target_xy})
    steps += [
        {"do": "combo", "mods": [], "key": "E"},
        {"do": "wait", "s": 0.5},
        {"do": "type", "text": str(int(distance_km))},
        {"do": "combo", "mods": [], "key": "ENTER"},
    ]
    return ActionSpec("keep_range", steps)


def act_lock(entry_xy: tuple[int, int]) -> ActionSpec:
    """Ctrl+click entry overview = lock (keybind 'Lock target': Ctrl).
    Sequence: keydown Ctrl → click entry → keyup Ctrl → verify qua eye.
    (P0-3 issue #1: click+Q là SAI — Q = approach.)"""
    steps = [
        {"do": "hold_ctrl_down"},          # keydown Ctrl
        {"do": "click", "at": entry_xy},   # click giữ Ctrl
        {"do": "hold_ctrl_up"},            # keyup Ctrl
    ]
    # verify: eye có ActiveItem (selected item window xuất hiện khi có selection)
    return ActionSpec("lock", steps, verify=_verify_locked, retry_max=2, verify_wait=1.0)


def _verify_locked(eye) -> bool:
    """Verify lock qua eye — CHƯA GROUND được node báo lock trên client thật
    (2026-11-09: SelectedItemWnd chỉ là selection, chưa phải lock; chưa có target
    trong tầm để test). Fail-closed: trả False cho tới khi ground được node lock
    thật trong abyss — KHÔNG đoán."""
    return False


def act_module(slot: int, rack: str = "high", enable: bool = True) -> ActionSpec:
    """F1-F8 (high) / Alt-F (mid) / Ctrl-F (low). Toggle nên dùng enable biết trạng thái
    qua eye (module_buttons isActive) — bot không bấm mù."""
    key = f"F{slot}"
    mods = {"high": (), "mid": ("alt",), "low": ("ctrl",)}[rack]
    return ActionSpec(f"module_{rack}_{slot}", [{"do": "combo", "mods": list(mods), "key": key}])


def act_overheat(slot: int, rack: str = "high") -> ActionSpec:
    key = f"F{slot}"
    mods = {"high": ("shift",), "mid": ("alt", "shift"), "low": ("ctrl", "shift")}[rack]
    return ActionSpec(f"overheat_{rack}_{slot}", [{"do": "combo", "mods": list(mods), "key": key}])


def act_reload() -> ActionSpec:
    """Ctrl+R reload ammo (module đang chọn)."""
    return ActionSpec("reload", [{"do": "combo", "mods": ["ctrl"], "key": "R"}])


def act_stop() -> ActionSpec:
    """Ctrl+Space dừng tàu."""
    return ActionSpec("stop", [{"do": "combo", "mods": ["ctrl"], "key": "SPACE"}])


def act_gate_jump(gate_xy: tuple[int, int]) -> ActionSpec:
    """D tại gate (Dock/Jump/Activate gate) — click gate trước rồi D."""
    return ActionSpec("gate", [{"do": "click", "at": gate_xy},
                               {"do": "combo", "mods": [], "key": "D"}])


def act_dock(station_xy: tuple[int, int]) -> ActionSpec:
    return ActionSpec("dock", [{"do": "click", "at": station_xy},
                               {"do": "combo", "mods": [], "key": "D"}])


def act_undock() -> ActionSpec:
    """Undock = click nút Undock (không có keybind mặc định) — eye phải tìm node."""
    return ActionSpec("undock", [{"do": "click", "at": (0, 0)}])   # xy do eye cung cấp


def act_undock_at(xy: tuple[int, int]) -> ActionSpec:
    """Undock tại toạ độ nút đã verify từ eye (tên 'Undock')."""
    return ActionSpec("undock", [{"do": "click", "at": xy}])


def act_launch_drones() -> ActionSpec:
    """Shift+F launch drones từ bay."""
    return ActionSpec("launch_drones", [{"do": "combo", "mods": ["shift"], "key": "F"}])


def act_drones_engage() -> ActionSpec:
    """F = all drones engage target đang lock."""
    return ActionSpec("drones_engage", [{"do": "combo", "mods": [], "key": "F"}])


def act_drones_return() -> ActionSpec:
    """Shift+R return to drone bay (sau đó đợi drone bay về trước khi warp)."""
    return ActionSpec("drones_return", [{"do": "combo", "mods": ["shift"], "key": "R"}],
                      retry_max=0)


def act_drones_orbit() -> ActionSpec:
    """Shift+Alt+R = drones return & orbit (merge 2026-11-10)."""
    return ActionSpec("drones_orbit",
                      [{"do": "combo", "mods": ["shift", "alt"], "key": "R"}])


def act_confirm() -> ActionSpec:
    """Enter confirm dialog (unmodifiable keybind)."""
    return ActionSpec("confirm", [{"do": "combo", "mods": [], "key": "ENTER"}])


def act_warp_to(entry_xy: tuple[int, int] | None = None) -> ActionSpec:
    """Chọn entry overview rồi S = Warp to (combat shortcut mặc định, EVE 2019+).

    Click trước để chọn đúng mục tiêu, rồi S. Không truyền toạ độ → chỉ bấm S
    (dùng khi đã chọn sẵn) — caller phải tự verify tên entry trước (P0-5).
    """
    steps = []
    if entry_xy:
        steps.append({"do": "click", "at": entry_xy})
        steps.append({"do": "wait", "s": 0.4})
    steps.append({"do": "combo", "mods": [], "key": "S"})
    return ActionSpec("warp_to", steps)


def act_warp_route() -> ActionSpec:
    """Warp theo route autopilot đang set: S khi không chọn gì (warp tới destination)."""
    return ActionSpec("warp_route", [{"do": "combo", "mods": [], "key": "S"}])


# ---------------- context menu (ground 2026-11-09) ----------------
# Ground thật trên client TQ: menu phải chuột = layer `l_menu` → `ContextMenu` (name=menuview)
# → `MenuEntryView` (name=context_menu_<Xxx>) → `TextBody` chứa text hiển thị.
# Menu nhiều cấp (Warp to Within → submenu) thì lần lượt: mở menu, hover entry, dump lại,
# bấm entry cấp con. KHÔNG bấm mù: mỗi bước phải đọc lại UI tree để lấy toạ độ entry thật.

def act_open_context_menu(xy: tuple[int, int]) -> ActionSpec:
    """Chuột phải tại toạ độ (overview entry / object) để mở context menu.

    Ground 2026-11-09: menu KHÔNG hiện ngay — đo được 1-2 s sau right-click.
    `wait 0.6` cũ quá ngắn → đọc UI tree thấy 0 menu. Caller phải POLL (# xem
    eye.wait_menu()) thay vì tin vào wait cố định; ở đây để 1.2 s làm mức tối thiểu.
    """
    return ActionSpec("open_menu", [{"do": "right_click", "at": xy},
                                    {"do": "wait", "s": 1.2}])


def act_menu_entry(entry_xy: tuple[int, int]) -> ActionSpec:
    """Bấm 1 entry trong context menu đang mở (toạ độ đọc từ UI tree, đã verify text)."""
    return ActionSpec("menu_entry", [{"do": "click", "at": entry_xy}])


def act_submenu_select(root_xy: tuple[int, int], parent_hover_xy: tuple[int, int],
                       child_click_xy: tuple[int, int],
                       verify: Callable[[Any], bool] | None = None) -> ActionSpec:
    """Menu nhiều cấp — chuỗi 3 bước chuẩn (merge 2026-11-10):
    right-click mở menu gốc → HOVER entry cha (click cha = menu sập ngay!) giữ
    dwell cho submenu bung → click entry con."""
    return ActionSpec(
        "submenu_select",
        [{"do": "right_click", "at": root_xy},
         {"do": "hover", "at": parent_hover_xy, "dwell_s": 0.30},
         {"do": "click", "at": child_click_xy}],
        verify=verify, retry_max=2, verify_wait=0.35)


def act_dismiss() -> ActionSpec:
    """Đóng context menu / popup.

    ⚠️ Ground 2026-11-09: **ESC trong EVE mở Settings window**, không đóng menu
    (đã thử: ESC → mất ShipUI + overview, hiện Settings). Vì vậy KHÔNG dùng ESC
    để đóng menu. Cách đúng: click chuột trái ra vùng trống của game.
    Caller phải truyền toạ độ vùng trống đã verify (không có UI node ở đó).
    """
    raise NotImplementedError(
        "dismiss: KHÔNG dùng ESC (ESC mở Settings). Dùng act_click_empty(xy)")


def act_click_empty(xy: tuple[int, int]) -> ActionSpec:
    """Click vào vùng trống trong game để đóng menu (thay ESC)."""
    return ActionSpec("dismiss_menu", [{"do": "click", "at": xy}])


def act_hotkey_dock_jump(xy: tuple[int, int]) -> ActionSpec:
    """Native EVE hotkey: giữ D + click chuột trái tại xy (gate/station/route marker).
    1 hit duy nhất, KHÔNG mở context menu, không sợ delay hay menu cũ."""
    return ActionSpec("hotkey_dock_jump", [{"do": "key_click", "key": "D", "at": xy}])


def act_drag_item(from_xy: tuple[int, int], to_xy: tuple[int, int]) -> ActionSpec:
    """Kéo thả item từ vị trí này sang vị trí khác (vd từ ItemHangar sang ShipHangar)."""
    return ActionSpec("drag_item", [{"do": "drag", "from": from_xy, "to": to_xy}])


# ---------------- AutoController (merge 2026-11-10) ----------------

class AutoController:
    """Binding cao cấp eye + win + control — sync cửa sổ rồi execute closed-loop."""

    def __init__(self, eye: Any = None, pid: int | None = None, dry: bool = False) -> None:
        self.eye = eye
        self.pid = pid
        self.dry = dry
        self.win: dict[str, Any] | None = None

    def sync_window(self) -> dict[str, Any] | None:
        if self.dry:
            return None
        from .win import find_client_window
        self.win = find_client_window(pid=self.pid)
        return self.win

    def run(self, spec: ActionSpec) -> dict[str, Any]:
        w = self.sync_window()
        return execute(spec, eye=self.eye, dry=self.dry, win=w)

    def safe_close_menus(self) -> dict[str, Any]:
        """Đóng menu còn sóng bằng click vùng trống do eye cung cấp — KHÔNG ESC.
        Fail-closed: eye chưa ground empty_point → không bấm mù."""
        if self.eye is None or not hasattr(self.eye, "empty_point"):
            return {"ok": False, "fail": "eye.empty_point chưa ground — không bấm mù"}
        return self.run(act_click_empty(self.eye.empty_point()))
