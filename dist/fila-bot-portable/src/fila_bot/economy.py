"""FILAMENT ECONOMY — chọn weather theo công thức lợi nhuận (nguồn: FILAMENT_MARKET.md).

expected_profit = P(success) × E[loot] − filament_price − (1−P) × ship_cost
Chạy weather nào = quyết định bằng số, không bằng sở thích.
"""
from __future__ import annotations

from typing import Any

# Giá T6 Jita 2024 (merchant 60B data) — KHÔNG cố định, bot nên check ESI trước session
T6_PRICES_2024: dict[str, int] = {
    "Dark": 29_180_000, "Electrical": 51_160_000, "Exotic": 19_290_000,
    "Firestorm": 9_410_000, "Gamma": 19_020_000,
}

# Trung bình loot theo combo (abysstracker 2026, giá trị ISK sau khi bán)
AVG_LOOT: dict[tuple[str, str], int] = {
    ("Fierce", "Dark"): 13_900_000,          # cruiser; frig ~36M
    ("Chaotic", "Gamma"): 107_000_000,
}


def pick_weather(fits: dict[str, float], tier_prices: dict[str, int] | None = None,
                 ship_cost: float = 50_000_000.0, avg_loot_scale: float = 1.0) -> list[dict[str, Any]]:
    """fits: {weather: P(success) ước lượng từ dữ liệu test của bot}.
    Trả list weather sort theo expected_profit giảm dần."""
    prices = tier_prices or T6_PRICES_2024
    out = []
    for weather, p in fits.items():
        price = prices.get(weather, 20_000_000)
        loot = 100_000_000 * avg_loot_scale   # placeholder — thay bằng E[loot] theo combo thật
        ev = p * loot - price - (1 - p) * ship_cost
        out.append({"weather": weather, "p": round(p, 3), "filament": price,
                    "ev_isk": int(ev)})
    out.sort(key=lambda x: x["ev_isk"], reverse=True)
    return out


def session_weather_recommendation(esi_prices: dict[str, int] | None = None,
                                   win_rates: dict[str, float] | None = None,
                                   ship_cost: float = 50_000_000.0) -> dict[str, Any] | None:
    """Quyết weather cho session: chỉ khi có win-rate đo THẬT từ Singularity.
    Không có data → trả None kèm lý do (không phán đoán)."""
    if not win_rates:
        return {"skip": True, "reason": "chưa có win-rate đo thật trên Singularity — "
                "chọn weather bằng cảm tính = phán đoán"}
    ranked = pick_weather(win_rates, tier_prices=esi_prices, ship_cost=ship_cost)
    return ranked[0] if ranked else None
