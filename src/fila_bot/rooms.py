"""ROOM PLAYBOOKS — ma trận room × weather → entry move + kill order + loot plan
+ hazard navigation (cloud/pylon), ROOM_TACTICS theo fit, bait gimmick.

Nguồn: minmatar.org Nergal/Retri/Deacon trio guide, Goon wiki per-room notes,
BushidoMaru room guide (Marshal/Leshak/Karen), Four Ohm T4 video (grace period),
eveworkbench Cerberus notes, UniWiki loot FAQ, abysstracker run data (2026-11-07);
merge 2026-11-10 thêm CLOUD_EFFECTS/PYLON_EFFECTS/evaluate_hazards (UniWiki).

Bot dùng: detect_room(names) → playbook → entry_move + kill_order(names, weather).
Contract test: ENTRY_MOVES đủ 12 kind, KILL_ORDERS KAREN[0] có "web" /
MARSHAL[0]=="Drainer Marshal" / LESHAK[0]=="Starving", WEATHER_NOTES theo ROOM,
loot_plan trả {"cache","nodes","reason"}, GATE_TRANSIT["grace_s"], EXIT["invul_s"].
"""
from __future__ import annotations
from typing import Any

# ---------------------------------------------------------------------------
# Room Recognition Signatures
# ---------------------------------------------------------------------------

ROOM_KINDS: dict[str, list[str]] = {
    "KIKI_SWARM": ["Striking Kikimora", "Ghosting Kikimora", "Tangling Kikimora",
                   "Kikimora", "Drekavac", "Damavik", "Rodiva"],
    "VEDMAK": ["Harrowing Vedmak", "Starving Vedmak", "Harrowing Vila Vedmak", "Vedmak"],
    "LESHAK": ["Leshak", "Striking Leshak", "Starving Leshak", "Renewing Leshak",
               "Blinding Leshak", "Tangling Leshak", "Warding Leshak"],
    "OVERMIND": ["Abyssal Overmind", "Photic Abyssal Overmind", "Twilit Abyssal Overmind",
                 "Bathyic Abyssal Overmind", "Hadal Abyssal Overmind",
                 "Benthic Abyssal Overmind", "Endobenthic Abyssal Overmind"],
    "TESSERA": ["Tessera", "Sparkgrip Tessera", "Embergrip Tessera",
                "Strikegrip Tessera", "Blastgrip Tessera", "Tessella"],
    "DEEPWATCHER": ["Lucid Deepwatcher", "Deepwatcher"],
    "KAREN": ["Karybdis Tyrannos", "Karybdis"],
    "SCYLLA": ["Scylla Tyrannos", "Ephialtes", "Lucid Watchman", "Lucid Sentinel",
               "Lucid Upholder"],
    "MARSHAL": ["Marshal Disparu Troop", "Attacker Marshal", "Arrester Marshal",
                "Drainer Marshal", "Marker Marshal", "Thunderchild Disparu Troop",
                "Enforcer", "Pacifier", "Skybreaker", "Stormbringer"],
    "SANSHA": ["Devoted Knight", "Devoted Hunter", "Devoted Smith", "Devoted Fisher",
               "Priest", "Trapper", "Lookout", "Herald", "Torchbearer"],
    "ANGEL": ["Elite Lucifer Cynabal", "Lucifer Cynabal", "Lucifer Ixion",
              "Lucifer Dramiel", "Cynabal", "Dramiel", "Ixion", "Fury", "Echo",
              "Medusa", "Burst", "Swordspine"],
}

# Thứ tự nhận diện: BS/đặc trưng room trước, swarm chung sau
_PRECEDENCE = ["KAREN", "OVERMIND", "LESHAK", "MARSHAL", "DEEPWATCHER", "TESSERA",
               "VEDMAK", "ANGEL", "SANSHA", "SCYLLA", "KIKI_SWARM"]


def detect_room(names: list[str]) -> str:
    """Tên quái trong room → room kind (ưu tiên BS/room đặc trưng)."""
    if not names:
        return "UNKNOWN"
    joined = " | ".join(names).lower()
    for kind in _PRECEDENCE:
        if any(tok.lower() in joined for tok in ROOM_KINDS.get(kind, [])):
            return kind
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Entry moves — giây 0–5 của room (nguồn: per-room guides)
# ---------------------------------------------------------------------------

