"""Recorded projected brackets: identity alone does not provide click geometry."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fila_bot.eye import Eye

e = Eye.__new__(Eye)
SPACE_DUMP = ROOT / "ui_dump_space.json"
if not SPACE_DUMP.is_file():
    print("[SKIP] local-only EVE projection dump is not included in portable artifacts")
    raise SystemExit(0)
e.root = json.loads(SPACE_DUMP.read_text(encoding='utf-8'))
e._pos = e._pos_root = None
rows = e.space_brackets()
assert rows
assert all(row.get('center') is None for row in rows), 'unexported native projection must not become layout click coordinates'
print('[PASS] recorded brackets retain identity without fabricated geometry')
