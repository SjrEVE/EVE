"""Abyss Behavior Tree — cay uu tien sinh ton > hanh dong (port tu NEXT_GEN_TECH_ROADMAP.md §1).

Cau truc:
    par root
    ├── sel SAFETY (chay moi tick, uu tien cao nhat)
    │   ├── cond connection_lost -> act E-STOP
    │   ├── cond hp_low (hp < 0.30) -> act SURVIVAL (orbit max + overheat)
    │   ├── cond cap_low (cap < 0.15, co doc) -> act POWER_SAVE (tat MWD/web)
    │   └── cond drones_out_and_warping -> act RECALL_DRONES (Shift+R)
    └── sel MISSION (hanh dong chinh)
        ├── cond docked & co filament & chua stop -> act UNDOCK
        ├── cond phase TRAVEL_ENTRY -> act FILA
        ├── cond phase FILA_SPOOL -> act CONFIRM
        ├── cond phase ROOMn_FIGHT -> act FIGHT (lock EWAR -> dps)
        ├── cond phase ROOMn_CLEARED (room 1/2) -> act GATE
        ├── cond phase ROOM3_CLEARED -> act WARP_HOME
        └── cond phase WARP_HOME -> act DOCK
"""
from __future__ import annotations

from typing import Any

from .bt import Node, Status, act, cond, par, sel, seq


def build_abyss_tree() -> Node:
    # ---------------- SAFETY branch ----------------
    safety_estop = seq("ESTOP_seq", [
        cond("connection_lost", lambda ctx: (
            Status.SUCCESS if ctx.get("connection_lost") else Status.FAILURE)),
        act("estop", lambda ctx: (
            ctx["actions"].append({"do": "estop"}) or Status.SUCCESS)),
    ])

    safety_hp = seq("HP_low_seq", [
        cond("hp<0.30", lambda ctx: (
            Status.SUCCESS
            if isinstance(ctx.get("hp"), (int, float)) and ctx["hp"] < 0.30
            else Status.FAILURE)),
        act("survival", lambda ctx: (
            ctx["actions"].append({"do": "survival"}) or Status.SUCCESS)),
    ])

    safety_cap = seq("CAP_low_seq", [
        cond("cap<0.15", lambda ctx: (
            Status.SUCCESS
            if isinstance(ctx.get("cap"), (int, float)) and ctx["cap"] < 0.15
            else Status.FAILURE)),
        act("power_save", lambda ctx: (
            ctx["actions"].append({"do": "power_save"}) or Status.SUCCESS)),
    ])

    safety_drones = seq("DRONE_seq", [
        cond("drones_out & warping", lambda ctx: (
            Status.SUCCESS
            if ctx.get("drones_in_space", 0) > 0
            and ctx.get("maneuver") in ("warp", "jump")
            else Status.FAILURE)),
        act("recall_drones", lambda ctx: (
            ctx["actions"].append({"do": "drones_return"}) or Status.SUCCESS)),
    ])

    safety = sel("SAFETY", [safety_estop, safety_hp, safety_cap, safety_drones])

    # ---------------- MISSION branch ----------------
    def phase_is(p: str) -> Any:
        return lambda ctx: Status.SUCCESS if ctx.get("phase") == p else Status.FAILURE

    mission = sel("MISSION", [
        seq("UNDOCK_seq", [
            cond("docked", lambda ctx: Status.SUCCESS if ctx.get("docked") else Status.FAILURE),
            cond("filaments>0", lambda ctx: (
                Status.SUCCESS if ctx.get("filaments", 0) > 0 else Status.FAILURE)),
            act("undock", lambda ctx: (
                ctx["actions"].append({"do": "undock"}) or Status.SUCCESS)),
        ]),
        seq("FILA_seq", [
            cond("phase=TRAVEL_ENTRY", phase_is("TRAVEL_ENTRY")),
            act("fila", lambda ctx: (
                ctx["actions"].append({"do": "fila"}) or Status.SUCCESS)),
        ]),
        seq("CONFIRM_seq", [
            cond("phase=FILA_SPOOL", phase_is("FILA_SPOOL")),
            act("confirm", lambda ctx: (
                ctx["actions"].append({"do": "confirm"}) or Status.SUCCESS)),
        ]),
        seq("FIGHT_seq", [
            cond("phase=*_FIGHT", lambda ctx: (
                Status.SUCCESS if str(ctx.get("phase", "")).endswith("_FIGHT")
                else Status.FAILURE)),
            act("fight", lambda ctx: (
                ctx["actions"].append({"do": "fight"}) or Status.SUCCESS)),
        ]),
        seq("GATE_seq", [
            cond("phase=*_CLEARED_1_2", lambda ctx: (
                Status.SUCCESS if ctx.get("phase") in ("ROOM1_CLEARED", "ROOM2_CLEARED")
                else Status.FAILURE)),
            act("gate", lambda ctx: (
                ctx["actions"].append({"do": "gate"}) or Status.SUCCESS)),
        ]),
        seq("WARP_HOME_seq", [
            cond("phase=ROOM3_CLEARED", phase_is("ROOM3_CLEARED")),
            act("warp_home", lambda ctx: (
                ctx["actions"].append({"do": "warp_home"}) or Status.SUCCESS)),
        ]),
        seq("DOCK_seq", [
            cond("phase=WARP_HOME", phase_is("WARP_HOME")),
            act("dock", lambda ctx: (
                ctx["actions"].append({"do": "dock"}) or Status.SUCCESS)),
        ]),
    ])

    return par("ABYSS_ROOT", [safety, mission])


def tick_tree(tree: Node, world: dict[str, Any]) -> list[dict[str, Any]]:
    """Dung chinh: world dict (từ read_world / sim) -> danh sach actions."""
    ctx: dict[str, Any] = dict(world)
    ctx["actions"] = []
    tree.tick(ctx)
    return ctx["actions"]
