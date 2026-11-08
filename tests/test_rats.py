"""Test rats DB — phân loại quái theo tên, thứ tự lock (mọi giá trị đối chiếu wiki)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.rats import classify, lock_order  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# web = priority 1
c = classify("Snarecaster Tessella")
ok("web_snarecaster", c["priority"] == 1 and "web" in c["ewar"] and c["faction"] == "RogueDrone", str(c))

c = classify("Lucid Warden")
ok("web_sleeper_warden", c["priority"] == 1 and c["faction"] == "Sleeper", str(c))

c = classify("Lucifer Cynabal")
ok("web_neut_cynabal", c["priority"] == 1 and set(c["ewar"]) == {"web", "neut"}
   and c["faction"] == "Angel", str(c))

c = classify("Devoted Knight")
ok("knight_web_neut", c["priority"] == 1 and c["faction"] == "Sansha", str(c))

# neut = 2
c = classify("Lucid Firewatcher")
ok("neut_firewatcher", c["priority"] == 2 and c["ewar"] == ["neut"], str(c))

c = classify("Starving Vedmak")
ok("neut_starving_vedmak", c["priority"] == 2 and c["faction"] == "Triglavian", str(c))

# scram = 3
c = classify("Anchoring Vila Damavik")
ok("scram_anchoring", c["priority"] == 3 and c["ewar"] == ["scram"], str(c))

# logi = 3
c = classify("Fieldweaver Tessella")
ok("logi_fieldweaver", c["priority"] == 3 and "logi" in c["ewar"], str(c))

c = classify("Renewing Rodiva")
ok("logi_rodiva", c["priority"] == 3 and c["hull"] == "Rodiva", str(c))

# paint = 4
c = classify("Spotlighter Tessella")
ok("paint_spotlighter", c["priority"] == 4 and c["ewar"] == ["paint"], str(c))

# DPS dealer = 6
c = classify("Sparkneedle Tessella")
ok("dps_tessella", c["priority"] == 6 and c["faction"] == "RogueDrone", str(c))

c = classify("Striking Damavik")
ok("dps_damavik", c["priority"] == 6 and c["faction"] == "Triglavian", str(c))

# BS đặc biệt = 5 + note
c = classify("Karybdis Tyrannos")
ok("karen_special", c["priority"] == 5 and "SPIRAL" in c["note"] and "verify" in c["note"], str(c))

c = classify("Attacker Marshal Disparu Troop")
ok("marshal_dps_race", c["priority"] == 5 and c["faction"] == "CONCORD"
   and "HP THẤP" in c["note"], str(c))

c = classify("Hadal Abyssal Overmind")
ok("overmind_t4", c["priority"] == 5 and c["hull"] == "Overmind"
   and "MÂU THUẪN" in c["note"], str(c))

c = classify("Lucid Deepwatcher")
ok("deepwatcher_timeout", c["priority"] == 5 and "orbit" in c["note"], str(c))

c = classify("Striking Leshak")
ok("leslak_ramp", c["priority"] == 5 and "ramp" in c["note"], str(c))

# SKIP swarmer
c = classify("Vila Swarmer")
ok("swarmer_skip", c["skip"] is True and c["priority"] == 0, str(c))

# ngoại lệ Harrowing Vedmak
c = classify("Harrowing Vedmak")
ok("harrowing_vedmak_exception", c["priority"] == 6 and "không paint" in c["note"], str(c))

# elite note
c = classify("Elite Lucifer Cynabal")
ok("elite_note", "ELITE" in c["note"], str(c))

# lock_order: web đầu, swarmer cuối, frigate trước BS cùng priority
order = lock_order([
    "Sparkneedle Tessella",          # dps frigate
    "Karybdis Tyrannos",             # BS
    "Snarecaster Tessella",          # web frigate
    "Vila Swarmer",                  # skip
    "Attacker Marshal Disparu Troop",# BS
    "Fieldweaver Tessella",          # logi
])
first = order[0]["raw"]
last_combat = [c for c in order if not c["skip"]][-1]["raw"]
ok("order_web_first", first == "Snarecaster Tessella", str([c["raw"] for c in order]))
ok("order_swarmer_last", order[-1]["raw"] == "Vila Swarmer", str([c["raw"] for c in order]))
ok("order_logi_before_dps", order.index(next(c for c in order if c["raw"] == "Fieldweaver Tessella"))
   < order.index(next(c for c in order if c["raw"] == "Sparkneedle Tessella")), str([c["raw"] for c in order]))

# ramp rate + no-switch behavior (nguồn Gustav "All 18 Rooms")
c = classify("Harrowing Vedmak")
ok("vedmak_ramp", c.get("ramp_per_cycle") == 4.0, str(c))
c = classify("Striking Kikimora")
ok("kikimora_ramp", c.get("ramp_per_cycle") == 2.0, str(c))
c = classify("Blastlance Tessella")
ok("tessella_no_switch", "Tessella" in (c.get("hull") or ""), str(c))

c = classify("Strikegrip Tessera")
ok("tessera_keep_12km", "12km" in c["note"], str(c))

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
