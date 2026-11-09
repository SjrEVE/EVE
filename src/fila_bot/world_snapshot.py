"""WorldSnapshot (Perception layer) — doc TOAN BO the gioi game trong 1 lan parse duy nhat.
Khong goi lat nhat tung Eye, khong scan lap lai cay UI.
Test 100% bang cac dump JSON fixtures co san.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent import AgentEye, location_links
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
    station: str | None = None
    system: str | None = None
    security: float | None = None
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


def parse_world(eye: Eye) -> WorldSnapshot:
    """Hợp nhất toàn bộ perception vào một WorldSnapshot duy nhất."""
    snap = WorldSnapshot()

    # 1. Connection Lost & Modals (Ưu tiên số 1 để E-STOP)
    snap.connection_lost = eye.connection_lost()
    snap.message_boxes = eye.message_boxes()

    # 2. Docked & Location
    snap.docked = eye.is_docked()
    me = MissionEye(eye)
    loc = me.location()
    snap.station = loc.get("station")
    snap.system = loc.get("system")
    snap.security = loc.get("security")

    # 3. Ship State (khi ở ngoài không gian)
    if not snap.docked:
        snap.speed_mps = eye.speed_mps()
        snap.maneuver = eye.maneuver()
        snap.ship_health = eye.ship_health()
        sel = eye.selected_item()
        if sel:
            snap.selected_name = sel.get("name")
        snap.selected_buttons = eye.selected_item_buttons()

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
