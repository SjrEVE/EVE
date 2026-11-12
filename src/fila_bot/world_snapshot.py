"""WorldSnapshot (Perception layer) — doc TOAN BO the gioi game trong 1 lan parse duy nhat.
Khong goi lat nhat tung Eye, khong scan lap lai cay UI.
Test 100% bang cac dump JSON fixtures co san.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent import AgentEye, agents_panel, location_links
from .eye import Eye
from .inventory import InventoryEye
from .mission import MissionEye


@dataclass
class RouteSnapshot:
    destination: str | None = None
    next_system: str | None = None
    jumps: int | None = None
    markers: int = 0


@dataclass
class DialogSnapshot:
    open: bool = False
    title: str | None = None
    chain: tuple[int, int] | None = None
    cargo_m3: float | None = None
    cargo_item: str | None = None
    cargo_qty: int | None = None
    pickup: dict[str, Any] | None = None
    dropoff: dict[str, Any] | None = None
    pickup_link_xy: tuple[int, int] | None = None
    dropoff_link_xy: tuple[int, int] | None = None
    buttons: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class InventorySnapshot:
    open: bool = False
    selected: str | None = None
    capacity: dict[str, float | None] | None = None
    hangars: dict[str, tuple[int, int]] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WorldSnapshot:
    docked: bool = False
    location_state: str = "UNKNOWN"
    location_known: bool = False
    station: str | None = None
    system: str | None = None
    security: float | None = None
    ship_ui_present: bool = False
    active_ship: dict[str, str] | None = None
    ship_panel_observed: bool = False
    module_buttons: list[dict[str, Any]] | None = None
    module_activity_known: bool = False
    drone_panel_observed: bool = False
    drones_in_space: int | None = None
    drones_in_bay: int | None = None
    agents: list[dict[str, Any]] | None = None
    agents_known: bool = False
    active_missions: list[str] | None = None
    mission_panel_observed: bool = False
    speed_mps: float | None = None
    maneuver: str | None = None
    ship_health: dict[str, float] | None = None
    route: RouteSnapshot = field(default_factory=RouteSnapshot)
    selected_name: str | None = None
    selected_buttons: dict[str, tuple[int, int]] = field(default_factory=dict)
    agent_dialog: DialogSnapshot = field(default_factory=DialogSnapshot)
    inventory: InventorySnapshot = field(default_factory=InventorySnapshot)
    connection_lost: bool = False
    message_boxes: list[dict[str, Any]] = field(default_factory=list)
    modal: dict[str, Any] | None = None


def parse_world(eye: Eye) -> WorldSnapshot:
    """Hợp nhất toàn bộ perception vào một WorldSnapshot duy nhất."""
    snap = WorldSnapshot()

    # 1. Connection Lost & Modals (Ưu tiên số 1 để E-STOP)
    snap.connection_lost = eye.connection_lost()
    snap.message_boxes = eye.message_boxes()

    # 1b. Modal chặn (Cannot Complete Mission...) -> world['modal'] để FSM dismiss
    snap.modal = None
    for mb in snap.message_boxes:
        btns = mb.get("buttons") or []
        ok_btn = next((b for b in btns if (b.get("text") or "").lower() in ("ok", "close")), None)
        if ok_btn:
            snap.modal = {"text": " ".join((mb.get("texts") or [])[:4]),
                          "ok_xy": ok_btn.get("center")}
            break

    # 2. Location & ship identity. Do not turn a missing location panel into
    # "in space"; distinguish an observed state from an unknown/transition state.
    me = MissionEye(eye)
    loc = me.location()
    snap.station = loc.get("station")
    snap.system = loc.get("system")
    snap.security = loc.get("security")
    lobby = eye.station_window()
    ship_ui = eye.ship_ui()
    snap.ship_ui_present = ship_ui is not None
    if lobby is not None and ship_ui is not None:
        snap.location_state = "TRANSITION"
    elif lobby is not None or snap.station is not None:
        snap.location_state = "DOCKED"
    elif ship_ui is not None:
        snap.location_state = "IN_SPACE"
    snap.location_known = snap.location_state in ("DOCKED", "IN_SPACE")
    snap.docked = snap.location_state == "DOCKED"

    ship_panel_observed, active_ship = eye.active_ship_observation()
    snap.ship_panel_observed = ship_panel_observed
    snap.active_ship = active_ship
    if ship_ui is not None:
        snap.module_buttons = eye.module_buttons()
        snap.module_activity_known = bool(snap.module_buttons) and all(
            isinstance(button.get("is_active"), bool) for button in snap.module_buttons
        )

    drones = eye.drones_observation()
    snap.drone_panel_observed = drones["observed"]
    snap.drones_in_space = drones["in_space"]
    snap.drones_in_bay = drones["in_bay"]

    # 3. Live ship state (only when the UI positively shows the ship in space).
    if snap.location_state == "IN_SPACE":
        snap.speed_mps = eye.speed_mps()
        snap.maneuver = eye.maneuver()
        snap.ship_health = eye.ship_health()
        sel = eye.selected_item()
        if sel:
            snap.selected_name = sel.get("name")
        snap.selected_buttons = eye.selected_item_buttons()

    # Current jobs and agent availability are separate observations; a missing
    # panel is UNKNOWN, not an empty list.
    snap.mission_panel_observed, snap.active_missions = me.mission_entries_observation()
    snap.agents = agents_panel(eye)
    snap.agents_known = snap.agents is not None


    # 4. Route Panel
    rt = me.route()
    snap.route = RouteSnapshot(
        destination=rt.get("destination"),
        next_system=rt.get("next_system"),
        jumps=rt.get("jumps"),
        markers=rt.get("markers", []),
    )

    # 5. Agent Dialogue Window
    ae = AgentEye(eye)
    if ae.window() is not None:
        off = ae.read_offer() or {}
        links = location_links(eye) or {}
        active_btns = {k: v for k, v in off.get("buttons", {}).items() if v is not None}
        snap.agent_dialog = DialogSnapshot(
            open=True,
            title=off.get("title"),
            chain=off.get("chain"),
            cargo_m3=off.get("cargo_m3"),
            cargo_item=off.get("cargo_item"),
            cargo_qty=off.get("cargo_qty"),
            pickup=off.get("pickup"),
            dropoff=off.get("dropoff"),
            pickup_link_xy=links.get("pickup"),
            dropoff_link_xy=links.get("dropoff"),
            buttons=active_btns,
        )

    # 6. Inventory Window
    ie = InventoryEye(eye)
    if ie.window() is not None:
        hangars = {e["name"]: e["center"] for e in (ie.tree_entries() or [])}
        snap.inventory = InventorySnapshot(
            open=True,
            selected=ie.selected_container(),
            capacity=ie.capacity(),
            hangars=hangars,
            items=ie.items() or [],
        )

    return snap
