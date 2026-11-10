# Audit toàn bộ UI/UX + Mechanic — fila-bot (2026-11-10)

Rà soát toàn bộ `src/fila_bot` + CLI + GUI + launcher. Mỗi mục dưới đây là **lỗi thật đọc
ra từ code**, không phải góp ý phong cách. Cột "Chứng minh" là lệnh/test đã chạy lại.

## P0 — Mechanic sai (bot không chạy được / chạy sai)

| # | Lỗi | Hậu quả thật | Sửa | Chứng minh |
|---|---|---|---|---|
| 1 | `AbyssMode._drive()` **thiếu nhánh `FILA_SPOOL`** | FSM kẹt vĩnh viễn ở FILA_SPOOL, `runs` luôn 0, không bao giờ vào abyss. Đây là lý do `ui --smoke` treo ở FILA_SPOOL | thêm `elif p == "FILA_SPOOL": self._cmd("CONFIRM")` | `cli abyss --engine fsm --max-runs 1` → `[OK] Hoan tat 1 run` |
| 2 | `AbyssMode._drive_bt()` chặn `max_runs` **trước cả lệnh DOCK** | tàu kẹt ở `WARP_HOME` mãi mãi sau run cuối | chỉ chặn bắt đầu run mới khi `phase == "DOCKED"` | `cli abyss --engine bt --max-runs 1` → về DOCKED, exit 0 |
| 3 | `LiveDistributionRunner.refresh()` **bịa `cargo_free = 400.0`** | `accept_rule` thấy "đủ chỗ" dù chưa mở Inventory → nhận mission có thể vượt cargo | trả `None` khi chưa đọc được; mode mở Inventory rồi thử lại | `test_ux_guards` #3 |
| 4 | `LiveDistributionRunner.refresh()` **bịa `route_hisec = True`** | nhận mission đi qua lowsec vì tưởng hisec | `route_hisec_value()`: chỉ `True` khi cùng hệ + sec ≥ 0.5 + 0 jump; còn lại `None` → block; `--allow-unknown-sec` để bỏ qua có ý thức | `test_ux_guards` #4, #6 |
| 5 | `apply("load_cargo")` kéo **`items[0]`** | kéo item đầu tiên (ammo/ore) vào cargo thay vì item mission | `pick_item_xy(items, mission_item)`; không khớp → không kéo (fail-closed) | `test_ux_guards` #5 |
| 6 | `DistributionMode` block **ngay tick đầu** khi chưa mở Inventory | bot dừng vĩnh viễn dù chỉ cần mở kho | `open_inventory` + `CARGO_RETRY = 8` rồi mới block | `test_ux_guards` #3, `test_distribution` |

## P0 — CLI/UX sai (treo, in sai, tham số bị bỏ)

| # | Lỗi | Hậu quả thật | Sửa |
|---|---|---|---|
| 7 | CLI chờ `sup.state in ("STOPPED","BLOCKED")` | `Supervisor` **không có** 2 trạng thái đó (chỉ IDLE/RUNNING/PAUSED/STOPPING) → `distribution --live` chạy vô hạn, timeout 124 | `_watch()` dừng theo `mode.status()["blocked"]`, `phase == "IDLE_DONE"`, abyss `max_runs`/hết filament; trả mã 0/3/130 |
| 8 | `--filament` chỉ **in ra**, không truyền vào mode | chọn Cataclysmic nhưng bot dùng Tranquil Exotic | `build_supervisor(..., filament=...)` → `AbyssMode(filament=...)` |
| 9 | `--max-missions` gán **sau** khi build, dễ trôi | mode không giới hạn đúng | truyền thẳng vào `DistributionMode(max_missions=...)` |
| 10 | `cmd_status` đọc `ship_health["hull"]` | key thật là `structure` → luôn in `Hull 0.0%` | in `Structure` |
| 11 | Eye/DLL lỗi → **traceback thô** | Boss thấy stack trace thay vì "mở EVE lên" | `_build()` bắt `RuntimeError/OSError` → `[FATAL] ... Mo EVE Online...`, exit 2 |
| 12 | `abyss --live` quảng cáo "LIVE" nhưng driver chưa ground | treo im lặng, không rõ vì sao | in cảnh báo trước khi chạy; mode báo `blocked` → CLI exit 3 kèm lý do |

## P1 — GUI (tkinter)

| # | Lỗi | Sửa |
|---|---|---|
| 13 | Log bị `delete("1.0","end")` + insert lại mỗi 300ms | **append-only** (`apply_log`), giữ vị trí cuộn/selection |
| 14 | Không nhập được filament / số run / số mission | thêm ô Filament, So mission, So run, Engine (fsm/bt), bật/tắt theo mode |
| 15 | Bỏ tick SIM + DRY là bấm thật **không hỏi** | `messagebox.askyesno` liệt kê mode + cảnh báo mất tàu |
| 16 | E-STOP bấm được cả khi IDLE | disable khi `state == "IDLE"` |
| 17 | Khung info luôn hiện Room/HP/Filament cả ở Distribution (toàn 0/None) | info theo mode: Abyss (room/HP/filament) vs Dist (mission xong/từ chối) |

## P1 — Launcher

- Bỏ số liệu cứng "25 Suites / 369 Tests" (đã lệch thực tế) → "Health Check — tất cả suite".
- Menu `[3]` ghi rõ Abyss LIVE chưa ground; hỏi `--max-runs`.
- Distribution LIVE hỏi có bỏ kiểm tra sec route không (`--allow-unknown-sec`), mặc định **N**.
- Thêm `[9]` Abyss SIM engine=bt để so sánh với FSM.

## Đã kiểm chứng chạy thật (không chỉ test)

```
python -m fila_bot.cli abyss --engine fsm --max-runs 1   -> [OK] Hoan tat 1 run abyss. exit 0
python -m fila_bot.cli abyss --engine bt  --max-runs 1   -> [OK] Hoan tat 1 run abyss. exit 0
python -m fila_bot.cli distribution --max-missions 1     -> [OK] Hoan tat: 1 nhiem vu. exit 0
python -m fila_bot.cli status                            -> exit 2, thong bao "EVE client chua chay"
python -m fila_bot.cli abyss --live --max-runs 1         -> [FATAL] Khong ket noi duoc EVE client, exit 2
python -m fila_bot.ui --smoke 60                         -> di het DOCKED..ROOM3..DOCKED
python -m fila_bot.ui --window-ms 1500                   -> mo cua so that, dong sach, exit 0
python tests/run_all.py                                  -> 30 files, 512 PASS, 0 FAIL
```

## Còn hở (không tự nhận là xong)

1. **Abyss LIVE**: undock/filament/gate/dock chưa ground → mode dừng có báo lỗi (đúng fail-closed), chưa chạy thật được.
2. **G7 Distribution live**: kéo cargo + `CompleteMission_Button` chưa ground trên client.
3. **Route sec**: chưa đọc được sec từng hệ trên route → mặc định chặn; muốn chạy phải `--allow-unknown-sec`.
4. **APF 3D / ONNX vision / shared-memory IPC / webhook**: chưa làm (xem `NEXT_GEN_TECH_ROADMAP.md`).