ENTRY_MOVES: dict[str, str] = {
    "KIKI_SWARM": "KITE — burn CHÉO khỏi spawn, giữ range >20km (kiki 2%/cycle ramp, sig nhỏ khó bắn khi bay)",
    "VEDMAK":     "APPROACH CACHE — orbit cache giữ vị trí trung tâm, trig sẽ lao vào (no-switch) → bắn con tới gần nhất",
    "LESHAK":     "APPROACH LESHAK ASAP — chúng spawn HP thấp + starburst chạy tách ra; lợi dụng grace drift để sát; KHÔNG cho starburst (theo hướng 1 con để kéo cả nhóm)",
    "OVERMIND":   "APPROACH CACHE — bật prop+hardener, ĐỢI aggro rồi mới drop drone; orbit BS 500m khi tới gần (under guns); tránh Blue Cloud + Tracking Pylon",
    "TESSERA":    "GIỮ >12km (kite 22km với Grip Tessera T5+) — Tessera tracking cực nhưng optimal ngắn; kite tròn quanh cache; yellow-box = nó đổi bắn drone → recall ngay",
    "DEEPWATCHER": "LOOT TRƯỚC (loot-n-first) rồi orbit <10km MWD-off — missile Kin/Exp application tệ ở close; room dễ, 3–5'",
    "KAREN":      "BAY CHÉO 45° SPIRAL vào <30km (đích <10km) — KHÔNG orbit cache/gate khi Karen sống (bị đánh đứng); KHÔNG để Karen sống cuối (self-rep shield); tránh Blue Cloud + Tracking Pylon",
    "SCYLLA":     "KITE — Scylla cruisers EWAR nhiều; giết theo EWAR priority, dùng TYPE column phân loại",
    "MARSHAL":    "BAY XA NGAY — Marshals neutron range khủng; giữ 60km (DLA) / 50km không DLA; kill Drainer Marshal ĐẦU TIÊN; cruiser kite 60-65km trừ khi bị Enforcer áp sát",
    "SANSHA":     "KITE RỘNG — Sansha chậm hơn mình, nguy hiểm sát; orbit xa >25km (Knight giữ 12-14km ngoài web), Knight orbit 500 quá close để web không bắt",
    "ANGEL":      "KITE + RESIST EM — Angel nhanh nhất abyss, Cynabal web+neut; giữ transversal, đừng speed-tank T4+ (web đứng im)",
    "UNKNOWN":    "BURN CHÉO KHỎI SPAWN (mặc định an toàn) + tactical overlay, assess rồi quyết",
}

# ---------------------------------------------------------------------------
# Kill orders per room (tên class → thứ tự; EWAR rank của rats.py vẫn dùng chung)
# Nguồn: minmatar trio guide + goon + BushidoMaru + eveworkback notes
# ---------------------------------------------------------------------------

KILL_ORDERS: dict[str, list[str]] = {
    "KIKI_SWARM":  ["Tangling", "Starving", "Ghosting", "Striking", "Damavik", "Kikimora"],
    "VEDMAK":      ["Tangling", "Starving", "Ghosting", "Renewing Rodiva", "Damavik", "Vedmak"],
    "LESHAK":      ["Starving", "Blinding", "Tangling", "Renewing", "Striking"],
    "OVERMIND":    ["Tangling", "Starving", "Snarecaster", "Fieldweaver", "Tessella", "Overmind"],
    "TESSERA":     ["Snarecaster", "Fieldweaver", "Spotlighter", "lance", "needle", "Tessera"],
    "DEEPWATCHER": ["burn-to-you frigs", "Upholder", "Sentinel", "Watchman", "Deepwatcher"],
    "KAREN":       ["Tangling/Echo/Entanglement (web)", "Dissipator/Fury/Nullcharge (neut)",
                    "Spearfisher/Trapper (scram)", "Lancer/Escort escorts", "Karybdis"],
    "SCYLLA":      ["Entanglement (web)", "Nullcharge (neut)", "Nullwarp (scram)",
                    "Confuser", "Illuminator", "Scylla"],
    "MARSHAL":     ["Drainer Marshal", "Attacker Marshal", "Marshal khác", "Thunderchild",
                    "Stormbringer", "Skybreaker", "Pacifier"],
    "SANSHA":      ["Fisher", "Trapper", "Smith", "Knight", "Priest", "Hunter",
                    "Torchbearer", "Herald", "Lookout"],
    "ANGEL":       ["Echo", "Cynabal", "Elite Cynabal", "Fury", "Swordspine", "Ixion",
                    "Medusa", "Dramiel", "Burst"],
    "UNKNOWN":     ["web", "neut", "scram", "logi", "paint", "td_damp", "rest"],
}

