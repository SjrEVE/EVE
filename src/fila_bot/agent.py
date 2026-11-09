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
# G2 GROUND 2026-11-09 (fixture ui_tree_agent_offer.json): nut nam trong ButtonGroup,
# Button._name = AcceptMission_Button / DeclineMission_Button / DeferMission_Button.
# Complete/Request CHUA thay tren client -> chi fallback theo text (fail-closed).
BUTTON_NAMES = {
    "accept": ("AcceptMission_Button",),
    "decline": ("DeclineMission_Button",),
    "delay": ("DeferMission_Button",),
}
# DLL thay ky tu ngoai ASCII bang ' ' -> 'm³' thanh 'm ' : "1 x Encoded Data Chip (0.1 m )"
_CARGO = re.compile(r"Cargo\s+(\d+)\s*x\s+(.+?)\s*\(\s*([0-9][0-9.,]*)\s*m", re.I)
_TITLE = re.compile(r"^(.+?)\s+Objectives\s+The following", re.I)
_CHAIN = re.compile(r"\((\d+)\s+of\s+(\d+)\)")
_ISK = re.compile(r"([0-9][0-9,]*)\s*ISK\b")
_SEC_NAME = re.compile(r"^(-?\d\.\d)\s+(.+)$")


def _loc(blob: str, start: str, ends: tuple[str, ...]) -> dict[str, Any] | None:
    """'Pickup Location 0.8 Nourvukaiken VI - ... Drop-off Location' -> {sec, name}."""
    i = blob.find(start)
    if i < 0:
        return None
    rest = blob[i + len(start):]
    cut = min([rest.find(e) for e in ends if rest.find(e) >= 0] or [len(rest)])
    seg = rest[:cut].strip()
    m = _SEC_NAME.match(seg)
    if not m:
        return {"sec": None, "name": seg or None}
    return {"sec": float(m.group(1)), "name": m.group(2).strip()}


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
        """Text trong cua so agent: label (_setText/_text) + noi dung HTML
        (SE_TextlineCore._sr.htmlstr — DLL 2c19958 da bo tag, ground 2026-11-09)."""
        w = self.window()
        if w is None:
            return None
        out: list[str] = []
        for n in self.eye.walk(w):
            a = n.get("attrs") or {}
            cands = [a.get("_setText"), a.get("_text")]
            sr = a.get("_sr")
            if isinstance(sr, dict):
                cands.append(sr.get("htmlstr"))
            for t in cands:
                if not isinstance(t, str):
                    continue
                c = re.sub(r"\s+", " ", _clean(t).replace("&nbsp;", " ")).strip()
                if c and c not in out:
                    out.append(c)
        return out

    def button_xy(self, key: str) -> tuple[int, int] | None:
        """Toa do nut: uu tien Button._name that (G2 ground), roi text khop DUNG
        (khong substring: 'Accept' != 'Accepted'). Chi trong cua so agent."""
        w = self.window()
        if w is None or key not in BUTTONS:
            return None
        names = BUTTON_NAMES.get(key, ())
        for n in self.eye.walk(w):
            if (n.get("attrs") or {}).get("_name") in names:
                return self.eye.abs_center(n)
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
        blob = " ".join(tx)
        low = blob.lower()
        mtype = ("courier" if ("transport objective" in low or "courier" in low
                               or ("cargo" in low and "deliver" in low))
                 else "encounter" if ("encounter" in low or "objective: destroy" in low
                                      or "destroy" in low and "objectives" in low)
                 else None)
        cargo_m3 = item = qty = None
        mc = _CARGO.search(blob)
        if mc:
            qty, item, cargo_m3 = int(mc.group(1)), mc.group(2).strip(), _vol(mc.group(3))
        else:
            m = _M3.search(blob)
            cargo_m3 = _vol(m.group(1)) if m else None
        title = chain = None
        for t in tx:
            mt = _TITLE.match(t)
            if mt:
                title = mt.group(1).strip()
                mch = _CHAIN.search(title)
                chain = (int(mch.group(1)), int(mch.group(2))) if mch else None
                break
        return {"type": mtype, "title": title, "chain": chain,
                "cargo_m3": cargo_m3, "cargo_item": item, "cargo_qty": qty,
                "pickup": _loc(blob, "Pickup Location", ("Drop-off Location",)),
                "dropoff": _loc(blob, "Drop-off Location", ("Cargo", "Rewards")),
                "isk": [int(x.replace(",", "")) for x in _ISK.findall(blob)],
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


# ---------------- G5: link Pickup/Drop-off trong objective (GROUND 2026-11-09) ----------------
# Fixture: tests/fixtures/ui_tree_pickup_menu.json. Link (_name='textlink') KHONG co text;
# text chi o Edit(objective_browser)._sr.htmlstr. Cau truc that:
#   Edit objective_browser > ... > VirtualTable > Cell 'tablecell R-C' > ... > Link
#   R=0 -> Pickup (ten wrap 3 dong = 3 Link), R=1 -> Drop-off (2 Link).
# Right-click Link dau cua row -> menu 'Set Destination' (verify bang InfoPanelRoute doi ten).
_CELL = re.compile(r"^tablecell\s+(\d+)-(\d+)$")


def location_links(eye: Any) -> dict[str, tuple[int, int]] | None:
    """{'pickup': xy, 'dropoff': xy} — toa do Link dau tien cua moi dia diem.
    Fail-closed (None) neu: khong co objective_browser, htmlstr khong co Pickup truoc
    Drop-off, hoac bang link khong dung 2 hang."""
    w = eye._find_by_type("AgentDialogueWindow", select_many=True) or []
    if not w:
        return None
    obj = None
    for n in eye.walk(w[0]):
        if n.get("type") == "Edit" and (n.get("attrs") or {}).get("_name") == "objective_browser":
            obj = n
            break
    if obj is None:
        return None
    sr = (obj.get("attrs") or {}).get("_sr")
    hs = sr.get("htmlstr", "") if isinstance(sr, dict) else ""
    ip, idr = hs.find("Pickup Location"), hs.find("Drop-off Location")
    if ip < 0 or idr < 0 or ip > idr:
        return None
    rows: dict[int, list[tuple[int, int]]] = {}

    def visit(n: dict[str, Any], row: int | None) -> None:
        if n.get("type") == "Cell":
            m = _CELL.match(str((n.get("attrs") or {}).get("_name") or ""))
            if m:
                row = int(m.group(1))
        if n.get("type") == "Link" and row is not None:
            rows.setdefault(row, []).append(eye.abs_center(n))
        for c in n.get("children") or []:
            visit(c, row)

    visit(obj, None)
    if sorted(rows) != [0, 1]:
        return None
    first = {r: min(v, key=lambda c: (c[1], c[0])) for r, v in rows.items()}
    if first[0][1] >= first[1][1]:      # pickup phai nam tren drop-off
        return None
    return {"pickup": first[0], "dropoff": first[1]}


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
