# Soi EVE-Master (bản free) — 11-11, đọc TOÀN VĂN bằng curl

> Boss: *"soi đúng thằng này ko thế? nó làm e2e bán được rồi kia. tao thì ko bán
> nhưng phải làm được thật"*.
> Báo cáo này đọc trang thật, không dùng search snippet. `web_extract` của phiên
> này là search-only nên tao dùng `curl -sL` và parse HTML. File gốc lưu ở
> `scratch/evemaster/`.

## 0. Nguồn đã fetch (kiểm chứng được)

| Trang | Bytes | Đọc được |
|---|---|---|
| `https://eve-master.com/` | 21 988 | tiêu đề, "30+ bots / 27.000+ nodes", free |
| `https://eve-master.com/nodestore` | **1 061 093** | **984 link node**, lọc hết |
| `https://eve-master.com/pricing` | (search snippet + HTML) | free vs Pro |
| `https://bot.eve-master.com/` | 322 580 | danh sách bot + menu doc |
| `https://bot.eve-master.com/bot-architecture-patterns/` | 334 972 | Linear vs **Recycle Pattern** |
| `https://bot.eve-master.com/eve_online_bot_execution/` | 323 768 | flow / Exit Success / Exit Error / Flow Split |
| `https://bot.eve-master.com/eve_online_bot_node/` | 323 022 | Root/User/Pro node, 20 phút |
| `https://bot.eve-master.com/eve_online_bot_user_interface/` | 333 348 | **UI Request language** + search operators |
| `https://bot.eve-master.com/eve-ui-hierarchy-viewer/` | 303 400 | UI Hierarchy Viewer, `Exists` |
| `https://eve-master.com/nodestore/44ba8979-…` (BOT Ratting Combat Site) | 265 257 | **58 loại node nội bộ**, v247, 6200 downloads |
| `https://eve-master.com/nodestore/db85eb46-…` (BOT Autopilot) | 43 192 | **14 node nội bộ**, v44, 2666 downloads |
| `https://eve-master.com/nodestore/d7c93f95-…` (Warp To Anomaly 20KM) | 40 368 | 14 node nội bộ |

## 1. Nói thẳng: nó KHÔNG có bot agent-mission

Quét **984 link** trong Node Store, đếm mọi node có `mission|agent|encounter|security|
deadspace|opportunit|bookmark|location|warp to|anomaly`: 161 node liên quan, **toàn bộ**
là ratting/mining/hauling/abyss/autopilot/bookmark. Tìm `mission`, `agent`, `encounter`
trong **toàn bộ text** của trang chỉ ra 2 chỗ:

- `BOT Intel Writer` — "Spy **agent** for sending messages to Intel channel" (không phải mission).
- `Encounter tab opener in Agency window` — "Opens the encounters tab in Agency Window",
  **0 downloads**, của user `bns`.

Chính `bot.eve-master.com` liệt kê 4 nhóm: **Killing Rats / Zero Autopilot / Mining bot /
Custom bots**. Không có "mission runner". Vậy cái "e2e bán được" là **vòng lặp e2e cho
ratting/mining/abyss**, không phải nhận mission → undock → warp site → đánh → trả thưởng.
Bản free: *"All nodes are free. Exclude: Mouse (20 minutes limit), Keyboard (20 minutes
limit)"* — logic đọc UI tree free, chỉ input chuột/phím bị cắt 20 phút mỗi session.[1][2]

**Kết luận:** không có mã nguồn mission bot để copy. Cái đáng lấy là **kiến trúc vòng lặp**
đã chạy thật 6200 lượt tải, và áp vào luồng mission của mình.

## 2. 6 cơ chế làm nó chạy thật (trích nguyên văn đã đọc)

1. **Recycle Pattern, không Exit.** *"Core principle in this pattern – do not use Exit
   nodes. That will force execution flow to comeback to the Start node when it stuck in
   node without forward execution flow connection… perfect to make continues validation
   of bunch of rules."* Linear Pattern bị chê: *"can do single task, do nothing else until
   complete it"* — khi có neutral xuất hiện giữa chừng thì phải nhân bản logic thành
   spaghetti. Mỗi vòng phải tự hỏi *"where the bot is now, in space or docked, has low
   health or doesn't"*.[3]
2. **Preflight validate trước khi start.** BOT Ratting: *"validate 'Station Path' input,
   it has to be valid, in other case bot will not be able to dock in emergency case. So
   need to avoid even start."*[3] → cấu hình sai = từ chối chạy, không chạy rồi mới kẹt.
