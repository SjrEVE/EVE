"""Recorded projected brackets: identity alone does not provide click geometry."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fila_bot.eye import Eye

e = Eye.__new__(Eye)
e.root = json.loads((ROOT / 'ui_dump_space.json').read_text(encoding='utf-8'))
e._pos = e._pos_root = None
rows = e.space_brackets()
assert rows
assert all(row.get('center') is None for row in rows), 'unexported native projection must not become layout click coordinates'
print('[PASS] recorded brackets retain identity without fabricated geometry')