# Ghi chú kill-order chi tiết hơn (merge 2026-11-10) — bổ sung cho KILL_ORDERS,
# gồm cả mồi nhử AI: giữ 1 Ephialtes Lancer / needle Tessella cuối cùng kéo Karen/Overmind lại gần.
KILL_ORDERS_DETAILED: dict[str, list[str]] = {
    "KAREN": ["Scylla Tyrannos (Nullcharge/Entanglement)", "Ephialtes Dissipator/Entangler/Illuminator",
              "Karybdis Tyrannos", "Ephialtes Lancer (GIỮ 1 con sống làm mồi orbit — Karen bám theo Lancer)"],
    "OVERMIND": ["Snarecaster Tessella", "Spotlighter Tessella", "Fieldweaver/Plateforger Tessella",
                 "Fogcaster Tessella", "Abyssal Overmind", "needle Tessella (GIỮ 1 con làm mồi orbit)"],
    "KIKI_SWARM": ["Starving Damavik", "Tangling Damavik", "Striking/Ghosting Kikimora",
                   "Renewing Rodiva", "Striking/Shining Drekavac"],
    "TESSERA": ["Snarecaster Tessella", "Plateforger/Fieldweaver Tessella",
                "Sparkgrip/Blastgrip/Strikegrip (theo lỗ kháng fit)", "Embergrip Tessera"],
}

# ---------------------------------------------------------------------------
# Weather × room — hiệu chỉnh chiến thuật (Boss: "weather cũng khác nhau xử lý khác nhau")
# ---------------------------------------------------------------------------

WEATHER_NOTES: dict[str, dict[str, str]] = {
    "LESHAK": {
        "Firestorm": "NGUY HIỂM NHẤT: Leshak +40% armor + Firestorm +50% armor nữa → TTK nổ gấp 3; cân nhắc chain gate sớm",
        "Electrical": "EM hole cho Triglavian → đạn EM/súng EM ăn; cap regen x2 phục vụ active tank",
    },
    "DEEPWATCHER": {
        "Firestorm": "Deepwatcher armor 65% (thay vì 50%) → timeout risk tăng; bỏ node, orbit bắn liền",
        "Gamma": "Shield HP +50% cho BS nữa → timeout risk tăng",
    },
    "MARSHAL": {
        "*": "Toàn explosive — giữ speed MAX tới khi room checked; không kite bằng angular (missile)",
    },
    "ANGEL": {
        "Electrical": "XẤU NHẤT: Angel damage EM/Exp + weather phá EM resist của mình → hardener EM bắt buộc",
        "Dark": "Turret optimal −50/70% cả Cynabal → chúng miss nhiều; đòn của mình cũng vậy → missile fit lợi",
    },
    "KAREN": {
        "Dark": "Tachyon cloud phổ biến — tuyệt đối không MWD vào cloud; spiral cẩn thận",
        "Gamma": "Karen shield HP +50% → room dài hơn; có thể bỏ cache room này nếu timer ngặt",
    },
    "OVERMIND": {
        "Gamma": "Overmind shield +50% — timeout killer; đổi đạn Exp/Therm đúng tier",
    },
    "VEDMAK": {
        "Firestorm": "Trig +40% armor + Firestorm +50% → Vedmak timeout risk; kill Damavik trước để giảm ramp DPS",
    },
}

# Cơ chế weather thuần (merge 2026-11-10) — penalty/bonus theo wiki, hợp nhất
# với WEATHER_NOTES (theo room) ở trên: key = tên weather.
WEATHER_MECHANICS: dict[str, dict[str, str]] = {
    "Electrical": {"penalty": "-30/50/70% EM resist", "bonus": "-50% cap recharge time",
                   "note": "active tank/cap-heavy fit lợi; chú ý lỗ EM ở Sansha/Angel/Spark Tessera"},
    "Exotic": {"penalty": "-30/50/70% Kinetic resist", "bonus": "+50% scan res",
               "note": "đạn/drone Kinetic; NGOẠI LỆ Twilit Overmind kháng Kinetic cao → xài Thermal"},
    "Firestorm": {"penalty": "-30/50/70% Thermal resist", "bonus": "+50% armor HP",
                  "note": "DPS-check gắt nhất: Leshak/Karen/Overmind dày thêm; Trig đánh Thermal đau hơn"},
    "Gamma": {"penalty": "-30/50/70% Explosive resist", "bonus": "+50% shield HP",
              "note": "buffer shield fit lợi; Arrester Marshal + Angel đánh Explosive"},
    "Dark": {"penalty": "-30/50/70% turret optimal+falloff (CẢ DRONE TURRET)", "bonus": "+50% max velocity",
             "note": "dùng missile; Cynabal vẫn đuổi kịp; coi chừng Tachyon Cloud văng biên đỏ"},
}

