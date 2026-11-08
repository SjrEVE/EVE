# EVE UI Tree — Attrs thật đã ground (nguồn: Sanderling/ParseUserInterface.elm 2,893 dòng)

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
