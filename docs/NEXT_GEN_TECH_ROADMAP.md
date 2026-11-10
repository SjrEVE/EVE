# Lộ Trình Công Nghệ Hiện Đại (Next-Gen Tech Roadmap) Cho fila-bot

Tài liệu nghiên cứu các công nghệ bot game và AI tự hành tiên tiến nhất hiện nay (2025–2026), phân tích tính khả thi và phương án áp dụng cụ thể vào EVE Online (`fila-bot`).

## Trạng thái thực hiện (cập nhật 2026-11-10)

| # | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | Behavior Tree thay FSM | **XONG (engine=bt)** | `src/fila_bot/bt.py`, `bt_abyss.py`; `AbyssMode(engine="bt")`; `python -m fila_bot.cli abyss --engine bt --max-runs 1` → `[OK] Hoan tat 1 run` |
| 2 | APF 3D cho Abyss T5/T6 | Chưa làm | cần đọc vector 3D (chưa ground) |
| 3 | Hybrid ONNX vision | Chưa làm | — |
| 4 | Shared memory IPC | Chưa làm | JSON ~50–100ms/frame hiện tại |
| 5 | Webhook Telegram/Discord | Chưa làm | — |

> Ghi chú: BT chạy **song song** với FSM (`--engine fsm|bt`), không xoá FSM để còn đường lui khi live.

---

## 1. Behavior Trees (BT) & Hierarchical Task Networks (HTN) Thay Thế FSM

### 1.1. Giới hạn của Finite State Machine (FSM) hiện tại
- Hiện tại bot sử dụng FSM tuyến tính: `AGENT` $\rightarrow$ `OFFER` $\rightarrow$ `LOAD` $\rightarrow$ `TO_DROPOFF` $\rightarrow$ `COMPLETE` (Distribution) hoặc `DOCKED` $\rightarrow$ `UNDOCK` $\rightarrow$ `ROOM_FIGHT` $\rightarrow$ `GATE` (Abyss).
- **Vấn đề cốt lõi:** Khi môi trường game phát sinh các sự kiện bất thường (ví dụ: bị gank giữa đường, rớt mạng, hết pin, drone bị quái cắn, dialog bị cửa sổ khác đè), FSM dễ bị rơi vào trạng thái bùng nổ (state explosion) — lập trình viên phải viết hàng chục nhánh `if/else` chắp vá để chuyển trạng thái tạm thời rồi quay lại.

### 1.2. Giải pháp Behavior Tree (Cây Hành Vi)
Behavior Tree (chuẩn Unreal Engine / Robotics) tổ chức logic thành các node có cấu trúc phân tầng:
1. **Parallel Nodes (Xử lý song song):**
   - *Nhánh 1 (Sinh tồn & An toàn - chạy liên tục):* Giữ pin $>30\%$, theo dõi Shield/Armor, tự động thu hồi drone khi bị tụt máu, E-STOP khi mất kết nối.
   - *Nhánh 2 (Thực hiện mục tiêu):* Bay theo route, tiêu diệt quái, trả nhiệm vụ.
2. **Selector Nodes (Ưu tiên từ cao xuống thấp):**
   - `[Ưu tiên 1]` Nếu phát hiện popup "Connection Lost" $\rightarrow$ E-STOP.
   - `[Ưu tiên 2]` Nếu máu $< 30\%$ $\rightarrow$ Kích hoạt Overheat Shield Booster + bay vòng né đòn.
   - `[Ưu tiên 3]` Nếu có quái EWAR (Web/Neut) $\rightarrow$ Khóa mục tiêu và tiêu diệt trước.
   - `[Ưu tiên 4]` Bay bình thường theo nhiệm vụ.
3. **Decorator Nodes:** Tự động retry có giới hạn, debounce menu, hoặc đảo ngược điều kiện.

$\rightarrow$ **Lợi ích:** Cực kỳ dễ mở rộng. Muốn thêm một tính năng mới (ví dụ: tự động ăn thuốc booster khi máu đỏ), chỉ cần cắm 1 nhánh con vào cây mà không cần sửa bất kỳ dòng code nào của các tính năng cũ.

---

## 2. Spatial 3D Vector Math & Artificial Potential Fields (APF) Cho Abyss T5/T6

### 2.1. Thách thức không gian 3 chiều trong Abyss
Trong Abyssal Deadspace cấp cao (T4, T5, T6), cự ly 2D Overview là không đủ để sống sót. Có 3 mối đe dọa không gian 3D cùng lúc:
1. **Biên giới tử thần (Boundary):** Hình cầu bán kính 70 km tâm là Gate. Bay lọt ra ngoài 1 mét là nổ tàu sau vài giây.
2. **Mây độc hại (Clouds):**
   - *Deviant Automata Suppressor:* Giật sét diện rộng làm hỏng drone và mất máu.
   - *Multibody Tracking Pylon:* Tăng tracking cho quái vật.