# ---------------------------------------------------------------------------
# LOOT — giá trị thật (abysstracker runs 2026) + policy
# ---------------------------------------------------------------------------

LOOT_VALUES: dict[str, dict[str, Any]] = {
    "Triglavian Survey Database": {"price_isk": 100_000, "sell": "NPC buy order (unlimited, cố định)",
                                   "drop_rate": 0.98, "note": "red loot — ISK token"},
    "Crystalline Isogen-10":      {"price_isk": 47_000,  "sell": "market Jita/Amarr",
                                   "drop_rate": 0.85, "note": "biến động — check giá trước"},
    "Zero-Point Condensate":      {"price_isk": 36_000,  "sell": "market",
                                   "drop_rate": 0.60, "note": "khối lượng lớn — cân cargohold"},
    "Filament (cùng tier)":       {"price_isk": 8_000_000, "sell": "market", "drop_rate": 0.14,
                                   "note": "tier cao giá cao hơn; T5 ~17M"},
    "Mutaplasmid":                {"price_isk": 0, "sell": "market lottery", "drop_rate": 0.03,
                                   "note": "rare, giá 0–2.8B"},
}

# Tỷ trọng giá trị theo container (merge 2026-11-10) — cache chứa ~80-85% giá trị
LOOT_PRIORITY: dict[str, dict[str, Any]] = {
    "Triglavian Bioadaptive Cache":    {"priority": 1, "share_of_value": 0.80, "always_drop": True},
    "Triglavian Biocombinative Cache": {"priority": 1, "share_of_value": 0.85, "always_drop": True},
    "Triglavian Extraction Node":      {"priority": 2, "share_of_value": 0.15, "always_drop": False},
    "Triglavian Extraction SubNode":   {"priority": 3, "share_of_value": 0.05, "always_drop": False},
}

CACHE_HP = 300            # 1 đạn là nổ
NODE_LOOT_POOL = ["Triglavian Survey Database", "Zero-Point Condensate",
                  "Crystalline Isogen-10", "Mutaplasmids", "Triglavian BPCs"]


def loot_plan(room_n: int, timer_left_s: int, cache_dist_m: int,
              nodes_dist_m: list[int], run_avg_min: int = 12) -> dict[str, Any]:
    """Quyết định loot theo UniWiki FAQ + reddit lessons:
    - cache: loot nếu thuận đường (≤15km) hoặc timer dư (>240s)
    - room 1 với run trung bình ≥15': KHÔNG loot node kỹ (đừng tham đầu trận)
    - node: chỉ khi timer dư (>420s) + gần đường (≤12km)
    - panic (timer < (3-room)*180+90) + cache >18km: bỏ hết, burn gate
    """
    plan: dict[str, Any] = {"cache": False, "nodes": [], "reason": "",
                            "take_cache": False, "emergency_burn_gate": False}
    avg_run_s = run_avg_min * 60
    panic_threshold_s = max(90, (3 - room_n) * 180 + 90)
    emergency = timer_left_s < panic_threshold_s and cache_dist_m > 18000
    plan["emergency_burn_gate"] = emergency
    if emergency:
        plan["reason"] += "PANIC: timer ngặt + cache xa — bỏ hết loot, burn gate ngay; "
        return plan
    if cache_dist_m <= 15000 or timer_left_s > 240:
        plan["cache"] = True
        plan["take_cache"] = True
        plan["reason"] += "cache: phá (300HP) + loot; "
    else:
        plan["reason"] += "cache: SKIP (xa gate + timer ngặt); "
    # room 1 với run dài: đừng kỹ
    if room_n == 1 and avg_run_s >= 900:
        plan["nodes"] = []
        plan["reason"] += "room1: bỏ node (run dài — đừng tham đầu trận); "
        return plan
    for i, d in enumerate(nodes_dist_m):
        if timer_left_s > 420 and d <= 12000:
            plan["nodes"].append(i)
    if plan["nodes"]:
        plan["reason"] += f"nodes {plan['nodes']}: loot (timer dư >7' + gần đường)"
    else:
        plan["reason"] += "nodes: bỏ (timer/ngoài đường)"
    return plan


