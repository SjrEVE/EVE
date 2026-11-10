"""Opportunities (JobBoard / Freelance Jobs + Agent Missions) parser — doc tu UI tree.

Nguon ground: dumps/g8_freelance.json va dumps/g8_opportunities_open.json (live EVE 2026-11-10,
AIR Career Program -> Freelance Jobs). Cau truc card (reg 2026-11-10):
  JobBoardWindow > content_container > FreelanceProjectsFeaturePage > Container main_container
   > ScrollContainer > Container clipCont > ContainerAutoSize mainCont
     > header_container > FeaturePageSummaryBar > SummaryStat(+Icon) {valueLabel}
     > Container content_container > CardsContainer > FreelanceProjectCard name=entry_freelance_projects:<uuid>
        > middle > TextHeader (title loi keu)
        > topCont > headerRow > titleCont > TextBody top_title (ten corp/nguoi dang)
        > topCont > SolarSystemChip > TextDetail locationName (system) | securityStatus (so le sec) | numJumps (kcach lon)

Parser KHONG bia: moi truong lay tu that; khong co thi tra gtri de trong/None.
"""
from __future__ import annotations

import re
from typing import Any

_ANY_EYE = Any


class OpportunityJob(dict):
    """1 gop viec (freelance) tren JobBoardWindow. La dict de serialize JSON de dang."""


_CARDS = "FreelanceProjectCard"
_PAGES = ("FreelanceProjectsFeaturePage",)


def _walk(node: dict[str, Any]):
    yield node
    for c in node.get("children") or []:
        yield from _walk(c)


def _attrs(n: dict[str, Any]) -> dict[str, Any]:
    return n.get("attrs") or {}


def _text(n: dict[str, Any] | None) -> str | None:
    if not n:
        return None
    return _attrs(n).get("_setText")


def _find_name(n: dict[str, Any], name: str) -> dict[str, Any] | None:
    for x in _walk(n):
        if _attrs(x).get("_name") == name:
            return x
    return None


def parse_jobboard(root: dict[str, Any]) -> dict[str, Any]:
    """Doc toan bo JobBoardWindow (Neocom: AIR Career Program -> Freelance Jobs).

    Tra ve dict {summary: {...}, jobs: [OpportunityJob...], opened: bool}.
    opened=False khi client khong co JobBoardWindow (khong bia du lieu).
    """
    if root is None:
        return {"opened": False, "summary": {}, "jobs": []}
    jb = None
    for n in _walk(root):
        if n.get("type") == "JobBoardWindow":
            jb = n
            break
    if jb is None:
        return {"opened": False, "summary": {}, "jobs": []}

    # 1) summary bar (3 stat tren doan dau)
    summary: dict[str, str] = {}
    for n in _walk(jb):
        if n.get("type") in ("SummaryStat", "SummaryStatIcon"):
            lab = None; val = None
            for x in _walk(n):
                a = _attrs(x)
                if x.get("type") == "EveLabelLarge" and not lab:
                    lab = a.get("_setText")
                if a.get("_name") == "valueLabel" and not val:
                    val = a.get("_setText")
            if lab:
                summary[str(lab)] = str(val) if val else ""
    # cung doan: "0 Opportunities" (TextHeader trong filter cont)
    opp_count = None
    for n in _walk(jb):
        if n.get("type") == "TextHeader" and _attrs(n).get("_setText", "").strip().endswith("Opportunities"):
            opp_count = _attrs(n).get("_setText", "").strip().rsplit(" ", 1)[0]
            break
    if opp_count is not None:
        summary["Opportunities"] = str(opp_count)

    # 2) cards
    jobs: list[OpportunityJob] = []
    for card in _walk(jb):
        if card.get("type") != _CARDS:
            continue
        a_name = str(_attrs(card).get("_name") or "")
        if not a_name.startswith("entry_freelance_projects:"):
            continue
        uuid = a_name.split(":", 1)[1] if ":" in a_name else None
        title = _text(_find_name(card, "top_title"))
        tdiag_locator = None
        system = None; sec = None; jumps = None; header = None
        # TextHeader trong container 'middle' — tim 'middle' cap 1
        for x in _walk(card):
            if _attrs(x).get("_name") == "middle":
                a_child = _attrs(x).get("children") or []
                for thu in _walk(x):
                    if thu.get("type") == "TextHeader":
                        header = _text(thu)
                        break
                break
        chip = _find_name(card, "locationName")
        system = _text(chip) if chip else None
        chip2 = _find_name(card, "securityStatus")
        sec = _text(chip2) if chip2 else None
        chip3 = _find_name(card, "numJumps")
        jumps = _text(chip3) if chip3 else None
        jobs.append(OpportunityJob({
            "uuid": uuid,
            "title": title,
            "header": header,
            "system": system,
            "sec": sec,
            "jumps": jumps,
        }))
    return {"opened": True, "summary": summary, "jobs": jobs}


def format_summary(data: dict[str, Any]) -> str:
    lines = []
    if not data.get("opened"):
        return "JobBoardWindow chua mo (mo Neocom -> AIR Career Program -> Freelance Jobs)."
    s = data.get("summary") or {}
    for k, v in s.items():
        lines.append(f"  {k}: {v}")
    jobs = data.get("jobs") or []
    lines.append(f"  ---- {len(jobs)} card:")
    for j in jobs:
        loc = ",".join(str(x) for x in (j.get("system"), j.get("sec")) if x)
        jumps = j.get("jumps")
        header = (j.get("header") or "").replace("\n", " ")[:80]
        lines.append(f"    - {loc or '?'} jumps={jumps or '?'} | {header}")
    return "\n".join(lines)


def build_cmd(root: dict[str, Any]) -> dict[str, Any]:
    """Phan code can cho CLI: parse_jobboard + format_summary."""
    data = parse_jobboard(root)
    return data
