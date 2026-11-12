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
    "quit": ("quit mission",),
    "close": ("close",),
}
_M3 = re.compile(r"([0-9][0-9.,]*)\s*m(?:3|\u00b3)", re.I)
# G2 GROUND 2026-11-09 (fixture ui_tree_agent_offer.json): nut nam trong ButtonGroup,
# Button._name = AcceptMission_Button / DeclineMission_Button / DeferMission_Button.
# Catalog 42 dump (docs/UI_CATALOG.md): them CompleteMission_Button / QuitMission_Button /
# CloseAgentConversation_Button. Request CHUA thay -> chi fallback theo text (fail-closed).
BUTTON_NAMES = {
    "accept": ("AcceptMission_Button",),
    "decline": ("DeclineMission_Button",),
    "delay": ("DeferMission_Button",),
    "complete": ("CompleteMission_Button",),
    "quit": ("QuitMission_Button",),
    "close": ("CloseAgentConversation_Button",),
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

    def loaded(self) -> bool:
        """True = dialog da render noi dung (co Edit briefing/objective — catalog
        42 dump TQ: 16/16 AgentDialogueWindow load xong deu co 2 Edit).
        False = dang load (LoadingWheel — dump TQ 2026-11-10 16:02: 60 node,
        0 Edit, 0 Button) hoac cay rong bat thuong. Goi truoc khi tin offer."""
        w = self.window()
        if w is None:
            return False
        return any(n.get("type") == "Edit" for n in self.eye.walk(w))

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

        # Ground 11-11 tu dump TQ that (dumps/g2_offer_v3_165506.json va
        # dumps/g10_turnin_dialog.json) + CCP SDE build 3682781:
        #  - "Transport Objective" = courierMission that (agent Distribution).
        #  - "Bring Item Objective / Acquire these goods" = killMission co item
        #    objective (agent Security L1, title "Cargo Delivery").
        # Cam: KHONG duoc suy "courier" tu cap tu ("cargo" + "deliver") hay title.
        # Truoc day chinh cap tu nay bien Cargo Delivery thanh courier -> bi block
        # TRUOC ca nut Accept (docs/MISSION_RESEARCH_DEEP_2026-11-11.md P0).
        from .missions_db import template_kind  # local: tranh vong import
        kind = template_kind(title)
        has_transport = "transport objective" in low or "courier" in low
        has_item = ("bring item objective" in low or "acquire these goods" in low
                    or kind == "kill_item" or (item is not None and kind == "kill"))
        # Ground LIVE 11-11 (agent Inikko Samanuni, "What's in a Name - Change of
        # Address"): objective text "Give the diplomats enough time to evacuate.
        # Engage any hostiles. Location 0.9 Hirtamon". Day la bang chung duong tinh
        # mission co combat objective -> duoc phep di chuyen, NHUNG khong cap quyen
        # ban (van can faction ID + title trong catalog, xem authorize_security_targets).
        # Dung cum tu DAY DU, khong dung substring ngan de tranh khop oan infix.
        has_combat = any(phrase in low for phrase in (
            "engage any hostiles", "destroy all hostile", "eliminate the hostile",
            "destroy the hostile"))
        objective_kind = ("transport" if has_transport and not has_item
                          else "item" if has_item else "combat" if has_combat else None)
        # Ground LIVE 11-11 (client TQ): "Objective Destroy the Gallente Broadcast
        # Tower. Location 0.9 New Caldari" va SelectedItemWnd nameLabel "Gallente
        # Broadcast Tower". Day la TEN structure/site that, KHONG phai generic
        # "Celestial Beacon" (Derelict Ruins). Chi dung de loc overview, khong de warp mu.
        msite = re.search(r"Objective\s+Destroy (?:the )?([^.]+)\.", blob)
        site_hint = msite.group(1).strip() if msite else None
        if has_transport and not has_item:
            mtype = "courier"
        elif has_item or "encounter" in low or "destroy" in low:
            mtype = "encounter"
        else:
            mtype = None
        return {"type": mtype, "objective_kind": objective_kind, "template_kind": kind,
                "site_hint": site_hint,
                "title": title, "chain": chain,
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


def mission_location_link(eye: Any) -> tuple[int, int] | None:
    """Link toa do "Location <sec> <system>" trong objective_browser.

    Ground 11-11 tu dump LIVE `ui_tree_e2e_06_live_cannot_complete.json`:
    htmlstr co "Location 0.9 Hirtamon"; Link nam trong `Cell tablecell 0-3` cua
    VirtualTable dong Location, tai (670, 352). Cac Link khac nam o `inlines`
    (tieu de / objective), KHONG phai link toa do. Chi lay Link nam trong Cell.
    Tra None khi khong thay objective_browser, khong co chu 'Location', hoac
    khong co Link trong Cell (fail-closed, khong doan toa do).
    """
    wins = eye._find_by_type("AgentDialogueWindow", select_many=True) or []
    if not wins:
        return None
    obj = None
    for n in eye.walk(wins[0]):
        if n.get("type") == "Edit" and (n.get("attrs") or {}).get("_name") == "objective_browser":
            obj = n
            break
    if obj is None:
        return None
    sr = (obj.get("attrs") or {}).get("_sr")
    html = sr.get("htmlstr", "") if isinstance(sr, dict) else ""
    if "Location" not in html:
        return None
    candidates: list[tuple[int, int]] = []
    for cell in eye.walk(obj):
        if cell.get("type") != "Cell":
            continue
        for n in eye.walk(cell):
            if n.get("type") == "Link":
                xy = eye.abs_center(n)
                if xy:
                    candidates.append(xy)
    if not candidates:
        return None
    return min(candidates, key=lambda c: (c[1], c[0]))


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
