# EVE Online Bot World Model & Unified Architecture

Tài liệu thiết kế và tổng hợp cơ chế gameplay, database thực thể và kiến trúc điều khiển end-to-end cho `fila-bot`.

---

## 1. Cơ Chế Trò Chơi (Gameplay Mechanics)

### 1.1. Distribution (Courier Missions)
- **Bản chất:** Vận chuyển hàng hóa giữa các trạm không gian theo yêu cầu của Agent (Division: Distribution).
- **Chu trình vận hành chuẩn (FSM):**
  1. `AGENT`: Đang dock tại trạm có Agent $\rightarrow$ Mở hội thoại qua nút chat `agentChatBtn` trên `AgentsPanel`.
  2. `OFFER`: Đọc đề nghị nhiệm vụ:
     - Tên nhiệm vụ (vd: *Rancorous Researcher (1 of 5)*).
     - Khối lượng hàng (m³) $\le$ Thể tích trống của Cargo Hold.
     - Hệ sao đích đến nằm trong Hisec (Security status $\ge 0.5$, tránh Low/Null/Pochven).
     - Chấp nhận: Bấm nút `AcceptMission_Button`. Từ chối nếu không đủ tiêu chuẩn: Bấm `DeclineMission_Button`.
  3. `LOAD`:
     - Nếu đang ở trạm nhận hàng (Pickup): Mở `InventoryPrimary`.
     - Kéo item nhiệm vụ từ `ItemHangar` thả vào `ShipHangar` (dùng tọa độ tĩnh trên cây thư mục bên trái).
     - Nếu trạm nhận hàng ở xa: Bật Autopilot / Set Destination tới trạm Pickup $\rightarrow$ Undock $\rightarrow$ Bay tới trạm Pickup $\rightarrow$ Dock $\rightarrow$ Lấy hàng.
  4. `TO_DROPOFF`:
     - Set Destination tới trạm trả hàng (Dropoff Station).
     - Undock $\rightarrow$ Nhảy cổng (Jump Stargates) $\rightarrow$ Cập bến trạm trả hàng (Dock).
  5. `COMPLETE`:
     - Mở lại hội thoại Agent $\rightarrow$ Bấm nút `CompleteMission_Button`.
     - Nhận thưởng ISK, Điểm Trung Thành (Loyalty Points - LP), và Điểm Quan Hệ (Standing).
  6. `TO_AGENT`: Nếu là chuỗi nhiệm vụ nhiều phần, bay về trạm gốc hoặc tiếp tục nhận nhiệm vụ kế tiếp (2 of 5).

---

### 1.2. Abyssal Deadspace
- **Bản chất:** Không gian biệt lập (instanced dungeon) gồm đúng 3 phòng (pockets). Thời gian tối đa 20 phút (quá giờ $\rightarrow$ Nổ tàu + nổ pod tử nạn ngay lập tức).
- **Phân loại Filament:**
  - **7 Tiers:** T0 (Tranquil), T1 (Calm), T2 (Agitated), T3 (Fierce), T4 (Raging), T5 (Chaotic), T6 (Cataclysmic).
  - **5 Hiệu ứng Thời tiết (Weather):**
    - *Dark:* Giảm tầm bắn turret/drone; Tăng 50% tốc độ bay (Thích hợp cho Missile / Frigate).
    - *Electrical:* Giảm EM resist; Giảm 50% thời gian sạc tụ năng lượng (Capacitor).
    - *Exotic:* Giảm Kinetic resist; Tăng 50% tốc độ quét (Scan Resolution).
    - *Firestorm:* Giảm Thermal resist; Tăng 50% máu giáp (Armor HP).
    - *Gamma:* Giảm Explosive resist; Tăng 50% máu khiên (Shield HP).
- **Thứ tự ưu tiên tiêu diệt (Kill Order):**
  1. **EWAR đe dọa sinh tồn:**
     - *Webifier:* Làm chậm tàu $\rightarrow$ Mất speed tank $\rightarrow$ Chết trước tiên.
     - *Energy Neutralizer (Neut):* Hút cạn pin $\rightarrow$ Tắt khiên / tắt armor rep $\rightarrow$ Ưu tiên 2.
     - *Warp Scrambler:* Tắt Afterburner / MWD.
  2. **Tàu hồi máu (Remote Repair):** Phải dứt điểm trước khi chúng kịp hồi máu cho đồng đội.
  3. **Tàu sát thương chính (DPS Dealers):** Battleship (Karen - Karybdis Tyrannos), Cruisers (Vedmak, Leshak...).
