# FILAMENT MARKET & META ECONOMICS — giá là một chiến thuật (nguồn: Goon wiki, merchant
# 60B reddit 2024, Abyssal Lurkers guide, UniWiki Community Fits)

## 1. NGUYÊN TẮC SỐ 1: GIÁ FILAMENT QUYẾT LỖ — KHÔNG PHẢI LOOT
Goon wiki nói thẳng: "Did you really just pull 40M from that T4 Electrical when it
cost 25M for the filament? No — you brought in 15M and a day trader is laughing."
- Ví dụ thật (forum): T4 Electrical 8M/filament × 3 runs = 24M chi phí, loot trung
  bình 8M/run → **T4 elec có khi TỔN** dù loot "giống T3".
- Filament giá không cố định: Electrical nổi tiếng → đắt nhất; Firestorm rẻ nhất
  (39% price deviation) vì ít người chạy; Dark biến động mạnh (120% deviation).

## 2. BẢNG GIÁ T6 THẬT (Jita, 2024 — merchant 60B experiment)
| Filament T6 | Jita sell | Volume (3 tháng) | Deviation |
|---|---|---|---|
| Cataclysmic Dark | 29.18M | 266 | 120.9% |
| Cataclysmic Electrical | **51.16M** | 233 | **212.1%** |
| Cataclysmic Exotic | 19.29M | 298 | 80.0% |
| Cataclysmic Firestorm | **9.41M** | 359 | 39.0% |
| Cataclysmic Gamma | 19.02M | 180 | 78.8% |

→ Suy ra chiến lược bot: **chạy weather có filament RẺ nhưng fit mình tank nổi**.
Firestorm rẻ nhất (9.4M) nhưng khó nhất (armor ×1.5 quái); Gamma cân bằng (19M,
shield +50% cho Gila). Electrical 51M = phải giỏi thật mới có lãi.

## 3. META VÒNG QUAY (why prices move)
- Weather nào được "giải" (new fits/mutas đắt) → filament giá lên → chạy weather đó
  bớt lãi → dân chuyển → giá xuống. Bot phải CHECK GIÁ FILAMENT TRƯỚC MỖI SESSION
  (ESI market API — free) và chọn weather theo công thức:
  expected_profit = P(success) × E[loot] − filament_price − ship_loss_risk
- T4 Dark từng spike vì Hawk meta; T6 elec 51M vì Stormbringer/Retri T6 elec meta.
- Exotics: "cannot recommend enough... filaments start getting really expensive"
  — High reward but high entry cost = dành cho bot đã có win-rate data.

## 4. RED LOOT = AN TOÀN DUY NHẤT (goon)
Triglavian Survey Database = 100K × NPC buy order unlimited = floor thu nhập.
Còn lại (BPC, muta, isogen, filament drop) = biến động theo thị trường.
→ Bot plan: tính "guaranteed income" = red_loot_count × 100K; mọi thứ khác là bonus.

## 5. UNIWIKI COMMUNITY FITS — T0 fits được TEST (cái bảng bot T0 cần)
| Ship | Filament | DPS | Tank EHP/s | Giá fit | SP cần |
|---|---|---|---|---|---|
| Kestrel | T0 Dark | 82 | 33 | 4.4M | 800k |
| Punisher | T0 Electrical | 112 | 65 | 3M | 500k |
| Rifter | T0 Electrical | 110 | 50 | 4.2M | 700k |
| Tristan | T0 Electrical | 90 | 30 | 2.3M | 1.1M |
Mỗi fit có: video youtube, skill plan <1M SP, tested vs Skybreaker + Devoted Hunter
(hai killer của T0). Punisher notes: "stagger reps half cycle, orbit 2500 multifreq".
Rifter notes: orbit 500m trừ Tessella (5km), web ASAP, Devoted Hunter = killer cần cả
2 reppers chạy.
→ Đây là **fits bắt đầu cho bot test pipeline** — rẻ (3-4M), chết không đau, số liệu
đủ chuẩn để đo win-rate bot vs người thật.

## 6. HISTORY — TẦNG UPDATE (để hiểu vì sao wiki đôi khi mâu thuẫn)
- 2018 Into the Abyss: T0-T5, 3 tiers đầu chỉ frig/cruiser.
- Nov 2020: Tachyon cloud thay Caustic (−80% armor rep — chết chóc, bỏ).
- Nov 2022 Depths of the Abyss: **T0 (Tranquil) + T6 (Cataclysmic) mới**; destroyer
  duo mode (2 filaments); CONCORD strike teams mới; capital mutaplasmids (T6 only);
  Marshal nerfed từ full HP → 0 shield/28% armor (vì "unfairly difficult").
- 2024: Exploit notification — extending abyssal timers (đã vá).
- May 2026: suspect-flag rework theo hệ sec (0.5 = mọi tier không suspect).
→ Khi wiki ghi "Marshal 427 DPS full HP" ở chỗ nào đó = THỜI GIAN CŨ — luôn check
  patch-date của nguồn trước khi tin.
