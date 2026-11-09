# Memory Reader Architecture, Profiling & Navigation Models

Tài liệu đối chiếu kiến trúc đọc bộ nhớ, phân tích điểm nghẽn hiệu năng và mô hình điều hướng không gian giữa các hệ thống bot game (EVE Online).

---

## 1. Vòng Đời Đọc Bộ Nhớ (Memory Reading Lifecycle)

Các bot đọc bộ nhớ client (như `eve-memory-reader.dll`, Sanderling, BotLab) hoạt động theo mô hình 2 pha:

### Pha 1: Initial Scan (Khởi tạo - Boot)
- **Tác vụ:** Quét toàn bộ các vùng nhớ `MEM_COMMIT` trong không gian địa chỉ tiến trình 64-bit của game để tìm kiếm cấu trúc `UIRoot` (gốc của cây đối tượng giao diện người dùng).
- **Chi phí thời gian:** Mất từ **10 đến 13 giây** tùy thuộc vào dung lượng RAM client đang chiếm giữ (thường 2–4 GB committed memory).
- **Đặc điểm:** Tốn CPU và I/O, chỉ diễn ra 1 lần khi gọi hàm `initialize()`.

### Pha 2: Steady-State Polling (Đọc định kỳ - Tick)
- **Tác vụ:** Sau khi đã xác định được địa chỉ `primary_ui_root`, các lần gọi `read_ui_trees()` tiếp theo không quét lại toàn bộ RAM mà duyệt đệ quy cây con trực tiếp từ địa chỉ gốc.
- **Tối ưu hóa bằng Hash Table Cache:** Cache các con trỏ kiểu Python (`python_type_name_cache`), chuỗi ký tự (`python_string_value_cache`), và dict entries.
- **Chi phí thời gian:** Chỉ mất **100–250 mili-giây** cho mỗi frame đọc.
- **Chiến lược flush cache:** Cứ sau mỗi chu kỳ (ví dụ 30 giây), xả bớt các mục cache cũ (`stale items`) để tránh rò rỉ bộ nhớ.

---

## 2. Cạm Bẫy Chuyển Cảnh / Đổi Session (Session Transitions)

Trong EVE Online, khi người chơi:
1. **Undock** (từ trạm bay ra không gian).
2. **Dock** (từ không gian vào trạm).
3. **Jump Stargate** (nhảy qua hệ sao khác).
4. **Enter/Exit Conduit** (vào hoặc ra khỏi phòng Abyssal Deadspace).

Game engine sẽ hủy bỏ toàn bộ cây giao diện cũ và cấp phát lại một cây `UIRoot` mới.

### Nguy cơ:
- Con trỏ `primary_ui_root` lưu trong DLL trở nên trỏ vào vùng nhớ rác hoặc cây bị thu hẹp (`number_of_children <= 5`).
- Nếu memory reader không phát hiện con trỏ bị vô hiệu hóa, bot sẽ đọc ra một cây UI rỗng hoặc crash.
- Nếu reader tự động gọi lại `get_memory_and_root_addresses`, bot sẽ bị **đóng băng 12 giây** giữa lúc vừa load vào môi trường mới.

### Giải pháp kỹ thuật chuẩn:
- Duy trì danh sách `ui_roots` candidates từ lần quét đầu tiên thay vì chỉ lưu 1 con trỏ duy nhất.
- Khi cây hiện tại rớt số con xuống 0, thử ngay các candidate còn lại trong danh sách trước khi quyết định re-scan toàn bộ bộ nhớ.
- Khi làm nhiệm vụ chiến đấu / Abyss: Phải đảm bảo bot chỉ vào phòng khi đã xác nhận session change hoàn tất và con trỏ UI root đã ổn định.

---

## 3. So Sánh Mô Hình Điều Hướng: 2D Overview vs 3D Spatial Vector

| Đặc tính | **Mô hình 2D Overview / Widget (Fila-bot / Sanderling cơ bản)** | **Mô hình 3D Spatial Vector (Abyss-Autopilot / Anathema cao cấp)** |
|---|---|---|
| **Cơ chế xác định tọa độ** | Dựa trên khoảng cách ghi bằng văn bản trên Overview (`15 km`, `2,500 m`) và góc nhìn camera. | Đọc trực tiếp tọa độ vector 3 chiều $(X, Y, Z)$ và vận tốc $(\dot{X}, \dot{Y}, \dot{Z})$ của tàu và mọi thực thể trong grid. |
| **Quyết định quỹ đạo bay** | Gửi lệnh `Orbit(distance)`, `KeepAtRange(distance)`, hoặc `Approach(target)`. Game client tự lái. | Tính toán trường thế năng nhân tạo (Potential Fields) hoặc đường cong Bezier 3D né vật cản. |
| **Xử lý vật cản & Mây độc** | Không thể né mây nếu mây nằm trên đường thẳng tiếp cận. | Vẽ đường bay vòng tránh hoàn toàn các khối cầu mây độc (Clouds) và tính cự ly tới mặt cầu biên giới 70km. |
| **Mức độ phù hợp** | Cực kỳ hiệu quả và an toàn cho **Distribution, Mining, Abyss T0–T3**. | Bắt buộc đối với **Abyss T5–T6** (nơi dính 1 đám mây trừ turret hoặc lọt ra ngoài rìa là nổ tàu). |
