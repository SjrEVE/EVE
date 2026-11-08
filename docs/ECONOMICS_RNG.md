# ECONOMICS & RNG — kinh tế abyss + spawn RNG + drone aggro (nguồn: CCP dev AMA 2018,
# abysstracker per-weather data 2026, reddit/forum kinh nghiệm, UniWiki Tips)

## 1. SỐ CHÍNH THỨC TỪ CCP (dev AMA — CCP Rise, 2018; vẫn là floor thấp nhất ghi nhận)
- Spawn distribution: FLAT (trung thực, không thiên vị) — mỗi combo room xác suất như nhau.
  → Không có "chắc chắn gặp dễ" — phải fit cho WORST CASE, không phải trung bình.
- Success rate ngày đầu: T4 ≈ 80%, T5 ≈ 60% — NGƯỜI CHƠI THẬT với fit tốt.
  → Kế hoạch bot: T5 target ≥60%, nếu test thấy <50% → tier quá cao, lùi 1.
- Leshak đã bị tune giảm số lượng spawn (CCP confirm "one of the most dangerous").
- Loot pool GIAO NHAU: "almost any loot can drop at any difficulty" — nhưng môi trường
  cao hơn = nhiều loot hơn + mutaplasmid thiên theo weather.

## 2. KHINH TẾ THẬT PER WEATHER-TIER (abysstracker, 2026 — số submit thật)
| Combo | Runs submitted | Avg loot | Ghi chú |
|---|---|---|---|
| Fierce Dark (T3) | 9,062 | 8.8M (80th pct) / 13.9M cruiser / 36.3M frig | frig ×3 loot rõ |
| Chaotic Gamma (T5) | 29,815 | 107M trung bình | tăng nhờ Gamma phổ biến Gila |
| T3 Povertila elec | — | 6.3M profit/run (run mẫu) | rẻ, ổn định |
Drop rates từ data thật: filament cùng tier ~10-21%, mutant decayed ~13%, Survey DB 98%.

## 3. MUTAPLASMID LOTTERY (nguồn goon+reddit)
- Mutaplasmid GẮN WEATHER: Dark → prop mod mutas (đắt, "universally useful"),
  Gamma → shield mod mutas, Firestorm → armor, Electrical → cap/neutralizer,
  Exotic → misc. Chọn weather chạy = chọn lottery mình chơi.
- Đổi muta rủi ro 2 chiều: roll tốt ×5-10 giá; roll tệ mất giá module gốc.
  Người chơi nghiêm túc: bán muta thô cho trader, KHÔNG tự roll trừ khi biết rõ.
- Blueprint drop bất kể tier (frigate/cruiser/BS BPC ở cả T1 — CCP confirm).

## 4. RNG 3 TẦNG (nguồn: rant/forum — cái giá phải tính vào kế hoạch)
1. Spawn RNG: cùng 1 tier, room có thể "AFK win" hoặc "guaranteed loss" (ví dụ thật:
   Drifter BS 70km + 8 neut cruisers trong T3 — con Gila T4-ready suýt chết).
2. Loot RNG: multi-layer — từ can → nội dung → giá thị trường.
3. Server RNG: "Socket Closed" = mất cả chuỗi tiến trình không đền bù.
→ KẾT LUẬN KẾ HOẠCH BOT: T4/T5 cần mô hình "80% runs ok, 20% mất tàu" — lãi = số lượng
× EV, không phải từng run. Bot phải ĐO win-rate thật trên Singularity trước khi TQ.

## 5. DRONE AGGRO — CƠ CHẾ + QUY TẮC BOT (UniWiki Tips + Drone mechanics + forum T0 Tristan)
- Rats đổi aggro sang drone DỄ; drone dying = recall NGAY, đợi redbox (bị bắn) rồi launch lại.
- Trước khi launch: phải REDBOX (đã bị bắn) — launch sớm = drone bị nuke off-field.
- Trig/Sleeper/Drifter frigates + rogue drone frigs YÊU drone nhất (target drones often).
- Giữ drone leash 20-25km (sentry xa hơn) — xa leash = drone trả về chậm = chết.
- Nâng aggro về mình: DPS ship nhiều hơn, EWAR, spider tank, ở trong range của rats.
- Webbing frigs giết sớm — web tăng application lên drone + chậm recall.
- Drone bay ra ngoài control range → idle trôi về chậm (sublight) — "return and orbit" dùng MWD.
- "Reconnect to lost drones" (right-click ship) — bot sau mỗi room nên check drone count.
- Gila bonus 250% drone HP = gần như immune aggro; non-Gila frig drones dễ chết vcc.

## 6. CHI PHÍ & BREAK-EVEN (tổng hợp các nguồn)
- Filament T3 ~1-3M, T5 ~17M (Gamma rẻ hơn ~8M nhưng HP quái +50% = lâu hơn).
- Boosters/drugs ~15M/h (Standard Exile + Hardshell cho Gila).
- Ship cost trong kế hoạch: THROWAWAY philosophy — frig 40-50M/acc thì mất 20% fleet vẫn lãi;
  Gila 2B+ thì 1 lần chết xóa nhiều giờ lãi.
- Break-even point từng fit có trên abysstracker fit page (median ISK/run × runs needed).
