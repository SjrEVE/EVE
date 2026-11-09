# Viir/bots framework — những gì đọc được từ SOURCE (2026-11-09)

Nguồn: `github.com/Viir/bots` nhánh main, bản copy tại `.hermes/research/viir/`:
- `Bot_autopilot.elm` (eve-online-warp-to-0-autopilot, version 2026-09-27, 518 dòng)
- `ParseUserInterface.elm` (3702 dòng), `BotFramework.elm` (2177 dòng)

> CẢNH BÁO: tên node dưới đây là dòng Sanderling. Client Photon đã từng lệch (vd `OverView` → `OverviewWindow`,
> `ActiveItem` → `SelectedItemWnd`). Mọi tên PHẢI verify bằng dump client thật trước khi code dùng (fail-closed).

## 1. Travel (autopilot warp-to-0) — Bot_autopilot.elm

| Việc | Cách Viir làm | Dòng |
|---|---|---|
| Marker route | node `AutopilotDestinationIcon` trong `InfoPanelRoute`; lấy marker ĐẦU | PUI 942-956, Bot 147 |
| Hành động | mở context menu trên marker → entry chứa `dock` trước, rồi `jump` (không phân biệt hoa thường) | Bot 193-206 |
| Chờ | nếu ShipUI báo đang warp/jump → không bấm gì | Bot 187-190 |
| Đếm jump | `currentSolarSystemName` ĐỔI so với lần đọc trước | Bot 226-241 |
| Kết thúc route | đã từng có route VÀ >3 lần đọc liên tiếp không còn marker | Bot 153 |
| Bẫy đã gặp | route marker BIẾN MẤT khi đang jump; đôi khi đọc lỗi lẻ tẻ → không kết luận từ 1 lần đọc | Bot 150-152, 250-252 |
| Nhịp | 1 bước / 2000 ms | Bot 178 |
| Undock | bot KHÔNG tự undock | Bot 166-170 |

→ Port thẳng sang `travel.py`: marker đầu → menu → dock|jump; xác nhận bằng tên system đổi / ShipUI mất; debounce ≥3 lần đọc.

## 2. Inventory — PUI 2097-2262

- Window: type `InventoryPrimary` hoặc `ActiveShipCargo`.
- Dung tích: node có type CHỨA `CapacityGauge` → lấy display text DÀI NHẤT → parse `used / maximum` (m³).
- Cây trái: tree view entries (text = tên container: item hangar, ship...).
- Bên phải: `Container` có `_name` chứa `right`; caption `_name` bắt đầu `subCaptionLabel`.
- Container đang chọn: type ∈ `ShipCargo, ShipDroneBay, ShipGeneralMiningHold, StationItems, ShipFleetHangar, StructureItemHangar`.
- Item: list view → type `Item` (cells theo header); icon view → type chứa `InvItem`.
- Nút list view: ButtonIcon texture kết thúc `38_16_190.png`; nút Stack All: hint chứa `Stack All`.

## 3. Targets (lock THẬT, không phải selected) — PUI 1376-1420

- Mỗi target đã khoá = node `TargetInBar`; text sắp từ trên xuống.
- Target đang active = có hậu duệ `ActiveTargetOnBracket`.
→ Sửa sai nghĩa hiện tại `targets = 1 if selected_item()` trong `main.py`/`mission.py`.

## 4. Module — Bot 436-453

- `ModuleButton.isActive`; một số module KHÔNG có ramp → Viir fallback đo độ xanh pixel cạnh nút. fila-bot không chụp màn hình → module không có ramp = trạng thái MÙ (trả None).

## 5. Popup / dialog

| Node | Cấu trúc | Dòng |
|---|---|---|
| `KeyActivationWindow` (confirm filament) | con `ActivateButton` | PUI 2977-2997 |
| `MessageBox` | + `HybridWindow` nằm trong `LayerCore` có `_name` chứa `modal`; buttons có `mainText` | PUI 3106-3134 |
| `LobbyWnd` | nút theo text `undock` / `undocking` (abort) | PUI 2070-2094 |
| Context menu | entry = type chứa `menuentry` | PUI 984-990 |

## 6. Agent / mission — KHÔNG có sẵn

- `AgentDialogueWindow` → Viir chỉ giữ `uiNode`, KHÔNG parse nút Accept/Decline/Complete (PUI 2703-2714).
- `InfoPanelAgentMissions` → `MissionEntry` chỉ `uiNode` (PUI 959-981).
→ G1/G2/G3/G7 vẫn phải tự ground trên client. Không có đường tắt.

## 7. Tác động lên plan

| Ground | Trước | Sau khi đọc Viir |
|---|---|---|
| G4 inventory | mù | có schema ứng viên (§2) — chỉ cần 1 dump để xác nhận |
| G5/G6 jump/dock | mù | có thuật toán hoàn chỉnh (§1) |
| G8 lock/module | mù | có schema ứng viên (§3, §4) |
| G10 filament | mù | có `KeyActivationWindow/ActivateButton` (§5) |
| G2 agent buttons | mù | VẪN MÙ |
