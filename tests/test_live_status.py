"""Read-only CLI status must report observed data and keep unknown distinct."""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot import cli  # noqa: E402
from fila_bot.eye import Eye  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def status_for(fixture: str) -> tuple[int, str]:
    eye = Eye.__new__(Eye)
    eye.root = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    eye._pos = None
    eye._pos_root = None
    eye.refresh = lambda: eye.root
    output = io.StringIO()
    with mock.patch.object(cli, "Eye", return_value=eye), \
         mock.patch.object(cli, "find_client_window", return_value=None), \
         contextlib.redirect_stdout(output):
        code = cli.cmd_status(SimpleNamespace(dll=None))
    return code, output.getvalue()


code, out = status_for("ui_tree_station_menu.json")
assert code == 0
assert "Location state           : DOCKED" in out
assert "Solar system             : UNKNOWN" in out
assert "Active ship               : Amarr Shuttle" in out
assert "Amarr Shuttle - Oksora Aivo" in out
assert "Active missions           : UNKNOWN" in out
assert "Route                     : UNKNOWN" in out
print("[PASS] status reports docked, active ship, and unknown fields honestly")

code, out = status_for("ui_tree_mission_accepted.json")
assert code == 0
assert "Rancorous Researcher (1 of 5)" in out
print("[PASS] status reports live Job Board mission title")

print("ALL OK test_live_status")
