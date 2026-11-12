"""Security mission mode (PvE) — điều khiển toàn diện chu trình làm mission.

Vòng đời 1 mission:
    DOCKED (nhận agent) -> UNDOCK -> TRAVEL_SITE (warp beacon)
    -> AT_SITE (combat: AB + RLML + Drone) -> POCKET_CLEAR (wave wait 18s)
    -> GATE (nếu có gate) / TRAVEL_HOME (về trạm) -> DOCKED (trả mission nhận ISK)
    -> READ-BACK (mission entry biến mất) -> IDLE_DONE.

An toàn Fail-Closed:
- Nhận offer theo policy riêng (chỉ decline Anomic); KHÔNG tự bắn hay undock
  mission chưa được hỗ trợ (courier / item-objective / unknown).
- Quyền bắn cần CẢ mission lẫn faction target được nhận diện dương tính.
- Khiên tàu < escape_hp (25%) -> tự động warp_out khẩn cấp.
- Turn-in CHỈ tính khi đọc lại thấy mission entry đã biến mất, không tính theo click.
"""
from __future__ import annotations

import time
from typing import Any

from . import Mode
from ..missions_db import evaluate_offer, authorize_security_targets
from ..objective_ref import ACTIVATE, APPROACH, TRAVEL, objective_reference
from ..mission_target import _distance_m

WAVE_WAIT_S = 18.0
TURNIN_GRACE_S = 20.0   # sau bấm Complete, client cần vài giây cập nhật panel
WARP_COOLDOWN_S = 60.0  # warp 27 AU mất hàng chục giây — không bấm S+click mỗi tick
WARP_MAX_ATTEMPTS = 3
# Ground LIVE 11-11 20:29-20:31: 3 click Undock ok=True trong 9s -> bot BLOCKED,
# nhung probe doc ngay sau do thay docked=False / IN_SPACE. Undock DA THANH CONG;
# EVE doi session lau hon cua so dem click. Dung bang chung + timeout (EVE-Master
# "Wait while ship indicator"), khong block theo so lan bam.
UNDOCK_EVIDENCE_TIMEOUT_S = 45.0
# Owner dung may -> EVE mat foreground. Do la TAM THOI (chu so huu dang can chuot),
# khong phai loi bot: cho lai quyen nhap thay vi giet ca run (live 11-12 13:20).
# Chi dung han khi mat focus lien tuc qua nguong nay, de bot khong ban vao app khac.
INPUT_LOST_GIVE_UP_S = 120.0
# Gate approach: tiến trình đo bằng KHOẢNG CÁCH GIẢM, không phải số lần bấm.
# Live 11-12 13:39: 18 km -> 16 km trong 24 s; ngân sách "3 lần x 8 s" hết
# trước khi tàu tới nơi và bot block oan. Cho tổng thời gian bay thật + chỉ
# coi là kẹt khi khoảng cách KHÔNG đổi trong GATE_APPROACH_STALL_S.
GATE_APPROACH_TOTAL_S = 240.0
GATE_APPROACH_STALL_S = 25.0
UNDOCK_RETRY_INTERVAL_S = 12.0
UNDOCK_MAX_CLICKS = 3
APPROACH_COOLDOWN_S = 8.0
# Tầm đánh thật của fit Gila (RLML II + drone): ngoài ngưỡng này bot phải bay
# tới, không đứng chờ quái tự đến. Ground LIVE 11-12: quái ở 60-65 km, tàu speed
# 0 -> không có đòn nào được phát ra dù đã lock + fire + launch drone.
ENGAGE_RANGE_M = 25000.0
# Bay tới mục tiêu: chỉ gửi lại khi khoảng cách KHÔNG giảm trong ENGAGE_STALL_S
# (gửi lại mỗi tick sẽ khởi động lại manoeuvre và tàu không bao giờ bay).
ENGAGE_STALL_S = 20.0
ENGAGE_MAX_ATTEMPTS = 6
# Panel mission chưa render ngay sau undock KHÔNG phải "mission không hỗ trợ":
# chờ bằng chứng (bounded) trước khi kết luận, nếu không sẽ chặn oan mission
# đang chạy đúng (live 11-12 15:15).
AUTH_WAIT_S = 30.0
# Không đọc được panel mission trong space = KHÔNG biết objective: về trạm đọc
# lại, không warp vào nút 'Warp to Location' không tồn tại (live 11-12 15:45).
NO_MISSION_GRACE_S = 20.0
# Ngay sau khi nhảy cổng, overview còn cây CŨ vài giây: thiếu tín hiệu lúc đó là
# TRANSITION, không phải "không có cổng" (live 11-12 16:37 BLOCKED oan dù đã về
# đúng hệ Piak).
HOME_TRANSITION_GRACE_S = 20.0
# Sau khi bấm 'Warp to Location' client đổi cảnh: UI tree ngừng parse ~10s
# (ground 11-12 18:27). Trong cửa sổ đó KHÔNG được đọc là "không có mission" rồi
# bấm lại cùng nút — phải chờ và đếm số lần bấm.
WARP_SETTLE_S = 20.0
# Panel agent trong trạm render SAU khi dock (ground 11-12 16:48: tick đầu thấy 0
# agent, đọc lại vài giây sau thấy 4 gồm Jitkavaja Ninsen). Danh sách rỗng ngay
# sau khi dock KHÔNG phải "không có agent".
AGENTS_RENDER_WAIT_S = 30.0
# Lock phải ĐỌC LẠI được từ target bar. Ground 11-12: owner hỏi "drone thả ra ko
# lock target thì bắn kiểu gì?" — đúng, trước đây _verify_locked() hard-code False
# nên lock chưa bao giờ xác nhận, và F (drone đánh target đang lock) được gửi mù.
LOCK_RETRY_S = 4.0
LOCK_MAX_ATTEMPTS = 4
# HUD reports nothing in space (`ramp_active`/`isActive` not exported), so the
# launcher state cannot be read back. Pressing again only after a long quiet
# stretch, and only while hostiles are still primary, keeps a launcher that ran
# dry from being dead for the rest of the mission without toggling a running one
# off every few seconds.
WEAPON_REARM_S = 45.0
WEAPON_REARM_MAX = 3
APPROACH_MAX_ATTEMPTS = 3
TARGET_UNRESOLVED_TIMEOUT_S = 15.0


def _gate_in_activation_range(distance: Any) -> bool:
    """Ground 11-11: overview 'Acceleration Gate | 0 m'.

    Chi kich hoat gate khi o trong tam (EVE ~2500 m). 'AU'/'km' hoac None ->
    False (fail-closed), khong bam gate tu xa.
    """
    d = str(distance or "").strip().lower()
    if not d.endswith(" m") or d.endswith(" km"):
        return False
    try:
        return float(d[:-2].replace(",", "")) <= 2500.0
    except ValueError:
        return False


