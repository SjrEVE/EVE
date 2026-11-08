# OPERATOR PROTOCOL v2 — bot tự trị 100% thuần Python

> v2: bỏ FC/LLM (Boss chốt: không có tiền chạy LLM =)) — bot tự quyết mọi thứ,
> ngâm toàn bộ chiến thuật vào bảng cứng (rats/rooms/guards) thay vì suy luận.

## 0. World model (bot thuộc lòng — nguồn: wiki.eveuniversity.org/Abyssal_Deadspace)

1. **3 phòng, 20 phút.** Gate mở khi clear hết quái. Quá 20' = nổ tàu + nổ pod.
2. **Không thoát được** (không warp/cloak/local) → hp thấp = SURVIVAL, không warp-out.
3. Spawn 35–70km từ gate, quái đứng trên gate. Vùng đỏ + cloud = chết/đau.
4. **Weather** 5 loại — bot đọc tên filament → chọn ammo/behavior theo bảng rooms.py.
5. Vào: ≥1000km từ station/gate, không deadspace, không logoff timer. Hết filament = FILA_MISSING, không retry.
6. Spool 15s + confirm — CHỈ confirm khi eye thấy dialog (không bấm theo timer).
7. Cache 300HP = 80% giá trị; node phụ, không tham (guards chặn).

## 1. Vai trò (1 cái duy nhất)

| Side | Làm gì | Tần số |
|---|---|---|
| **Bot (python)** | mọi thứ: nhìn (eye), quyết (combat_brain + guards + rooms), bấm (control), tự vệ (SURVIVAL), loot, gate | tick 0.3s |

Không có "chỉ huy ngoài" — KHÔNG LLM, KHÔNG cloud, KHÔNG subscription. Chạy offline.

## 2. Kênh: `bus/` chỉ còn là LOG (outbox) để người xem + debug
- `bot_to_fc.jsonl` → đổi tên thành **`events.jsonl`** (log events thuần, không ai trả lời)
- `fc_to_bot.jsonl` → **BỎ**. Người muốn can thiệp: PAUSE/STOP bằng hotkey (Ctrl+Shift+Space, issue #1 P2-4) hoặc sửa config.

## 3. Autonomy ladder (thứ tự quyết định mỗi tick)

1. **guards.py** — 9 cái chết: overview-empty, loop, drones-out, cloud, cap, damping, greed, wrong-filament, drift → an toàn trước mọi thứ
2. **rooms.py playbook** — entry move theo room type × weather
3. **combat_brain.py** — rats.lock_order → lock/orbit/activate
4. **drone.py** — redbox-launch, leash, recall
5. **reflex FSM** — phase machine (spool/confirm-by-eye/gate/timer)
6. Tất cả fail-closed: thiếu thông tin → dừng + log, không đoán

## 4. Event schema (log-only)

```json
{"t":"...","seq":12,"type":"STATE","phase":"ROOM2_FIGHT","room":2,"hp":0.86,...}
{"t":"...","type":"ROOM_CLEARED","room":2}
{"t":"...","type":"GUARD","guard":"cap_starve","action":"power_save","reason":"..."}
{"t":"...","type":"MAYDAY","reason":"UNKNOWN 45s"}
{"t":"...","type":"SAFE_EXIT","mode":"survival","reason":"..."}
```

## 5. Params (`config.yaml` — không còn SET qua bus)

| Param | Mặc định | Ý nghĩa |
|---|---|---|
| `escape_hp` | 0.25 | hp dưới ngưỡng → SURVIVAL/warp_home |
| `unknown_timeout` | 45s | UNKNOWN quá lâu → MAYDAY + survival |
| `orbit_default` | 2500 | mét orbit mặc định |
| `humanize` | true | jitter + (kế hoạch) trajectory cong |
| `tick_interval` | 0.3 | chu kỳ tick |
| `warn_timer_left` | 300 | mốc báo timer |
| `max_session_hours` | 8 | khuyến nghị EVE Master: không 24/7 |

## 6. An toàn

1. SURVIVAL là floor — không tắt được.
2. Kill-switch nóng: Ctrl+Shift+Space (P2-4) + PAUSE/STOP từ UI.
3. Fail-closed: thiếu ground → dừng + log, không đoán.
4. CHỈ test server (Singularity) + acc rỗng. Live = EULA 2-strike.
