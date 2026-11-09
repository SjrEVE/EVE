---
name: eve-abyss-mechanics
description: "Facts về Abyssal Deadspace khi code/test fila-bot."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [eve, abyss, game-knowledge, fila-bot]
---

# EVE Abyssal Deadspace — World Model (sự thật game, có nguồn)

## When to Use
Load khi code FSM/decision/test cho fila-bot, khi Boss hỏi cơ chế abyss (phòng, timer, weather, enemy, loot), hoặc khi cần verify một hành vi in-game có thật trước khi đưa vào bot.

Skill này chỉ chứa FACT GAME. Khi cần ground UI tree/client thật, build lại DLL đọc memory, hoặc đối chiếu attr perception: nạp skill `llm-fc-bot` rồi đọc file tham khảo `abyss-ui-tree-attrs.md` của nó (schema đã verify + recipe dump/build).

## Enemy DB đầy đủ (7 phe, mọi ship name + EWAR + priority lock) nằm ở `references/abyss-enemy-db.md` — ĐỌC TRƯỚC khi làm bất cứ việc gì liên quan rats/lock target. Code: fila_bot/rats.py (27 test PASS).

### Bổ sung từ nguồn sâu hơn (Gustav "All 18 Rooms" LJBCZ4fwxKA + Abyss Tracker cheat-sheet)
- **Ramp rate Triglavian**: Vedmak/Damavik/Leshak 4%/cycle · Kikimora 2% · Drekavac 1% · Vila 0.75% (bot đếm cycle đổi target).  Tổng room types = 18 (6 Trig + 4 Drone + 5 Sleeper/Drifter + 3 Empire/Pirate).
- **NO TARGET SWITCH**: Kikimora, Drone frig/BC (Tessella/Tessera), Vila Vedmak, Lucid Aegis/Escort — chúng cắn người đầu tiên rồi cắm mặt. Multibox dùng làm tank-magnet; bot solo: con đầu vào room là con KHÓA MÌNH — chọn spawn angle cho tank accept.
- **Karen (Karybdis)**: cheat sheet Abyss Tracker = SPIRAL vào <30km (UniWiki FAQ: <10km orbit close nó không hit nổi). Goon wiki nói herd về gate — NGUỒN MÂU THUẪN, verify in-game trước khi tin 1 bên.
- **Overmind tier mapping MÂU THUẪN**: UniWiki (Photic T1 → Endobenthic T6 theo thứ tự tier) vs AbyssTracker (Photic/Twilit/Hadal T0-3, Bathyic/Benthic/Endobenthic T4-6) — VERIFY in-game khi có client.
- **Marshal**: HP thấp (cheat sheet) — giết nhanh hơn là kite; Attacker Marshal + EDENCOM tụ quanh 1 "commander" ship (Gustav).
- **Tessera BC**: damage + tracking cực, optimal ngắn → giữ >12km.
- **CONCORD room**: toàn Explosive — giữ speed cao tới khi room checked; Vorton chain = friendly fire exploit.
- **Vila drones**: kill Triglavian mothership = tắt drone; drone chết = spawn mới (chỉ kill mothership).

**Chiều MÌNH (fit/tank/application/movement đối ứng) nằm ở D:/fila-bot/docs/OWN_SIDE_MECHANICS.md — tra cùng enemy-db khi quyết fit/đạn/orbit.**

**Chiều TAY (keybind thật + ActionSpec verify-after-press) nằm ở D:/fila-bot/docs/CONTROL_LAYER.md — code: control.py/keys.py/input.py (11 test). Mọi action phải bấm theo keybind này + verify qua eye trước khi coi là xong.**

**ROOM × WEATHER × LOOT ma trận (entry move + kill order + loot policy từng room, grace 15-20s, exit invul 60s) nằm ở D:/fila-bot/docs/ROOM_PLAYBOOKS.md + code rooms.py (31 test) — ĐỌC trước khi quyết định in-room bất cứ room nào.**

**KINH TẾ + RNG + DRONE AGGRO (CCP dev AMA số liệu: spawn FLAT, T4 80%/T5 60% success; mutaplasmid gắn weather; drone aggro rules + redbox trước launch) nằm ở D:/fila-bot/docs/ECONOMICS_RNG.md + code drone.py (8 test).**

> Nguồn: EVE UniWiki (Abyssal_Deadspace, Possible_rooms, FAQ), Goon Wiki, dev blog CCP, thonky (typeID).
> Dùng khi code/test bot: mọi FSM/decision phải bám vào các fact này, không bịa.

