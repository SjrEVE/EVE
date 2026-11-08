"""RATS DB — phân loại quái Abyss theo TÊN trong overview (nguồn: EVE UniWiki
Abyssal_Deadspace + Possible_rooms, dump 2026-11-07).

Dùng: overview trả về tên quái ("Snarecaster Tessella", "Striking Vila Damavik"...)
→ classify(name) → faction/hull/ewar/priority → lock_order() trả thứ tự lock.

Priority (số nhỏ = bắn trước):
  0 = SKIP (Vila Swarmer — không cần giết, gate vẫn mở)
  1 = WEB (giết trước nhất — bẻ tốc là chết)
  2 = NEUT (giết sớm nếu active tank/logi)
  3 = SCRAM + LOGI (scram giữ mình; logi kéo máu quái)
  4 = PAINTER/TD/DAMP (khó chịu nhưng chậm chết hơn web/neut)
  5 = BS DPS-race (Marshal/Thunderchild/Deepwatcher/Overmind/Karen) — có xử lý riêng
  6 = DPS dealer thường
"""
from __future__ import annotations

import re
from typing import Any

# ---------------- token → EWAR class ----------------
WEB = {"Tangling", "Snarecaster", "Warden", "Upholder", "Echo", "Arrester",
       "Entangler", "Entanglement", "Fisher", "Knight"}
NEUT = {"Firewatcher", "Sentinel", "Dissipator", "Nullcharge", "Starving",
        "Fury", "Drainer", "Smith"}
SCRAM = {"Anchoring", "Trapper", "Spearfisher", "Nullwarp"}
PAINT = {"Spotlighter", "Marker", "Swordspine", "Illuminator", "Torchbearer",
         "Harrowing", "Shining", "Ixion"}   # lưu ý: Harrowing Vedmak KHÔNG paint (ngoại lệ, xử riêng)
TDDAMP = {"Fogcaster", "Ghosting", "Blinding", "Medusa", "Obfuscator",
          "Gazedimmer", "Lookout", "Herald", "Confuser"}
LOGI = {"Fieldweaver", "Plateforger", "Preserver", "Priest", "Burst", "Renewing", "Rodiva"}

SKIP_TOKENS = {"Swarmer"}          # Vila Swarmer — bỏ qua
BS_TOKENS = {"Karybdis", "Overmind", "Marshal", "Thunderchild", "Deepwatcher", "Leshak"}

# Ramp rate %/cycle của disintegrator Triglavian (Gustav "All 18 Rooms" LJBCZ4fwxKA)
RAMP_PER_CYCLE = {"Vedmak": 4.0, "Damavik": 4.0, "Leshak": 4.0,
                  "Kikimora": 2.0, "Drekavac": 1.0, "Vila": 0.75}

# Quái KHÔNG ĐỔI TARGET (Gustav) — aggro lock. Multibox: dùng làm tank-magnet.
NO_TARGET_SWITCH = {"Kikimora", "Tessella", "Tessera", "Overmind", "Vila",
                    "Aegis", "Escort"}   # Aegis/Escort = Lucid frig

# faction theo token phe
FACTION_TOKENS = [
    ("Tessella", "RogueDrone"), ("Tessera", "RogueDrone"), ("Overmind", "RogueDrone"),
    ("Tyrannos", "Drifter"), ("Ephialtes", "Drifter"),
    ("Lucid", "Sleeper"),
    ("Damavik", "Triglavian"), ("Kikimora", "Triglavian"), ("Vedmak", "Triglavian"),
    ("Rodiva", "Triglavian"), ("Drekavac", "Triglavian"), ("Leshak", "Triglavian"),
    ("Devoted", "Sansha"),
    ("Pacifier", "CONCORD"), ("Enforcer", "CONCORD"), ("Marshal", "CONCORD"),
    ("Skybreaker", "EDENCOM"), ("Stormbringer", "EDENCOM"), ("Thunderchild", "EDENCOM"),
    ("Lucifer", "Angel"), ("Cynabal", "Angel"), ("Dramiel", "Angel"),
]

