"""Ground LIVE 2026-11-12: a Navy defense post must not block a combat mission.

Evidence: .hermes/evidence/missionrunner-v1/20261112-space-state/overview_raw.json
(the real overview captured in Piak while 'Seek and Destroy' was active) and
mission_panel_observation() = type_label 'Encounter (Deadspace)', agent 3016216.

Two separate defects were proven live, so two separate rules are asserted here:
1. hostiles() must not report Empire Navy structures/contacts as attackable.
2. A mission the game itself labels 'Encounter (Deadspace)' is positively
   identified as combat even when its title is absent from the catalog.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.mission import MissionEye  # noqa: E402
from fila_bot.missions_db import authorize_security_targets  # noqa: E402

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {msg}")


class OverviewEye:
    """Minimal eye returning a captured real overview."""

    def __init__(self, entries):
        self._entries = entries

    def overview_entries(self):
        return self._entries


entries = json.loads(
    (ROOT / "tests/fixtures/ui_overview_20261112_piak.json").read_text(encoding="utf-8"))
me = MissionEye(OverviewEye(entries))

hostiles = me.hostiles()
names = [h["name"] for h in hostiles]
ok("navy defense post is not a hostile target",
   "Caldari Navy Defense Post" not in names, str(names))
ok("no station is ever reported as hostile",
   not any("Station" in n or "Reserve" in n or "Refinery" in n for n in names), str(names))
ok("empty overview-with-only-protected yields no hostiles at all",
   hostiles == [], str(hostiles))

protected = me.protected_contacts()
ok("protected contacts are reported separately, not silently dropped",
   any(p["name"] == "Caldari Navy Defense Post" for p in protected), str(protected))

# The live mission panel said Encounter (Deadspace) for a title outside the catalog.
guristas = [{"name": "Pithi Arrogator", "faction": "Guristas", "hull": "Pithi"}]

allowed, reason = authorize_security_targets("Seek and Destroy", guristas,
                                             "Encounter (Deadspace)")
ok("panel-labelled encounter authorizes fire on approved pirates", allowed, reason)

# 'Seek and Destroy' is now in the catalog from this same live grounding, so the
# unknown-title case must use a title that really has no evidence at all.
allowed, reason = authorize_security_targets("Uncatalogued Mystery Mission", guristas)
ok("title alone (unknown catalog, no panel label) still fails closed",
   not allowed, reason)

allowed, reason = authorize_security_targets("Seek and Destroy",
                                             [{"name": "Caldari Navy Defense Post",
                                               "faction": "CaldariNavy"}],
                                             "Encounter (Deadspace)")
ok("protected faction is still refused even with a combat label", not allowed, reason)

allowed, reason = authorize_security_targets("Uncatalogued Mystery Mission",
                                             [{"name": "Pithi Arrogator",
                                               "faction": "Guristas"}],
                                             "Courier")
ok("a non-encounter label does not authorize fire", not allowed, reason)

print(f"\nKet qua: {PASS} PASS / {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
