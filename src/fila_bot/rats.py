"""RATS DB — phân loại quái Abyss theo TÊN trong overview (nguồn: EVE UniWiki
Abyssal_Deadspace + Possible_rooms, dump 2026-11-07; bản merge 2026-11-10 thêm
lớp chiến thuật T4-T6: HIGH_THREAT_DPS, anti-drone, resist-hole, split-fire).

Dùng: overview trả về tên quái ("Snarecaster Tessella", "Striking Vila Damavik"...)
→ classify(name) → faction/hull/ewar/priority → lock_order() trả thứ tự lock.

Priority (số nhỏ = bắn trước) — DB wiki, KHÔNG đổi (test + skill DB là chuẩn):
  0 = SKIP (Vila Swarmer — không cần giết, gate vẫn mở)
  1 = WEB (giết trước nhất — bẻ tốc là chết)
  2 = NEUT (giết sớm nếu active tank/logi)
  3 = SCRAM + LOGI (scram giữ mình; logi kéo máu quái)
  4 = PAINTER/TD/DAMP (khó chịu nhưng chậm chết hơn web/neut)
  5 = BS DPS-race (Marshal/Thunderchild/Deepwatcher/Overmind/Karen) — có xử lý riêng
  6 = DPS dealer thường

Lớp chiến thuật (chỉ áp khi lock_order(fit_type=...) != "default" — LIVE theo fit):
  - Scram thuần giảm ưu tiên khi chạy Afterburner (AB không bị scram ảnh hưởng)
  - HIGH_THREAT_DPS (Kikimora/Cynabal/Leshak ramp/Marshal drainer...) được nâng
  - Rogue Drone ưu tiên theo lỗ kháng: Spark=EM, Ember=Thermal, Strike=Kinetic, Blast=Explosive
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

SKIP_TOKENS = {"Swarmer",          # Vila Swarmer — bỏ qua
               "Bioadaptive Cache", "Biocombinative Cache",   # loot container — không phải quái
               "Extraction Node", "Extraction SubNode",
               "Transfer Conduit", "Origin Conduit"}           # gate — không phải quái
BS_TOKENS = {"Karybdis", "Overmind", "Marshal", "Thunderchild", "Deepwatcher", "Leshak"}

# Ramp rate %/cycle của disintegrator Triglavian (Gustav "All 18 Rooms" LJBCZ4fwxKA;
# khớp skill eve-abyss-mechanics: Vedmak/Damavik/Leshak 4%, Kikimora 2%, Drekavac 1%, Vila 0.75%)
RAMP_PER_CYCLE = {"Vedmak": 4.0, "Damavik": 4.0, "Leshak": 4.0,
                  "Kikimora": 2.0, "Drekavac": 1.0, "Vila": 0.75}

# Quái KHÔNG ĐỔI TARGET (Gustav) — aggro lock. Multibox: dùng làm tank-magnet.
NO_TARGET_SWITCH = {"Kikimora", "Tessella", "Tessera", "Overmind", "Vila",
                    "Aegis", "Escort"}   # Aegis/Escort = Lucid frig

# faction theo token phe (tên KHÔNG khoảng trắng — contract mission.py/test)
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

# ---------------- lớp chiến thuật T4-T6 (merge 2026-11-10) ----------------
# Rats chủ động đổi aggro sang player drone (yellow-box = đang bắn drone)
ANTI_DRONE_TOKENS = {"Tessera", "Sparkgrip", "Embergrip", "Strikegrip", "Blastgrip",
                     "Elite Lucifer", "Lancer", "Spearfisher", "Aegis", "Upholder",
                     "Anchoring Damavik", "Tangling Damavik"}

# DPS dealer chết người — phải giết sớm, không để bị xếp xuống priority 5-6
# (spool-up Leshak/Kikimora tích sát thương; Cynabal đuổi kịp mọi fit)
HIGH_THREAT_DPS = {
    "Elite Lucifer Cynabal": 1, "Lucifer Cynabal": 1,
    "Striking Kikimora": 2, "Kikimora": 2,
    "Devoted Knight": 2,
    "Drainer Marshal": 1, "Arrester Marshal": 2, "Attacker Marshal": 2,
    "Starving Leshak": 1, "Renewing Leshak": 2, "Blinding Leshak": 2,
    "Starving Vedmak": 1, "Harrowing Vedmak": 2,
    "Assault Enforcer": 3, "Drainer Enforcer": 2, "Devoted Hunter": 3,
}

# Prefix Rogue Drone → damage type (ưu tiên diệt theo lỗ kháng của fit)
ELEMENTAL_PREFIX_DAMAGE = {"Spark": "em", "Ember": "thermal",
                           "Strike": "kinetic", "Blast": "explosive"}

# Lỗ kháng tự nhiên theo phe/boss (chọn đạn/drone)
NATURAL_RESIST_HOLES = {
    "Triglavian": ("explosive", "thermal"),
    "Sansha": ("em", "thermal"),
    "Devoted Knight": ("em", "explosive"),
    "Angel": ("explosive", "kinetic"),
    "CONCORD": ("thermal", "kinetic", "em", "explosive"),
    "EDENCOM": ("thermal", "em"),
    "Twilit Abyssal Overmind": ("thermal", "explosive"),  # kháng Kinetic cao cả trong Exotic!
}

# optimal nguy hiểm của NPC (km) — dùng cho quyết định kite/orbit
OPTIMAL_KM = [("tessera", 15), ("kikimora", 25), ("vedmak", 25),
              ("devoted knight", 30), ("marshal", 65), ("karybdis", 45), ("overmind", 45)]


def _detect_faction(name: str) -> str | None:
    for tok, fac in FACTION_TOKENS:
        if tok in name:
            return fac
    return None


def _detect_elemental_damage(name: str) -> str | None:
    for prefix, dmg in ELEMENTAL_PREFIX_DAMAGE.items():
        if prefix.lower() in name.lower():
            return dmg
    if "Arrester Marshal" in name:
        return "explosive"
    if "Marshal" in name:
        return "thermal"
    if "Devoted" in name:
        return "em"
    if "Lucifer" in name:
        return "em"
    return None


def classify(name: str) -> dict[str, Any]:
    """Tên quái trong overview → phân loại. Không cần biết trước phe.

    Giữ 100% keys cũ (raw/faction/hull/ewar/priority/skip/note/ramp_per_cycle);
    thêm keys chiến thuật mới (name/is_bs/web/neut/.../anti_drone/optimal_km...).
    """
    out: dict[str, Any] = {"raw": name, "name": name, "faction": None, "hull": None,
                           "ewar": [], "priority": 6, "skip": False, "note": "",
                           "is_bs": False, "web": False, "neut": False, "scram": False,
                           "paint": False, "td_damp": False, "logi": False,
                           "no_switch": False, "anti_drone": False, "is_high_dps": False,
                           "damage_type": None, "optimal_km": 10, "ramp_rate": 0.0}
    if not name:
        return out
    low = name.lower()
    if any(t in name for t in SKIP_TOKENS):
        out.update(skip=True, priority=0, faction="Triglavian", hull="Vila Swarmer",
                   note="Không cần giết — gate vẫn mở khi mothership chết / container không khóa được")
        return out
    out["faction"] = _detect_faction(name)
    # hull theo từ chứa
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
            out[cls] = True
    # priority = min rank của các EWAR class, mặc định 6
    if out["ewar"]:
        out["priority"] = min(EWAR_RANK[c] for c in out["ewar"])
    # BS đặc biệt: DPS-race / xử riêng
    if "Karybdis" in name:
        out.update(priority=5, is_bs=True, note="Karen: SPIRAL vào <30km (cheat sheet) — dưới ~10km nó không track nổi; "
                  "KHÔNG approach thẳng (alpha wrecking). Lưu ý: nguồn Goon nói herd về gate — cần verify in-game")
    elif "Overmind" in name:
        out.update(priority=5, is_bs=True, note="Rogue Drone BS: đổi đạn theo tier — MÂU THUẪN nguồn: UniWiki (T1 Photic→T6 Endobenthic) "
                  "vs AbyssTracker (Photic/Twilit/Hadal=T0-3, Bathyic/Benthic/Endobenthic=T4-6). VERIFY in-game trước khi tin. "
                  "Web từ T5. Kinetic+Thermal dmg")
    elif "Marshal" in name:
        out.update(priority=5, is_bs=True, note="CONCORD BS 427 DPS missile nhưng HP THẤP (cheat sheet) — giết nhanh để giảm incoming; "
                  "Attacker Marshal + EDENCOM tụ quanh 1 'commander' (Gustav)")
    elif "Thunderchild" in name:
        out.update(priority=5, is_bs=True, note="EDENCOM alpha cao, Kinetic chủ đạo; vorton chain nếu đứng gần đồng đội nó")
    elif "Deepwatcher" in name:
        out.update(priority=5, is_bs=True, note="Sleeper BS timeout-killer: orbit <10km để né, giết nhanh")
    elif "Leshak" in name:
        out.update(priority=5, is_bs=True, note="Triglavian BS ramp 4%/cycle — càng đánh lâu càng đau, giết sớm; Firestorm +40% armor")
    # Tessera BC: damage + tracking cực nhưng optimal ngắn
    if "Tessera" in name:
        out["note"] = (out["note"] + " TESSERA BC: optimal ngắn — GIỮ >12km (cheat sheet).").strip()
    # ramp rate cho Triglavian
    for hull, rate in RAMP_PER_CYCLE.items():
        if hull in name and hull != "Vila":
            out["ramp_per_cycle"] = rate
            out["ramp_rate"] = rate
            break
    else:
        if "Vila" in name:
            out["ramp_per_cycle"] = 0.75
            out["ramp_rate"] = 0.75
    # Elite prefix tăng độ nguy hiểm (chỉ ghi chú, không đổi priority)
    if "Elite" in name:
        out["note"] = (out["note"] + " ELITE variant (dmg/tracking cao hơn).").strip()
    # ngoại lệ wiki
    exc = EXCEPTIONS.get(name) or EXCEPTIONS.get(re.sub(r"^\d+ x ", "", name))
    if exc:
        out.update(exc)
    # ---- fields chiến thuật mới ----
    out["no_switch"] = any(tok.lower() in low for tok in NO_TARGET_SWITCH)
    out["anti_drone"] = any(tok.lower() in low for tok in ANTI_DRONE_TOKENS)
    out["is_high_dps"] = any(tok.lower() in low for tok in HIGH_THREAT_DPS) \
        or "lance tessella" in low
    out["damage_type"] = _detect_elemental_damage(name)
    if not out["is_bs"]:
        out["is_bs"] = any(tok.lower() in low for tok in BS_TOKENS)
    for tok, km in OPTIMAL_KM:
        if tok in low:
            out["optimal_km"] = km
            break
    return out


def hull_rank(c: dict[str, Any]) -> int:
    """0 = frigate/drone, 1 = cruiser/BC/dessie, 2 = battleship (theo hull token)."""
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


def lock_order(names: list[str], fit_type: str = "default",
               resist_hole: str | None = None) -> list[dict[str, Any]]:
    """Trả list quái theo thứ tự nên lock/bắn. Skip đứng cuối (không lock).

    fit_type="default" (SIM/test): thứ tự wiki thuần (priority, hull_rank).
    fit_type tactical ("ab_cruiser"/"mwd_cruiser"/"ab_trio"/...): chỉnh theo meta LIVE —
      scram thuần giảm ưu tiên khi chạy AB, HIGH_THREAT_DPS nâng lên, drone đánh
      theo lỗ kháng (resist_hole), Lance Tessella (2x DPS needle) nâng nhẹ.
    """
    cls = [classify(n) for n in names]
    combat = [c for c in cls if not c["skip"]]
    skip = [c for c in cls if c["skip"]]
    tactical = fit_type != "default"

    def sort_key(c: dict[str, Any]) -> tuple[float, int, float, int]:
        prio = float(c["priority"])
        hr = hull_rank(c)
        name_l = c["raw"].lower()
        if tactical:
            # 1. AB fit không sợ scram thuần (chỉ sợ web/neut/scram gắn kèm)
            if "ab" in fit_type.lower() and c["ewar"] == ["scram"]:
                prio = 4.5
            # 2. nâng DPS dealer chết người trong tier của nó
            for tok, override in HIGH_THREAT_DPS.items():
                if tok.lower() in name_l:
                    prio = min(prio, override + 0.2)
                    break
            # 3. Enforcer trong room Marshal: giết con áp sát trước BS
            if "enforcer" in name_l and any("marshal" in n.lower() for n in names):
                hr = min(hr, 1)
            # 4. Rogue Drone trúng lỗ kháng → diệt trước
            if resist_hole and c.get("damage_type") == resist_hole.lower():
                prio -= 0.35
            # 5. Lance Tessella x2 DPS so với needle
            if "lance tessella" in name_l:
                prio -= 0.15
        # ramp cao → chết trước trong cùng (priority, hull) để bớt spool
        return (prio, hr, -float(c.get("ramp_rate", 0.0) or 0.0), names.index(c["raw"]))

    combat.sort(key=sort_key)
    return combat + skip


def split_fire_plan(names: list[str], has_drones: bool = True,
                    fit_type: str = "ab_cruiser",
                    resist_hole: str = "em") -> dict[str, Any]:
    """Kế hoạch tách hỏa lực cho cruiser có drone (Gila/Ishtar) hoặc trio.

    Room BS trâu không tự hồi liên kết (KAREN/OVERMIND) mà EWAR nguy hiểm đã sạch:
    drone cắn BS liên tục, súng/missile dọn frigate/cruiser gần — tiết kiệm 60-90s
    thời gian drone bay qua bay lại. Room có logi/Sleeper/Triglavian hồi nhau →
    focus fire 100% cùng một đích.
    """
    ordered = lock_order(names, fit_type=fit_type, resist_hole=resist_hole)
    if not ordered:
        return {"focus_fire": True, "primary_target": None, "drone_target": None,
                "weapon_target": None, "ordered_names": []}
    combat = [c for c in ordered if not c["skip"]]
    has_remote_rep = any(c["logi"] or c["faction"] in ("Sleeper", "Triglavian")
                         for c in combat)
    bs = [c for c in combat if c["is_bs"]]
    non_bs = [c for c in combat if not c["is_bs"]]
    critical_ewar = any(c["web"] or c["neut"] or c["paint"] for c in non_bs)
    primary = combat[0]["name"]
    if has_drones and bs and non_bs and not critical_ewar and not has_remote_rep:
        return {"focus_fire": False, "primary_target": primary,
                "drone_target": bs[0]["name"], "weapon_target": non_bs[0]["name"],
                "ordered_names": [c["name"] for c in ordered]}
    return {"focus_fire": True, "primary_target": primary, "drone_target": primary,
            "weapon_target": primary, "ordered_names": [c["name"] for c in ordered]}


# Damage type nên dùng theo weather (wiki "Damage to deal")
DAMAGE_BY_WEATHER = {
    "Dark": "Explosive/Thermal (Triglavian hole); không có resist hole — dùng đạn mạnh nhất fit",
    "Electrical": "EM (mình lẫn quái cùng ăn -EM)",
    "Exotic": "Kinetic",
    "Firestorm": "Thermal",
    "Gamma": "Explosive",
}