EWAR_RANK = {"web": 1, "neut": 2, "scram": 3, "logi": 3, "paint": 4, "td_damp": 4}

# Ngoại lệ đã biết từ wiki
EXCEPTIONS = {
    # Harrowing Vedmak: prefix thường = painter nhưng wiki ghi rõ nó KHÔNG paint
    "Harrowing Vedmak": {"ewar": [], "priority": 6, "note": "Harrowing Vedmak không paint (wiki)"},
}


def classify(name: str) -> dict[str, Any]:
    """Tên quái trong overview → phân loại. Không cần biết trước phe."""
    out: dict[str, Any] = {"raw": name, "faction": None, "hull": None,
                           "ewar": [], "priority": 6, "skip": False, "note": ""}
    if not name:
        return out
    if any(t in name for t in SKIP_TOKENS):
        out.update(skip=True, priority=0, faction="Triglavian", hull="Vila Swarmer",
                   note="Không cần giết — gate vẫn mở khi mothership chết")
        return out
    for tok, fac in FACTION_TOKENS:
        if tok in name:
            out["faction"] = fac
            break
    # hullTriglavian theo từ chứa
    for hull in ("Damavik", "Kikimora", "Vedmak", "Rodiva", "Drekavac", "Leshak",
                 "Tessella", "Tessera", "Cynabal", "Dramiel", "Ixion", "Fury",
                 "Echo", "Medusa", "Burst", "Swordspine", "Escort", "Aegis",
                 "Warden", "Firewatcher", "Preserver", "Watchman", "Upholder",
                 "Sentinel", "Deepwatcher", "Knight", "Hunter", "Fisher", "Priest",
                 "Trapper", "Smith", "Lookout", "Herald", "Torchbearer",
                 "Pacifier", "Enforcer", "Marshal", "Skybreaker", "Stormbringer",
                 "Thunderchild", "Tyrannos", "Overmind"):
        if hull in name:
            out["hull"] = hull
            break
    # EWAR tokens (subword match để bắt "Entanglem" vs "Entangler"...)
    for token, cls in [("Snarecaster", "web"), ("Warden", "web"), ("Upholder", "web"),
                       ("Tangling", "web"), ("Echo", "web"), ("Arrester", "web"),
                       ("Entangl", "web"), ("Fisher", "web"), ("Knight", "web"),
                       ("Firewatcher", "neut"), ("Sentinel", "neut"), ("Dissipator", "neut"),
                       ("Nullcharge", "neut"), ("Starving", "neut"), ("Fury", "neut"),
                       ("Drainer", "neut"), ("Smith", "neut"),
                       ("Anchoring", "scram"), ("Trapper", "scram"), ("Spearfisher", "scram"),
                       ("Nullwarp", "scram"),
                       ("Spotlighter", "paint"), ("Marker", "paint"), ("Swordspine", "paint"),
                       ("Illuminator", "paint"), ("Torchbearer", "paint"), ("Ixion", "paint"),
                       ("Fogcaster", "td_damp"), ("Ghosting", "td_damp"), ("Blinding", "td_damp"),
                       ("Medusa", "td_damp"), ("Obfuscator", "td_damp"), ("Gazedimmer", "td_damp"),
                       ("Lookout", "td_damp"), ("Herald", "td_damp"), ("Confuser", "td_damp"),
                       ("Fieldweaver", "logi"), ("Plateforger", "logi"), ("Preserver", "logi"),
                       ("Priest", "logi"), ("Burst", "logi"), ("Renewing", "logi"), ("Rodiva", "logi"),
                       ("Cynabal", "web"), ("Cynabal", "neut")]:  # wiki: Cynabal = web+neut (Angel)
        if token in name and cls not in out["ewar"]:
            out["ewar"].append(cls)
    # priority = min rank của các EWAR class, mặc định 6
    if out["ewar"]:
        out["priority"] = min(EWAR_RANK[c] for c in out["ewar"])
    # BS đặc biệt: DPS-race / xử riêng
    if "Karybdis" in name:
        out.update(priority=5, note="Karen: SPIRAL vào <30km (cheat sheet) — dưới ~10km nó không track nổi; "
                  "KHÔNG approach thẳng (alpha wrecking). Lưu ý: nguồn Goon nói herd về gate — cần verify in-game")
    elif "Overmind" in name:
        out.update(priority=5, note="Rogue Drone BS: đổi đạn theo tier — MÂU THUẪN nguồn: UniWiki (T1 Photic→T6 Endobenthic) "
                  "vs AbyssTracker (Photic/Twilit/Hadal=T0-3, Bathyic/Benthic/Endobenthic=T4-6). VERIFY in-game trước khi tin. "
                  "Web từ T5. Kinetic+Thermal dmg")
    elif "Marshal" in name:
        out.update(priority=5, note="CONCORD BS 427 DPS missile nhưng HP THẤP (cheat sheet) — giết nhanh để giảm incoming; "
                  "Attacker Marshal + EDENCOM tụ quanh 1 'commander' (Gustav)")
    elif "Thunderchild" in name:
        out.update(priority=5, note="EDENCOM alpha cao, Kinetic chủ đạo; vorton chain nếu đứng gần đồng đội nó")
    elif "Deepwatcher" in name:
        out.update(priority=5, note="Sleeper BS timeout-killer: orbit <10km để né, giết nhanh")
    elif "Leshak" in name:
        out.update(priority=5, note="Triglavian BS ramp 4%/cycle — càng đánh lâu càng đau, giết sớm; Firestorm +40% armor")
    # Tessera BC: damage + tracking cực nhưng optimal ngắn
    if "Tessera" in name:
        out["note"] = (out["note"] + " TESSERA BC: optimal ngắn — GIỮ >12km (cheat sheet).").strip()
    # ramp rate cho Triglavian
    for hull, rate in RAMP_PER_CYCLE.items():
        if hull in name and hull != "Vila":
            out["ramp_per_cycle"] = rate
            break
    else:
        if "Vila" in name:
            out["ramp_per_cycle"] = 0.75
    # Elite prefix tăng độ nguy hiểm (chỉ ghi chú, không đổi priority)
    if "Elite" in name:
        out["note"] = (out["note"] + " ELITE variant (dmg/tracking cao hơn).").strip()
    # ngoại lệ wiki
    exc = EXCEPTIONS.get(name) or EXCEPTIONS.get(re.sub(r"^\d+ x ", "", name))
    if exc:
        out.update(exc)
    return out