3. **Close Dialogs Pack + Close Neocom mỗi vòng.** Có trong cả BOT Autopilot lẫn BOT
   Ratting (`6493b7ee… Close Dialogs Pack v18`, `b61a89bb… Close Neocom`). UI noise được
   dọn trước khi đọc trạng thái.[4][5]
4. **`Wait while ship indicator` v16 (3 lần trong BOT Autopilot).** Xác nhận đổi trạng
   thái bằng **chỉ báo trên UI**, không ngủ timer cố định.[4] Đây là cái mình đang thiếu
   và vừa gây bug live (§4).
5. **UI Request có scope.** `/-->undockparent/-->@undock@` — *"Why just not use
   `/-->@undock@`? Because the word 'undock' could be found in chat as a message, or
   like a nickname… That is why firstly we search the root UI element of station buttons
   when you are docked."* Operator: `name`, `[index]`, `"text"`, `#name#`, `@text@`,
   `^hint^`, `$Type$`, `?prop=value?`, `/-->` (deep), `:A|B:` (OR). `UI Get Property`
   trả thêm bool **`Exists`**.[6] Hierarchy Viewer khuyên: *"better to always open UI
   Element by unique property"*, Index chỉ là đường cuối.[7]
6. **Node tái dùng + báo lỗi.** `Click context menu item (by name)` v40 (3 lần trong
   Autopilot), `Is Docked` v4, `UI.Find Next destination target in path` v1,
   `Message Alert Last Error` v2 (**7 lần** trong BOT Ratting), `Return all Drones
   (Hotkey)` v23, 9 `flow.split`, 19 `get.bool`, 35 `get.string`, 14 `set.bool`.[4][5]

## 3. fila-bot đang khớp / đang thiếu

| Cơ chế | fila-bot |
|---|---|
| Recycle loop `refresh → tick → execute` mỗi vòng | ✅ `Supervisor.step()` (`runner.py:112`) |
| `last_error`, kill-switch Ctrl+Shift+Space, runlog crash | ✅ `runner.py:49,122,153` |
| Read-back thay vì tin lần click | ✅ turn-in, `Cannot Complete Mission` |
| Fail-closed `BLOCKED` có lý do | ✅ |
| Preflight validate config/window/agent | ⚠️ mới chỉ check cửa sổ EVE khi `--confirm-input` |
| Close Dialogs Pack / Close Neocom mỗi vòng | ⚠️ chỉ có nhánh `CLOSE_DIALOG` cục bộ |
| **Wait while ship indicator (verify bằng UI)** | ❌ **vừa sửa** (§4): còn `WARP_COOLDOWN_S=60` timer cố định |
| UI Request có scope (tránh substring toàn cây) | ⚠️ `Eye.find(contains=True)` vẫn global |
| `Message Alert Last Error` surfaced cho operator | ⚠️ `last_error` có nhưng chưa đẩy ra log/UI rõ |

## 4. Bug live thật vừa bắt được nhờ áp cơ chế (4)

`AUTO.bat 1` có giám sát 20:29:39 → 20:30:09 (`scratch/auto_evemaster_check.log`):

```
[20:29:42] Chấp nhận: What s in a Name - Poke (3 of 5)   ← click thật, offer đọc được
[20:29:49] SET_DESTINATION
WARNING set_destination: menu link Location khong co Add Waypoint/Set Destination
[20:29:57] CLOSE_DIALOG
INFO undock: xy=(889,282) ok=True  (20:29:59 / 20:30:02 / 20:30:05 — 3 lần)
[20:30:09] BLOCKED | Undock không hiệu lực sau 3 lần bấm
```

Probe read-only **ngay sau đó** (`scratch/probe_undock_after_fix.txt`):
`docked: False | location: IN_SPACE | station_window: {}` — **Undock ĐÃ THÀNH CÔNG**.
Bot sai, client đúng: nó kết luận thất bại sau 9 giây đếm click, trong khi EVE đổi
session lâu hơn. Đúng lỗi mà `Wait while ship indicator` của họ sinh ra để tránh.

**Fix:** `security.py` thay `if self._undock_attempts >= 3: BLOCKED` bằng
`UNDOCK_EVIDENCE_TIMEOUT_S=45` + `UNDOCK_RETRY_INTERVAL_S=12` +
`UNDOCK_MAX_CLICKS=3`: bấm tối đa 3 lần cách nhau 12s, còn lại **chờ bằng chứng
`world.docked=False`**, chỉ BLOCKED khi hết 45s mà vẫn DOCKED. Khi IN_SPACE xuất hiện,
`tick()` reset sạch bộ đếm. Regression `tests/test_undock_evidence_wait.py` **12 PASS**
tái hiện đúng trace 20:29. Suite **39 files / 621 PASS / 0 FAIL**.

