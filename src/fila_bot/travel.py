"""Travel core (M2) — đi theo route autopilot bằng context menu, port từ Viir warp-to-0.

Nguồn: docs/VIIR_FRAMEWORK_NOTES.md §1 (Bot_autopilot.elm 147-275).
- Marker = AutopilotDestinationIcon ĐẦU trong InfoPanelRoute.
- Hành động: right-click marker → entry chứa 'dock' (ưu tiên) rồi 'jump'.
- Đang warp/jump → chờ, không bấm.
- Jump OK = tên system ĐỔI (không tin timer).
- Hết route = đã từng có route VÀ > NO_ROUTE_DEBOUNCE lần đọc liên tiếp không marker
  (marker biến mất lúc đang jump / đọc lỗi lẻ tẻ).
- Dock OK = ShipUI biến mất.

Toàn bộ logic chạy trên snapshot dict → test không cần client. `read_world(eye)` là
adapter thật; node nào không đọc được trả None (fail-closed).
"""
from __future__ import annotations

from typing import Any

NO_ROUTE_DEBOUNCE = 3
MENU_TIMEOUT_S = 6.0
PROGRESS_TIMEOUT_S = 90.0      # không jump/dock/warp trong 90s sau khi bấm → blocked
MENU_PREFS = ("dock", "jump")
AFTER_CLICK_S = 8.0            # sau khi bấm Dock/Jump: không bấm lại trong 8s (menu cũ còn trong tree)
MENU_RETRY = 3                 # menu thiếu dock/jump: đóng + thử lại 3 lần rồi mới BLOCKED


def read_world(eye: Any) -> dict[str, Any]:
    """Snapshot travel từ eye thật. None = không đọc được (không đoán)."""
    from .mission import MissionEye
    loc = MissionEye(eye).location()
    markers: list[tuple[int, int]] = []
    panels = eye._find_by_type("InfoPanelRoute", select_many=True) or []
    if panels:
        for n in eye.walk(panels[0]):
            if n.get("type") == "AutopilotDestinationIcon":
                xy = eye.abs_center(n)
                if xy:
                    markers.append(xy)
    man = eye.maneuver()
    menu: list[tuple[str, tuple[int, int]]] = []
    for m in eye.context_menus() or []:
        for e in m.get("entries", []):
            if e.get("text") and e.get("center"):
                menu.append((e["text"], e["center"]))
    return {
        "system": loc.get("system"),
        "station": loc.get("station"),
        "docked": eye.ship_ui() is None,
        "markers": markers,
        "warping": isinstance(man, str) and man.lower() in ("warp", "jump"),
        "menu": menu,
        "route_panel": bool(panels),
    }


def pick_menu_entry(menu: list[tuple[str, Any]]) -> tuple[str, Any] | None:
    """Entry đầu khớp 'dock', không có thì 'jump' (không phân biệt hoa thường)."""
    for pref in MENU_PREFS:
        for text, xy in menu:
            if pref in str(text).lower():
                return text, xy
    return None


