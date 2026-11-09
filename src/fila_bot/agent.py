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
