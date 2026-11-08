"""ROOM PLAYBOOKS — ma trận room × weather → entry move + kill order + loot plan.

Nguồn: minmatar.org Nergal/Retri/Deacon trio guide, Goon wiki per-room notes,
BushidoMaru room guide (Marshal/Leshak/Karen), Four Ohm T4 video (grace period),
eveworkbench Cerberus notes, UniWiki loot FAQ, abysstracker run data (2026-11-07).

Bot dùng: detect_room(names) → playbook → entry_move + kill_order(names, weather).
"""
from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------
# Room signatures — nhận diện room từ set hull có mặt (đếm theo group lớn nhất)
# ----------------------------------------------------------------
ROOM_KINDS = {
    "KIKI_SWARM":  {"Kikimora", "Damavik"},                 # frig/dessie swarm
    "VEDMAK":      {"Vedmak", "Damavik", "Rodiva"},          # cruiser room
    "LESHAK":      {"Leshak"},                               # BS starburst
    "OVERMIND":    {"Overmind"},                             # rogue drone BS
    "TESSERA":     {"Tessera", "Tessella"},                  # drone BC room
    "DEEPWATCHER": {"Deepwatcher"},                          # sleeper BS
    "KAREN":       {"Karybdis"},                             # drifter BS
    "SCYLLA":      {"Scylla"},                               # drifter cruisers
    "MARSHAL":     {"Marshal", "Enforcer", "Pacifier", "Thunderchild", "Skybreaker", "Stormbringer"},
    "SANSHA":      {"Knight", "Hunter", "Fisher", "Priest", "Trapper", "Smith", "Lookout", "Herald", "Torchbearer"},
    "ANGEL":       {"Cynabal", "Dramiel", "Ixion", "Fury", "Echo", "Medusa", "Burst", "Swordspine"},
    "DEEPWATCHER2": {"Deepwatcher"},                          # T3+ pairs — same playbook
}


def detect_room(names: list[str]) -> str:
    """Tên quái trong room → room kind (ưu tiên BS/room đặc trưng)."""
    joined = " | ".join(names)
    if "Karybdis" in joined:
        return "KAREN"
    if "Deepwatcher" in joined:
        return "DEEPWATCHER"
    if "Leshak" in joined:
        return "LESHAK"
    if "Overmind" in joined:
        return "OVERMIND"
    if "Marshal" in joined or "Thunderchild" in joined:
        return "MARSHAL"
    if "Scylla" in joined:
        return "SCYLLA"
    if "Tessera" in joined:
        return "TESSERA"
    if "Vedmak" in joined:
        return "VEDMAK"
    if any(s in joined for s in ("Knight", "Hunter", "Priest")):
        return "SANSHA"
    if any(s in joined for s in ("Cynabal", "Dramiel", "Ixion")):
        return "ANGEL"
    if "Kikimora" in joined:
        return "KIKI_SWARM"
    return "UNKNOWN"


# ----------------------------------------------------------------
# Entry moves — giây 0–5 của room (nguồn: per-room guides)
# ----------------------------------------------------------------
ENTRY_MOVES: dict[str, str] = {
    "KIKI_SWARM": "KITE — burn CHÉO khỏi spawn, giữ range >20km (kiki 2%/cycle ramp, sig nhỏ khó bắn khi bay)",
    "VEDMAK":     "APPROACH CACHE — orbit cache giữ vị trí trung tâm, trig sẽ lao vào (no-switch) → bắn con tới gần nhất",
    "LESHAK":     "APPROACH LESHAK ASAP — chúng spawn HP thấp + starburst chạy tách ra; lợi dụng grace drift để sát; KHÔNG cho starburst (theo hướng 1 con để kéo cả nhóm)",
    "OVERMIND":   "APPROACH CACHE — bật prop+hardener, ĐỢI aggro rồi mới drop drone; orbit BS 500m khi tới gần (under guns)",
    "TESSERA":    "GIỮ >12km — Tessera tracking cực nhưng optimal ngắn; kite tròn quanh cache",
    "DEEPWATCHER": "LOOT TRƯỚC (loot-n-first) rồi orbit <10km MWD-off — missile Kin/Exp application tệ ở close; room dễ, 3–5'",
    "KAREN":      "BAY CHÉO 45° SPIRAL vào <30km (đích <10km) — KHÔNG orbit cache/gate khi Karen sống (bị đánh đứng); KHÔNG để Karen sống cuối (self-rep shield)",
    "SCYLLA":     "KITE — Scylla cruisers EWAR nhiều; giết theo EWAR priority, dùng TYPE column phân loại",
    "MARSHAL":    "BAY XA NGAY — Marshals neutron range khủng; giữ 60km (DLA) / 50km không DLA; kill Drainer Marshal ĐẦU TIÊN",
    "SANSHA":     "KITE RỘNG — Sansha chậm hơn mình, nguy hiểm sát; orbit xa >25km, Knight orbit 500 quá close để web không bắt",
    "ANGEL":      "KITE + RESIST EM — Angel nhanh nhất abyss, Cynabal web+neut; giữ transversal, đừng speed-tank T4+ (web đứng im)",
    "UNKNOWN":    "BURN CHÉO KHỎI SPAWN (mặc định an toàn) + tactical overlay, assess rồi quyết",
}