class SecurityMode(Mode):
    name = "security"

    def __init__(self, runner: Any = None, escape_hp: float = 0.25,
                 max_missions: int | None = None,
                 clock=time.monotonic, is_sim: bool = False,
                 session: Any = None) -> None:
        super().__init__()
        self.runner = runner
        self.session = session
        self._turnin_key: str | None = None
        self.escape_hp = escape_hp
        self.max_missions = max_missions
        self.clock = clock
        self.is_sim = is_sim
        self.clear_since: float | None = None
        self.blocked: str | None = None
        self._phase = "UNKNOWN"
        self.completed_missions = 0
        self._locked_target: str | None = None
        self._last_detail: str = ""
        # G9 (log 05:43/11-11): dialog TQ load content KHÔNG đồng bộ — dump
        # 2026-11-10 16:02: click chat xong cây chỉ 60 node + LoadingWheel,
        # offer render sau đó. Đọc offer trên cây rỗng -> title None -> DECLINE
        # mù -> block vĩnh viễn. Ba đồng hồ chống lại điều đó:
        self.dialog_since: float | None = None   # lần đầu thấy dialog (mở/loading)
        self.loaded_since: float | None = None   # lần đầu thấy dialog load xong
        self.request_since: float | None = None  # lần đầu bấm Request Mission
        self.door_since: float | None = None     # bấm Accept/Decline/Complete xong (chờ chuyển cảnh)
        self._home_sent: float | None = None     # đã phát warp_home — chống spam lệnh mỗi tick
        self._weapons_firing: bool = False       # đã phát fire_weapons — chống bấm F1-F4 mỗi tick
        self._weapons_sent: float | None = None  # lần bấm gần nhất (retry có cooldown)
        self._weapons_rearms: int = 0            # số lần bật lại giàn (bounded)
        self._hostiles_gone: bool = False        # pocket đã sạch (không còn mục tiêu)
        self._ab_sent: float | None = None       # lần toggle afterburner gần nhất
        self._defense_sent: dict[str, float] = {}  # lần toggle hardener theo slot
        self._ab_blind_warned: bool = False
        # Một lần hành động cho mỗi engagement (mission, target). Ở space HUD
        # KHÔNG xuất trạng thái module, nên "bấm lại nếu chưa active" sẽ toggle
        # giàn đang chạy thành OFF; "chờ cờ đọc được" thì đứng im mãi.
        self._engagement_id: Any = None
        self._engagement_modules_on: bool = False
        # Bay tới mục tiêu ngoài tầm bắn (ground live 11-12: quái 60-65 km).
        self._approach_target: str | None = None
        self._approach_started: float | None = None
        self._approach_last_move: float | None = None
        self._approach_last_dist: float | None = None
        self._approach_cmd_sent: float | None = None
        self._approach_attempts: int = 0
        self._route_sent: float | None = None    # lần bấm route/tracker gần nhất
        self._auth_wait_since: float | None = None  # chờ panel loại mission render
        self._no_mission_since: float | None = None  # space mà KHÔNG đọc được panel
        self._jump_sent: float | None = None      # lần nhảy cổng về hệ home
        self._home_transition_since: float | None = None  # chờ overview render sau nhảy
        self._agents_wait_since: float | None = None  # chờ panel agent render sau dock
        self._lock_sent: float | None = None       # lần gửi lock_target gần nhất
        self._lock_attempts: int = 0
        self._drones_wait_lock: bool = False       # drone đã ra, chờ lock trước khi F
        self._drones_engaged_for: str | None = None  # target đã gửi F (1 lần/target)
        self._quit_pressed: bool = False         # đã bấm Quit courier — chờ client xử lý
        self._refusal_dismissed: bool = False    # đã đóng modal refusal có từ trước
        # Mất quyền nhập (owner dùng máy) là TẠM THỜI, không phải lỗi bot: giữ
        # FSM sống, chỉ dừng khi mất focus liên tục quá INPUT_LOST_GIVE_UP_S.
        self._input_lost_since: float | None = None
        # Gate ngoài tầm kích hoạt (live 11-12: objective 'activate the
        # Acceleration Gate' nhưng gate ở 18 km) -> phải approach trước, có
        # cooldown + giới hạn, không đứng bấm Warp to Location vô hạn.
        self._gate_approach_sent: float | None = None
        self._gate_approach_attempts: int = 0
        self._gate_approach_started: float | None = None
        self._gate_approach_last_move: float | None = None
        self._gate_approach_distance: float | None = None
        # Live 11-12 20:39: `activate_gate` bi ban lai moi tick (2 lan/giay) vi
        # khoi AT_GATE chay lien tuc khi con trong tam. Mot lenh cho moi objective.
        self._gate_activate_objective: str | None = None
        # Turn-in read-back: không tăng counter theo lần click Complete.
        self._await_turnin: bool = False
        self._turnin_title: str | None = None
        self._turnin_since: float | None = None
        # Phân biệt "vừa nhận mission, cần undock" và "đi làm về, cần mở chat trả".
        # Thiếu cờ này bot mở lại hội thoại agent ngay sau Accept và KHÔNG BAO GIỜ
        # undock (deadlock E2E 11-11).
        self._was_in_space: bool = False
        # Đã từng thấy quái tại site -> mới được phép kết luận "xong, về trạm".
        self._site_visited: bool = False
        # Chống spam lệnh warp tới beacon (ground live 11-11: TRAVEL_SITE đứng
        # 75s vì mỗi tick bấm S+click lại, warp không bao giờ kịp hoàn tất).
        self._warp_sent: float | None = None
        self._warp_attempts: int = 0
        # Di theo route toi he cua mission (M2 TravelTo), ground tu context menu marker.
        from ..travel import TravelTo
        self.travel = TravelTo()
        self._destination_set: bool = False
        self._undock_attempts: int = 0
        self._undock_wait_since: float | None = None   # bat dau cho bang chung IN_SPACE
        self._undock_sent_at: float | None = None      # lan bam Undock gan nhat
        self._dialog_close_attempts: int = 0
        # Approach objective: one command per cooldown, bounded attempts.
        self._approach_sent: float | None = None
        self._approach_attempts: int = 0
        self._approach_label: str | None = None
        self._target_unresolved_since: float | None = None
        # Courier delegate (11-11): mission courier (Cargo Delivery...) do
        # DistributionMode xử lý trọn gói (load/giao/trả) — runner có thể cung cấp
        # "dist_runner" (LiveDistributionRunner). Sim/test không có -> tự xử lý cơ bản.
        self._dist: Any = None

    @property
    def phase(self) -> str:
        return getattr(self, "_phase", "UNKNOWN")

    @phase.setter
    def phase(self, v: str) -> None:
        self._phase = v

    @property
    def at_safe_point(self) -> bool:
        return self._phase in ("DOCKED", "IDLE_DONE")

    @staticmethod
    def _dialog_loaded(world: dict[str, Any]) -> bool:
        """True khi dialog trong world đã render offer (có Edit briefing/objective).
        LiveSecurityRunner nhét AgentEye vào world['_agent_eye']; runner/test
        double không có -> coi như đã load và chỉ tin offer/title."""
        ae = world.get("_agent_eye")
        loaded = getattr(ae, "loaded", None)
        return bool(loaded()) if callable(loaded) else True

    def status(self) -> dict[str, Any]:
        return {
            "mode": self.name,
            "phase": self._phase,
            "completed": self.completed_missions,
            "blocked": self.blocked,
            "detail": getattr(self, "_last_detail", ""),
        }

    def on_action_results(self, results: list[Any]) -> None:
        """React to executor results: yield on lost focus, stop when navigation is impossible.

        Ground LIVE 2026-11-12 13:20: the owner moved the mouse, EVE lost
        foreground for a moment and the old behaviour set BLOCKED immediately —
        ending a run that was mid-warp with a mission already accepted. Losing
        focus is the owner taking control, not a bot failure. Give the window
        back, keep the FSM alive, and only stop after a sustained loss
        (INPUT_LOST_GIVE_UP_S) so a forgotten bot cannot fire into another app.
        """
        lost = any(isinstance(r, dict) and r.get("status") == "INPUT_NOT_OWNED"
                   for r in (results or []))
        home_missing = any(isinstance(r, dict) and r.get("status") == "HOME_NOT_IN_SYSTEM"
                           for r in (results or []))
        if home_missing:
            # Ground LIVE 2026-11-12 16:01 (run16): the ship was left in another
            # system with no route home. Repeating warp_home every tick is a
            # silent loop; stop and state the real gap (a route to the home
            # system), without docking at some other station.
            self._phase = "BLOCKED"
            self.blocked = ("Không có route về hệ của trạm home — tàu đang ở hệ khác. "
                            "Cần set destination về trạm rồi chạy lại; bot không dock "
                            "trạm khác.")
            self._last_detail = self.blocked
            return
        if lost:
            if self._input_lost_since is None:
                self._input_lost_since = self.clock()
            self._last_detail = ("Chờ quyền nhập: cửa sổ EVE không foreground "
                                 "(owner đang dùng máy) — không bấm sang cửa sổ khác")
        else:
            if self._input_lost_since is not None:
                self._last_detail = "Đã có lại quyền nhập — tiếp tục"
            self._input_lost_since = None

    def _input_lost_expired(self) -> bool:
        if self._input_lost_since is None:
            return False
        return self.clock() - self._input_lost_since >= INPUT_LOST_GIVE_UP_S

    def _update_approach_progress(self, dist_m: float | None) -> None:
        """Track real closing progress: distance decreasing counts as movement.

        Ground LIVE 2026-11-12: a "3 attempts" budget expired while the ship was
        still closing at 500 m/s. Progress must be measured on the game's own
        distance readout, not on how many times a key was pressed.
        """
        now = self.clock()
        if dist_m is None:
            return
        prev = self._approach_last_dist
        self._approach_last_dist = dist_m
        if prev is not None and prev - dist_m >= 200.0:
            self._approach_last_move = now
            self._approach_attempts = 0

    def _closing_command(self, xy, name, dist_m: float) -> dict[str, Any] | None:
        """Fly toward a target that is outside weapon range.

        One command, bounded: repeat only when the distance has not dropped for
        ENGAGE_STALL_S, so the ship keeps flying instead of re-issuing approach
        every tick (which restarts the manoeuvre) and instead of standing still.
        """
        now = self.clock()
        if self._approach_target != name:
            self._approach_target = name
            self._approach_last_move = now
            self._approach_attempts = 0
            self._approach_last_dist = None
        if self._approach_started is None:
            self._approach_started = now
        stalled = (now - self._approach_last_move
                   if self._approach_last_move is not None else 0.0)
        if self._approach_cmd_sent is not None and stalled < ENGAGE_STALL_S:
            self._last_detail = (f"Đang bay tới {name} (còn {dist_m / 1000:.0f} km, "
                                 f"cần < {int(ENGAGE_RANGE_M / 1000)} km)")
            return None
        if self._approach_attempts >= ENGAGE_MAX_ATTEMPTS:
            self._phase = "BLOCKED"
            self.blocked = (f"Không vào được tầm bắn {int(ENGAGE_RANGE_M / 1000)} km "
                            f"tới {name} sau {ENGAGE_MAX_ATTEMPTS} lần "
                            f"(còn {dist_m / 1000:.0f} km)")
            self._last_detail = self.blocked
            return {"do": "blocked", "why": self.blocked}
        self._approach_attempts += 1
        self._approach_cmd_sent = now
        self._approach_last_move = now
        self._last_detail = (f"Bay tới {name} (còn {dist_m / 1000:.0f} km) "
                             f"lần {self._approach_attempts}/{ENGAGE_MAX_ATTEMPTS}")
        return {"do": "close_distance", "at": xy, "why": self._last_detail}

    def _should_travel(self, world: dict[str, Any]) -> bool:
        """Vừa nhận mission, chưa rời trạm, có bằng chứng nơi cần đến.

        Boss 11-11: "cứ nhận mission, undock warp đến nơi làm mission". Áp dụng
        CẢ khi Job Board chưa mở (has_active_mission=False) — lúc đó dialog vẫn
        có nút Complete/Quit/Close và bot cũ nhầm thành turn-in rồi đứng im.
        """
        if self._was_in_space:
            return False
        # Da bat dau di (set destination xong) -> giu che do travel, KHONG mo lai
        # hoi thoai agent. Live 11-11: dong dialog xong bot lai click chat agent,
        # dialog mo lai che nut Undock -> 3 lan bam Undock deu vo hieu.
        if self._destination_set:
            return True
        if not world.get("mission_travel_support"):
            return False
        off = world.get("offer") or {}
        btns = off.get("buttons") or {}
        if btns.get("accept"):          # offer chưa accept -> chưa được đi
            return False
        link = world.get("mission_link_xy")
        markers = (world.get("travel") or {}).get("markers") or []
        return bool(link or markers)

    def _travel_actions(self, world: dict[str, Any]) -> list[dict[str, Any]]:
        """Set Destination (link Location) -> dong dialog -> undock (co gioi han)."""
        markers = (world.get("travel") or {}).get("markers") or []
        link = world.get("mission_link_xy")
        if not markers and link and not self._destination_set:
            self._destination_set = True
            self._phase = "SET_DESTINATION"
            self._last_detail = "Set Destination toi dia diem mission (link Location trong briefing)"
            return [{"do": "set_destination", "at": link, "why": self._last_detail}]
        # Ground LIVE 11-11: AgentDialogueWindow phu len nut Undock (889,282).
        # Dong bang nut Close truoc, neu khong click Undock bi dialog an (60 lan
        # ok=True ma tau van dock).
        if world.get("agent_dialog_open") and self._dialog_close_attempts < 3:
            btns = ((world.get("offer") or {}).get("buttons") or {})
            if btns.get("close"):
                self._dialog_close_attempts += 1
                self._phase = "CLOSE_DIALOG"
                self._last_detail = "Đóng hội thoại agent trước khi bấm Undock (dialog che nút)"
                return [{"do": "close_dialog", "at": btns["close"],
                         "why": self._last_detail}]
        # Khong con dem 3 click roi BLOCKED. Live 11-11: click Undock co tac dung
        # nhung EVE doi session sau >10s; bot da tu block truoc khi thay IN_SPACE.
        # Chờ BẰNG CHỨNG (world.docked=False) voi timeout, gian cach cac lan bam.
        now_u = self.clock()
        if self._undock_wait_since is None:
            self._undock_wait_since = now_u
        waited = now_u - self._undock_wait_since
        if waited >= UNDOCK_EVIDENCE_TIMEOUT_S:
            self._phase = "BLOCKED"
            self.blocked = (f"Da bam Undock {self._undock_attempts} lan, cho "
                            f"{int(UNDOCK_EVIDENCE_TIMEOUT_S)}s van DOCKED — can ground "
                            f"lai nut Undock / trang thai cua so")
            self._last_detail = self.blocked
            return [{"do": "blocked", "why": self.blocked}]
        if (self._undock_sent_at is not None
                and now_u - self._undock_sent_at < UNDOCK_RETRY_INTERVAL_S):
            self._phase = "UNDOCK"
            self._last_detail = (f"Da bam Undock, cho EVE doi session "
                                 f"({int(waited)}/{int(UNDOCK_EVIDENCE_TIMEOUT_S)}s) — "
                                 f"KHONG bam lai, KHONG voi BLOCKED")
            return [{"do": "wait", "why": self._last_detail}]
        if self._undock_attempts >= UNDOCK_MAX_CLICKS:
            self._phase = "UNDOCK"
            self._last_detail = (f"Da bam Undock {self._undock_attempts} lan, van cho "
                                 f"bang chung IN_SPACE "
                                 f"({int(waited)}/{int(UNDOCK_EVIDENCE_TIMEOUT_S)}s)")
            return [{"do": "wait", "why": self._last_detail}]
        self._undock_attempts += 1
        self._undock_sent_at = now_u
        self._phase = "UNDOCK"
        self._last_detail = (f"Mission da nhan — Undock di toi site "
                             f"(lan {self._undock_attempts}/{UNDOCK_MAX_CLICKS}, "
                             f"cho {int(UNDOCK_EVIDENCE_TIMEOUT_S)}s bang chung)")
        return [{"do": "undock", "at": world.get("undock_xy"), "why": self._last_detail}]

    def _unverified_turnin(self, title: str | None) -> list[dict[str, Any]]:
        """Nút Complete KHÔNG phải bằng chứng objective xong (ground live 11-11).

        EVE hiện "Complete Mission" ngay sau Accept dù objective chưa làm;
        bấm vào ra modal "Cannot Complete Mission". Chưa rời trạm = chưa có
        bằng chứng đã làm mission -> giữ tàu, báo rõ, không Quit, không retry.
        """
        self._phase = "OBJECTIVE_UNVERIFIED"
        self.blocked = (f"Vừa nhận '{title or '(không đọc title)'}' nhưng bot chưa rời trạm — "
                        "nút Complete không phải bằng chứng objective xong (EVE hiện cả khi "
                        "chưa xong). Giữ tàu ở trạm, chờ operator / objective-complete "
                        "evidence; KHÔNG Quit mission.")
        self._last_detail = self.blocked
        return [{"do": "blocked", "why": self.blocked}]

    def tick(self, world: Any) -> list[dict[str, Any]]:
        # 1. Tương thích ngược với runner cũ / test double
        if world is None or not isinstance(world, dict):
            if hasattr(self.runner, "me"):
                st = self.runner.me.state()
                self._phase = st.phase
                hp = st.hp or {}
                low = min(hp.values()) if hp else None

                if st.phase in ("AT_SITE", "POCKET_CLEAR") and low is not None and low < self.escape_hp:
                    return [{"do": "warp_out", "why": f"hp {low:.2f} < {self.escape_hp} — mission warp ra duoc"}]

                if self.stop_requested:
                    if st.phase == "DOCKED":
                        return []
                    if st.phase != "AT_SITE":
                        return [{"do": "warp_home", "why": "STOP an toan — ve station"}]

                if st.phase == "POCKET_CLEAR":
                    now = self.clock()
                    if self.clear_since is None:
                        self.clear_since = now
                    if now - self.clear_since < WAVE_WAIT_S:
                        return [{"do": "wait", "why": f"wave_wait {int(now - self.clear_since)}/{int(WAVE_WAIT_S)}s"}]
                else:
                    self.clear_since = None

                acts = self.runner.next_actions() or []
                b = [a for a in acts if a.get("do") == "blocked"]
                self.blocked = b[0].get("why") if b else None
                return acts
            return []

        # 2. Logic điều khiển LIVE từ world snapshot
        if self._phase == "IDLE_DONE":          # chốt trạng thái kết thúc
            return []
        self.blocked = None                      # blocked cũ không được kéo sang tick sau
        if self._input_lost_expired():
            self._phase = "BLOCKED"
            self.blocked = (f"Mất quyền nhập quá {int(INPUT_LOST_GIVE_UP_S)}s — "
                            "dừng hẳn. Bot không bấm sang cửa sổ khác; "
                            "đưa EVE lên foreground rồi chạy lại.")
            self._last_detail = self.blocked
            return [{"do": "blocked", "why": self.blocked}]
        if world.get("connection_lost"):
            self.blocked = "Mất kết nối server (Connection Lost)"
            return [{"do": "estop", "why": "Connection Lost"}]
        if world.get("location_known") is False or world.get("snapshot_valid") is False:
            # Ground LIVE 2026-11-12 18:27: right after a warp click the client
            # changes session and the UI tree stops parsing for ~10 s. This state
            # is a TRANSITION, not an emergency: wait for the re-read and count
            # the warp attempt, instead of silently burning the whole click budget
            # (the generic branch then re-clicked the same button for minutes).
            if self._warp_sent is not None:
                waited = self.clock() - self._warp_sent
                if waited < WARP_SETTLE_S:
                    self._phase = "TRANSITION"
                    self._last_detail = (
                        f"Client đang đổi cảnh sau warp — chờ đọc lại "
                        f"({int(waited)}/{int(WARP_SETTLE_S)}s), không bấm gì")
                    return [{"do": "wait", "why": self._last_detail}]
                if self._warp_attempts >= WARP_MAX_ATTEMPTS:
                    self._phase = "BLOCKED"
                    self.blocked = (
                        f"Đã bấm 'Warp to Location' {WARP_MAX_ATTEMPTS} lần mà client "
                        "vẫn không đọc lại được — có thể tàu chưa ở hệ của mission; "
                        "cần operator xác nhận vị trí")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
            self._phase = "UNKNOWN"
            self._last_detail = "Snapshot/location UNKNOWN or TRANSITION — no input"
            return [{"do": "wait", "why": self._last_detail}]
        prof_agent = world.get("profile_agent_id")
        active_agent = world.get("mission_agent_id")
        if prof_agent and active_agent and str(prof_agent) != str(active_agent):
            self._phase = "FOREIGN_MISSION"
            self.blocked = (
                f"Mission đang active thuộc agent {active_agent}, không phải agent "
                f"profile {prof_agent} — ngoài phạm vi V1 (một agent/level 1). "
                "Không tự chạy/không bấm; cần operator xử lý mission này.")
            self._last_detail = self.blocked
            return [{"do": "blocked", "why": self.blocked}]
        if not world.get("docked"):
            self._was_in_space = True
            self._undock_attempts = 0
            self._undock_wait_since = None
            self._undock_sent_at = None
            self._dialog_close_attempts = 0
            self._destination_set = False
        if world.get("connection_lost"):
            self.blocked = "Mất kết nối server (Connection Lost)"
            return [{"do": "estop", "why": "Connection Lost"}]

        hp = world.get("ship_health") or {}
        shield = hp.get("shield")
        low = min(hp.values()) if hp else None

        # Modal chặn mọi click. NHƯNG "Cannot Complete Mission" là bằng chứng
        # EVE VỪA TỪ CHỐI trả thưởng do objective chưa xong — ground trực tiếp
        # tu dump TQ 11-11 (g10_turnin_dialog.json: "you must deliver 1 x Crates
        # of Synthetic Oil"). Dismiss rồi bấm Complete lại = vòng lặp vô hạn.
        # Fail-closed: dừng, báo lý do thật, KHÔNG click OK, KHÔNG Quit mission.
        modal = world.get("modal")
        if modal:
            mtext = str(modal.get("text") or "")
            low = mtext.lower()
            refusal = ("cannot complete" in low
                       or "objectives have not been completed" in low
                       or "must deliver" in low)
            # Ground LIVE 2026-11-12 (two traces, one rule):
            #  - 19:33 run24: a box left over from an EARLIER turn-in was still in
            #    the tree when a FRESH mission had just been accepted. Treating it
            #    as a refusal killed that valid mission before it undocked.
            #  - 18:19 Piak: the same text, produced while the bot was trying to
            #    complete a mission that really was not finished.
            # Evidence that separates them (ground 2026-11-12):
            #  - 18:19 / dump g10_turnin_dialog: EVE refuses a Complete we just
            #    pressed -> terminal, and the counter must not move.
            #  - 19:33 run24 and 19:42 run25: the same box was STILL in the tree
            #    on a later visit where the bot had pressed nothing (no
            #    complete_mission in the log) and, at 19:42, had never even left
            #    the station. A box the bot did not provoke is stale UI.
            # A real refusal therefore requires a Complete click in THIS run.
            if refusal and self._await_turnin:
                self._phase = "OBJECTIVE_UNVERIFIED"
                self.blocked = f"EVE từ chối Complete (objective chưa xong): {mtext[:180]}"
                self._last_detail = self.blocked
                return [{"do": "blocked", "why": self.blocked}]
            if refusal:
                if not self._refusal_dismissed:
                    self._refusal_dismissed = True
                    self._last_detail = ("Modal 'Cannot Complete Mission' có từ trước "
                                         "(run này chưa bấm Complete) — đóng rồi làm "
                                         "tiếp mission")
                    return [{"do": "dismiss_modal", "at": modal.get("ok_xy"),
                             "why": self._last_detail}]
                self._phase = "BLOCKED"
                self.blocked = ("Modal 'Cannot Complete Mission' vẫn còn sau khi đóng "
                                "— không rõ nguồn; dừng để operator xem client")
                self._last_detail = self.blocked
                return [{"do": "blocked", "why": self.blocked}]
            self._last_detail = f"Đóng modal: {mtext[:60]}"
            return [{"do": "dismiss_modal", "at": modal.get("ok_xy"), "why": self._last_detail}]

        # Guard: Thoát hiểm khi khiên yếu
        if not world.get("docked") and low is not None and low < self.escape_hp:
            return [{"do": "warp_out", "why": f"Shield {low*100:.1f}% < {self.escape_hp*100:.0f}% — Warp thoát hiểm!"}]

        # Guard: Dừng an toàn khi người dùng ấn STOP
        if self.stop_requested:
            if world.get("docked"):
                self._phase = "IDLE_DONE"
                return []
            if not world.get("hostiles"):
                return [{"do": "warp_home", "why": "STOP an toàn — về trạm"}]

        # Giới hạn số lượng mission
        if self.max_missions and self.completed_missions >= self.max_missions:
            if world.get("docked"):
                self._phase = "IDLE_DONE"
                return []

        # ---------------- GIAI ĐOẠN TRONG TRẠM (DOCKED) ----------------
        if world.get("docked"):
            self._phase = "DOCKED"
            self.clear_since = None
            self._home_sent = None    # đã về tới trạm — reset đồng hồ warp_home
            self._approach_sent = None
            self._approach_attempts = 0
            self._approach_label = None
            self._target_unresolved_since = None

            # --- READ-BACK TURN-IN: chỉ tính khi panel mission ĐÃ quan sát được
            #     và entry biến mất. Click Complete KHÔNG phải bằng chứng hoàn tất.
            if self._await_turnin:
                now_t = self.clock()
                if self._turnin_since is None:
                    self._turnin_since = now_t
                if world.get("has_active_mission"):
                    if now_t - self._turnin_since < TURNIN_GRACE_S:
                        self._last_detail = ("Đã bấm Complete — chờ client cập nhật panel: "
                                             f"{int(now_t - self._turnin_since)}/{int(TURNIN_GRACE_S)}s")
                        return [{"do": "wait", "why": self._last_detail}]
                    self.blocked = ("Complete không hiệu lực: mission vẫn active sau "
                                    f"{int(TURNIN_GRACE_S)}s — EVE có thể từ chối do objective chưa xong")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                if world.get("mission_panel_observed") is not True:
                    # Ground LIVE 2026-11-12 15:02 (Piak, 'The Guristas Spies'):
                    # after a successful Complete the Job Board/tracker both
                    # disappear (`panel_types_present == []`), so waiting for
                    # "panel observed and mission absent" looped forever while
                    # the agent dialog itself said "The Guristas Spies
                    # Objectives Complete" and offered a NEW 'Request Mission'
                    # with no Complete button. That dialog state is the client
                    # confirming the turn-in — use it instead of stalling.
                    offer_now = world.get("offer") or {}
                    btns = offer_now.get("buttons") or {}
                    texts_now = " ".join(offer_now.get("texts") or []).lower()
                    dialog_ok = bool(
                        world.get("agent_dialog_open")
                        and btns.get("request")
                        and not btns.get("complete")
                        and ("objectives complete" in texts_now
                             or "accomplishment has been noted" in texts_now))
                    if not dialog_ok:
                        self._last_detail = ("Chờ đọc lại Job Board (panel chưa quan sát được) "
                                             "— không tự xác nhận")
                        return [{"do": "wait", "why": self._last_detail}]
                    counted = True
                    if self.session is not None and self._turnin_key:
                        counted = self.session.confirm_turnin(
                            self._turnin_key,
                            objective_complete=True,
                            response_confirmed=True,
                            panel_observed=False,
                            mission_absent=True,
                            dialog_evidence=True,
                        )
                    if counted:
                        self.completed_missions += 1
                        self._last_detail = (
                            f"Turn-in XÁC NHẬN: {self._turnin_title or '(không đọc title)'} — "
                            "dialog agent báo 'Objectives Complete' + offer mới, "
                            "KHÔNG còn nút Complete")
                    else:
                        self._last_detail = ("Turn-in đã xảy ra nhưng thiếu bằng chứng "
                                             "— KHÔNG cộng mission (không bịa thành công)")
                    # Ground LIVE 2026-11-12 18:19 (Piak): EVE itself said
                    # "One or more mission objectives have not been completed" in
                    # the dialog, so this mission was NEVER finished. The ledger
                    # must not keep it active: the next accept would then conflict
                    # (and the run before this one abandoned a mission exactly
                    # that way). Clear the key WITHOUT counting a completion.
                    if self.session is not None and self._turnin_key:
                        try:
                            self.session.reconcile_absent(panel_observed=True,
                                                          mission_absent=True)
                        except Exception:  # noqa: BLE001 — ledger must not kill the run
                            pass
                    self._await_turnin = False
                    self._turnin_key = None
                    self._turnin_title = None
                    self._turnin_since = None
                    self._was_in_space = False
                    self._site_visited = False
                    self._warp_sent = None
                    self._warp_attempts = 0
                    self._destination_set = False
                    self._undock_attempts = 0
                    self._undock_wait_since = None
                    self._undock_sent_at = None
                    self.door_since = None
                    if self.max_missions and self.completed_missions >= self.max_missions:
                        self._phase = "IDLE_DONE"
                    return [{"do": "wait", "why": self._last_detail}]
                counted = True
                if self.session is not None and self._turnin_key:
                    counted = self.session.confirm_turnin(
                        self._turnin_key,
                        objective_complete=world.get("objective_complete") is True,
                        response_confirmed=True,
                        panel_observed=True,
                        mission_absent=True,
                    )
                if counted:
                    self.completed_missions += 1
                    self._last_detail = (f"Turn-in XÁC NHẬN: {self._turnin_title or '(không đọc title)'} "
                                         "— mission entry đã biến mất khỏi panel")
                else:
                    self._last_detail = ("Turn-in đã xảy ra nhưng thiếu bằng chứng objective-complete "
                                         "— KHÔNG cộng mission (không bịa thành công)")
                self._await_turnin = False
                self._turnin_key = None
                self._turnin_title = None
                self._turnin_since = None
                self._was_in_space = False
                self._site_visited = False
                self._warp_sent = None
                self._warp_attempts = 0
                self._destination_set = False
                self._undock_attempts = 0
                self._undock_wait_since = None
                self._undock_sent_at = None
                self.door_since = None
                if self.max_missions and self.completed_missions >= self.max_missions:
                    self._phase = "IDLE_DONE"
                    return []

            # --- NHAN -> SET DESTINATION -> UNDOCK (áp dụng cả khi Job Board chưa mở) ---
            if self._should_travel(world):
                return self._travel_actions(world)

            # Có mission đang hoạt động -> phân biệt COURIER vs COMBAT:
            # - Combat (kill): undock đi bắn
            # - Courier: nếu chưa có hàng trong cargo -> load cargo TRƯỚC rồi undock;
            #   nếu đã giao xong (objective done) -> dialog sẽ có nút Complete hiệu lực.
            if world.get("has_active_mission"):
                offer = world.get("offer")
                buttons = (offer or {}).get("buttons") or {}
                now0 = self.clock()
                # Sau khi bấm nút cửa (Accept/Complete) client cần vài giây đổi
                # cảnh. Đừng đọc panel mission ngay rồi undock/Complete lần 2.
                if self.door_since is not None and now0 - self.door_since < 6.0:
                    self._last_detail = (f"Chờ client cập nhật sau nút cửa: "
                                         f"{int(now0 - self.door_since)}/6s")
                    return [{"do": "wait", "why": self._last_detail}]
                cur_title = ((offer or {}).get("title")
                             or ((world.get("missions") or [""])[0]
                                 if world.get("missions") else None))
                if self.session is not None and cur_title:
                    try:
                        self.session.bind(cur_title)
                    except ValueError as exc:
                        # Ground LIVE 2026-11-12 17:27: the ledger still held
                        # 'The Guristas Spies' active because that turn-in could
                        # not be counted when the tracker vanished. The new offer
                        # had ALREADY been accepted, so blocking here abandoned a
                        # mission the game had given us. If the game shows no
                        # mission at all, the stale key is not active — clear it
                        # WITHOUT counting a completion, then bind the new title.
                        absent = (world.get("mission_panel_observed") is True
                                  and not (world.get("missions") or []))
                        cleared = False
                        if absent and not self._was_in_space:
                            cleared = self.session.reconcile_absent(
                                panel_observed=True, mission_absent=True)
                        if cleared:
                            self.session.bind(cur_title)
                            self._last_detail = (
                                f"Đã xoá key mission cũ (game không còn mission nào) — "
                                f"nhận {cur_title} (KHÔNG cộng completed)")
                        else:
                            self._phase = "MISSION_IDENTITY_CONFLICT"
                            self.blocked = f"Mission identity conflict: {exc}"
                            self._last_detail = self.blocked
                            return [{"do": "blocked", "why": self.blocked}]
                # Đã nhận nhưng CHƯA có flow tự chạy đã verify (courier /
                # item-objective / unknown): giữ tàu ở trạm, báo rõ. Tuyệt đối
                # không Quit (trái policy nhận offer), không undock/bắn mù.
                support = world.get("mission_support")
                # Bang chung combat objective doc tu briefing live cho phep DI
                # CHUYEN (undock/warp) du title chua co trong combat catalog.
                # Day KHONG phai quyen ban: authorize_security_targets() van cham
                # truoc moi lock/fire (can title + faction ID duong tinh).
                travel_ok = (support == "combat"
                             or bool(world.get("mission_travel_support")))
                unsupported = world.get("mission_is_courier") or (
                    support is not None and support != "combat" and not travel_ok)
                has_complete = bool(world.get("agent_dialog_open") and buttons.get("complete"))
                obj_complete = world.get("objective_complete")
                # The game's own tracker says an objective is still open. Clicking
                # Complete now produces "Cannot Complete Mission" and a dismissal
                # loop, so refuse the click and say why.
                if has_complete and obj_complete is False:
                    self._phase = "OBJECTIVE_IN_PROGRESS"
                    self.blocked = ("Game báo objective CHƯA xong "
                                    f"({str(world.get('mission_objective_text') or '')[:120]!r}) — "
                                    "không bấm Complete, không Quit mission")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                # GROUND LIVE 11-11: EVE hiện nút Complete ngay sau Accept dù
                # objective chưa xong -> bấm là ăn modal "Cannot Complete Mission".
                if has_complete and not self._was_in_space:
                    return self._unverified_turnin(cur_title)
                if unsupported and not has_complete:
                    self._phase = "ACCEPTED_UNSUPPORTED"
                    self.blocked = (f"Đã nhận '{cur_title or '(không đọc title)'}' theo policy, "
                                    f"nhưng execution support = {support or 'courier'}, "
                                    "chưa ground objective/ship — giữ tàu ở trạm, "
                                    "không tự undock hay bắn. Cần operator hoặc fixture mới.")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                # ĐÃ đi làm về (từng ở space), dialog có nút Complete -> trả thưởng
                if has_complete:
                    # Ground LIVE 2026-11-12 18:19 (Piak): the dialog itself can
                    # say "One or more mission objectives have not been completed"
                    # while still showing Complete/Quit. That is the client
                    # REFUSING the turn-in: clicking Complete only produces the
                    # refusal loop. Read the dialog text, not just the button.
                    blob = " ".join((offer or {}).get("texts") or []).lower()
                    if ("objectives have not been completed" in blob
                            or "cannot complete" in blob):
                        self._phase = "OBJECTIVE_IN_PROGRESS"
                        self.blocked = (
                            "Game (chính dialog agent) báo objective CHƯA hoàn thành "
                            f"cho '{cur_title or '(không đọc title)'}' — không bấm "
                            "Complete/Quit; cần làm nốt objective trong space")
                        self._last_detail = self.blocked
                        return [{"do": "blocked", "why": self.blocked}]
                    self._await_turnin = True
                    self._turnin_title = (offer or {}).get("title") or cur_title
                    self._turnin_key = (self.session.active_key
                                        if self.session is not None else None)
                    self._turnin_since = now0
                    self.door_since = now0
                    self._last_detail = f"Bấm Complete: {self._turnin_title or '(chưa đọc tiêu đề)'} — chờ read-back"
                    return [{"do": "complete_mission", "at": buttons["complete"], "why": self._last_detail}]
                # Dialog mở nhưng đang load -> chờ (không undock vội)
                if world.get("agent_dialog_open") and not world.get("offer"):
                    if self.dialog_since is None:
                        self.dialog_since = now0
                    if now0 - self.dialog_since < 20.0:
                        self._last_detail = "Mission active + dialog đang mở — chờ render"
                        return [{"do": "wait", "why": self._last_detail}]
                    self.dialog_since = None
                # VỪA NHẬN mission (chưa từng ra space) -> undock đi làm.
                # Nếu không có nhánh này, bot mở lại hội thoại agent ngay sau
                # Accept rồi chờ offer vĩnh viễn = deadlock E2E.
                if not self._was_in_space:
                    self._last_detail = "Mission vừa nhận — Undock bay tới site"
                    return [{"do": "undock", "at": world.get("undock_xy"), "why": self._last_detail}]
                # ĐÃ Ở SPACE VỀ -> mở chat agent để trả (chống undock lặp vô hạn, G10)
                agents = world.get("agents") or []
                sec_agents = [ag for ag in agents if "security" in (ag.get("division") or "").lower() and ag.get("available")]
                preferred = world.get("agent_name")
                if preferred:
                    named = [a for a in sec_agents
                             if str(a.get("name") or "").strip().casefold()
                             == str(preferred).strip().casefold()]
                    if named:
                        sec_agents = named
                if sec_agents:
                    ag = sec_agents[0]
                    self._last_detail = f"Mission active — mở chat {ag.get('name')} để trả"
                    return [{"do": "open_agent_chat", "at": ag.get("chat_xy"), "why": self._last_detail}]
                self._last_detail = "Mission active — không thấy agent, undock (trường hợp biên)"
                return [{"do": "undock", "at": world.get("undock_xy"), "why": self._last_detail}]

            offer = world.get("offer")
            buttons = (offer or {}).get("buttons") or {}
            now = self.clock()

            # Nút Complete ưu tiên trả mission cũ trước mọi nhánh khác.
            # Nhưng không được bấm khi bot chưa từng rời trạm (ground live 11-11).
            if buttons.get("complete"):
                if world.get("objective_complete") is False:
                    self._phase = "OBJECTIVE_IN_PROGRESS"
                    self.blocked = ("Game báo objective CHƯA xong "
                                    f"({str(world.get('mission_objective_text') or '')[:120]!r}) — "
                                    "không bấm Complete")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                if not self._was_in_space:
                    return self._unverified_turnin(offer.get("title"))
                self._await_turnin = True
                self._turnin_title = offer.get("title")
                self._turnin_key = (self.session.active_key
                                    if self.session is not None else None)
                self._turnin_since = now
                self.door_since = now
                self._last_detail = f"Bấm Complete: {self._turnin_title or '(chưa đọc tiêu đề)'} — chờ read-back"
                return [{"do": "complete_mission", "at": buttons["complete"], "why": self._last_detail}]

            # Vòng hội thoại CHƯA mở -> tìm agent, click chat
            if not world.get("agent_dialog_open"):
                self.dialog_since = self.loaded_since = None
                self.request_since = self.door_since = None
                agents = world.get("agents") or []
                sec_agents = [ag for ag in agents if "security" in (ag.get("division") or "").lower() and ag.get("available")]
                preferred = world.get("agent_name")
                if preferred:
                    named = [a for a in sec_agents
                             if str(a.get("name") or "").strip().casefold()
                             == str(preferred).strip().casefold()]
                    if named:
                        sec_agents = named
                if sec_agents:
                    ag = sec_agents[0]
                    self._agents_wait_since = None
                    self._last_detail = f"Mở đối thoại với {ag.get('name')}"
                    return [{"do": "open_agent_chat", "at": ag.get("chat_xy"), "why": self._last_detail}]
                # Ground LIVE 2026-11-12 16:48: the ship docked home and the FSM
                # blocked on the first tick with "Không tìm thấy Security Agent"
                # — but a fresh read seconds later showed 4 agents including
                # Jitkavaja Ninsen (Security, level 1, available). The station
                # agent list renders asynchronously, so an empty list right
                # after docking is NOT "no agent". Wait, bounded, then block.
                if self._agents_wait_since is None:
                    self._agents_wait_since = self.clock()
                waited = self.clock() - self._agents_wait_since
                if waited < AGENTS_RENDER_WAIT_S:
                    self._phase = "DOCKED"
                    self._last_detail = (
                        "Panel agent chưa render (0 Security agent) — chờ "
                        f"{int(waited)}/{int(AGENTS_RENDER_WAIT_S)}s, không kết luận")
                    return [{"do": "wait", "why": self._last_detail}]
                self._phase = "BLOCKED"
                self.blocked = "Không tìm thấy Security Agent khả dụng trong trạm này"
                self._last_detail = self.blocked
                return [{"do": "blocked", "why": self.blocked}]

        # Dialog vừa bấm nút xong -> EVE cần vài giây chuyển cảnh (dialog mới,
        # offer render, panel mission cập nhật). Chờ, đừng kết luận vội.
        if self.door_since is not None:
            now_door = self.clock()
            if now_door - self.door_since < 6.0:
                self._last_detail = (f"Chờ client xử lý sau khi bấm nút: "
                                     f"{int(now_door - self.door_since)}/6s")
                return [{"do": "wait", "why": self._last_detail}]
            self.door_since = None

        # Hội thoại agent (chỉ khi đã dock) — mọi quyết định offer/turn-in nằm ở đây.
        offer = world.get("offer")
        buttons = (offer or {}).get("buttons") or {}
        now = self.clock()

        if world.get("docked") and world.get("agent_dialog_open"):
            # Dialog MỞ nhưng chưa render offer (LoadingWheel) -> chờ có hạn.
            # Ground G9: nội dung xuất hiện khi cây có Edit briefing/objective.
            # world["offer"] != None chỉ nghĩa là cửa sổ tồn tại, KHÔNG phải đã load.
            if self.dialog_since is None:
                self.dialog_since = now
            if not offer or not self._dialog_loaded(world):
                if now - self.dialog_since > 20.0:
                    self.blocked = ("Dialog agent mở quá 20s mà không render offer "
                                    "(có thể agent hết mission — thử agent khác)")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                self._last_detail = (f"Dialog đang load, chờ offer render: "
                                     f"{int(now - self.dialog_since)}/20s")
                return [{"do": "wait", "why": self._last_detail}]

            # Offer đã render nhưng chưa có nút nào -> có thể phải bấm Request
            # Mission trước (hội thoại lần đầu không tự rải offer).
            if not any(buttons.get(k) for k in ("accept", "decline", "delay", "request", "quit")):
                if self.request_since is not None:
                    if now - self.request_since < 8.0:
                        self._last_detail = (f"Đã bấm Request, chờ offer: "
                                             f"{int(now - self.request_since)}/8s")
                        return [{"do": "wait", "why": self._last_detail}]
                    self.blocked = ("Đã bấm Request Mission nhưng không thấy nút "
                                    "offer nào sau 8s")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                self.request_since = now
                self._last_detail = "Hội thoại mới — bấm Request Mission để xin offer"
                return [{"do": "request_mission", "why": self._last_detail}]

            # Có nút offer = đã load. loaded_since chốt ở lần đầu thấy nút
            # (đóng vai đồng hồ grace cho việc đọc tiêu đề bên dưới).
            if self.loaded_since is None:
                self.loaded_since = now
            title = offer.get("title") or ""
            decision, reason = evaluate_offer(title or None)

            if decision == "BLOCKED":
                # Không đọc được tiêu đề: KHÔNG decline mù (bug 05:43). Chờ thêm,
                # block nếu kéo dài — dialog có offer mà không đọc được là dữ liệu lạ.
                if now - self.loaded_since > 12.0:
                    self.blocked = (f"Không đọc được offer dù dialog đã load 12s "
                                    f"({reason})")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                self._last_detail = (f"Chờ đọc được tiêu đề mission: "
                                     f"{int(now - self.loaded_since)}/12s")
                return [{"do": "wait", "why": self._last_detail}]

            if decision == "ACCEPT":
                if buttons.get("accept"):
                    self.door_since = now
                    self._last_detail = f"Chấp nhận: {title} ({reason})"
                    return [{"do": "accept_mission", "at": buttons["accept"],
                             "why": self._last_detail}]
                self.blocked = "Không tìm thấy nút Accept trong bảng hội thoại Agent"
                self._last_detail = self.blocked
                return [{"do": "blocked", "why": self.blocked}]
            if buttons.get("decline"):
                self.door_since = now
                self._last_detail = f"Từ chối: {title} ({reason})"
                return [{"do": "decline_mission", "at": buttons["decline"],
                         "why": self._last_detail}]
            self.blocked = "Không tìm thấy nút Decline trong bảng hội thoại Agent"
            self._last_detail = self.blocked
            return [{"do": "blocked", "why": self.blocked}]

        # ---------------- GIAI ĐOẠN NGOÀI KHÔNG GIAN (IN SPACE) ----------------
        hostiles = world.get("hostiles") or []
        gates = world.get("gates") or []
        beacons = world.get("beacons") or []

        # Có quái được nhận diện trong overview: xác thực CẢ mission title lẫn
        # faction trước bất kỳ lock/fire/drone action nào. Mission không rõ, faction
        # không rõ, Empire Navy, CONCORD, MissionNPC generic => BLOCKED, không bắn.
        if hostiles:
            mission_titles = world.get("missions") or []
            mission_title = world.get("active_mission_title") or (mission_titles[0] if mission_titles else None)
            attackable = [h for h in hostiles if not h.get("skip")]
            authorized, reason = authorize_security_targets(
                mission_title, attackable, world.get("mission_type_label"))
            if not authorized:
                # Ground LIVE 2026-11-12 15:15: right after undock the job panel
                # has not rendered yet (`mission_panel_observed` False,
                # `mission_type_label` None) while hostiles are already in the
                # overview. That is "chưa đọc được loại mission", not "mission
                # không hỗ trợ" — blocking here killed a mission the bot was
                # executing correctly. Wait for the panel, bounded; only block
                # when the panel IS observed and still refuses.
                panel_ready = world.get("mission_panel_observed") is True
                if not panel_ready:
                    if self._auth_wait_since is None:
                        self._auth_wait_since = self.clock()
                    if self.clock() - self._auth_wait_since < AUTH_WAIT_S:
                        self._phase = "AT_SITE"
                        self._last_detail = (
                            "Quái đã hiện nhưng panel mission chưa render — chờ bằng "
                            f"chứng loại mission ({int(self.clock() - self._auth_wait_since)}"
                            f"/{int(AUTH_WAIT_S)}s), không bấm gì")
                        return [{"do": "wait", "why": self._last_detail}]
                self._phase = "BLOCKED"
                self.blocked = f"Combat authorization denied: {reason}"
                self._last_detail = self.blocked
                return [{"do": "blocked", "why": self.blocked}]
            self._auth_wait_since = None
            hostiles = attackable

        # Có quái -> Đang ở Combat Site
        if hostiles:
            self._hostiles_gone = False
            self._phase = "AT_SITE"
            self._site_visited = True
            self._warp_sent = None       # đã tới site, reset đồng hồ warp
            self._warp_attempts = 0
            self.clear_since = None
            self._home_sent = None    # có quái = đang ở site, không phải đang về

            # Sắp xếp quái theo mức độ đe dọa (priority nhỏ = diệt trước)
            hostiles_sorted = sorted(hostiles, key=lambda r: (r.get("priority", 6), r.get("distance") or 999999))
            target = hostiles_sorted[0]
            t_name = target.get("name")
            t_xy = target.get("center")

            acts: list[dict[str, Any]] = []

            # Ground LIVE 2026-11-12 (client source shipmodulebutton.py):
            # `ramp_active` is only True while the ramp animation cycles and
            # IdleRamps() clears it, so in space the HUD/serializer reports
            # nothing for every slot (`null`) — the state is simply not
            # exported there. Waiting for that flag made the bot stand still at
            # the site with the mission running ("vào site mà module đéo biết bật
            # thì oẳng"). Reliable rule that needs no flag: ACT ONCE PER
            # ENGAGEMENT. EVE modules keep cycling on their own once activated,
            # and a second press would toggle them OFF.
            # One module action per MISSION, not per target: pressing again when
            # the next hostile becomes primary would toggle a running launcher or
            # hardener OFF, and in space the state cannot be read back to notice.
            mission_tag = (world.get("active_mission_title")
                           or (world.get("missions") or [None])[0])
            if self._engagement_id != mission_tag:
                self._engagement_id = mission_tag
                self._engagement_modules_on = False
            first_of_engagement = not self._engagement_modules_on

            # Tank TRUOC khi lock: hardener (Med 2/6 Multispectrum Shield
            # Hardener II) phai bat truoc khi tau an damage.
            if first_of_engagement:
                for d in (world.get("defense_modules") or []):
                    slot = d.get("slot")
                    if d.get("observed") is True or not isinstance(slot, int):
                        continue
                    acts.append({"do": "toggle_defense", "slot": slot,
                                 "why": (f"Bật hardener slot {slot} "
                                         "(lần đầu engagement này)")})
                prop_slot = world.get("propulsion_slot")
                if not world.get("modules_observed"):
                    # Sim/legacy eye: khong co module data nao -> giu hanh vi cu
                    # (bat AB mot lan moi engagement).
                    acts.append({"do": "toggle_ab", "why": "Bật Afterburner giữ tốc độ"})
                elif isinstance(prop_slot, int) and world.get("propulsion_observed") is not True:
                    acts.append({"do": "toggle_ab", "slot": prop_slot,
                                 "why": "Bật Afterburner (lần đầu engagement này)"})
                self._engagement_modules_on = True

            # Ground LIVE 2026-11-12 14:26 (Piit, 'The Guristas Spies'): bot sat at
            # the site with speed 0 m/s while the rats hovered at 60-65 km. It
            # locked, fired and launched drones and then did nothing: no step
            # closes the distance, so nothing ever got in range. A Gila with RLML
            # fights around 20-25 km, so the FSM must fly to the target instead of
            # waiting for the rats to come to it.
            dist_m = _distance_m(target.get("distance"))
            self._update_approach_progress(dist_m)
            if dist_m is not None and dist_m > ENGAGE_RANGE_M:
                cmd = self._closing_command(t_xy, target.get("name"), dist_m)
                if cmd is not None:
                    acts.append(cmd)
            elif dist_m is not None and dist_m <= ENGAGE_RANGE_M:
                self._approach_target = None
                self._approach_last_move = None
                self._approach_attempts = 0

            # LOCK: bấm Ctrl+click rồi KIỂM TRA bằng target bar của client. Ground
            # LIVE 2026-11-12 (owner: "drone thả ra ko lock target thì bắn kiểu
            # gì?"): trước đây `_verify_locked()` hard-code False nên lock chưa
            # bao giờ được xác nhận, và lệnh drone `F` (đánh target ĐANG LOCK)
            # được gửi dù có thể chẳng có gì lock. Giờ: gửi lock, đọc lại target
            # bar; chỉ coi là đã lock khi client báo ActiveTarget.
            locked_now = world.get("locked_target")
            bar_supported = world.get("target_bar_supported")
            lock_ok = bool(locked_now) and (
                not t_name
                or str(t_name).strip().casefold() in
                " ".join(str(x) for x in (locked_now.get("texts") or [])).casefold())
            if bar_supported is not True:
                # Eye không đọc được target bar: "chưa lock" là KHÔNG BIẾT, không
                # phải "lock thất bại". Giữ hành vi cũ (một lệnh lock mỗi mục tiêu)
                # và KHÔNG block — nhưng cũng không được coi là đã lock.
                if t_name != self._locked_target:
                    acts.append({"do": "lock_target", "at": t_xy,
                                 "why": f"Khóa mục tiêu {t_name} "
                                        f"(Priority {target.get('priority')})"})
                    self._locked_target = t_name
                lock_ok = False
            elif not lock_ok:
                now_lk = self.clock()
                if (self._locked_target != t_name
                        or self._lock_sent is None
                        or now_lk - self._lock_sent >= LOCK_RETRY_S):
                    if self._lock_attempts >= LOCK_MAX_ATTEMPTS:
                        self._phase = "BLOCKED"
                        self.blocked = (
                            f"Không lock được {t_name} sau {LOCK_MAX_ATTEMPTS} lần "
                            "(target bar của client không có ActiveTarget)")
                        self._last_detail = self.blocked
                        return [{"do": "blocked", "why": self.blocked}]
                    self._lock_attempts += 1
                    self._lock_sent = now_lk
                    self._locked_target = t_name
                    acts.append({"do": "lock_target", "at": t_xy,
                                 "why": f"Khóa mục tiêu {t_name} "
                                        f"(lần {self._lock_attempts}/{LOCK_MAX_ATTEMPTS}, "
                                        f"Priority {target.get('priority')})"})
                elif not world.get("drones_out"):
                    # Chưa lock được thì KHÔNG gửi F (drone sẽ cắn hụt).
                    self._last_detail = (f"Chờ lock {t_name} — chưa gửi lệnh drone "
                                         f"({int(now_lk - self._lock_sent)}/{int(LOCK_RETRY_S)}s)")
            else:
                self._lock_attempts = 0
                self._lock_sent = None

            # Vũ khí: nếu HUD đọc được thì chỉ bấm slot đang OFF; nếu HUD không
            # xuất trạng thái (bình thường khi ở space) thì bấm ĐÚNG MỘT LẦN cho
            # engagement này — KHÔNG bấm lại, vì bấm lại là tắt giàn.
            weapons_obs = world.get("weapons_active")
            now_w = self.clock()
            if weapons_obs is True:
                self._weapons_firing = True
            elif weapons_obs is None:
                # Ground LIVE 2026-11-12: `ramp_active`/`isActive` is not exported
                # in space, so the state cannot be read back. "Once per mission"
                # was the fix for not toggling a running launcher OFF — but it is
                # also wrong: a launcher that runs dry or is reloaded ends up
                # inactive with the mission still going, and the bot never presses
                # it again. Bounded re-arm is the honest compromise: press again
                # only after WEAPON_REARM_S of continuous fight, at most
                # WEAPON_REARM_MAX extra presses, and only while a hostile is
                # still primary (i.e. the fight is genuinely still on).
                if first_of_engagement:
                    acts.append({"do": "fire_weapons",
                                 "why": "Kích hoạt giàn tên lửa (một lần/engagement)"})
                    self._weapons_firing = True
                elif (not self._hostiles_gone
                        and self._weapons_rearms < WEAPON_REARM_MAX
                        and self._weapons_sent is not None
                        and now_w - self._weapons_sent >= WEAPON_REARM_S):
                    self._weapons_rearms += 1
                    self._weapons_sent = now_w
                    acts.append({"do": "fire_weapons",
                                 "why": (f"Bật lại giàn (lần {self._weapons_rearms}/"
                                         f"{WEAPON_REARM_MAX}) — HUD không cho đọc trạng thái")})
                else:
                    self._last_detail = ("Giàn đã kích hoạt — không bấm lại (HUD không "
                                         f"đọc được trạng thái, re-arm {self._weapons_rearms}"
                                         f"/{WEAPON_REARM_MAX})")
            else:
                if (self._weapons_sent is None
                        or now_w - self._weapons_sent >= 8.0):
                    acts.append({"do": "fire_weapons",
                                 "why": "Slot vũ khí observed chưa active — bấm lại"})
                    self._weapons_sent = now_w
                    self._weapons_firing = True

            # Thả Drone và tấn công — CHỈ khi có target ĐÃ LOCK (F = đánh target
            # đang lock; không lock thì drone bay không).
            if not world.get("drones_out"):
                acts.append({"do": "launch_drones", "why": "Phóng 2 Medium Drone"})
                self._drones_wait_lock = True
            elif self._drones_wait_lock:
                # Ground LIVE 2026-11-12: `F` (drones attack) acts on the LOCKED
                # target. This reader build exports no target bar, so the lock
                # itself is UNVERIFIED — say that out loud. But the historical
                # behaviour (launch then one F) is what actually cleared pockets
                # live, so F is sent EXACTLY ONCE per target and never repeated:
                # a repeat carries no new evidence and only risks re-targeting.
                if lock_ok or self._drones_engaged_for != t_name:
                    acts.append({"do": "engage_drones",
                                 "why": (f"Drone cắn {t_name} "
                                         + ("(đã lock)" if lock_ok
                                            else "(lock KHÔNG đọc lại được — gửi F 1 lần)"))})
                    self._drones_engaged_for = t_name
                    self._drones_wait_lock = False
                else:
                    self._last_detail = (f"Đã gửi F cho {t_name} — không gửi lại "
                                         "(client không cho đọc lock)")

            return acts

        # Không còn quái trong overview
        now = self.clock()

        # CHƯA TỚI SITE: không áp wave-wait (logic đó chỉ dành cho pocket vừa
        # clear). Nếu không có nhánh này bot đứng chờ 18s ngay sau undock và
        # báo phase DOCKED dù đang ở không gian.
        if not self._site_visited:
            self._phase = "IN_SPACE"
            self.clear_since = None
            # Ground LIVE 2026-11-12 15:45 (run15): the job panel was gone
            # (`mission_panel_observed False`, no objective text) while the ship
            # sat in space, so the generic warp branch re-clicked 'Warp to
            # Location' 173 times — a button that does not exist without a
            # mission — and then blocked. With NO mission evidence there is
            # nothing to warp to: go back to a station and re-read the state.
            # Ground LIVE 2026-11-12 18:27 (Elonaya): the tracker said 'Warp to
            # Location' while the ship was in the WRONG system (mission location
            # is Elonaya 0.7, ship in Piak). Clicking that button starts a session
            # change, the UI tree stops parsing (`location_state` UNKNOWN, panel
            # None) for ~10 s, the FSM sees "no mission panel" and falls through to
            # the generic warp branch, which re-clicks the same button. Loop.
            # A warp attempt is bounded and must wait for a re-read.
            if world.get("mission_panel_observed") is not True:
                if self._no_mission_since is None:
                    self._no_mission_since = now
                if self._warp_sent is not None:
                    waited = now - self._warp_sent
                    if waited < WARP_SETTLE_S:
                        self._last_detail = (
                            f"Đang warp / client đang đổi cảnh — chờ đọc lại "
                            f"({int(waited)}/{int(WARP_SETTLE_S)}s), không bấm lại")
                        return [{"do": "wait", "why": self._last_detail}]
                    if self._warp_attempts >= WARP_MAX_ATTEMPTS:
                        self._phase = "BLOCKED"
                        self.blocked = (
                            "Đã bấm 'Warp to Location' "
                            f"{WARP_MAX_ATTEMPTS} lần mà panel mission vẫn không đọc "
                            "lại được — có thể tàu chưa tới hệ của mission; cần "
                            "operator xác nhận vị trí")
                        self._last_detail = self.blocked
                        return [{"do": "blocked", "why": self.blocked}]
                if now - self._no_mission_since >= NO_MISSION_GRACE_S:
                    # Không có mission để làm: ưu tiên về ĐÚNG hệ của trạm home
                    # bằng cổng có tên hệ đó trong overview (ground 11-12: tàu ở
                    # Elonaya, overview có "Piak | Stargate (Caldari System)"),
                    # rồi mới dock.
                    if world.get("home_system") and world.get("home_in_system") is False:
                        gate_xy = world.get("home_gate_xy")
                        if gate_xy:
                            self._phase = "TRAVEL_HOME_SYSTEM"
                            now_j = self.clock()
                            # Một lệnh nhảy, rồi CHỜ bằng chứng đã đổi hệ. Ground
                            # LIVE 16:37: bot bấm click+D mỗi tick với toạ độ đổi
                            # liên tục (overview tự sắp lại) — cùng một cổng mà
                            # spam lệnh. Không bấm lại trong cooldown.
                            if (self._jump_sent is not None
                                    and now_j - self._jump_sent < WARP_COOLDOWN_S):
                                self._last_detail = (
                                    f"Đã nhảy cổng về {world.get('home_system')} — chờ "
                                    f"đổi hệ ({int(now_j - self._jump_sent)}/"
                                    f"{int(WARP_COOLDOWN_S)}s)")
                                return [{"do": "wait", "why": self._last_detail}]
                            self._jump_sent = now_j
                            self._last_detail = (
                                f"Không có mission — nhảy cổng về hệ "
                                f"{world.get('home_system')}")
                            return [{"do": "jump_to_system", "at": gate_xy,
                                     "why": self._last_detail}]
                        # Ground LIVE 16:37: ngay sau khi nhảy, overview còn cây
                        # CŨ (chưa có trạm của hệ mới) nên cả hai tín hiệu đều
                        # thiếu và bot BLOCKED oan dù đã về đúng hệ. Chờ render
                        # có giới hạn trước khi kết luận.
                        if self._home_transition_since is None:
                            self._home_transition_since = now
                        if now - self._home_transition_since < HOME_TRANSITION_GRACE_S:
                            self._last_detail = (
                                f"Đang đổi hệ / overview chưa render — chờ "
                                f"{int(now - self._home_transition_since)}/"
                                f"{int(HOME_TRANSITION_GRACE_S)}s")
                            return [{"do": "wait", "why": self._last_detail}]
                        self._phase = "BLOCKED"
                        self.blocked = (
                            f"Cần về hệ {world.get('home_system')} nhưng overview "
                            "không có đúng một cổng tên hệ đó — không nhảy cổng khác")
                        self._last_detail = self.blocked
                        return [{"do": "blocked", "why": self.blocked}]
                    self._home_transition_since = None
                    self._jump_sent = None
                    self._phase = "TRAVEL_HOME"
                    self._last_detail = (
                        "Không có panel mission/objective trong space "
                        f"{int(now - self._no_mission_since)}s — về trạm đọc lại "
                        "thay vì warp mù")
                    return [{"do": "warp_home", "why": self._last_detail}]
                self._last_detail = ("Chưa đọc được panel mission — chờ "
                                     f"{int(now - self._no_mission_since)}"
                                     f"/{int(NO_MISSION_GRACE_S)}s, không warp mù")
                return [{"do": "wait", "why": self._last_detail}]
            self._no_mission_since = None
            # Con route marker (destination da set) -> di theo route: right-click
            # marker -> Jump/Dock. Ground M2 (travel.py), khong tin timer.
            tw = world.get("travel") or {}
            if (tw.get("markers") or tw.get("warping")) and not beacons:
                t_acts = self.travel.tick(tw, self.clock())
                if t_acts:
                    b = [x for x in t_acts if x.get("do") == "blocked"]
                    if b:
                        self.blocked = b[0].get("why")
                        self._last_detail = self.blocked or ""
                    self._phase = "TRAVEL_ROUTE"
                    return t_acts
            # Ground LIVE 11-11 20:4x (scratch/live_after_panel_fix.json): game
            # tu bao trong Opportunities "You need to activate the Acceleration
            # Gate", overview co "Acceleration Gate | 0 m" o Josameto 0.6.
            # Day la BANG CHUNG CUA GAME -> kich hoat gate de vao pocket, KHONG
            # warp tiep (ISXEVE EVEBot "NextRoom", EVE Uni wiki). Fail-closed:
            # can ca objective text LAN gate trong tam moi bam.
            objective = str(world.get("mission_objective_text") or "").lower()
            gate0 = (gates or [None])[0]
            if (gate0 and "activate the acceleration gate" in objective
                    and _gate_in_activation_range(gate0.get("distance"))):
                self._phase = "AT_GATE"
                self._warp_sent = None
                self._warp_attempts = 0
                self._gate_approach_sent = None
                self._gate_approach_attempts = 0
                self._gate_approach_started = None
                self._gate_approach_last_move = None
                self._gate_approach_distance = None
                # Live 11-12 20:39: khoi nay chay moi tick khi con o trong tam, nen
                # no ban `activate_gate` 2 lan/giay suot 2 phut. Mot lenh cho moi
                # lan objective doi (khong doi -> khong ban lai).
                if self._gate_activate_objective != objective:
                    self._gate_activate_objective = objective
                    self._last_detail = (
                        f"Game bao '{world.get('mission_objective_text')}' — kich hoat "
                        f"{gate0.get('name')} ({gate0.get('distance')}) de vao pocket")
                    return [{"do": "activate_gate", "at": gate0.get("center"),
                             "why": self._last_detail}]
                self._last_detail = (
                    f"Da gui kich hoat {gate0.get('name')} "
                    f"({gate0.get('distance')}) — cho game xac nhan vao pocket")
                return [{"do": "wait", "why": self._last_detail}]
            # Ground LIVE 2026-11-12 13:32 (Piak, 'Furrier Fiasco'): objective =
            # 'You need to activate the Acceleration Gate' but the gate is at
            # '18 km'. Activating from there is impossible, and the warp branch
            # below just re-clicked 'Warp to Location' forever (60 s cooldown,
            # 3 attempts) because the ship was already at the site. The gate
            # entry itself has a real overview center, so approach it the same
            # way as an approach objective: bounded, cooldown, and only click
            # the entry the game listed.
            if (gate0 and "activate the acceleration gate" in objective
                    and gate0.get("center")):
                now_g = self.clock()
                dist_m = _distance_m(gate0.get("distance"))
                if self._gate_approach_started is None:
                    self._gate_approach_started = now_g
                if self._gate_approach_last_move is None:
                    self._gate_approach_last_move = now_g
                prev_m = self._gate_approach_distance
                self._gate_approach_distance = dist_m
                # Bang chung tien trinh la KHOANG CACH GIAM, khong phai so lan
                # bam. Live 11-12 13:39: 18 km -> 16 km trong 24 s, nhung ngan
                # sach "3 lan x 8 s" het truoc khi tau toi noi -> block oan.
                if dist_m is not None and prev_m is not None and dist_m < prev_m - 5:
                    self._gate_approach_last_move = now_g
                    self._gate_approach_attempts = 0
                elapsed = now_g - self._gate_approach_started
                stalled = now_g - self._gate_approach_last_move
                if elapsed >= GATE_APPROACH_TOTAL_S:
                    self._phase = "BLOCKED"
                    self.blocked = (f"Approach {gate0.get('name')} {int(elapsed)}s "
                                    f"không vào được tầm kích hoạt "
                                    f"(còn {gate0.get('distance')})")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                # Gui lenh approach NGAY lan dau, roi chi gui lai khi tau
                # khong tien lai gan trong GATE_APPROACH_STALL_S.
                need_send = (self._gate_approach_sent is None
                             or (stalled >= GATE_APPROACH_STALL_S
                                 and now_g - self._gate_approach_sent >= GATE_APPROACH_STALL_S))
                if need_send:
                    if self._gate_approach_attempts >= APPROACH_MAX_ATTEMPTS:
                        self._phase = "BLOCKED"
                        self.blocked = (f"Tàu không tiến lại gần {gate0.get('name')} "
                                        f"sau {APPROACH_MAX_ATTEMPTS} lần "
                                        f"(còn {gate0.get('distance')})")
                        self._last_detail = self.blocked
                        return [{"do": "blocked", "why": self.blocked}]
                    self._gate_approach_attempts += 1
                    self._gate_approach_sent = now_g
                    self._gate_approach_last_move = now_g
                    self._phase = "AT_GATE"
                    self._last_detail = (
                        f"Approach {gate0.get('name')} ({gate0.get('distance')}) "
                        f"để vào tầm kích hoạt "
                        f"(lần {self._gate_approach_attempts}/{APPROACH_MAX_ATTEMPTS})")
                    return [{"do": "approach_target", "at": gate0.get("center"),
                             "why": self._last_detail}]
                self._phase = "AT_GATE"
                self._last_detail = (
                    f"Đang approach {gate0.get('name')} "
                    f"(còn {gate0.get('distance')}, {int(elapsed)}s) — "
                    f"vào tầm 2.5 km sẽ kích hoạt")
                return [{"do": "wait", "why": self._last_detail}]
            # Objective "You need to approach <target>": the label comes from
            # the game's showinfo link; only ONE exact overview entry may
            # authorize a click. Never fall through to a blind warp when the
            # target cannot be resolved, but still allow a grounded beacon to
            # carry the ship to the site first.
            ref = objective_reference(world.get("mission_objective_text"))
            if ref and ref.get("verb") == APPROACH:
                target = world.get("mission_target") or {}
                center = target.get("center")
                label = target.get("label") or ref.get("label")
                if center:
                    self._target_unresolved_since = None
                    if label != self._approach_label:
                        self._approach_label = label
                        self._approach_attempts = 0
                        self._approach_sent = None
                    dist = target.get("distance_m")
                    if isinstance(dist, (int, float)) and dist <= 2500:
                        self._phase = "AT_TARGET"
                        return [{"do": "wait",
                                 "why": (f"Đã tới gần {label} ({dist:.0f} m) — "
                                         "chờ game xác nhận objective")}]
                    now_a = self.clock()
                    if (self._approach_sent is not None
                            and now_a - self._approach_sent < APPROACH_COOLDOWN_S):
                        return [{"do": "wait",
                                 "why": (f"Đang approach {label}: "
                                         f"{int(now_a - self._approach_sent)}/"
                                         f"{int(APPROACH_COOLDOWN_S)}s")}]
                    if self._approach_attempts >= APPROACH_MAX_ATTEMPTS:
                        self._phase = "BLOCKED"
                        self.blocked = (f"Approach {label} không đổi objective sau "
                                        f"{APPROACH_MAX_ATTEMPTS} lần — cần ground lại")
                        self._last_detail = self.blocked
                        return [{"do": "blocked", "why": self.blocked}]
                    self._approach_sent = now_a
                    self._approach_attempts += 1
                    self._phase = "AT_TARGET"
                    return [{"do": "approach_target", "at": center,
                             "why": (f"Game bảo approach {label} — click + Q "
                                     f"(lần {self._approach_attempts}/"
                                     f"{APPROACH_MAX_ATTEMPTS})")}]
                if not beacons:
                    now_u = self.clock()
                    if self._target_unresolved_since is None:
                        self._target_unresolved_since = now_u
                    if now_u - self._target_unresolved_since < TARGET_UNRESOLVED_TIMEOUT_S:
                        return [{"do": "wait",
                                 "why": (f"Objective bảo approach {ref.get('label')!r} "
                                         "nhưng overview chưa có entry khớp duy nhất — "
                                         "không warp mù")}]
                    self._phase = "OBJECTIVE_UNVERIFIED"
                    self.blocked = (f"Objective approach {ref.get('label')!r} nhưng "
                                    "không có entry overview khớp duy nhất sau "
                                    f"{int(TARGET_UNRESOLVED_TIMEOUT_S)}s")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
            else:
                self._target_unresolved_since = None
            if beacons or world.get("empty_xy"):
                self._phase = "TRAVEL_SITE"
                now_w = self.clock()
                # Progress is evidence of ARRIVAL (overview gains a site beacon,
                # or the ship stops), not of "we clicked". Live run26 (19:52-19:53)
                # kept printing "bấm 'Warp to Location' (lần 1/3)" on every tick
                # for a full minute after the click, so the log read like the bot
                # was hammering the button while it was really waiting. Tell the
                # truth: this branch WAITS.
                if (self._warp_sent is not None
                        and now_w - self._warp_sent < WARP_COOLDOWN_S):
                    self._last_detail = (
                        f"Đã gửi warp tới site (lần {self._warp_attempts}/"
                        f"{WARP_MAX_ATTEMPTS}) — chờ tàu tới, "
                        f"({int(now_w - self._warp_sent)}/{int(WARP_COOLDOWN_S)}s)")
                    return [{"do": "wait", "why": self._last_detail}]
                if self._warp_attempts >= WARP_MAX_ATTEMPTS:
                    self._phase = "BLOCKED"
                    self.blocked = (f"Warp tới mission site không hiệu lực sau "
                                    f"{WARP_MAX_ATTEMPTS} lần — cần ground lại menu/site")
                    self._last_detail = self.blocked
                    return [{"do": "blocked", "why": self.blocked}]
                self._warp_sent = now_w
                self._warp_attempts += 1
                if beacons:
                    b = beacons[0]
                    self._last_detail = (f"Warp tới SITE ĐÃ GROUND: {b.get('name')} "
                                         f"(lần {self._warp_attempts}/{WARP_MAX_ATTEMPTS})")
                    return [{"do": "warp_beacon", "at": b.get("center"),
                             "why": self._last_detail}]
                # KHONG co ten site da ground -> KHONG warp vao "Celestial Beacon"
                # bat ky (Derelict Ruins la cosmic anomaly — sai 11-11). Dung menu
                # 'Agent Missions / Encounter (Deadspace) / Warp to Location' theo
                # docs/MISSION_TRAVEL_RESEARCH_2026-11-11.md. Runner fail-closed neu
                # menu khong co entry nay (khong fallback warp beacon).
                self._last_detail = (
                    f"Không có site beacon đã ground (site_hint="
                    f"{world.get('mission_site_hint')}) — bấm 'Warp to Location' "
                    f"(lần {self._warp_attempts}/{WARP_MAX_ATTEMPTS})")
                return [{"do": "warp_to_mission", "at": world["empty_xy"],
                         "why": self._last_detail}]
            self._last_detail = "Đang di chuyển — chưa thấy site/empty point"
            return [{"do": "wait", "why": self._last_detail}]

        # ĐÃ Ở SITE: chờ 18 giây để bắt wave quái ra muộn
        if self.clear_since is None:
            self.clear_since = now
        if now - self.clear_since < WAVE_WAIT_S:
            return [{"do": "wait", "why": f"Chờ wave quái ra trễ: {int(now - self.clear_since)}/{int(WAVE_WAIT_S)}s"}]

        # Pocket đã sạch hoàn toàn
        self._phase = "POCKET_CLEAR"

        # Thu hồi drone trước khi nhảy gate hoặc về trạm
        if world.get("drones_out"):
            return [{"do": "recall_drones", "why": "Thu hồi Drone trước khi rời pocket"}]

        # Nếu còn Acceleration Gate -> Tiến vào Pocket tiếp theo
        if gates:
            gate = gates[0]
            return [{"do": "activate_gate", "at": gate.get("center"),
                     "why": f"Kích hoạt {gate.get('name')} sang pocket mới"}]

        # Không còn gate và không còn quái -> về trạm trả mission
        if world.get("has_active_mission") or self._phase == "POCKET_CLEAR":
            # Ground LIVE 2026-11-12 14:40 (Piak/Elonaya): sau khi clear pocket,
            # panel đổi thành "You need to travel to Piak 0.7" và nút tracker là
            # 'Set Destination'. Bot cũ bỏ qua câu đó, gọi warp_home và đứng im
            # 120 s vì trạm home không nằm trong overview của hệ đang đứng. Luật:
            # GAME bảo đi đâu thì đi đó trước (route/tracker), chỉ warp_home khi
            # objective không còn đòi đi nơi khác.
            ref_clear = objective_reference(world.get("mission_objective_text"))
            if ref_clear and ref_clear.get("verb") == TRAVEL:
                self._phase = "TRAVEL_ROUTE"
                now_t = self.clock()
                if (self._route_sent is not None
                        and now_t - self._route_sent < WARP_COOLDOWN_S):
                    self._last_detail = (
                        f"Game bảo đi tới {ref_clear.get('label')} — đang theo route "
                        f"({int(now_t - self._route_sent)}/{int(WARP_COOLDOWN_S)}s)")
                    return [{"do": "wait", "why": self._last_detail}]
                self._route_sent = now_t
                self._last_detail = (f"Game bảo 'travel to {ref_clear.get('label')}' — "
                                     "bấm tracker Set Destination/Warp to Location")
                return [{"do": "warp_to_mission", "at": world.get("empty_xy"),
                         "why": self._last_detail}]
            self._phase = "TRAVEL_HOME"
            # Chống spam warp_home: lệnh giữ 1 lần, đang warp thì chỉ chờ
            if self._home_sent is None:
                self._home_sent = now
            if now - self._home_sent < 120.0:   # warp về trạm hiếm khi quá 2 phút
                return [{"do": "warp_home", "why": "Nhiệm vụ hoàn thành — quay về trạm trả ISK"}]
            return [{"do": "wait", "why": f"Đang bay về trạm ({int(now - self._home_sent)}s — đợi dock)"}]

        return [{"do": "wait", "why": "Đang di chuyển / Đợi tín hiệu"}]

