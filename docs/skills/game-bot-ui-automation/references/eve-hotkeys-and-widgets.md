# EVE Online Native Hotkeys & Widget Mapping Reference

Tham chiếu chuẩn hóa các phím nóng và UI widget của EVE Online client dùng để điều khiển bot không qua context menu chuột phải.

## 1. Native Global Hotkeys (Zero-Menu 1-Hit Actions)

Thay vì click chuột phải $\rightarrow$ chờ menu 1–2s $\rightarrow$ tìm text $\rightarrow$ click:

| Hành động | Hotkey Native | Thao tác tương đương trên UI | Ghi chú an toàn |
|---|---|---|---|
| **Dock / Jump / Gate** | Giữ `D` + Click chuột trái | Click vào Stargate, Station, hoặc Autopilot Route Marker | 1 hit duy nhất, game tự warp tới và dock/jump |
| **Warp to 0** | Giữ `S` + Click chuột trái | Click vào Bookmark, Celestial, hoặc Overview item | Warp ngay lập tức về 0m |
| **Align to** | Giữ `A` + Click chuột trái | Click vào đối tượng cần align | Đổi hướng và tăng tốc tới 75% max speed |
| **Lock Target** | Giữ `Ctrl` + Click chuột trái | Click vào Overview entry hoặc Bracket trong không gian | Không giới hạn số lượng khóa tối đa của tàu |
| **Approach** | Giữ `Q` + Click chuột trái | Click vào đối tượng | Bay thẳng tới đối tượng |
| **Orbit** | Giữ `W` + Click chuột trái | Click vào đối tượng | Orbit ở khoảng cách mặc định đã lưu |
| **Stop Ship** | `Ctrl + Space` | Nút Stop trên HUD (`StopButton`) | Dừng tàu khẩn cấp |

## 2. SelectedItemWnd Widget Buttons (Tọa độ tĩnh)

Khi click chọn bất kỳ đối tượng nào (qua Overview hoặc Route Marker), widget `SelectedItemWnd` xuất hiện cụm nút chức năng cố định:

| Tên Node `_name` | Tác vụ | Vị trí thông thường |
|---|---|---|
| `selectedItemDock` | Cập bến trạm không gian | Cố định trên thanh nút |
| `selectedItemJump` | Nhảy qua Stargate | Thay thế vị trí của Dock khi chọn Stargate |
| `selectedItemWarpTo` | Warp tới đối tượng | Nằm cạnh nút Dock/Jump |
| `selectedItemAlignTo` | Align về hướng đối tượng | Nút đầu tiên |
| `selectedItemLockTarget` | Khóa mục tiêu | Nằm giữa thanh nút |

## 3. Inventory Container Mapping (Kéo Thả An Toàn)

- **Tránh:** Kéo thả vào vùng trống rộng lớn của Inventory window.
- **Chuẩn:** Nhắm vào các node tĩnh trên cây Hangar bên trái (`TreeViewEntryWithTag` / `TreeViewEntryInventoryCargo`):
  - `ItemHangar`: Kho đồ trạm (`topCont_ItemHangar`, kích thước cố định 160×24px).
  - `ShipHangar` / Active Ship: Kho đồ tàu (`topCont_ShipHangar`).
  - `ShipDroneBay`: Kho drone (`topCont_ShipDroneBay`).
- **Kỹ thuật kéo thả:** Gửi `MOUSEEVENTF_LEFTDOWN` tại tâm item $\rightarrow$ nội suy 5–6 bước di chuyển mượt $\rightarrow$ `MOUSEEVENTF_LEFTUP` tại tâm hangar đích $\rightarrow$ chờ 100ms.

## 4. Modal Popup "Connection Lost" (E-STOP)

- Khi client mất mạng, xuất hiện `MessageBox` (`_name='modal'`) chứa text `"Connection to server was lost"`.
- Nút duy nhất là `ok_dialog_button` (`Quit`).
- **Quy tắc tuyệt đối:** Không click nút Quit (sẽ tắt client). Bật ngay cờ `connection_lost = True` và chuyển toàn bộ bot FSM sang trạng thái `BLOCKED` (E-STOP an toàn).
