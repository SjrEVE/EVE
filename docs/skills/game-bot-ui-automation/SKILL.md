---
name: game-bot-ui-automation
description: "Use when building game bots with UI trees. Rules and tools."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [game-automation, bot, ui-tree, memory-reading, hotkeys, testing]
---

# Game Bot UI Automation — Fast Development Workflow

## When to Use
Load when building, refactoring, or grounding any game automation bot (such as EVE Online, MMORPGs, desktop games) that interacts via memory-mapped UI trees, window messages, or synthetic input.

Tài liệu tham khảo chuyên sâu:
- Hotkeys & UI widget mapping: xem `references/eve-hotkeys-and-widgets.md`.
- Kiến trúc Memory Reader, profiling & 3D vector: xem `references/memory-reader-architecture.md`.

## Core Rules & Anti-Patterns

### 1. DẸP BỎ quy trình "Dò từng click / từng ảnh" (The 5-Year Trap)
- **CẤM:** Gửi 1 click $\rightarrow$ chờ $\rightarrow$ chụp screenshot $\rightarrow$ gọi Vision API soi $\rightarrow$ đoán tọa độ $\rightarrow$ sửa 1 hàm. Quy trình này cực kỳ chậm ("5 năm không xong"), hao token, và gãy vụn khi mạng lag hoặc state game đổi.
- **CHUẨN:**
  1. **Catalog-first:** Thu thập toàn bộ node type & `_name` từ 30+ dump JSON thật + đối chiếu source framework cộng đồng (Sanderling, Viir, open-source bots).
  2. **Single-pass Perception (`WorldSnapshot`):** Parse toàn bộ UI tree mỗi frame vào một dataclass tĩnh duy nhất. Viết và test 100% offline bằng file fixture dump JSON.
  3. **Visual DOM Inspector:** Dùng công cụ HTML/Canvas offline (`inspector.html`) để vẽ wireframe bounding box, hover xem node details — không tốn screenshot hay Vision API.
  4. **In-process Test Runner:** Chạy toàn bộ test suite in-process (<10s cho 300+ tests) thay vì shell loop lặp (mất vài phút).

### 2. Triệt tiêu Context Menu (Zero-Menu Interaction)
- Menu chuột phải trong game client thường bị 3 vấn đề chí mạng:
  1. Trễ render 1–2 giây.
  2. Vết menu cũ lưu trong UI tree sau click gây ra spam click lặp lại.
  3. Menu con (submenu) dễ trượt khi hover.
- **Giải pháp thay thế:**
  - **Native Hotkeys:** Tận dụng hotkey giữ phím + click (VD: EVE giữ `D` + Click để Dock/Jump; giữ `S` + Click để Warp; giữ `Ctrl` + Click để Lock; giữ `Q` + Click để Approach).
  - **Fixed Action Widgets:** Click chọn đối tượng 1 lần $\rightarrow$ bấm nút cố định trên panel điều khiển (VD: `SelectedItemButton` như `selectedItemDock`, `selectedItemJump` tại vị trí pixel cố định).

### 3. Kéo thả an toàn (Drag & Drop)
- Không thả vào khoảng trống mênh mông (dễ trượt do window offset / scaling).
- Luôn nhắm vào các container tĩnh có nhãn rõ ràng (VD: `topCont_<Hangar>` trên cây thư mục bên trái, kích thước cố định 160x24px).
- Di chuyển chuột nội suy mượt (interpolated steps, 5–6 bước) để game engine kịp nhận diện drag gesture.

### 4. An toàn & Can thiệp của con người
- **E-STOP khi mất kết nối:** Modal popup "Connection Lost" phải kích hoạt cờ dừng khẩn cấp ngay lập tức; không bao giờ click nút Quit hay cố đoán mật khẩu để login lại.
- **Phát hiện người đang lái:** So sánh snapshot trước khi bấm; nếu state thay đổi khi bot chưa gửi lệnh (tàu di chuyển, đổi vị trí, đổi selection), bot phải NGỪNG BẤM NGAY và hỏi người dùng.

### 5. Unified End-to-End Bot Engine & CLI Pattern
- **Kiến trúc CLI thống nhất (`cli.py`):**
  - Lệnh `status`: Đọc và hiển thị snapshot hiện tại (zero side-effect, không gửi bất kỳ click/phím nào).
  - Lệnh chạy mode (`distribution`, `abyss`, ...): Hỗ trợ cả `--live` (client thật) lẫn giả lập (SIM), mặc định an toàn DRY-RUN (chỉ log, không bấm) trừ khi có cờ tường minh `--confirm-input`.
  - Lệnh `inspect`: Mở nhanh visual DOM inspector.
- **Tách biệt FSM và Runner:**
  - FSM chỉ quyết định dựa trên `world: dict` chuẩn và phát ra danh sách `actions: list[dict]`.
  - Giả lập (`SimWorld`) và thực tế (`LiveRunner`) cùng tuân thủ đúng một hợp đồng: `refresh() -> dict` và `apply(acts) -> list[dict]`. Code FSM không sửa một dòng nào khi chuyển từ sim sang live.
  - Fail-closed gate: Khi thiếu dữ liệu ở bất kỳ bước nào, trả về trạng thái `BLOCKED` kèm lý do cụ thể, tuyệt đối không click mù.

### 6. Quản Lý Vòng Đời Memory Reader & Session Transitions
- **Boot vs Tick Performance:**
  - Quá trình scan committed memory tìm địa chỉ `primary_ui_root` mất 10–13s khi khởi tạo. Sau khi lock được con trỏ, mỗi tick chỉ tốn 100–250ms qua hash table cache.
  - **Cạm bẫy chuyển session (Dock/Undock/Gate jump):** Khi game đổi cảnh, `primary_ui_root` cũ bị hủy. Memory reader phải kiểm tra số con (`children > 5`), nếu rớt về 0 hoặc con trỏ rác thì phải tự động re-scan tìm root mới, tránh trả về cây rỗng làm FSM phán đoán sai.
  - **Chiến thuật cho Combat/Abyss:** Tuyệt đối không để xảy ra memory re-scan 12s giữa trận đánh. Phải lock sẵn danh sách candidates hoặc xác định root ổn định trước khi bước vào combat pocket.

### 7. Đóng Gói 1-Click Launchers Cho Người Dùng
- Đừng bắt người dùng nhớ các cờ lệnh terminal dài dòng.
- Luôn tạo sẵn bộ 4 file `.bat` tiêu chuẩn ngay tại thư mục gốc:
  1. `KIEM_TRA_TRANG_THAI.bat` $\rightarrow$ Chạy `cli.py status` xem snapshot (zero side-effect).
  2. `CHAY_<MODE>_TEST.bat` $\rightarrow$ Chạy thử live ở chế độ DRY-RUN (chỉ log, không bấm phím chuột).
  3. `CHAY_<MODE>_THAT.bat` $\rightarrow$ Chạy thật có xác nhận `--confirm-input`.
  4. `MO_UI_INSPECTOR.bat` $\rightarrow$ Mở visual DOM inspector trên trình duyệt.
