# CONTROL LAYER — quyết định → input thật (keybind UniWiki Havoc 21.06, dump 2026-11-07)

> Chiều thứ 3: chiều địch (enemy-db) + chiều mình (OWN_SIDE_MECHANICS.md) + **chiều tay** (file này).
> Code: `src/fila_bot/control.py` (ActionSpec + execute + verify) + `keys.py` + `input.py`. Test: `tests/test_control.py` (11 PASS).

## Keybind thật của EVE (default, UniWiki "Keyboard controls")

### Combat / Nav
| Hành động | Phím | Ghi chú cho bot |
|---|---|---|
| Approach | **Q** | cần target đang chọn (click entry trước) |
| Orbit | **W** + gõ km + Enter | có dialog nhập khoảng cách |
| Keep at Range | **E** + gõ km + Enter | dùng khi tank |
| Warp to | **S** | ngoài abyss; trong abyss KHÔNG dùng |
| Align | **A** | ít dùng trong abyss |
| Dock/Jump/Gate | **D** | gate/bay vào station |
| Lock target | **Ctrl** (+click entry) | hiện đại: click chọn → Ctrl toggle lock |
| Unlock | **Ctrl+Shift** | |
| Stop ship | **Ctrl+Space** | khẩn cấp |
| Focus overview | **Alt+Space** | chơi bàn phím thuần |
| Select next/prev target | **Alt+Right/Left** | chọn target không cần click |
| Tactical overlay | **Ctrl+D** | xem spawn layout |

### Modules
| | High | Mid | Low |
|---|---|---|---|
| Bật/tắt | **F1–F8** | **Alt+F1–F8** | **Ctrl+F1–F8** |
| Overheat | **Shift+F1–F8** | **Alt+Shift+F1–F8** | **Ctrl+Shift+F1–F8** |
| Overheat cả rack | Ctrl+3 | Ctrl+2 | Ctrl+1 |
| Reload | **Ctrl+R** | | |

### Drones (Gila phụ thuộc drone — phải biết)
| Lệnh | Phím |
|---|---|
| Launch | **Shift+F** |
| Engage target đang lock | **F** |
| Return and Orbit | **Shift+Alt+R** |
| Return to Bay | **Shift+R** |
| Aggressive/Passive | (không default — map trong settings nếu cần) |

### Dialog
- **Enter** = Confirm (unmodifiable) — filament confirm dialog
- **Esc** = đóng dialog/cancel

## Kiến trúc ActionSpec — bấm có VERIFY, không bấm mù

```python
ActionSpec(name, steps, verify_fn, retry_max, verify_wait)
execute(spec, eye, dry) → {ok, attempts, input_log, verified}
```

- **steps**: chuỗi input (`combo`/`click`/`type`/`wait`) — keybind thật 100%
- **verify**: đọc eye (UI tree) kiểm tra game ĐÃ NHẬN lệnh chưa —VD: lock xong phải thấy `targetedByMe` trên entry; module bật xong `isActive=True`; confirm xong dialog biến mất
- **retry**: verify fail → bấm lại (max retry_max) → vẫn fail → emit event cho FC, KHÔNG crash
- **humanize**: mọi phím/click có jitter ±50% — nhịp không máy móc

### Verify checklist theo action (map với eye.py)
| Action | Verify qua eye |
|---|---|
| lock | entry indication `targetedByMe=true` |
| module on/off | `module_buttons()[slot].is_active` đổi trạng thái |
| approach/orbit | `maneuver()` = approach/orbit |
| gate jump | `maneuver()` = jump rồi room đổi |
| confirm dialog | `confirm_dialog()` = None sau bấm |
| drones engage | DroneView entries đổi trạng thái |
| undock | ShipUI xuất hiện (đang dock thì không có) |

## Chuỗi control cho các combat action hoàn chỉnh (từ enemy-db + own-side)

1. **Lock đúng ưu tiên**: overview entries → rats.lock_order() → lấy entry đầu chưa lock → click + Ctrl → verify targetedByMe
2. **Kiting**: target XY → W + km (theo OWN_SIDE: 5–8km Deepwatcher, 500 Sansha Knight, 10–20 generic) → verify maneuver=orbit
3. **Bắn**: module RLM (high F1–F4) đang on; drone Shift+F launch 1 lần đầu room → F engage sau mỗi lần lock target mới
4. **Defensive**: hp ngưỡng → Alt+F1 (hardener mid slot) verify is_active; cap thấp → tắt prop (Alt+F2 off)
5. **Gate**: quái hết (overview trừ cache) → click gate entry + D → verify maneuver=jump → ROOM_N+1
6. **Filament**: cargo → click filament trong inventory (eye tìm node) → đợi 15s spool → Enter confirm → verify KeyActivationWindow biến mất + grid đổi
7. **Panic**: Ctrl+Space stop (dừng进食 Karen alpha) → tank on → emit MAYDAY
