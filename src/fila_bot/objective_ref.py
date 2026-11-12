"""Conservative objective syntax and identity extraction, NOT click authority.

Ground truth (client source V24.02 + live TQ dumps 11-11):

    EveLabelMedium text='You need to approach <a href= showinfo:10131//9002321446000117567 >Fire Cloud</a>'
    EveLabelMedium text='You need to travel to <a href= showinfo:5//30000156 >Josameto</a>'

Some observed objectives contain a ``showinfo`` link with ``<typeID>//<itemID>``.
Others, including the gate instruction, have no link. In space brackets are named
``__inflightbracket_<ballID>`` (grounded in ui_dump_space.json, produced by
``bracketMgr.py``: ``name='__inflightbracket_%s' % itemID``). Same itemID space
proves identity only: projected render geometry is NOT exported by the reader.
A caller still needs observed, fresh and visible geometry before any input.

This module is deliberately pure: it parses text and matches bracket names.
No clicking, no client access — ``security.py`` decides, ``live_security.apply``
executes.
"""
from __future__ import annotations

import re
import html
from typing import Any

# `<a href= showinfo:<typeID>//<itemID> >Label</a>` — the client emits a space
# after `href=` and around the label, so tolerate arbitrary whitespace.
_SHOWINFO = re.compile(
    r'''<a\s+href\s*=\s*(["']?)showinfo:([0-9]+)//([0-9]+)\1\s*>(.*?)</a>''',
    re.IGNORECASE | re.DOTALL,
)

# Objective verbs the client uses. Only these grant any movement authority.
APPROACH = "approach"
ACTIVATE = "activate"
TRAVEL = "travel"
UNKNOWN = "unknown"


def _clean_label(label: str) -> str:
    """Strip residual markup/entities from an anchor label."""
    text = html.unescape(re.sub(r"<[^>]+>", "", label or ""))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def objective_reference(objective_text: str | None) -> dict[str, Any] | None:
    """Parse the objective's ``showinfo`` link.

    Returns ``{"verb", "type_id", "item_id", "label", "raw"}`` or ``None`` when
    the text carries no link (e.g. "You need to activate the Acceleration Gate"
    is a plain sentence with no anchor).

    ``verb`` is conservative: an unrecognised sentence yields ``UNKNOWN`` so the
    caller can refuse to move.
    """
    if not isinstance(objective_text, str) or not objective_text.strip():
        return None
    raw = objective_text.strip()
    # Only observed positive imperative forms. A verb in an anchor label, a
    # warning, or a negative sentence is not an instruction to move.
    plain = _clean_label(raw).lower()
    verb_match = re.match(r"^you need to (approach|activate|travel to)\b", plain)
    verb = ({"approach": APPROACH, "activate": ACTIVATE, "travel to": TRAVEL}
            .get(verb_match.group(1), UNKNOWN) if verb_match else UNKNOWN)

    match = _SHOWINFO.search(raw)
    if not match:
        return {"verb": verb, "type_id": None, "item_id": None,
                "label": None, "raw": raw}
    _, type_id, item_id, label = match.groups()
    return {
        "verb": verb,
        "type_id": int(type_id),
        "item_id": int(item_id),
        "label": _clean_label(label),
        "raw": raw,
    }


def bracket_name_for(item_id: int | str | None) -> str | None:
    """Bracket node name the client uses for a ball: ``__inflightbracket_<id>``."""
    if isinstance(item_id, bool) or not isinstance(item_id, (int, str)):
        return None
    text = str(item_id)
    if not re.fullmatch(r"[0-9]+", text):
        return None
    return f"__inflightbracket_{text}"


def match_bracket(brackets: list[dict[str, Any]], item_id: int | str | None,
                  label: str | None = None) -> dict[str, Any] | None:
    """Unique exact ID only. A label or suffix cannot override mismatched IDs."""
    want = bracket_name_for(item_id)
    matches = [b for b in brackets if want is not None and b.get("name") == want]
    return matches[0] if len(matches) == 1 else None