## 5. Kết quả live SAU khi áp 3 fix (20:41 → 20:50, có giám sát)

Chuỗi **chạy thật trên client TQ**, log `scratch/auto_after_panel_fix.log` +
`scratch/auto_gate_live.log`:

| Thời điểm | Sự kiện thật | Bằng chứng |
|---|---|---|
| 20:29 | Accept `What s in a Name - Poke (3 of 5)` | `auto_evemaster_check.log` |
| 20:29–20:31 | Undock 3 click `ok=True`, bot tự BLOCKED **sai** | probe: `docked: False / IN_SPACE` |
| 20:35 | `ACCEPTED_UNSUPPORTED` — title không có trong catalog | panel `Encounter (Deadspace)` + `You need to travel to Josameto 0.6` + nút `Set Destination` |
| 20:41–20:43 | `TRAVEL_ROUTE` / `TRAVEL_SITE`, **không crash, không BLOCKED** (timeout cắt 170s) | `auto_after_panel_fix.log` |
| 20:4x | Tàu **có mặt ở Josameto 0.6** đúng hệ mission | overview: `Josameto - Star`, `Josameto IV…`, `Acceleration Gate \| 0 m` |
| 20:49:58 | `AT_GATE`: game bảo *"You need to activate the Acceleration Gate"* → bot bấm gate | `auto_gate_live.log` |
| 20:50:15 | **ĐÃ VÀO POCKET**: 4 `Gallente Lookout` + `Gallente Starbase Control Tower` + `Gallente Battleship Vessel` xuất hiện | probe `scratch/probe_firecloud.txt` |

3 fix đã áp (đều có regression):
1. `security.py`: bỏ "3 click → BLOCKED", thay `UNDOCK_EVIDENCE_TIMEOUT_S=45` +
   chờ bằng chứng `docked=False` (`tests/test_undock_evidence_wait.py`, 12 PASS).
2. `eye.py::mission_panel_observation()` + `live_security.py`: đọc
   `Encounter (Deadspace)` / `Set Destination` từ **chính panel game** → cấp quyền
   TRAVEL, KHÔNG cấp quyền bắn (`tests/test_mission_panel_evidence.py`, 12 PASS).
3. `security.py`: objective *"You need to activate the Acceleration Gate"* + gate
   trong tầm → `activate_gate`; fail-closed khi gate ở AU/km hoặc thiếu text
   (`tests/test_activate_gate_evidence.py`, 14 PASS).

**Suite: 41 files / 647 PASS / 0 FAIL**, `compileall` OK.

## 6. Còn lại (không giả vờ)

- Vào pocket rồi nhưng game bảo *"You need to approach **Fire Cloud**"* kèm
  *"Attention, you are approaching a Gallente Federation vessel on official
  exercises. Turn back now."* → objective **KHÔNG PHẢI KILL**. `authorize_security_targets()`
  từ chối bắn là **đúng**, không phải lỗi. `Fire Cloud` không có trong overview preset
  hiện tại → cần ground thêm trước khi viết flow "approach". Đây đúng là "các bước
  khác" mà Boss bảo chưa nói tới.
- Nhãn `Warp to Location` vẫn **chưa có dump TQ**; đã ground `Undock`,
  `Set Destination`, `You need to travel to …`, `You need to activate …`,
  `You need to approach …`.
- Chưa có read-back turn-in / về trạm trên live.
- `WARP_COOLDOWN_S` vẫn timer cố định; nên thay bằng đọc `ManeuverWarp`/speed như
  `Wait while ship indicator`.
- `Eye.find(contains=True)` vẫn global substring — nên áp UI Request có scope
  (`/-->undockparent/-->@undock@`) để tránh dính text chat.

## Sources (toàn văn đã fetch)
[1] https://eve-master.com/ và https://eve-master.com/pricing
[2] https://bot.eve-master.com/eve_online_bot_node/
[3] https://bot.eve-master.com/bot-architecture-patterns/
[4] https://eve-master.com/nodestore/db85eb46-4ac3-4310-b8f2-7d1884135c9c
[5] https://eve-master.com/nodestore/44ba8979-04cb-4f45-9926-04dc147b1b0d
[6] https://bot.eve-master.com/eve_online_bot_user_interface/
[7] https://bot.eve-master.com/eve-ui-hierarchy-viewer/
[8] https://bot.eve-master.com/eve_online_bot_execution/
[9] https://eve-master.com/nodestore (984 link, lưu `scratch/evemaster/eve-master.com_nodestore.html`)
