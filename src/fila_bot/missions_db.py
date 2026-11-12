"""Database các Security Mission (L1-L4) và bộ quy tắc đánh giá (Accept / Decline).

Thiết kế Fail-Closed:
- Mọi mission trong Blacklist (Burners/Anomic, Empire Navy) -> BẮT BUỘC DECLINE để bảo vệ tàu và standing.
- Whitelist các mission chuẩn, an toàn, đã được phân tích mechanic.
- Level 1-2: Mặc định ACCEPT nếu không dính blacklist (cực kỳ an toàn cho Gila).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# CCP SDE build 3682781 (2026-11-10), đọc và ghi nhận trong
# docs/MISSION_RESEARCH_DEEP_2026-11-11.md §1. Chi gom nhung title duoc NEU RO
# trong bao cao do; KHONG them title khac vao bang nay (khong duoc biạ level/faction).
SDE_BUILD = "3682781"
SDE_TEMPLATES: dict[str, str] = {
    # killMission co item objective: 16 record, 4 cap objective item/qty khac nhau.
    "cargo delivery": "kill_item",
    # killMission 4 bien the, briefing nhac cac tau Empire/State/Republic.
    "counter-attack": "kill",
    # killMission nhung CCP goi optional, decline khong mat standing.
    "anomic agent": "burner",
    "anomic team": "burner",
    "anomic base": "burner",
}


def normalize_title(title: str | None) -> str:
    """Bo chain '(1 of 5)', khoang trang, lowercase — de so sanh DUNG title."""
    t = re.sub(r"\s*\(\d+\s+of\s+\d+\)\s*$", "", str(title or "")).strip().lower()
    return re.sub(r"\s+", " ", t)


def template_kind(title: str | None) -> str | None:
    """Loai template theo SDE (chi title da ground); None = khong biet."""
    return SDE_TEMPLATES.get(normalize_title(title))


# Bang chung objective doc TRUC TIEP tu dump client that (khong phai suy luan).
# Chi cap quyen DI CHUYEN (undock/warp), KHONG cap quyen ban — quyen ban van o
# authorize_security_targets(). Moi entry phai co source fixture + evidence that.
GROUNDED_COMBAT_OBJECTIVES: dict[str, dict[str, str]] = {
    "what s in a name - change of address": {
        "evidence": ("Objective Give the diplomats enough time to evacuate. "
                     "Engage any hostiles. Location 0.9 Hirtamon"),
        "source": "tests/fixtures/ui_tree_e2e_06_live_cannot_complete.json",
        "division": "Security",
        "level": "1",
        "location": "Hirtamon 0.9",
    },
    "pirate intrusion": {
        "evidence": ("EVE-Survival PirateIntrusion2gu/2se: Faction Guristas, "
                     "Deadspace, Acceleration Gate 26km, 2 pockets, frig/cruiser "
                     "rats (Despoiler/Saboteur/Killer jamming). Accepted live "
                     "2026-11-13 from agent 3016830 L2, briefing link Location."),
        "source": "https://eve-survival.org/?wakka=PirateIntrusion2gu",
        "division": "Security",
        "level": "2",
        "location": "Piak 0.7",
    },
    "gone berserk": {
        "evidence": ("EVE-Survival GoneBerserk1: Faction EoM, Deadspace có gate, "
                     "3 group auto-aggro (Imp x2 + Fiend trigger), Wave 1 (3x "
                     "Fiend) -> Wave 2 (2x Incubus). Accepted live 2026-11-13."),
        "source": "https://eve-survival.org/?wakka=GoneBerserk1",
        "division": "Security",
        "level": "2",
        "location": "Piak 0.7",
    },
}


def grounded_combat_objective(title: str | None) -> dict[str, str] | None:
    """Bang chung combat objective da ground cho title nay, hoac None."""
    return GROUNDED_COMBAT_OBJECTIVES.get(normalize_title(title))


@dataclass
class MissionSpec:
    name: str
    faction: str
    level: int
    damage_weakness: str  # "kinetic", "thermal", "em", "explosive"
    is_burner: bool = False
    is_empire: bool = False
    cargo_m3: float = 0.0
    notes: str = ""


# Whitelist các security mission phổ biến
MISSION_CATALOG: dict[str, MissionSpec] = {
    # L1-L3
    "the blockade": MissionSpec("The Blockade", "Pirate", 3, "kinetic", notes="4 waves theo trigger"),
    "damsel in distress": MissionSpec("Damsel in Distress", "Mercenary", 3, "thermal", cargo_m3=0.1, notes="Kill Kruul, destroy hub, scoop Damsel"),
    "the spies": MissionSpec("The Spies", "Pirate", 3, "kinetic", notes="1 pocket, auto-aggro"),
    "the guristas spies": MissionSpec("The Guristas Spies", "Guristas", 3, "kinetic"),
    "the angel cartel spies": MissionSpec("The Angel Cartel Spies", "Angel", 3, "explosive"),
    "silence the informant": MissionSpec("Silence The Informant", "Mercenary", 3, "thermal"),
    "gone berserk": MissionSpec("Gone Berserk", "Rogue Drone", 3, "em"),
    "unauthorized military presence": MissionSpec("Unauthorized Military Presence", "Mercenary", 3, "thermal", cargo_m3=10.0),
    "smash the supplier": MissionSpec("Smash the Supplier", "Mercenary", 3, "thermal"),
    "the score": MissionSpec("The Score", "Guristas", 3, "kinetic"),
    "alluring emanations": MissionSpec("Alluring Emanations", "Rogue Drone", 1, "em"),
    "cargo delivery": MissionSpec("Cargo Delivery", "Pirate", 1, "kinetic"),
    "vengeance": MissionSpec("Vengeance", "Pirate", 3, "kinetic"),
    "recon": MissionSpec("Recon", "Pirate", 3, "kinetic", notes="Chuỗi 3 chặng"),
    "intercept the saboteurs": MissionSpec("Intercept the Saboteurs", "Pirate", 2, "kinetic"),
    # Grounded LIVE 2026-11-12 (agent 3016216 L1, Piak): mission tracker =
    # 'Encounter (Deadspace)', pocket rats = 'Pithi Arrogator' (Guristas), wrecks
    # 'Pithi Arrogator Wreck'. Before this entry the title classified as
    # 'unknown' and authorize_security_targets refused every target.
    "seek and destroy": MissionSpec("Seek and Destroy", "Guristas", 1, "kinetic",
                                    notes="grounded live 2026-11-12: Pithi Arrogator frigates, 1 pocket"),
    "the assault": MissionSpec("The Assault", "Guristas", 4, "kinetic"),
}

# Blacklist decline (Boss 11-11: chỉ trừ burner — mọi mission khác NHẬN HẾT,
# kể cả Counter-Attack / mission navy; standing không còn là mối quan tâm).
BLACKLIST_KEYWORDS = (
    "anomic",          # Burner missions -> NGUY HIỂM CHÍ MẠNG (concussion/burner)
)


def evaluate_offer(title: str | None, level: int = 1) -> tuple[str, str]:
    """Trả về ('ACCEPT'|'DECLINE'|'BLOCKED', lý do).

    BLOCKED = không đọc được tiêu đề mission (dialog chưa render offer) ->
    caller TỰ xử lý (bấm Request / chờ), TUYỆT ĐỐI không decline mù:
    G9 ground 2026-11-11 — bot đọc offer trên cây dialog đang load
    (title=None) rồi decline -> không có nút Decline -> đứng im (log 05:43).
    """
    t = (title or "").lower().strip()
    if not t:
        return "BLOCKED", "không đọc được tiêu đề mission (dialog chưa render offer)"

    for kw in BLACKLIST_KEYWORDS:
        if kw in t:
            return "DECLINE", f"Từ chối an toàn: Khớp blacklist '{kw}'"

    # Với Level 1 hoặc Level 2: Gila quá mạnh, an toàn 100%
    if level in (1, 2):
        return "ACCEPT", f"Chấp nhận: Mission L{level} an toàn tuyệt đối cho Gila"

    # Với Level 3-4: Kiểm tra xem có trong catalog không (khớp ĐÚNG title, đã bỏ chain)
    spec = MISSION_CATALOG.get(normalize_title(title))
    if spec is not None:
        return "ACCEPT", f"Khớp catalog: {spec.name} (Yếu với {spec.damage_weakness})"

    return "ACCEPT", f"Mission thường (không dính blacklist): {title}"


# Combat permission is deliberately narrower than offer acceptance. The owner may
# accept any non-Anomic offer, but the bot only fires when BOTH the mission class
# and each target faction are positively identified. Empire Navy / CONCORD and
# generic MissionNPC are never valid automatic targets.
COMBAT_FACTIONS = frozenset({
    "Angel", "Guristas", "Serpentis", "Blood", "Sansha", "RogueDrone", "Mercenary",
    "EoM",  # Enemies of Man — Gone Berserk L1/L2 (EVE-Survival + live 13-11)
})
PROTECTED_FACTIONS = frozenset({
    "AmarrNavy", "CaldariNavy", "GallenteNavy", "MinmatarNavy", "CONCORD",
})


def classify_security_mission(title: str | None) -> str:
    """Phan loai EXECUTION support, khong phai accept policy.

    Ground 11-11: CCP SDE xep 'Cargo Delivery' vao killMission co item objective,
    dump TQ `dumps/g10_turnin_dialog.json` la agent SECURITY L1 voi nut Complete.
    Khong duoc gan no thanh courier chi vi title co chu 'cargo' hoac offer co cargo.
    'combat' chi khi title khop DUNG catalog da ground; con lai fail-closed.
    """
    t = normalize_title(title)
    if not t:
        return "unknown"
    if re.search(r"\banomic\b", t):
        return "burner"
    kind = template_kind(t)
    if kind == "kill_item":
        return "item_objective"
    if kind == "courier":
        return "courier"
    if kind == "burner":
        return "burner"
    # Khop DUNG title (cat chain), khong substring: 'counter' nam trong
    # 'encounter' khong duoc phep thanh blacklist/decline.
    if t in MISSION_CATALOG and t != "cargo delivery":
        return "combat"
    return "unknown"


def authorize_security_targets(title: str | None,
                               targets: list[dict[str, Any]] | None,
                               type_label: str | None = None) -> tuple[bool, str]:
    """Fail closed unless the mission is positively identified as combat.

    Two independent positive-evidence routes (never a title keyword guess):
    1. Title matches the grounded combat catalog.
    2. The game's own mission panel says this is an ``Encounter (Deadspace)``
       (ground LIVE 2026-11-12: mission tracker ``EveLabelLarge`` = 'Encounter
       (Deadspace)' for agent 3016216 L1 'Seek and Destroy'). The panel is the
       client describing its own mission, which is stronger evidence than a
       title that happens to be absent from the catalog.

    Either way every visible target must still be an approved hostile faction.
    """
    kind = classify_security_mission(title)
    labeled_encounter = bool(type_label) and any(
        token in str(type_label).lower() for token in ("encounter", "deadspace"))
    if kind != "combat" and not labeled_encounter:
        return False, f"mission type {kind!r} is not positively identified as supported combat"
    active = [target for target in (targets or []) if not target.get("skip")]
    if not active:
        return False, "no positively identified attackable targets"
    for target in active:
        faction = target.get("faction")
        name = target.get("name") or "<unnamed>"
        if faction in PROTECTED_FACTIONS:
            return False, f"protected faction {faction}: refusing to fire at {name}"
        if faction not in COMBAT_FACTIONS:
            return False, f"unapproved/unknown faction {faction!r}: refusing to fire at {name}"
    return True, "positively identified combat mission; all visible targets are approved hostile factions"
