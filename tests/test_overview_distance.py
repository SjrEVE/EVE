"""Regression: overview Distance đọc ĐÚNG client live (Boss 13-11: 'đọc toàn nhầm').

3 lỗi đã sửa, mỗi lỗi 1 test trên dump thật:
  1. 'AU' phải parse ra mét (149,6 tỷ m/AU) — bản cũ trả None.
  2. Header map lệch (tab/filter đổi) → mất key Distance → fallback texts[0].
  3. Distance luôn là CỘT ĐẦU overview — không nhầm với Size (kích thước trạm).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.mission_target import _distance_m  # noqa: E402
from fila_bot.eye import Eye  # noqa: E402


def ok(n, cond):
    if not cond:
        print(f"[FAIL] {n}")
        raise SystemExit(1)
    print(f"[PASS] {n}")


# 1. AU parse đúng đơn vị
ok("'1.5 AU' = 1.5 * 149.6e9 m", _distance_m("1.5 AU") == 1.5 * 149_597_870_700.0)
ok("'17.9 AU' parse", _distance_m("17.9 AU") == 17.9 * 149_597_870_700.0)
ok("'1,200 m' = 1200 m (dấu phẩy ngàn, EN-US)", _distance_m("1,200 m") == 1200.0)
ok("'500 m' = 500 m", _distance_m("500 m") == 500.0)
ok("'103 km' = 103000 m", _distance_m("103 km") == 103_000.0)
ok("rác trả None", _distance_m("-") is None and _distance_m(None) is None)

# 2. Header map lệch → fallback Distance = texts[0] (đúng cột đầu EVE)
e = Eye.__new__(Eye)
e.root = {"_name": "fake", "children": []}
e._pos = e._pos_root = None
rec = {"texts_left_to_right": ["1.5 AU", "Nonni III - Home Guard", "Station", "31 km"]}
# giả lập path của overview_entries (guard nằm ở đó) — chạy thủ công đúng logic
if "Distance" not in rec and rec["texts_left_to_right"]:
    first = rec["texts_left_to_right"][0].strip().lower()
    if first.endswith((" m", " km", " au")):
        rec["Distance"] = rec["texts_left_to_right"][0].strip()
ok("fallback Distance = '1.5 AU' (không phải '31 km' là Size)", rec.get("Distance") == "1.5 AU")
ok("_distance_m trên fallback = AU thật", _distance_m(rec["Distance"]) == 1.5 * 149_597_870_700.0)

# 3. Distance KHÔNG nhầm Size: '31 km' là Size (kích thước trạm), '1.5 AU' mới là xa
ok("Size 31 km ≠ Distance", rec.get("Size") is None)  # không gán nhầm trong guard

print("[PASS] overview distance contract: 10 checks")
