# FC PROTOCOL v1 — LLM chỉ ra lệnh chữ, script tự chạy phản xạ
> Quyết định của Boss 07/11/2026: KHÔNG computer-use trong vòng điều khiển.
> FC (LLM) = chỉ huy hạm: lệnh macro chữ + suy luận tình hình. Bot = thuyền trưởng: phản xạ 3Hz.
> v1 = viết lại sau khi học world model THẬT từ EVE UniWiki + keybind CCP + log forum AbyssBot.

## 0. World model (FC phải thuộc — nguồn: wiki.eveuniversity.org/Abyssal_Deadspace)

1. **3 phòng, 20 phút.** Gate sang phòng sau chỉ mở khi clear hết quái. Quá 20 phút từ lúc vào = nổ tàu + nổ pod. Mỗi phòng phải clear < 6.66 phút.
2. **Vào trong thì KHÔNG THỂ thoát**: không warp out, không cloak, không fleet warp tới, không local chat. "Thoát an toàn" duy nhất = clear 3 phòng; nếu không nổi → SURVIVAL MODE (tank + tốc độ + tiếp tục kill).
3. **Spawn cách gate 35–70km, quái đứng trên gate.** Biên vùng đỏ (danger zone) bay vào là nổ — orbit phải giữ trong vùng an toàn.
4. **Weather** (Dark/Electrical/Exotic/Firestorm/Gamma): penalty theo tier áp cho CẢ HAI bên; bonus +50% luôn có. FC đọc tên filament trước khi kích hoạt → chọn đạn/module.
5. **Điều kiện vào:** cách gate/station/depot ≥ 1000km, không trong deadspace, không logoff timer. Hết filament trong kho = bot báo FILA_MISSING, không retry vô hạn.
6. **Spool-up 15s + confirm dialog** sau khi bấm filament — bot chờ 15s rồi CONFIRM, không spam bấm.
7. **Loot:** Bioadaptive/Biocombinative Cache luôn có loot — loot trước khi rời.

## 1. Vai trò & tần số

| Side | Làm gì | KHÔNG làm | Tần số |
|---|---|---|---|
| FC (LLM) | đọc telemetry, ra macro, chỉnh param, quyết khi UNKNOWN, đọc weather → chọn module | click/vision thực thi | poll 10–30s + khi MAYDAY |
| Bot | lock/orbit/bắn/nạp/tank/gate/loot/confirm + SAFE_EXIT | đợi LLM trong combat | tick 0.3s |

Độ trễ LLM chịu được vì: mọi lệnh FC là **macro** — trong lúc LLM "nghĩ", bot vẫn tự combat theo lệnh cũ. Delay 15s chỉ đổi macro, không hỏng phản xạ.

## 2. Kênh file-based: `bus/fc_to_bot.jsonl` (lệnh), `bus/bot_to_fc.jsonl` (events)
Mỗi dòng 1 JSON. Tự trim giữ ~500 dòng cuối. FC đọc tail, bot poll tăng dần.

## 3. Command DSL v1 — mapping thẳng keybind thật của EVE

| Lệnh | arg | Keys bot bấm | Ghi chú game |
|---|---|---|---|
| `TARGET` | `nearest` \| 0–11 | focus overview (Alt+Space) → Ctrl+click row / arrow+Ctrl | lock quái |
| `APPROACH` | tên/idx | Q (với target đang chọn) | áp sát |
| `ORBIT` | mét | set default range + W | giữ transversal, né damage |
| `KEEP_RANGE` | mét | E | giữ khoảng cách (khi tank) |
| `ACTIVATE` / `DEACTIVATE` | slot 1–5 | F1–F5 (toggle) | bắn/tank/MWD |
| `RELOAD` | — | context menu module | ammo thấp thì nạp |
| `STOP` | — | Ctrl+Space | dừng tàu NGAY (khẩn) |
| `SPEED` | 0–100 | bật/tắt module MWD/AB | không có slider — map %→module |
| `GATE` | — | approach gate → D | chỉ hợp lệ khi ROOM_CLEARED |
| `DOCK` / `UNDOCK` | — | D tại station / Undock btn | ngoài abyss |
| `JUMP` | tên dest | S+click (warp) / D (gate) | ngoài abyss |
| `FILA` | tên filament | activate item → chờ spool → CONFIRM | precheck: ≥1000km từ station + có hàng |
| `CONFIRM` | — | nút confirm dialog | filament popup phải giữa màn hình |
| `LOOT` | — | loot wreck/cache (context) | sau khi EXIT room 3 |
| `SET` | `param value` | — | param runtime (xem §5) |
| `HOLD` | — | — | giữ nguyên mọi thứ |
| `ABORT` | — | — | trong abyss → SURVIVAL; ngoài → dock/warp home |
| `STATUS` | — | — | bot emit STATE ngay |

