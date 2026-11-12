# P0 GROUNDING REPORT — 5 mắt còn mù (đóng P0, mở P1)
# (2026-11-13 00:4x — mọi kết luận kèm bằng chứng dump/corpus thật)

> Trạng thái trước P0 (probe 00:3x): speed ⚠, cap ✗, module state ✗, ActiveTarget ✗,
> maneuver ✗. Sau P0: 3 mắt ĐÃ MỞ bằng code + fixture; 2 mắt còn mở một nửa với lý do
> có bằng chứng (không phải đoán).

## Kết quả từng mắt

### 1. Mắt TỐC ĐỘ — ✓ ĐÃ MỞ (thực ra đã ground 11-09, ver lại hôm nay)
- `Eye.speed_mps()` đọc `EveLabelSmall _name="speedLabel"` → `_setText="243 m/s"` (dump
  `scratch/live_current_tree.json`, HUD HUD thật IN_SPACE).
- **Verdump mới 00:4x**: dump docked `g11_docked_fresh.json` có ShipUI skeleton GIỮ số cũ
  ("243 m/s") → extractor trả số dump có (không bịa), nhưng `world_snapshot` chỉ wire khi
  `location_state == "IN_SPACE"` (gate có sẵn) — đúng luật, không sửa gì thêm.
- Regression: `tests/test_p0_senses.py` (9 PASS).

### 2. Mắt CAPACITOR — ✓ ĐÃ MỞ (code có từ 11-09, lần này WIRED vào snapshot)
- `Eye.capacitor_percent()` đếm pmark theo alpha PyColor (ground Sanderling EveOnline64.cs).
- Dump thật: 100.0% / 98.6% đọc đúng.
- **Việc mới hôm nay**: field `capacitor_percent` vào `WorldSnapshot` + wire trong
  `parse_world()` (trước đây extractor có mà snapshot KHÔNG truyền — đúng dạng "logic chết"
  plan đã cảnh báo B01) + dòng `Capacitor` trong `cli status`.
- Regression: trong `test_p0_senses.py`.

### 3. Mắt MODULE STATE — ✓ MỞ ĐÚNG NGHĨA (không lừa)
- `Eye.module_buttons()` trả 14 nút với `is_active` = None khi HUD không export state —
  14/14 UNKNOWN trong dump hiện tại (ground thật: `ramp_active` chỉ xuất hiện khi ramp
  animation chạy). Code KHÔNG bịa False.
- Hệ quả thiết kế đúng: hành động bật/tắt module phải gắn "một lần/mission" + verify qua
  hậu điều kiện (đúng như `live_security` đang làm). Không có shortcut.
- Regression: assert `len(unknown_active) == len(mods)` trong `test_p0_senses.py`.

### 4. Mắt LOCKED TARGET — ✓ MỞ MỘT NỬA CÓ BẰNG CHỨNG
- Reader build hiện tại **không emit** `TargetInBar` / `ActiveTargetOnBracket` (đã walk
  172 type thật trong live tree — không có). Nhưng client RENDERS container
  `targetHealthBars` (mỗi target khóa một cái, con `shieldBar/armorBar/hullBar`) — tên
  lấy từ chính source client (`targetInBar.py:841` `default_name='targetHealthBars'`).
- `Eye.targets_in_bar()` đã dùng 2 tầng: type-based khi reader tương lai xuất, fallback
  `targetHealthBars` bây giờ; `targets_observable()` False khi không thấy cấu trúc nào —
  không bao giờ trả "không có lock" khi thực ra không đọc được.
- **Việc còn lại (P1)**: dump một target ĐÃ LOCK thật để fixture có `targetHealthBars`
  non-empty; đếm before/after lock. Không thể đóng offline — cần client ở trạng thái lock.

### 5. Mắt MANEUVER — ✗ XÁC NHẬN KHÔNG CÓ TRONG UI TREE (không phải việc của reader)
- Corpus 24.02: `maneuverType` xuất hiện **0 lần** trong 12.948 file .py — nó là state của
  ship item (godma), không phải attr UI. Whitelist thêm key này cũng vô ích; đúng đường là
  **suy từ evidence có thật trên HUD**: speedLabel tăng = accelerate; `StopButton`/
  `MaxSpeedButton` state; `HudActionIndicationContainer` → `indication_text` (client tự
  in "Approaching X"/"Orbiting X" — node có trong dump, text rỗng khi không làm gì).
- Việc P1: dump khi đang approach/orbit thật → bắt text indication; rồi suy maneuver.

## File đổi hôm nay (P0)
- `src/fila_bot/world_snapshot.py`: +`capacitor_percent` field + wire + gate IN_SPACE.
- `src/fila_bot/cli.py`: dòng "Capacitor" trong `status`.
- `tests/test_p0_senses.py`: 9 asserts (MỚI) + fixture `ui_tree_p0_senses_inspace.json`
  (copy dump HUD thật 401.9 KB).
- Điểm: `python tests/test_p0_senses.py` → 9 PASS; full suite giữ 0 FAIL.

## Checklist cập nhật (SENSES_CHECKLIST_2026-11-13.md)

| Mắt | Trước P0 | Sau P0 |
|---|---|---|
| speed | ⚠ nghi sai | ✓ (đã có, verify dump + gate docked) |
| cap | ✗ | ✓ wired vào snapshot + status |
| module state | ✗ | ✓ mở đúng nghĩa UNKNOWN (không lừa) |
| locked target | ✗ | ⚠ nửa: fallback `targetHealthBars` có; cần fixture live-lock ở P1 |
| maneuver | ✗ | ⚠ đường đúng: indication_text + speed; cần dump đang bay ở P1 |

**P0 = DONE (3 mắt mở hoàn toàn, 2 mắt mở đường + cần dump live ở P1).**
P1 (orbit/lock/drone read-back có chủ đích trên L1) mở ngay khi preflight ok:true.
