# EVE UI Tree — Attrs thật đã ground (nguồn: Sanderling/ParseUserInterface.elm 2,893 dòng)

## ⚠️ GROUND LẠI 2026-11-09 trên client thật (TQ, Photon HUD) — ĐÈ lên bảng Sanderling bên dưới

Dump: `ui_dump_space*.json` (Jita, undocked, tàu không module) + fixture khoá schema
`tests/fixtures/ui_tree_ground_tq.json` + test `tests/test_ground.py`.

| Thứ cần đọc | Sanderling cũ (SAI với client này) | THẬT 2026-11-09 |
|---|---|---|
| Overview window | `OverView` | **`OverviewWindow`** (name=`overview`, có `_display`) |
| Text trong entry | `_setText` | **`OverviewLabel.attrs["_text"]`** (không phải _setText) |
| Selected item | `ActiveItem` | **`SelectedItemWnd`** (name=`selecteditemview`), text ở `_setText` |
| HP gauge | `Gauge._lastValue` | **`ShipHudSpriteGauge._lastValue`** (float 0..1) |
| Speed | (không rõ) | **`SpeedGauge` → label `_name=speedLabel`, `_setText="600 m/s"`** |
| Module buttons | `ShipSlot` → `ModuleButton` | HUD mới: `SlotsContainer` (chứa `OverloadBtn`); tàu CÓ module chưa ground được |
| Cap pmarks | `pmark` color alpha | `pmark._color` = **`PyColor`** → DLL decode thành `{"aPercent","rPercent","gPercent","bPercent"}` (ground từ Sanderling EveOnline64.cs); `aPercent<20` = đoạn cap còn → đếm/tổng |
| Toạ độ | `_displayX/Y` | **TƯƠNG ĐỐI với cha** → phải cộng dồn từ UIRoot (`Eye.abs_center`) |

**Bug DLL đã fix (2026-11-09):** `read_python_type_float()` trong `dll-source/eve-memory-reader.c`
là hàm RỖNG → mọi float trong UI tree trả `null` (HP luôn None dù gauge có giá trị).
Đã implement đọc `PyFloatObject.ob_fval` (double @ +0x10) và đổi `FLOAT float_value` → `double`.
Build lại bằng mingw-w64: xem `dll-source/build_mingw.sh` + `dll-source/PROVENANCE.md`.

**Đã decode 2026-11-09:** PyColor (39 màu khác nhau trên dump thật) → cap đọc được 100% khi đầy.
**Chưa xác minh động:** cap CẠN MỘT PHẦN (chưa có module tiêu cap) — công thức lấy từ Sanderling.
**Chưa ground được (fail-closed, KHÔNG đoán):** node báo target đã lock, module button khi có
module, popup confirm filament. Cần client ở trong abyss / tàu có fit.

---

> Phần dưới là tài liệu Sanderling gốc — giữ để tham khảo, nhưng chỗ nào lệch bảng trên thì **bảng trên thắng**.

> Mọi attrs dưới đây là **sự thật đã được cộng đồng BotLab dùng 10 năm** trên EVE client 64-bit.
> eye.py đọc UI tree JSON từ eve-memory-reader.dll → cây node có:
> `pythonObjectTypeName` (tên class), `dictEntriesOfInterest` (attrs: _setText, _name, _lastValue...),
> và display region (x, y, width, height).

## Node types chính (pythonObjectTypeName)

| Type | Ý nghĩa | attrs quan trọng |
|---|---|---|
| `ShipUI` | HUD tàu | chứa toàn bộ gauge/cap/module con |
| `CapacitorContainer` | thanh cap | con có `pmark` (mỗi pmark = 1 segment; alpha < 20 = còn đầy) |
| `ShipSlot` | 1 slot module | chứa `ModuleButton` |
| `ModuleButton` | nút module | `isActive`, `isHiliteVisible`, `rampRotationMilli` |
| `SpeedGauge` | tốc độ | |
| `OverView` | cửa sổ overview | chứa `OverviewScrollEntry` |
| `OverviewScrollEntry` | 1 dòng overview | texts trái→phải, cells theo header |
| `ActiveItem` | selected item window | nút orbit theo **texture path kết thúc `44_32_21.png`** |
| `DroneView` | cửa sổ drone | `DroneEntry`, group headers |
| `MessageBox` | popup/alert | |
| `KeyActivationWindow` | popup confirm (filament!) | |
| `AgentDialogueWindow`, `FittingWindow`, `MarketOrdersWnd`... | cửa sổ khác | |

## HP gauges — CÁCH ĐỌC CHUẨN (đã verify trong ParseUserInterface.elm dòng 931–944)

Node con của ShipUI có **name** (`getNameFromDictEntries`) bằng một trong:
- `structureGauge` → `_lastValue` = float 0..1 = % hull
- `armorGauge` → `_lastValue` = % armor
- `shieldGauge` → `_lastValue` = % shield

→ `ship_health()`: tìm 3 node theo name, đọc `_lastValue` (nhân 100 = %). **KHÔNG dùng template ảnh.**

## Capacitor — cách đọc chuẩn (dòng 1018–1050)

Node `CapacitorContainer` chứa các node name=`pmark`; mỗi pmark có màu (alpha).
`levelFromPmarksPercent` = (số pmark có alpha < 20 / tổng pmark) × 100.

## Overview — cách đọc chuẩn (dòng 1200–1300)

1. Tìm node type=`OverView`
2. `entriesHeaders`: node type chứa "headers" → text của từng cột (Order: Name/Type/Distance...)
3. `entries`: mỗi node type=`OverviewScrollEntry`:
   - `textsLeftToRight` = list text các cell (sort theo x)
   - map theo header → `objectName`, `objectType`, `objectDistance` (parse "12 km" → 12000 m)
   - `commonIndications`: `targetedByMe`, `targeting`, `isWarpDisruptingMe` (icons trong entry)

## Selected Item window (khóa target rồi)

- type=`ActiveItem`; nút **orbit** nhận diện theo texture `_name`/texture path **kết thúc `44_32_21.png`**

## Maneuver (đang bay gì) — ShipUIIndication

Node name chứa `indicationcontainer` → parse `maneuverType`: Warp/Jump/Orbit/Approach
→ eye dùng để nhận biết phase (đang warp = chờ, đang approach = OK...)

## Drones

`DroneView` → `DroneEntry` list; group headers type chứa "Group"

## Điều tìm được trong combat-anomaly-bot (pattern FSM EVE thật, Elm)

- Chọn anomaly từ scan results, tránh anomaly đã thăm (memory `visitedAnomalies`)
- Nhớ: wreck có thể loot không (wreckCanLoot), target đã unlock, module names override
- Quyết định theo cây nhánh: "Not in anomaly → return drones & enter" / "Wait for matching anomaly"

## Kết luận cho fila-bot

eye.py v2 map thẳng schema này:
- `ship_health()`: 3 gauge name → _lastValue ✅ implement được ngay
- `capacitor()`: pmarks alpha ✅
- `overview()`: OverView + OverviewScrollEntry + headers ✅
- `maneuver()`: indicationcontainer ✅
- `module_buttons()`: ShipSlot → ModuleButton (isActive) ✅
- `filament_confirm_dialog()`: KeyActivationWindow / MessageBox có text confirm ✅
→ Tất cả attrs này PHẢI verify lại 1 lần trên Singularity client thật (bản client mới có thể đổi) — nhưng là điểm xuất phát có căn cứ, không phải đoán.