Bot REJECT lệnh lạ/lỗi arg — không crash, event `REJECT` kèm reason.

## 4. Event schema (bot → FC)

```json
{"t":"...","seq":12,"type":"STATE","phase":"ROOM2_FIGHT","room":2,"hp":0.86,"cap":0.73,
 "shield":0.9,"armor":0.55,"hull":1.0,"dist_gate":42000,"targets":3,"timer_left_s":712,
 "weather":"Dark","ammo":0.52,"unknown":false}
{"t":"...","type":"ROOM_CLEARED","room":2,"gate_open":true}
{"t":"...","type":"FILA_MISSING","reason":"không còn filament trong kho"}
{"t":"...","type":"TIMER_WARN","timer_left_s":298,"phase":"ROOM2_FIGHT"}
{"t":"...","type":"MAYDAY","reason":"UNKNOWN 45s","hint":"overview empty"}
{"t":"...","type":"SAFE_EXIT","mode":"survival","reason":"hp<25% trong abyss"}
{"t":"...","type":"SAFE_EXIT","mode":"warp_home","reason":"ABORT ngoài abyss"}
```

Phase FSM: `DOCKED → TRAVEL_ENTRY → FILA_SPOOL(15s) → ROOM1_FIGHT → ROOM1_CLEARED → GATE_TRANSIT → ROOM2_FIGHT → ... → EXIT → LOOT → WARP_HOME → DOCKED`

STATE kèm tóm tắt số (không ảnh) → FC đọc rẻ về token.

## 4b. Combat doctrine (nạp từ eve-abyss-mechanics — bot phải biết chơi, không chỉ bắn)

**Thứ tự bắn (bot ưu tiên lock theo thứ tự):**
1. EWAR nguy hiểm mình: **web > neut > scram/tracking-disrupt > painter** (tên quái trong overview cho biết loại: Entanglem/Entangling = web, Dissipator = neut, Scylla = web/scram)
2. Remote-repair ships (giết con nhỏ TRƯỚC khi repair kịp land)
3. Damage dealers gây damage vào resist hole theo weather (Electrical→EM dealer trước, v.v.)
4. Battleship "Karen" (Karybdis Tyrannos): manual bay chéo 45°, KHÔNG approach thẳng (alpha wrecking giết cruiser); herd (bay hướng gate để kéo nó về) vì nó bay trốn

**Quái KHÔNG cần giết:** Vila Swarmers (giết mothership là tụi nó tắt, gate vẫn mở), rogue drones lẻ — bot bỏ qua, đừng phí DPS/timer.

**Loot doctrine:** Bioadaptive Cache 300 HP chỉ cần 1 đạn — phá khi bay NGANG đường tới gate (không đi vòng); bỏ Extraction Node trừ khi còn >4 phút dư và đúng đường. Run gần 15' → không loot room 1 quá kỹ.

**Movement:** sau khi vào room, bay chéo khỏi hướng spawn (không bay thẳng vào mặt quái), orbit/keep-range theo fit; KHÔNG bay vào cloud (trắng ở Dark = chết), KHÔNG lấn vùng đỏ.

**Timer:** còn warn_timer_left → bỏ loot, chain gate liền. Đây là lệnh FC ra, bot chỉ emit TIMER_WARN.

Skill `eve-abyss-mechanics` + `eve-abyss-strategy` là nguồn đầy đủ — FC (LLM) load 2 skill đó để ra quyết định chiến thuật; bot chỉ cần thứ tự bắn ở trên để phản xạ lock/priority.

## 5. Param runtime (`SET`)

| Param | Mặc định | Nhỏ | Lớn |
|---|---|---|---|
| `escape_hp` | 0.25 | 0.05 | 0.9 |
| `unknown_timeout` | 45s | 10 | 300 |
| `orbit_default` | 2500 | 500 | 20000 |
| `humanize` | true | — | — |
| `tick_interval` | 0.3 | 0.1 | 2.0 |
| `warn_timer_left` | 300s | 60 | 1200 |

## 6. An toàn

1. SAFE_EXIT **không tắt được** — chỉ SET đổi ngưỡng. Trong abyss: SURVIVAL là floor (không đứng im ăn đòn, không tự sát bằng warp-into-red).
2. Bot độc lập FC: FC chết → bot giữ phase + survival khi cần.
3. Chỉ chạy **test server**. Acc test riêng không tài sản quý. Live = EULA 2-strike (3 ngày → vĩnh viễn) — KHÔNG chạy.