3. **Chiến hạm Karen (Karybdis Tyrannos):** Sát thương phát bắn đầu tiên cực lớn nếu bay thẳng mặt.

### 2.2. Thuật toán Lực Tiềm Năng Nhân Tạo (Artificial Potential Field - APF)
Áp dụng toán học trường thế năng để điều khiển vector bay của tàu:
- **Lực hút ($\vec{F}_{att}$):** Hướng về phía mục tiêu cần tiếp cận (Transfer Conduit hoặc Triglavian Bioadaptive Cache).
- **Lực đẩy ($\vec{F}_{rep}$):**
  - Đẩy khỏi thành hình cầu 70 km khi cự ly tới biên $< 15$ km.
  - Đẩy khỏi tâm của các đám mây độc.
  - Đẩy vuông góc với vector vận tốc của quái vật để tạo quỹ đạo xoắn ốc (Transversal Spiral).
- **Vector tổng hợp:**
  $$\vec{F}_{total} = \vec{F}_{att} + \sum \vec{F}_{rep}$$
  Bot chỉ cần click đúp chuột trên màn hình không gian theo hướng của vector $\vec{F}_{total}$. Tàu sẽ tự động lướt đi mượt mà như phi công thật, vừa né mây vừa không bao giờ chạm biên đỏ.

---

## 3. Kiến Trúc Lai (Multi-Modal Hybrid Perception): Memory + Local ONNX Vision

### 3.1. Điểm mạnh và giới hạn của Memory Reading
- **Ưu điểm:** Đọc chính xác 100% text, tọa độ pixel widget, HP, tên trạm, item trong kho. Không có hiện tượng ảo giác (hallucination) như AI thuần hình ảnh.
- **Hạn chế:** Một số thực thể 3D trong game (như hiệu ứng luồng sét, vệt mây vũ trụ không có icon riêng trên overview) khó được trích xuất từ cây UI DOM.

### 3.2. Mô hình lai (Hybrid)
- **Tầng 1 (Core Truth - Memory):** Đảm nhiệm 90% logic: UI widget, inventory, text, health, target lock.
- **Tầng 2 (Lightweight Local Vision - ONNX):** Dùng mô hình thị giác siêu nhẹ (như YOLOv10-nano hoặc MobileNet ONNX chạy local trên CPU máy Boss, tốn $< 5\%$ CPU) chỉ để scan góc màn hình phát hiện vệt mây không gian hoặc đạn pháo khi cần né tránh đặc thù.

---

## 4. Tối Ưu Hóa Giao Tiếp Bộ Nhớ: Zero-Copy Shared Memory IPC

### 4.1. Hiện trạng
- DLL C++ (`eve-memory-reader.dll`) được Python gọi qua `ctypes`.
- Khi gọi `read_ui_trees()`, C++ cấp phát bộ nhớ chuỗi JSON, Python đọc chuỗi này rồi gọi `json.loads()`.
- Việc serialize/deserialize JSON chiếm từ 50–100ms mỗi frame.

### 4.2. Cải tiến tương lai
- Chuyển DLL C++ thành một background worker chạy liên tục trên luồng riêng.
- Sử dụng **Bộ nhớ dùng chung (Shared Memory - Windows Memory Mapped Files)**:
  - C++ parse cấu trúc cây UI trực tiếp vào Shared Memory Buffer dạng Binary C Struct (không dùng JSON text).
  - Python mapping trực tiếp buffer qua `mmap` / `ctypes.Structure`.
- **Hiệu quả:** Thời gian cập nhật frame giảm xuống dưới **10ms**, đạt tốc độ thời gian thực 60 FPS mà CPU gần như bằng 0%.

---

## 5. Giám Sát Từ Xa (Remote Telemetry) Qua Telegram / Discord Webhook

Khi bot chạy tự động 24/7 (kể cả khi Boss đang ngủ hoặc đi làm):
1. **Báo cáo định kỳ:**
   - Sau mỗi chuyến hàng Courier hoặc mỗi run Abyss: Tự động gửi tin nhắn báo cáo:
     *"✅ [Run #15] Hoàn thành trọn gói. Kiếm được 2.4M ISK + 1,200 LP. Thời gian: 4m15s. Sức khỏe tàu: 100%."*
2. **Cảnh báo khẩn cấp (Emergency Alerts):**
   - Khi phát hiện "Connection Lost" $\rightarrow$ Gửi thông báo kèm ảnh chụp màn hình client.
   - Khi máu tàu xuống $< 50\%$ hoặc phát hiện kẻ thù lạ (Local chat có người -10 standing) $\rightarrow$ Rung chuông điện thoại cảnh báo.
3. **Lệnh điều khiển từ xa (Two-Way Bot Command):**
   - Nhắn tin `/status` để xem ảnh chụp màn hình và số dư ví tiền hiện tại.
   - Nhắn `/pause` hoặc `/estop` để dừng tàu từ xa ngay lập tức.