## Cấu trúc instance
1. 3 phòng (pockets). Gate tên: Transfer Conduit (giữa phòng), Origin Conduit (phòng 3 về nhà), Proving Conduit (event).
2. Gate đóng cho tới khi clear hết quái (NGOẠI LỆ: Vila Swarmers không cần giết — giết mothership là chúng tắt, gate vẫn mở; rogue drone tương tự có thể bỏ sót).
3. Spawn cách gate 35–70 km; quái đứng 0 m trên gate.
4. Timer 20 phút từ lúc filament nhảy. Quá = nổ tàu + nổ pod. Trung bình mỗi phòng phải < 6.66 phút.
5. Vùng đỏ (danger ring) ngoài rìa phòng — bay vào là nổ. CLOUDS trắng/đỏ có hiệu lực cục bộ (neut/web/damage) — KHÔNG bay xuyên cloud, đặc biệt cloud trắng ở Dark.

## Điều kiện vào (precheck bắt buộc cho lệnh FILA)
- Ở space (không dock), không có logoff timer, không trong deadspace khác.
- Cách mọi gate/station/depot/trace khác ≥ 1000 km.
- Hệ sec: 1.0/0.9 KHÔNG dùng được filament abyss; T4–T6 ở hệ 0.8+ → suspect flag khi ra.
- Fleet: frigate cần 3 filament + fleet (fleet 1 người vẫn được); cruiser 1 filament, không cần fleet.
- Spool-up 15 s rồi có confirm dialog.

## Weather (5 loại; penalty theo tier: T0–T3 roll 30/50%, T4–T6 roll 50/70%; bonus luôn +50% cho cả mình lẫn quái)
| Weather | Penalty | Bonus |
|---|---|---|
| Dark | -30/50/70% turret optimal+falloff (CẢ DRONE) | +50% max velocity |
| Electrical | -EM resist | -50% cap recharge time |
| Exotic | -Kinetic resist | +50% scan res |
| Firestorm | -Thermal resist | +50% armor HP |
| Gamma | -Explosive resist | +50% shield HP |

Hệ quả thiết kế fit: Dark → dùng missile (Kestrel/Hookbill/Gila), tránh turret/drone. Electrical → chống EM. Firestorm → Sacrilege/Ikitursa hợp.

## Yêu cầu sức mạnh theo tier (cruiser, UniWiki FAQ)
| Tier | DPS cần | EHP/s cần |
|---|---|---|
| T0 | 100 | 50 |
| T1 | 150 | 150 |
| T2 | 300 | 300 |
| T3 | 450 | 450 |
| T4 | 600 | 600 |
| T5 | 750 | 750 |
| T6 | 850 | 950 |

## Loot
- Triglavian Bioadaptive Cache: 300 HP, chứa loot chính của phòng (multiplier ×3/×2 cho frigate/destroyer runs).
- Extraction Node/SubNode: loot phụ, không bảo đảm; bỏ qua nếu chạy tier thấp hoặc thiếu giờ.
- Không có wreck từ NPC — loot chỉ ở 2 loại can trên.
- Cache có thể phá bất kỳ lúc nào (gate mới bị khoá theo clear) — playbook thường: bay qua cache khi chạy tới gate, phá + loot nhanh khi thuận đường.

## Enemy & thứ tự bắn (UniWiki + Goon)
1. EWAR đe dọa mình trước tiên: web > neut > scram/tracking disrupt > target painter (web nguy hiểm nhất nếu dùng AB/speed tank; neut nguy hiểm nếu active tank cap-hungry).
2. Remote repair ships (Sleeper luôn có RR) — giết nhỏ trước khi repair kịp land.
3. Damage dealers theo loại damage bất lợi cho resist hole của mình.
4. Karybdis Tyrannos ("Karen", battleship sleeper): phòng khó nhất. Alpha wrecking lúc mới vào — bay chéo 45°, giết web/neut escort trước (Scylla/Ephialtes/Entanglem/Dissipator). Karen doctrine MÂU THUẪN nguồn (xem bullet Karen đầu skill): AbyssTracker/UniWiki FAQ = spiral vào <30km (<10km nó không track nổi); Goon = herd về gate — CHƯA verify in-game. Dark T5+ không học Karen đừng vào.
5. Dusma/Damavik/Overmind: kiểu bay trốn tương tự, xử cùng nguyên tắc.

## Filament (typeID mẫu, thonky)
- Tên tier: Tranquil (T0), Calm (T1), Agitated (T2), Fierce (T3), Raging (T4), Chaotic (T5), Cataclysmic (T6) + weather (Dark/Electrical/Exotic/Firestorm/Gamma).
- typeID ví dụ: Agitated Dark 47892, Agitated Gamma 47900, Calm Gamma 47764, Chaotic Exotic 47891, Fierce Exotic 47889, Fierce Gamma 47901, Raging Exotic 47890, Tranquil Exotic 56133.