# ---------------------------------------------------------------------------
# Gate/exit procedure (nguồn: Timers wiki + Four Ohm + forum gank counter)
# ---------------------------------------------------------------------------

GATE_TRANSIT: dict[str, Any] = {
    "grace_s": 18,      # 15–20s: KHÔNG ra lệnh/kích module → rats không aggro
    "keep_prop_on": True,   # giữ prop mod qua gate — nó giữ cycle + auto-drift tới conduit
    "recall_drones_before_activate": True,   # merge 2026-11-10: DEATH #3 — drone ngoài = mất
    "reset_reactive_hardener": True,         # đổi resist theo phe room mới
    "note": "drift của prop mod không phá grace — dùng 18s drift để vào sâu miễn phí",
}

EXIT_PROCEDURE: dict[str, Any] = {
    "invul_s": 60,      # invul khi exit abyss nếu không move (transfer cargo được)
    "invuln_window_s": 60,
    "wait_trace_despawn_s": 35,
    "check_dscan_and_overview": True,
    "steps": ["Xuất hiện → KHÔNG MOVE (giữ invul 60s)",
              "Đợi trace despawn 30–45s",
              "Transfer loot nếu có Orca/alt",
              "Hết invul → warp off ngay; ganker thường camp exit + drop depot chặn filament tiếp theo"],
    "danger": "Abyssal gankers camp trace — bắt window 60s invul để loot/transfer rồi warp",
}

# ---------------------------------------------------------------------------
# Hazard matrix (merge 2026-11-10) — Cloud × Pylon (UniWiki Abyssal Mechanics)
# ---------------------------------------------------------------------------

ROOM_TACTICS: dict[str, dict[str, Any]] = {
    "KAREN": {"maneuver": "spiral_then_orbit", "orbit_km": 2, "kite_km": 60,
              "spiral_angle_deg": 40, "forbid_blue_cloud": True, "forbid_tracking_pylon": True,
              "bait_token": "Ephialtes Lancer", "split_fire": True},
    "OVERMIND": {"maneuver": "spiral_keep_outside_web", "orbit_km": 16,
                 "kite_km": 45, "spiral_angle_deg": 35, "forbid_blue_cloud": True,
                 "forbid_tracking_pylon": True, "bait_token": "needle Tessella", "split_fire": True},
    "LESHAK": {"maneuver": "orbit_under_guns", "orbit_km": 5, "kite_km": 55,
               "spiral_angle_deg": 30, "forbid_blue_cloud": True, "forbid_tracking_pylon": True,
               "bait_token": None, "split_fire": False},
    "MARSHAL": {"maneuver": "kite_or_brawl_under", "orbit_km": 12, "kite_km": 65,
                "spiral_angle_deg": 0, "forbid_blue_cloud": True, "forbid_tracking_pylon": False,
                "bait_token": None, "split_fire": False},
    "DEEPWATCHER": {"maneuver": "orbit_never_stop", "orbit_km": 5, "kite_km": 20,
                    "spiral_angle_deg": 0, "forbid_blue_cloud": False,
                    "forbid_tracking_pylon": True, "bait_token": None, "split_fire": False},
    "TESSERA": {"maneuver": "kite_outside_15km", "orbit_km": 22, "kite_km": 25,
                "spiral_angle_deg": 0, "forbid_blue_cloud": True, "forbid_tracking_pylon": True,
                "bait_token": None, "split_fire": False},
    "KIKI_SWARM": {"maneuver": "brawl_or_out_optimal", "orbit_km": 8, "kite_km": 28,
                   "spiral_angle_deg": 20, "forbid_blue_cloud": False,
                   "forbid_tracking_pylon": False, "bait_token": None, "split_fire": False},
    "VEDMAK": {"maneuver": "stop_or_counter_orbit", "orbit_km": 5, "kite_km": 28,
               "spiral_angle_deg": 0, "forbid_blue_cloud": False, "forbid_tracking_pylon": True,
               "bait_token": None, "split_fire": False},
    "ANGEL": {"maneuver": "brawl_overheat_defense", "orbit_km": 5, "kite_km": 15,
              "spiral_angle_deg": 0, "forbid_blue_cloud": True, "forbid_tracking_pylon": True,
              "bait_token": None, "split_fire": False},
    "SANSHA": {"maneuver": "kite_outside_web_or_orbit_500", "orbit_km": 13, "kite_km": 32,
               "spiral_angle_deg": 30, "forbid_blue_cloud": True, "forbid_tracking_pylon": True,
               "bait_token": None, "split_fire": False},
    "SCYLLA": {"maneuver": "approach_cache_orbit", "orbit_km": 10, "kite_km": 25,
               "spiral_angle_deg": 0, "forbid_blue_cloud": False, "forbid_tracking_pylon": False,
               "bait_token": None, "split_fire": True},
}

