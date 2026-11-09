# Enemy DB — mọi quái Abyss theo tên + EWAR + priority (nguồn UniWiki 2026-11-07 dump)

> Implement code: D:/fila-bot/src/fila_bot/rats.py + tests/test_rats.py (23 test).
> Bot classify theo TÊN trong overview → priority lock.

## Priority chuẩn
0=SKIP (Vila Swarmer — ko cần giết, gate vẫn mở) · 1=WEB · 2=NEUT · 3=SCRAM+LOGI · 4=PAINT/TD/DAMP · 5=BS đặc biệt (DPS race/đổi đạn) · 6=DPS dealer
Thứ tự tuyệt đối: web → neut → scram → logi (giết frigate nhỏ trước khi repair kịp land) → paint/td → DPS. BS xử riêng theo loại.

## Rogue Drones (suffix Tessella=frig / Tessera=BC / Overmind=BS)
| Prefix | Damage | | Tên | EWAR/Role |
|---|---|---|---|---|
| Spark | EM | | Snarecaster | WEB |
| Ember | Therm | | Fogcaster | Tracking Disrupt |
| Strike | Kin | | Gazedimmer | Sensor Damp |
| Blast | Exp | | Spotlighter | Target Paint |
| needle = dmg thấp | | | Fieldweaver | Remote SHIELD logi (0 dmg) |
| lance = dmg x2 | | | Plateforger | Remote ARMOR logi (0 dmg) |
| grip Tessera = BC dmg cực, range <15km | | | |
Overmind theo tier (đổi đạn khi đánh): T1 Photic=Exp · T2 Twilit=Therm (kin resist rất cao) · T3 Bathyic=Therm/Kin · T4 Hadal=Exp · T5 Benthic=Therm/Kin · T6 Endobenthic=Therm/Kin. T4 có tracking 4.33 (khó speed-tank nhất); T5/T6 có web.
Gimmick: BS orbit theo frigate dps dealer của nó → kéo BS lại gần (có lợi cho AB fit).

## Drifters + Seekers
- BS **Karybdis Tyrannos** ("Karen"): omni dmg, bay trốn 300m/s kéo mình ra rìa → NÓI CHÉO 45°, herd về gate; T3+ alpha nặng, spawn sẵn 40% shield/33% armor/48% hull (Frontline ~41/24/45). Không có doomsday/EWAR. Gimmick: orbit theo Ephialtes Lancer nếu có trong room.
- Cruiser **Scylla Tyrannos** (tên phe Drifter — phải xem TYPE): Entanglement=web, Nullwarp=scram, Nullcharge=neut.
- Seeker (prefix **Ephialtes**): Lancer=dps, Entangler=web, Spearfisher=scram, Illuminator=paint, Dissipator=neut, Obfuscator=damp, Confuser=Turret+Missile Disrupt.
- Drifter cruiser spawn sẵn 24% shield/14% armor (50% Firestorm)/30% hull.

## Sleepers (prefix **Lucid**) — TẤT CẢ đều có remote repair → giết con NHỎ trước khi repair land
| Frigate | | Cruiser | | BS |
|---|---|---|---|---|
| Escort | dps | Watchman | dps | **Deepwatcher** (paint; T1/T2 đơn, T3/T4 đôi, T5/T6 ba) |
| Aegis | dps mạnh | Upholder | WEB | |
| Warden | WEB | Sentinel | NEUT | |
| Firewatcher | NEUT | | | |
| Preserver | STRONG logi | | | |
Deepwatcher: 50% armor (65% Firestorm), 65% hull, EM/Therm turret tracking TỆ + Kin/Exp missile application tệ → orbit <10km là né gần hết. Tank mạnh nhất game — timeout killer.

## Triglavians (dmg Thermal/Explosive, RAMP damage giữ target lâu)
Hull: Damavik (frig nhanh, sig to) · Kikimora (destroyer nhanh range xa) · Vedmak (cruiser đau) · Rodiva (cruiser logi) · Drekavac (BC, spawn 37/69/11) · Leshak (BS range xa, spawn 46% hull, 0 shield/armor; +40% armor Firestorm).
| Prefix | EWAR |
|---|---|
| Striking | dps (không RR) |
| Starving | NEUT, không RR |
| Harrowing/Shining | paint (Ngoại lệ: Harrowing Vedmak KHÔNG paint) |
| Anchoring | SCRAM |
| Renewing | strong RR |
| Blinding | damp |
| Tangling | WEB |
| Ghosting | Turret+Missile Disrupt |
| X Vila Y | spawn 3-4 Vila Swarmer (10-20 dmg mỗi phát, bỏ qua) |

## Sansha (prefix **Devoted**, EM/Therm, chậm — đánh range xa)
Cruiser: Knight = web+neut+heavy dps (newbie killer — counter: orbit 500 + tắt local rep).
Frigate: Hunter=dps x1.5, Fisher=web, Priest=logi, Trapper=scram, Smith=neut, Lookout=damp, Herald=TD, Torchbearer=paint.

## CONCORD + EDENCOM (suffix **Disparu Troop**) — DPS race, phi thuyền tank mỏng
CONCORD: Pacifier frig 39dps rocket, Enforcer cruiser 130dps HAM, Marshal BS 427dps Rapid Heavy — prefix: Attacker/Assault=dps, Arrester=WEB, Marker=paint, Drainer=neut nặng. Spawn sẵn: Marshal 0 shield/28% armor; Thunderchild 8/0/40.
EDENCOM (Vorton chain 10km — đứng gần bạn nó = tự làm FRIENDLY FIRE): Skybreaker 444dmg/6s EM-Kin, Stormbringer 666/9s Kin-EM, Thunderchild 2470/15s Kin-EM alpha to.
- Không bao giờ wrecking shot (dmg cố định theo sig/vel), missile = transversal vô nghĩa.

## Angels (prefix **Lucifer**, EM/Exp, nhanh nhất abyss — bane của speed-tank)
(Elite) Cynabal = web+neut+dps (giết đầu tiên) · Ixion = paint+missile disrupt · (Elite) Dramiel = dps (elite có web) · Fury=neut, Echo=web+scram, Medusa=damp, Burst=shield logi, Swordspine=paint.
T4+ web mình đứng im → đừng speed-tank.

## Damage theo weather (wiki "Damage to deal")
Electrical→EM · Exotic→Kinetic · Firestorm→Thermal · Gamma→Explosive · Dark: không resist hole, dùng dmg mạnh nhất fit (Triglavian yếu Exp→Therm).
Resist tự nhiên: Sansha (trừ Knight) yếu EM/Therm; Angel yếu Exp/Kin; Triglavian yếu Exp→Therm; CONCORD đều; EDENCOM yếu Therm/EM; Drifter/Sleeper đều (uniform).
