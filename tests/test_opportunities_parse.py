"""Parser Opportunities (JobBoardWindow / FreelanceProjectCard) — chi dung data dump that.

Fail-closed: khong bia. Moi truong lay tu dumps/g8_freelance.json (live EVE 2026-11-10).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.opportunities import format_summary, parse_jobboard  # noqa: E402

FREELANCE = ROOT / "dumps" / "g8_freelance.json"
CLOSED = ROOT / "dumps" / "g8_opportunities_open.json"


def main() -> int:
    n_pass = 0

    def ok(cond: bool, msg: str) -> None:
        nonlocal n_pass
        assert cond, msg
        n_pass += 1
        print(f"  [OK] {msg}")

    freelance = json.loads(FREELANCE.read_text(encoding="utf-8"))
    data = parse_jobboard(freelance)
    ok(data["opened"] is True, "JobBoardWindow doc duoc (opened=True)")

    s = data["summary"]
    ok(s.get("Jobs Available") == "0", f"summary Jobs Available = {s.get('Jobs Available')!r}")
    ok(s.get("Corporations") == "0", f"summary Corporations = {s.get('Corporations')!r}")
    ok(s.get("Jobs Accepted") == "0/3", f"summary Jobs Accepted = {s.get('Jobs Accepted')!r}")
    ok(s.get("Opportunities") == "0", f"summary Opportunities = {s.get('Opportunities')!r}")

    jobs = data["jobs"]
    ok(len(jobs) == 2, f"so card = {len(jobs)}")
    first = jobs[0]
    second = jobs[1]
    ok(first["uuid"] == "fa72b66d-fd6a-4129-8932-e1a9c3816d5d", f"uuid card 1 = {first['uuid']}")
    ok(first["system"] == "Akiainavas", f"system card 1 = {first['system']}")
    ok(first["sec"] == "0.7", f"sec card 1 = {first['sec']}")
    ok(second["uuid"] == "2ab105ef-9b45-429b-b022-89c1682af7c5", f"uuid card 2 = {second['uuid']}")
    ok("Kernite" in (first["header"] or ""), f"header card 1 co 'Kernite': {(first['header'] or '')[:70]}")
    ok(second["system"] == "Ruvas", f"system card 2 = {second['system']}")
    ok(second["sec"] == "0.8", f"sec card 2 = {second['sec']}")

    closed = json.loads(CLOSED.read_text(encoding="utf-8"))
    data2 = parse_jobboard(closed)
    ok(data2["opened"] is False, "JobBoardWindow dong (opened=False)")
    ok(data2["jobs"] == [], "list job rong khi dong")

    txt = format_summary(data)
    ok("JobBoardWindow chua mo" not in txt, "format khong bao chua mo")
    ok("Akiainavas" in txt, "format co system Akiainavas")
    print(f"[OK] test_opportunities_parse: {n_pass} pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
