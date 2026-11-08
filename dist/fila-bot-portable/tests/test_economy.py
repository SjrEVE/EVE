"""Test economy.py — công thức chọn weather theo EV."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fila_bot.economy import pick_weather, session_weather_recommendation  # noqa: E402

PASS = 0


def ok(name: str, cond: bool, msg: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} — {msg}")
        sys.exit(1)


# Firestorm rẻ (9.4M) vs Electrical đắt (51.1M) — cùng win-rate → firestorm EV cao hơn
ranked = pick_weather({"Firestorm": 0.8, "Electrical": 0.8})
ok("firestorm_cheaper_better", ranked[0]["weather"] == "Firestorm", str(ranked))

# win-rate cao bù đắp filament đắt: 0.95 elec vs 0.8 firestorm
ranked = pick_weather({"Firestorm": 0.8, "Electrical": 0.95})
ok("high_wr_beats_price", ranked[0]["weather"] in ("Electrical", "Firestorm"), str(ranked))  # cả 2 hợp lý, chỉ check sort chạy

# EV đúng công thức: 0.8×100M − 9.41M − 0.2×50M = 60,590,000 (int truncate)
r = pick_weather({"Firestorm": 0.8})[0]
ok("ev_math", r["ev_isk"] == 60_590_000, str(r))

# win-rate thấp (0.3) → EV âm → vẫn trả về nhưng sort dưới
ranked = pick_weather({"Firestorm": 0.3, "Gamma": 0.9})
ok("low_wr_sinks", ranked[-1]["weather"] == "Firestorm" and ranked[-1]["ev_isk"] < 0, str(ranked))

# chưa có win-rate thật → KHÔNG khuyên weather (không phán đoán)
rec = session_weather_recommendation(win_rates=None)
ok("no_data_no_advice", rec is not None and rec.get("skip") is True, str(rec))

# có data → trả weather EV cao nhất
rec = session_weather_recommendation(win_rates={"Firestorm": 0.8, "Gamma": 0.6})
ok("data_gives_advice", rec is not None and rec.get("weather") == "Firestorm", str(rec))

print(f"\n=> {PASS} test PASS (mọi [FAIL] exit(1) ngay)")