- **Quy tắc điều khiển trong phòng:**
  - *Frame 1:* Bật Afterburner và Shield/Armor Booster ngay khi vừa qua cổng.
  - *Góc bay:* Luôn bay chéo 45° so với bầy quái, không bay thẳng mặt Battleship (tránh dính full sát thương alpha).
  - *Biên giới tử thần (Danger Ring):* Tuyệt đối không bay ra ngoài bán kính 70km.
  - *Loot:* Bắn nổ *Triglavian Bioadaptive Cache* (300 HP) và nhặt hàng khi thuận đường bay tới Gate.
  - *Gate:* Tiếp cận *Transfer Conduit* $\le 2500m \rightarrow$ Nhảy sang phòng tiếp. Phòng 3 nhảy qua *Origin Conduit* để thoát về vũ trụ thường.

---

## 2. Nguyên Lý Tương Tác & Điều Khiển: Triệt Tiêu Context Menu

Thao tác chuột phải mở Context Menu trong game EVE Online thường bị trễ 1-2 giây, dễ trượt mục con và dễ bị dính vết menu cũ trong bộ nhớ. Bot áp dụng 2 kỹ thuật thay thế hoàn toàn menu:

1. **Native Hotkeys (Phím nóng tích hợp sẵn của game):**
   - Giữ `D` + Click chuột trái vào Stargate / Station / Route Marker $\rightarrow$ **DOCK / JUMP** tức thì (1 hit duy nhất).
   - Giữ `S` + Click $\rightarrow$ **WARP TO 0**.
   - Giữ `A` + Click $\rightarrow$ **ALIGN TO**.
   - Giữ `Ctrl` + Click $\rightarrow$ **LOCK TARGET**.
2. **Nút Cố Định Trên `SelectedItemWnd`:**
   - Khi chọn một mục, các nút chức năng xuất hiện tại vị trí pixel cố định: `selectedItemDock`, `selectedItemJump`, `selectedItemWarpTo`.
   - Click trực tiếp vào các nút này mà không cần mở context menu.
3. **Kéo Thả Item (Drag & Drop):**
   - Kéo từ ô item trong Hangar thả thẳng vào nhãn `topCont_ShipHangar` (160x24px) bên cây thư mục trái.
   - Di chuyển chuột nội suy mượt 6 bước để engine game nhận diện cử chỉ kéo thả.

---

## 3. Kiến Trúc Single-Pass Perception: `WorldSnapshot`

Toàn bộ cây UI (hàng ngàn node) mỗi tick chỉ được quét **đúng một lần duy nhất** trả về đối tượng `WorldSnapshot`:

```python
@dataclass
class WorldSnapshot:
    docked: bool                        # Đang trong trạm hay ngoài không gian
    station: str | None                 # Tên trạm hiện tại
    system: str | None                  # Hệ sao hiện tại
    security: float | None              # Hệ số an ninh hệ sao (vd 0.9)
    speed_mps: float | None             # Tốc độ bay (m/s)
    maneuver: str | None                # 'warp', 'jump', None
    ship_health: dict[str, float]       # Shield, Armor, Hull
    route: RouteSnapshot                # destination, jumps, markers
    selected_name: str | None           # Đối tượng đang chọn trong overview
    selected_buttons: dict[str, tuple]  # {'dock': xy, 'jump': xy, 'warpto': xy}
    agent_dialog: DialogSnapshot        # open, title, chain, buttons (accept/complete), links
    inventory: InventorySnapshot        # open, hangars (ItemHangar, ShipHangar), capacity, items
    connection_lost: bool               # CỜ E-STOP KHẨN CẤP khi mất mạng
```

---

## 4. Hướng Dẫn Sử Dụng Tool End-to-End

### 4.1. Xem trạng thái client hiện tại
```bash
python -m fila_bot.cli status
```

### 4.2. Chạy bot Distribution (Courier)
- Chạy thử nghiệm giả lập (SIM, không cần game):
  ```bash
  python -m fila_bot.cli distribution --max-missions 5
  ```
- Chạy trên game thật (Chế độ xem trước an toàn - DRY-RUN, chỉ log action không bấm):
  ```bash
  python -m fila_bot.cli distribution --live --max-missions 5
  ```
- Chạy thật và thực hiện bấm phím/chuột vào game:
  ```bash
  python -m fila_bot.cli distribution --live --confirm-input --max-missions 5
  ```

### 4.3. Chạy bot Abyssal Deadspace
- Chạy giả lập:
  ```bash
  python -m fila_bot.cli abyss --filament "Tranquil Exotic Filament"
  ```
- Chạy thật trên game client:
  ```bash
  python -m fila_bot.cli abyss --live --confirm-input --filament "Tranquil Exotic Filament"
  ```

### 4.4. Mở công cụ soi giao diện DOM trực quan (UI Inspector)
Mở file bằng trình duyệt:
`tools/inspector.html`
Kéo thả bất kỳ file dump `.json` nào trong `dumps/` hoặc `tests/fixtures/` vào để xem wireframe bounding box, hover xem tên node, `_name` và tọa độ pixel.