CLOUD_EFFECTS: dict[str, dict[str, Any]] = {
    "Bioluminescence Cloud": {
        "color": "blue",
        "effect": "+300% Signature Radius (4.0x) — thành đèn đèn lồng cho mọi pháo của quái",
        "danger_rooms": {"KAREN", "OVERMIND", "MARSHAL", "LESHAK", "TESSERA", "ANGEL", "SANSHA"},
        "benefit_rooms": {"KIKI_SWARM", "SCYLLA"},
    },
    "Filament Cloud": {
        "color": "orange",
        "effect": "-40% Shield Boost Amount, -40% Shield Boost Duration (+66% cap/s)",
        "danger_fits": {"active_shield"},
        "safe_fits": {"armor", "passive_shield"},
    },
    "Tachyon Cloud": {
        "color": "white",
        "effect": "+300% Velocity (4.0x), -50% Inertia (8.0xaccel) — văng biên đỏ là nổ",
        "danger_fits": {"mwd"},
        "boundary_slingshot_risk": True,
    },
}

PYLON_EFFECTS: dict[str, dict[str, Any]] = {
    "Deviant Automata Suppressor": {
        "short_range_km": 15,
        "medium_range_km": 40,
        "damages": ("drones", "light_missiles", "rogue_drone_frigates"),
    },
    "Multibody Tracking Pylon": {
        "short_range_km": 15,
        "medium_range_km": 40,
        "bonus_tracking_pct": (80, 60),
        "danger_rooms": {"KAREN", "OVERMIND", "LESHAK", "TESSERA", "SANSHA"},
    },
}


def evaluate_hazards(hazards: list[dict[str, Any]], room_kind: str,
                     fit_type: str = "ab_shield_drone") -> dict[str, Any]:
    """Đọc danh sách hazard (mây/tháp: {name, dist_km}) → chỉ thị điều hướng.

    Trả về: avoid (list tên cần né), exploit (list có thể lợi dụng),
    recall_drones (tháp Suppressor ngắn ≤15km), disable_mwd (Tachyon + fit MWD).
    """
    tactics = ROOM_TACTICS.get(room_kind, {})
    avoid: list[str] = []
    exploit: list[str] = []
    recall_drones = False
    disable_mwd = False

    for h in hazards:
        h_name = str(h.get("name", ""))
        dist_km = float(h.get("dist_km", 999.0))
        h_lower = h_name.lower()

        if "bioluminescence" in h_lower or "blue" in h_lower:
            if tactics.get("forbid_blue_cloud", True):
                if dist_km <= 15.0:
                    avoid.append(h_name)
            else:
                exploit.append(h_name)
        elif "filament" in h_lower or "orange" in h_lower:
            if "shield" in fit_type.lower() and "passive" not in fit_type.lower():
                if dist_km <= 12.0:
                    avoid.append(h_name)
        elif "tachyon" in h_lower or "white" in h_lower:
            if dist_km <= 12.0 and "mwd" in fit_type.lower():
                disable_mwd = True
                avoid.append(h_name)
        elif "suppressor" in h_lower:
            is_short = "short" in h_lower
            danger_radius = 16.0 if is_short else 40.0
            if "drone" in fit_type.lower() or "missile" in fit_type.lower():
                if dist_km <= danger_radius:
                    avoid.append(h_name)
                    if is_short:
                        recall_drones = True
            elif room_kind == "KIKI_SWARM":
                exploit.append(h_name)
        elif "tracking pylon" in h_lower or "multibody" in h_lower:
            if tactics.get("forbid_tracking_pylon", False) and dist_km <= 20.0:
                avoid.append(h_name)
            else:
                exploit.append(h_name)

    return {"avoid": avoid, "exploit": exploit,
            "recall_drones": recall_drones, "disable_mwd": disable_mwd}
