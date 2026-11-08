# Chiều MÌNH — ship/fit/tank/application (nguồn UniWiki + Abyss Tracker + Reddit fits)

> Rats DB = chiều địch (skill eve-abyss-mechanics / references/abyss-enemy-db.md).
> File này = chiều mình. Khi quyết fit/đạn/movement: tra cả 2.

## 1. Hai phép tính quyết định sống/chết

### Turret application (và đọc ngược: quái bắn mình)
Chance to hit = 0.5^[( Angular×40,000/(Tracking×Sig) )² + ( max(0,Dist−Optimal)/Falloff )²]
- Angular = transversal/dist (rad/s). Angular == Tracking → 50% hit, ~40% dmg.
- Bot giữ: Angular cao so với tracking của THẰNG ĐANG BẮN MÌNH (orbit chặt), nằm trong optimal+falloff của mình.
- Karen/Overmind/Deepwatcher = turret BS tracking tệ → orbit gần; CONCORD/EDENCOM = missile → **transversal vô nghĩa với chúng**, không kite được, phải DPS race.

### Missile application
Damage = D × min(1, S/E, (S×Ve/(E×Vt))^drf)
- Bắn quái nhanh/sig nhỏ → cần Ve cao/E nhỏ (light missile ăn frigate; heavy ăn cruiser).
- Quái đứng (Marshal, Karen, cache 300HP) → full dmg.
- Mình nhận missile (CONCORD/EDENCOM): giảm **speed + sig** mới đỡ được — giữ angular không có tác dụng.

## 2. Localized effects (phải né/hai lợi dụng)
| Cloud/Tower | Hiệu ứng | Hành vi bot |
|---|---|---|
| Filament (cam) | shield booster −40% hiệu quả/+66% cost | active shield tank không bay vào |
| Bioluminescence (xanh) | ×4 signature | speed-tank TRÁNH; có thể lùa quái nhỏ vào để dễ bắn |
| Tachyon (trắng) | ×4 vel + ×0.5 inertia = ×8 accel | **MWD vào = slingshot ra vùng đỏ chết ngay**; drone application chết |
| Deviant Automata Suppressor (40km/15km) | GIẾT drone + light missile | kéo drone ra khỏi radius |
| Multibody Tracking Pylon (+60/80% tracking) | cả quáiKaren/Overmind track tốt hơn | speed-tank tránh như biển báo đỏ |

## 3. Fit archetype Gila (chuẩn mọi nguồn hội tụ)
- [High] 4× Rapid Light Missile II + Drone Link Augmentor
- [Mid] RF 10MN Afterburner (MWD bị phạt sig — chỉ fit chuyên dụng), 2-3× Large Shield Extender II, amp theo weather hole (Pithum A-Type Therm giữ nguyên mọi site — ăn Trig spawn nguy hiểm nhất), Adaptive Invuln tùy
- [Low] 3× Beta Reactor Control SPR + DDA II (+BCS)
- [Rig] 3× Medium Core Defense Field Purger (passive regen)
- Drones faction/Augmented: HP + tracking cao — KHÔNG recall khi bị đánh (DPS loss; con bị đánh thì tank mình đỡ hơn)
- Số liệu fit 234 Abyss Tracker (2.1B): Gamma T5 median 42.09M/run, 14:35, 173.16M ISK/h; cheap 1B chạy T4/5 Gamma/Firestorm; Dark max T5

## 4. Tank math cho FSM
- **Passive shield Gila** (~540 hp/s regen): SURVIVAL ngưỡng shield <40%; PANIC armor <50% (armor không regen — buffer cạn là chết); structure = đã chết
- **Active armor**: theo cap — cap <30% → tắt web/prop giữ rep; hết cap = hết tank = chết
- **Buffer tank**: thời gian sống = EHP/incoming DPS; <60s còn sống → chain gate NGAY
- Weather tác động tank: Firestorm +50% armor (quái Trig +40% thêm → TTK dài, tránh room nhiều Trig BS); Gamma +50% shield (buffer passive Gila cũng phình +50%)

## 5. Ammo doctrine
- Mặc định theo weather: Electrical→EM? **KHÔNG** — fit Gila chuẩn: Kinetic cho Exotic, **Thermal cho mọi site còn lại** (kể cả Gamma/Electrical) — bonus Gila + Therm ăn Trig/CONCORD spawn nguy hiểm nhất
- Overmind BS: **đổi đạn giữa combat** (Exp T1/T4, Therm T2/T5/T6, Therm+Kin T3) — reload 10s đáng đổi
- Prep trước FILA: đủ ~300 đạn/phòng × 3

## 6. Chiều mình × chiều địch → quyết định movement theo phe
| Phe bắn mình | Cơ chế | Nước đi |
|---|---|---|
| Triglavian (ramp) | dmg tăng theo thời gian giữ target | đổi target mỗi ~20s hoặc giết Vedmak trước |
| Sansha (EM/Therm, chậm) | web+neut Knight | orbit 500 quá close web không bắt; range xa |
| Angel (nhanh nhất) | web T4+ đứng im | đừng speed-tank; buffer bền |
| CONCORD missile | transversal vô nghĩa | giảm sig; tránh Bioluminescence; DPS race |
| EDENCOM vorton | chain 10km | đứng cạnh con EDENCOM khác = friendly fire exploit |
| Sleeper Deepwatcher | missile application tệ close | orbit 5-8km |
| Drone BS Overmind | tracking theo tier (T4 4.33 cao nhất) | AB fit orbit close; T5/T6 có web — buffer |

## 7. Map fit → params fila-bot
- orbit_default: <10km vs Deepwatcher; 10-20km generic; 500 vs Sansha Knight
- escape_hp: 0.4 (Gila passive), 0.5 (active armor)
- warn_timer_left: 240s (T5 room dài — chain sớm)
- tick 0.3s + humanize: giữ nguyên
