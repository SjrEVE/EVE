"""Agent dialogue (M3 task 3.1) — doc offer + tim nut theo TEXT KHOP DUNG. READ-ONLY.

AgentDialogueWindow: Viir chi giu uiNode, KHONG parse nut (PUI 2703-2714).
Nut Accept/Decline/Complete CHUA ground tren Photon (G2/G7) -> chi tra toa do khi
thay label text khop DUNG trong chinh cua so agent; khong thay -> None (fail-closed).
"""
from __future__ import annotations

import re
from typing import Any

BUTTONS = {
    "request": ("request mission",),
    "accept": ("accept",),
    "decline": ("decline",),
    "delay": ("delay",),
    "complete": ("complete mission",),
    "close": ("close",),
}
_M3 = re.compile(r"([0-9][0-9.,]*)\s*m(?:3|\u00b3)", re.I)


def _clean(t: str) -> str:
    return re.sub(r"<[^>]*>", "", str(t)).strip()


def _vol(s: str) -> float | None:
    s = s.replace(",", "") if s.count(".") or s.count(",") > 1 else s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


class AgentEye:
    def __init__(self, eye: Any) -> None:
        self.eye = eye

    def window(self) -> dict[str, Any] | None:
        w = self.eye._find_by_type("AgentDialogueWindow", select_many=True) or []
        return w[0] if w else None

    def texts(self) -> list[str] | None:
        w = self.window()
        if w is None:
            return None
        out: list[str] = []
        for n in self.eye.walk(w):
            a = n.get("attrs") or {}
            t = a.get("_setText") or a.get("_text")
            if isinstance(t, str) and _clean(t) and _clean(t) not in out:
                out.append(_clean(t))
        return out

    def button_xy(self, key: str) -> tuple[int, int] | None:
        """Toa do nut theo text khop DUNG (khong substring: 'Accept' != 'Accepted')."""
        w = self.window()
        if w is None or key not in BUTTONS:
            return None
        want = BUTTONS[key]
        for n in self.eye.walk(w):
            a = n.get("attrs") or {}
            t = a.get("_setText") or a.get("_text")
            if isinstance(t, str) and _clean(t).lower() in want:
                return self.eye.abs_center(n)
        return None

    def read_offer(self) -> dict[str, Any] | None:
        tx = self.texts()
        if tx is None:
            return None
        blob = "\n".join(tx)
        low = blob.lower()
        mtype = ("courier" if "courier" in low or "cargo" in low and "deliver" in low
                 else "encounter" if "encounter" in low or "objective: destroy" in low
                 else None)
        m = _M3.search(blob)
        return {"type": mtype, "cargo_m3": _vol(m.group(1)) if m else None,
                "texts": tx, "buttons": {k: self.button_xy(k) for k in BUTTONS}}


# ---------------- G1: AgentsPanel trong station (GROUND 2026-11-09, TQ Photon) ----------------
# Fixture: tests/fixtures/ui_tree_agents_panel.json (Tunttaras IX - Moon 11, 3 agent Distribution)
# AgentEntry._name = ten agent; con: EveLabelMedium nameLabel ("Ten <color..>Level N</color>"),
# levelLabel (= division, vd "Distribution"), AgentConversationIcon _name=agentChatBtn (nut chat).
# Nhom kha dung: label header "Available to you" / "Not available to you" (khong co _name) —
# entry thuoc header gan nhat PHIA TREN no (so toa do y).
_LEVEL = re.compile(r"level\s*(\d)", re.I)
_HDR = {"available to you": True, "not available to you": False}


def agents_panel(eye: Any) -> list[dict[str, Any]] | None:
    """[{name, level, division, available, chat_xy}] ; None = khong thay AgentsPanel."""
    panels = eye._find_by_type("AgentsPanel", select_many=True) or []
    if not panels:
        return None
    panel = panels[0]
    headers: list[tuple[int, bool]] = []
    for n in eye.walk(panel):
        a = n.get("attrs") or {}
        t = _clean(a.get("_setText") or "").lower()
        if t in _HDR and a.get("_name") is None:
            xy = eye.abs_center(n)
            if xy:
                headers.append((xy[1], _HDR[t]))
    headers.sort()
    out: list[dict[str, Any]] = []
    for ent in eye.walk(panel):
        if ent.get("type") != "AgentEntry":
            continue
        a = ent.get("attrs") or {}
        rec: dict[str, Any] = {"name": a.get("_name"), "level": None, "division": None,
                               "available": None, "chat_xy": None}
        for n in eye.walk(ent):
            na = n.get("attrs") or {}
            nm = na.get("_name")
            if nm == "nameLabel":
                m = _LEVEL.search(_clean(na.get("_setText") or ""))
                rec["level"] = int(m.group(1)) if m else None
            elif nm == "levelLabel":
                rec["division"] = _clean(na.get("_setText") or "") or None
            elif n.get("type") == "AgentConversationIcon":
                rec["chat_xy"] = eye.abs_center(n)
        exy = eye.abs_center(ent)
        if exy and headers:
            above = [ok for y, ok in headers if y < exy[1]]
            rec["available"] = above[-1] if above else None
        out.append(rec)
    return out


def pick_agent(agents: list[dict[str, Any]] | None, division: str,
               max_level: int = 3) -> dict[str, Any] | None:
    """Agent kha dung dau tien dung division, level <= max_level, co nut chat."""
    for ag in agents or []:
        if (ag.get("available") is True and ag.get("chat_xy")
                and (ag.get("division") or "").lower() == division.lower()
                and ag.get("level") is not None and ag["level"] <= max_level):
            return ag
    return None


def accept_rule(offer: dict[str, Any] | None, cargo_free_m3: float | None,
                route_hisec: bool | None) -> tuple[str, str]:
    """('accept'|'decline'|'blocked', ly do). Thieu du kien -> blocked (khong doan)."""
    if offer is None:
        return "blocked", "khong thay AgentDialogueWindow"
    if offer.get("type") is None:
        return "blocked", "khong doc duoc loai mission (G2 chua ground)"
    if offer["type"] != "courier":
        return "decline", f"loai {offer['type']} — mode distribution chi nhan courier"
    if offer.get("cargo_m3") is None or cargo_free_m3 is None:
        return "blocked", "khong doc duoc cargo m3 hoac cho trong cargo"
    if offer["cargo_m3"] > cargo_free_m3:
        return "decline", f"cargo {offer['cargo_m3']} m3 > cho trong {cargo_free_m3} m3"
    if route_hisec is None:
        return "blocked", "chua doc duoc sec cac he tren route"
    if not route_hisec:
        return "decline", "route di qua he < 0.5"
    return "accept", "courier vua cargo, route hisec"