class TravelTo:
    """FSM đi hết route đang set. tick(world, now) -> list action dict (không tự bấm)."""

    def __init__(self) -> None:
        self.state = "START"          # START → EN_ROUTE → ARRIVED | BLOCKED
        self.jumps = 0
        self.last_system: str | None = None
        self.had_route = False
        self.no_route = 0
        self.menu_opened_at: float | None = None
        self.last_progress: float | None = None
        self.reason: str | None = None
        self.clicked_at: float | None = None
        self.dismissed = False
        self.last_entry: str | None = None
        self.bad_menus = 0

    def _block(self, why: str) -> list[dict[str, Any]]:
        self.state, self.reason = "BLOCKED", why
        return [{"do": "blocked", "why": why}]

    def tick(self, w: dict[str, Any], now: float) -> list[dict[str, Any]]:
        if self.state in ("ARRIVED", "BLOCKED"):
            return []
        if self.last_progress is None:
            self.last_progress = now

        sysname = w.get("system")
        if sysname and self.last_system and sysname != self.last_system:
            self.jumps += 1
            self.last_progress = now
            # game đã nhận lệnh Jump → hết chờ AFTER_CLICK_S ngay (không đợi timer)
            self.clicked_at, self.dismissed = None, False
        if sysname:
            self.last_system = sysname

        markers = w.get("markers") or []
        if markers:
            self.had_route, self.no_route = True, 0
        elif not w.get("warping"):
            self.no_route += 1

        if w.get("docked"):
            if self.had_route and not markers:
                self.state = "ARRIVED"
                return [{"do": "arrived", "station": w.get("station"), "jumps": self.jumps}]
            if not self.had_route and not markers:
                # Vừa bấm Set Destination: EVE tính route mất 1-2s -> chờ có hạn
                # (11-11: block ngay tick đầu làm courier không bao giờ khởi hành)
                if self.no_route <= 12:      # ~12 tick (tick 0.5-1s) trước khi bỏ cuộc
                    return [{"do": "wait", "why": f"chờ route sau Set Destination ({self.no_route})"}]
                return self._block("đang dock và không có route — set destination trước")
            return [{"do": "need_undock", "why": "còn route nhưng đang dock"}]

        if w.get("warping"):
            self.menu_opened_at = None
            self.last_progress = now
            return [{"do": "wait", "why": "đang warp/jump"}]

        if not markers:
            if self.had_route and self.no_route > NO_ROUTE_DEBOUNCE:
                self.state = "ARRIVED"
                return [{"do": "arrived", "station": w.get("station"), "jumps": self.jumps}]
            if not w.get("route_panel", True):
                return self._block("không thấy InfoPanelRoute — mở panel Route")
            return [{"do": "wait", "why": f"không thấy marker ({self.no_route})"}]

        if now - self.last_progress > PROGRESS_TIMEOUT_S:
            return self._block(f"{int(now - self.last_progress)}s không jump/dock/warp")

        menu = w.get("menu") or []
        # Ground G6 2026-11-09 (dumps/g6_log_174436.jsonl): sau khi bấm entry, UI tree
        # vẫn còn menu cũ vài giây → bot cũ bấm 'Dock' 17 lần. Sau click: chờ
        # AFTER_CLICK_S, menu còn → đóng 1 lần, KHÔNG bấm lại.
        if self.clicked_at is not None and now - self.clicked_at < AFTER_CLICK_S:
            if menu and not self.dismissed:
                self.dismissed = True
                return [{"do": "dismiss_menu", "why": "menu cũ còn sau khi bấm — đóng, không bấm lại"}]
            return [{"do": "wait", "why": f"chờ game nhận lệnh '{self.last_entry}'"}]
        if menu:
            hit = pick_menu_entry(menu)
            if hit is None:
                # Ground: lúc đang warp vào trạm, menu marker chỉ có Track/Show Info.
                # Đóng + thử lại vài lần rồi mới block.
                self.bad_menus += 1
                if self.bad_menus > MENU_RETRY:
                    return self._block("menu mở nhưng không có entry dock/jump "
                                       f"({self.bad_menus} lần)")
                self.menu_opened_at = None
                return [{"do": "dismiss_menu", "why": "menu thiếu dock/jump — đóng, thử lại"}]
            self.menu_opened_at = None
            self.last_progress = now
            self.clicked_at, self.dismissed, self.last_entry = now, False, hit[0]
            self.bad_menus = 0
            return [{"do": "menu_entry", "text": hit[0], "at": hit[1]}]

        if self.menu_opened_at is not None and now - self.menu_opened_at < MENU_TIMEOUT_S:
            return [{"do": "wait", "why": "chờ context menu hiện (1-2s)"}]
        self.menu_opened_at = now
        self.state = "EN_ROUTE"
        return [{"do": "open_menu", "at": markers[0], "label": "route marker"}]