# ----------------------------------------------------------------
# Kill orders per room (tên class → thứ tự; EWAR rank của rats.py vẫn dùng chung)
# Nguồn: minmatar trio guide + goon + BushidoMaru + eveworkbench notes
# ----------------------------------------------------------------
KILL_ORDERS: dict[str, list[str]] = {
    "KIKI_SWARM":  ["Tangling", "Starving", "Ghosting", "Striking", "Damavik", "Kikimora"],
    "VEDMAK":      ["Tangling", "Starving", "Ghosting", "Renewing Rodiva", "Damavik", "Vedmak"],
    "LESHAK":      ["Starving", "Blinding", "Tangling", "Renewing", "Striking"],
    "OVERMIND":    ["Tangling", "Starving", "Snarecaster", "Fieldweaver", "Tessella", "Overmind"],
    "TESSERA":     ["Snarecaster", "Fieldweaver", "Spotlighter", "lance", "needle", "Tessera"],
    "DEEPWATCHER": ["burn-to-you frigs", "Upholder", "Sentinel", "Watchman", "Deepwatcher"],
    "KAREN":       ["Tangling/Echo/Entanglement (web)", "Dissipator/Fury/Nullcharge (neut)",
                    "Spearfisher/Trapper (scram)", "Lancer/Escort escorts", "Karybdis"],
    "SCYLLA":      ["Entanglement (web)", "Nullcharge (neut)", "Nullwarp (scram)", "Confuser", "Illuminator", "Scylla"],
    "MARSHAL":     ["Drainer Marshal", "Attacker Marshal", "Marshal khác", "Thunderchild", "Stormbringer", "Skybreaker", "Pacifier"],
    "SANSHA":      ["Fisher", "Trapper", "Smith", "Knight", "Priest", "Hunter", "Torchbearer", "Herald", "Lookout"],
    "ANGEL":       ["Echo", "Cynabal", "Elite Cynabal", "Fury", "Swordspine", "Ixion", "Medusa", "Dramiel", "Burst"],
    "UNKNOWN":     ["web", "neut", "scram", "logi", "paint", "td_damp", "rest"],
}

# ----------------------------------------------------------------
# Weather × room — hiệu chỉnh chiến thuật (Boss: "weather cũng khác nhau xử lý khác nhau")
# ----------------------------------------------------------------
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

# ----------------------------------------------------------------
# LOOT — giá trị thật (abysstracker runs 2026) + policy
# ----------------------------------------------------------------
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

CACHE_HP = 300            # 1 đạn là nổ
NODE_LOOT_POOL = ["Triglavian Survey Database", "Zero-Point Condensate", "Crystalline Isogen-10"]


def loot_plan(room_n: int, timer_left_s: int, cache_dist_m: int,
              nodes_dist_m: list[int], run_avg_min: int = 12) -> dict[str, Any]:
    """Quyết định loot theo UniWiki FAQ + reddit lessons:
    - back-to-back runs → chỉ Bioadaptive cache
    - run trung bình ≥15' → KHÔNG loot room 1 kỹ
    - can xa gate → skip (LootGreedGuard chặn >15km)
    """
    plan = {"cache": False, "nodes": [], "reason": ""}
    avg_run_s = run_avg_min * 60
    # cache: luôn loot nếu thuận đường (dist nhỏ) hoặc timer dư
    if cache_dist_m <= 15000 or timer_left_s > 240:
        plan["cache"] = True
        plan["reason"] += "cache: phá (300HP) + loot; "
    else:
        plan["reason"] += "cache: SKIP (xa gate + timer ngặt); "
    # room 1 với run dài: đừng kỹ
    if room_n == 1 and avg_run_s >= 900:
        plan["nodes"] = []
        plan["reason"] += "room1: bỏ node (run dài — đừng tham đầu trận); "
        return plan
    # node: chỉ khi timer dư + gần đường
    for i, d in enumerate(nodes_dist_m):
        if timer_left_s > 420 and d <= 12000:
            plan["nodes"].append(i)
    if plan["nodes"]:
        plan["reason"] += f"nodes {plan['nodes']}: loot (timer dư >7' + gần đường)"
    else:
        plan["reason"] += "nodes: bỏ (timer/ngoài đường)"
    return plan


# ----------------------------------------------------------------
# Gate/exit procedure (nguồn: Timers wiki + Four Ohm + forum gank counter)
# ----------------------------------------------------------------
GATE_TRANSIT = {
    "grace_s": 18,      # 15–20s: KHÔNG ra lệnh/kích module → rats không aggro
    "keep_prop_on": True,   # giữ prop mod qua gate — nó giữ cycle + auto-drift tới conduit (drift không tính là lệnh)
    "note": "drift của prop mod không phá grace — dùng 18s drift để vào sâu miễn phí",
}

EXIT_PROCEDURE = {
    "invul_s": 60,      # invul khi exit abyss nếu không move (transfer cargo được)
    "steps": ["Xuất hiện → KHÔNG MOVE (giữ invul 60s)",
              "Đợi trace despawn 30–45s",
              "Transfer loot nếu có Orca/alt",
              "Hết invul → warp off ngay; ganker thường camp exit + drop depot chặn filament tiếp theo"],
    "danger": "Abyssal gankers camp trace — bắt window 60s invul để loot/transfer rồi warp",
}