def lock_order(names: list[str]) -> list[dict[str, Any]]:
    """Trả list quái theo thứ tự nên lock/bắn. Skip đứng cuối (không lock)."""
    cls = [classify(n) for n in names]
    combat = [c for c in cls if not c["skip"]]
    skip = [c for c in cls if c["skip"]]
    # sort: priority, rồi hull nhỏ (frigate) trước BS lớn — giết con nhỏ trước khi logi kịp land
    def hull_rank(c: dict[str, Any]) -> int:
        hull = c.get("hull") or ""
        if any(h in hull for h in ("Damavik", "Tessella", "Dramiel", "Escort", "Aegis",
                                   "Fisher", "Trapper", "Smith", "Lookout", "Herald",
                                   "Torchbearer", "Firewatcher", "Warden", "Priest", "Pacifier")):
            return 0
        if any(h in hull for h in ("Kikimora", "Cynabal", "Ixion", "Fury", "Echo",
                                   "Medusa", "Burst", "Swordspine", "Watchman", "Upholder",
                                   "Sentinel", "Knight", "Hunter", "Enforcer",
                                   "Vedmak", "Rodiva", "Drekavac", "Tessera")):
            return 1
        return 2   # battleship
    combat.sort(key=lambda c: (c["priority"], hull_rank(c)))
    return combat + skip


# Damage type nên dùng theo weather (wiki "Damage to deal")
DAMAGE_BY_WEATHER = {
    "Dark": "Explosive/Thermal (Triglavian hole); không có resist hole — dùng đạn mạnh nhất fit",
    "Electrical": "EM (mình lẫn quái cùng ăn -EM)",
    "Exotic": "Kinetic",
    "Firestorm": "Thermal",
    "Gamma": "Explosive",
}
