# EVE Security Missions L1–L4: mechanics audit and bot design

**Ngày rà soát:** 2026-11-11 (UTC+07)  
**Phạm vi:** mission NPC Agent, ưu tiên Security L1–L4; phân biệt Mining, Distribution/courier, Anomic/Burner, Counter-Attack và các mission có objective item.  
**Nguồn ưu tiên:** EVE Academy/CCP Support và Static Data Export (SDE) của CCP; code/dump fila-bot hiện có. Wiki cộng đồng trong tài liệu cũ không được xem là ground truth cho live combat.

## Kết luận điều hành

1. **Đã tìm thấy một lỗi có thể khiến bot không nhận `Cargo Delivery`.** Code xem mọi offer có `cargo_m3`/`dropoff`, hoặc title có từ `cargo/delivery/courier/transport`, là courier rồi chặn ngay trước nhánh Accept. Nhưng SDE TQ hiện hành xếp title `Cargo Delivery` vào `killMission` và ghi objective lấy hàng trong warehouse; đây là mission có item objective, không thể suy loại mission chỉ bằng từ “delivery”. Offline replay đúng shape của offer trả `BLOCKED`, không phải `accept_mission`.
2. **Nhận mission, phân loại objective và quyền bắn phải là ba quyết định riêng.** Theo policy Boss: chỉ decline Anomic; accept các offer khác. Nhưng accepted không có nghĩa là mission đã support, và tuyệt đối không cấp quyền bắn Empire Navy/CONCORD.
3. **Bot hiện chưa hiểu đầy đủ mission hay ship.** Nó chưa có mapping cấp mission L1–L4 trong SDE; chưa đọc objective-complete đáng tin; combat dựa vào tên NPC; ship/modules/drones có hardcode. Vì vậy 539 test xanh không đủ chứng minh chạy mượt hoặc an toàn live.
4. **Chưa bật live hoặc thay runtime code trong lượt nghiên cứu này.** Tôi đã rà source, phân tích SDE chính chủ, tái hiện lỗi offline, chạy full suite và cập nhật cảnh báo trong tài liệu nghiên cứu cũ. Báo cáo này đề xuất thứ tự sửa, không tuyên bố mission end-to-end đã được xác minh.

## 1. Nguồn và những gì dữ liệu chính thức thực sự cho biết

### 1.1 CCP Static Data Export hiện hành

Đọc manifest chính thức ngày **2026-11-11** cho thấy build **3682781**, phát hành `2026-11-10T12:19:55Z`. Tôi đọc file `missions.jsonl` trong ZIP build đó; SHA-256 của dữ liệu giải nén là `c12f8d67712bb24ba5e3d34ff1cf831efe18f419b552139fc07fe72c6063dee2` (53,388,038 bytes). CCP mô tả SDE là static game data, cập nhật theo game releases.[6][7][8]

Kết quả parse trực tiếp:

| Phép đếm | Kết quả | Cách hiểu |
|---|---:|---|
| Mission records | 2,892 | Bao gồm các biến thể và nhiều nhóm mission, không chỉ Security L1–L4 |
| Tên tiếng Anh duy nhất | 1,702 | Không đồng nghĩa có 1,702 mission thuộc pool L1–L4 |
| Record `killMission` / `courierMission` / khác | 1,662 / 1,155 / 75 | Loại template trong SDE |
| Title duy nhất theo nhóm | 913 / 718 / 71 | Không có title tiếng Anh nào xung đột giữa ba nhóm trong bản này |
| Title có nhiều biến thể | 346 | Cùng title có thể trỏ tới dungeon/objective khác nhau |
| Title có objective item type/quantity thay đổi | 150 | Title không đủ để suy item hoặc số lượng |

**SDE không cung cấp trường level cho các mission record này.** Nó cũng không phải bảng đầy đủ các wave trigger, thời điểm spawn, trạng thái từng objective hoặc dữ liệu agent nào sẽ offer mission nào ở level nào. Vì vậy không thể rút ra một “danh sách đầy đủ L1/L2/L3/L4” chỉ bằng cách đọc title trong SDE; level phải được lấy từ agent/offer thật trong game.

### 1.2 Ba ví dụ chứng minh không được phân loại theo keyword

- **`Cargo Delivery`:** có 16 record; tất cả là `killMission`, không phải pure `courierMission`. Các biến thể có bốn cặp objective item type/quantity khác nhau: `(42,10)`, `(2652,1)`, `(2732,1)`, `(12865,10)`. Record `_key=2959` yêu cầu một Synthetic Oil từ warehouse; briefing cũng cảnh báo nhìn chừng “suspicious activity”. Nên biểu diễn thành *mission-site/kill template + item objective*, rồi đọc item/quantity cụ thể từ offer đang mở — không map cứng từ title.[4][7]
- **`Counter-Attack`:** có bốn biến thể `killMission`; briefing nhắc các tàu Imperial, Federation, Caldari State và Republic. Theo policy Boss, offer vẫn được nhận, nhưng các target Empire phải bị chặn trước lock/fire/drone. Không được đổi “Counter-Attack” thành decline chỉ vì target faction nguy hiểm.[7]
- **`Anomic Agent`, `Anomic Team`, `Anomic Base`:** là mission site kiểu `killMission`, nhưng briefing SDE gọi là optional và nói rõ sẽ không phạt nếu decline. Đây là ngoại lệ phù hợp với policy chỉ decline Anomic; không nên gộp chúng vào combat mission thường.[7]

CCP Academy phân loại công việc Agent công khai thành Security, Mining và Distribution. Hai hệ phân loại cần giữ riêng: **division/career của agent** không giống **template/objective bên trong mission**. Một Security mission vẫn có thể bắt lấy item; một mission có từ “cargo” trong title không tự động là pure courier.[1][4][7]

## 2. Agent, level và vòng nhận/trả mission

### 2.1 Agent level là dữ liệu runtime, không suy từ mission title

Hướng dẫn chính thức đưa ra mức standing truy cập thường dùng: L2 `1.00`, L3 `3.00`, L4 `5.00` (L5 `7.00`); page Agents Panel `Available to you`/agent thật cần được ưu tiên hơn một default cứng.[2]

CCP cũng cảnh báo có thể mất standing khi fail mission hoặc decline hai mission từ cùng agent trong vòng bốn giờ.[2] Policy đã chốt của Boss là **chỉ decline Anomic**, nên quyết định accept/decline phải đơn giản và độc lập với việc mission có được bot support hay chưa:

1. Chọn agent đúng division (Security/Mining/Distribution), đọc level và `available` từ panel.
2. Mở dialog; đợi nó load thật (window tồn tại chưa có nghĩa nội dung đã sẵn sàng).
3. Đọc title đầy đủ, chain `n of m`, agent/level, objective, item và pickup/drop-off nếu có.
4. Decline đúng Anomic; accept mọi offer khác theo policy.
5. Sau click, xác minh offer biến mất và mission xuất hiện trong Job Board/mission panel. Không tính “accepted” chỉ vì đã gửi click.

### 2.2 Tách acceptance khỏi khả năng tự động chạy

Sau Accept, bot phải gắn trạng thái riêng, ví dụ:

- `accepted_and_supported`
- `accepted_but_unsupported` — giữ tàu ở station, không tự undock/attack, báo lý do cụ thể
- `objective_in_progress`
- `objective_complete_unverified`
- `turn_in_verified`

Như vậy vừa thực hiện đúng policy nhận offer, vừa không để mission không được hiểu dẫn tới bắn hoặc di chuyển mù.

### 2.3 Mission objective không chỉ là “giết hết NPC”

CCP xác nhận nhiều mission đòi khôi phục item cụ thể trong container/wreck.[4] Do đó mission planner cần một objective graph có thể chứa nhiều bước: tới site → combat/structure/trigger → lấy đúng item và quantity → giao/return → xác nhận objective complete. `killMission` trong SDE không có nghĩa “chỉ cần giết mọi NPC”; `Cargo Delivery` là ví dụ phản chứng.[4][7]

Không kết luận hoàn thành từ overview trống, hết 18 giây, không còn gate, hoặc đã bấm Complete. Cần đọc trạng thái objective/mission entry thật, rồi sau turn-in xác minh entry biến mất hoặc reward/turn-in state đổi.

## 3. Combat, Empire và CONCORD

- Quyền bắn phải cần **cả** mission template đã nhận diện **và** faction identity của từng target đã xác minh. MissionNPC generic/unknown vẫn là deny.
- Giữ hard deny cho CONCORD và cả bốn Navy/faction Empire theo policy Boss. Không dùng `mission title`, token substring hoặc “NPC xuất hiện trong overview” làm bằng chứng target hợp lệ.
- CCP ghi nhận việc dùng loại đạn quyết định damage type; EVE Academy khuyến nghị xem Show Info của hostile NPC để đọc thông tin target. Do đó ammo/target damage profile phải được lấy từ đúng NPC/fit, không lấy các con số `damage_weakness` chưa có nguồn trong bảng tĩnh.[1][9]
- Faction-standing loss và criminal response không nên bị trộn lẫn thành một khái niệm. Dù hậu quả chính xác còn phụ thuộc target/điều kiện, policy kỹ thuật ở đây vẫn rõ: Empire/CONCORD là protected; gặp một target đó thì zero lock/fire/launch/engage.

Đặc biệt, `Counter-Attack` phải **được nhận theo policy nhưng execution bị chặn** khi objective yêu cầu bắn các target protected. Accept mission không buộc bot phải thực hiện hành động trái whitelist.

## 4. Ship và cấp độ mission

EVE Academy mô tả lộ trình beginner tổng quát: frigate cho L1, T1 destroyer cho L2, cruiser/battlecruiser có thể làm L3 tùy kỹ năng/fit, và L4 thường cần battleship được fit tốt. Đây là baseline huấn luyện, **không phải luật cứng thay cho đọc ship/fit thật**.[1]

### Ship profile tối thiểu bot phải đọc trước khi tự chạy

- Hull/type/class thực tế; không mặc định “Gila” từ comment.
- Slot và loại module thực sự được lắp: weapon rack, propulsion, active repair/tank, sensor/utility.
- Ammo/charge đang nạp, số lượng ammo, reload/module active state.
- Drone bay: loại/số lượng/volume/HP, trạng thái in-bay/in-space và lệnh hiện tại.
- Shield/armor/structure/capacitor; cargo capacity, used/free và mission items.
- Mission level, NPC profile/range/ewar và các ship restriction được xác minh.

Chỉ sau khi đọc được profile thật mới lập fit-capability check: damage ứng phó, tank, range, mobility, cargo và module compatibility. Nếu module/charge/target identity không đọc được thì không bấm slot theo giả định.

## 5. Audit code fila-bot hiện tại

### P0 — offer có cargo bị chặn trước khi Accept

- `src/fila_bot/agent.py:125-156` phân loại offer bằng chữ trong nội dung (`cargo` + `deliver`, `courier`, `transport`).
- `src/fila_bot/modes/live_security.py:78-86` đặt `mission_is_courier=True` nếu offer có `cargo_m3`/`dropoff`, hoặc active title có `cargo/delivery/courier/transport`.
- `src/fila_bot/modes/security.py:168-176` block `mission_is_courier` **trước** nhánh DOCKED xử lý Accept.

Vì thế một `Cargo Delivery` security template có item objective bị biến thành courier và dừng trước nút Accept. Offline replay của cùng shape (`title="Cargo Delivery"`, `cargo_m3=0.1`, có nút Accept) trả `BLOCKED`, không có `accept_mission`. Đây là nguyên nhân cụ thể có thể tái hiện cho loại offer này; không khẳng định mọi lần “không nhận mission” đều cùng nguyên nhân.

### P1 — dữ liệu mission/faction chưa đủ tin cậy

- `src/fila_bot/missions_db.py:26-45` là bảng thủ công nhỏ, gắn level/faction/damage/notes nhưng không có nguồn cho đủ các trường; ví dụ `Cargo Delivery` được gắn Pirate/L1/kinetic trong khi SDE hiện không cấp level/damage đó.
- `classify_security_mission()` dùng danh sách thủ công và keyword: hiện `Cargo Delivery → courier`, `Counter-Attack → unknown`, dù SDE lần lượt là `killMission` có item objective và `killMission` hướng vào các faction ship.
- `src/fila_bot/mission.py:201-230` suy faction NPC từ substring tên trong `rats.classify()`, không đọc faction ID/type ID đáng tin từ target. Unknown bị block là đúng; nhưng token coverage chưa đủ để biến tên thành bằng chứng identity.
- `AgentEye.read_offer()` không đưa `agent_level` vào offer; `SecurityMode` gọi `evaluate_offer(title)` với default L1. Vì policy accept không phụ thuộc level nên chưa đổi được quyết định accept, nhưng làm mất dữ liệu cần chọn ship/plan theo level.

### P1 — ship/objective/turn-in state đang bị giả định

- `live_security.py` tự đặt `drones_in_space = 2 if self._drones_out else 0`; đây là biến nội bộ, không phải quan sát trạng thái drone thật.
- Combat action hardcode Mid 1 là afterburner và high slots F1–F4 là 4 RLML; không xác nhận hull/module/charge hiện đang lắp trước khi gửi phím.
- `SecurityMode` dùng fixed `WAVE_WAIT_S=18`; sau đó nếu không thấy target/gate có thể kết luận pocket clear/warp home mà không có objective-complete evidence.
- `SecurityMode` tăng `completed_missions` trước khi click Complete; runner chưa xác minh click thành công hoặc mission entry biến mất.
- Các run TQ ngày 2026-11-11 trước đó có fail-closed ở `cargo hold` và `docked but no route`. Chưa có live verification chứng minh pickup, cargo, route, turn-in hoặc full mission loop đã hết lỗi.

### Test coverage gap

`python tests/run_all.py` vẫn cho **33 test files, 539 PASS, 0 FAIL** (15.18s), nhưng test hiện xác nhận sai taxonomy: `tests/test_g9_dialog.py` mong `Cargo Delivery == courier` và `Counterattack == unknown`; `test_g10_mission_loop.py` cấp sẵn `mission_is_courier` thay vì kiểm tra parser+runner tích hợp. Test pass không phủ hợp đồng thật `SDE template → offer → acceptance → objective → turn-in`.

## 6. Mô hình dữ liệu và kiến trúc đề xuất

Tạo catalog versioned từ CCP SDE, nhưng không nhồi wave facts suy đoán vào đó. Mỗi canonical mission record cần tối thiểu:

```text
sde_build, mission_key, canonical_title, localized_titles,
template_kind (killMission/courierMission/other), variant_ids,
objective_type_ids, objective_quantities, requires_live_objective_parse,
agent_division, runtime_agent_level, target_faction_evidence,
objective_graph, wave_trigger_evidence, ship_constraints,
support_status, evidence_dump_ids, last_verified_build
```

`agent level`, exact objective item, spawned NPC/faction, wave trigger và completion state là **runtime/live evidence** chứ không được bịa từ title. Nếu SDE có nhiều biến thể khác nhau nhưng offer không đủ thông tin để xác định record, đánh dấu ambiguous/unsupported.

### Quy tắc decision layer

1. `evaluate_offer(title)`: chỉ decline Anomic; accept các offer khác theo policy.
2. `classify_template(title, SDE build)`: kill/courier/other/unknown — không dựa vào từ cargo/delivery.
3. `parse_objective(live offer)`: objective list, item name/quantity, pickup/dropoff, chain, deadline; thiếu field trọng yếu thì `BLOCKED` sau khi accept, không tự chạy.
4. `check_ship_capability(live fit)`: xác nhận hull/modules/ammo/drones/cargo.
5. `authorize_target(mission, target)`: target identity exact + mission allow-status; protected Empire/CONCORD luôn deny trước mọi action combat.
6. `complete_mission`: chỉ tăng counter sau read-back xác nhận turn-in thành công.

### FSM cần có pre/post-condition

```text
DOCKED → AGENT_DIALOG_LOADING → OFFER_READY
→ ACCEPT_CLICKED → ACCEPTED_CONFIRMED
→ OBJECTIVE_PARSED → SHIP_CHECKED → ROUTE_CONFIRMED
→ SITE_IDENTIFIED → OBJECTIVE_STEP / COMBAT
→ OBJECTIVE_COMPLETE_CONFIRMED → RETURN_TO_AGENT
→ COMPLETE_CLICKED → TURN_IN_CONFIRMED
```

Mỗi bước phải log dữ liệu quan sát + reason. Với pure courier, riêng flow capacity/item/route/dropoff. Với `killMission` có item objective như Cargo Delivery, giữ cùng mission loop và thêm pickup/objective step; không delegate sang Distribution chỉ vì tên hoặc có cargo.

## 7. Cổng nghiệm thu theo giai đoạn

1. **P0 regression:** kiểm tra dialog-loading; Cargo Delivery có cargo item vẫn phát `accept_mission`; sau accept nhận diện `killMission + item objective`; Counter-Attack được accept nhưng Empire target tạo zero lock/fire/drone action; Anomic duy nhất decline.
2. **Catalog tests:** toàn bộ 1,702 title tiếng Anh parse đúng nhóm theo SDE build; test title/chain/locale/variant conflict; cập nhật SDE mới phải báo diff.
3. **Ship snapshot tests:** fixture từng hull/module layout và missing UI field; không có module giả/default; chỉ fire khi module active/charge/target được xác minh.
4. **Objective tests:** từng dạng item, destroy structure, kill, gate, courier, multi-part chain, unknown/ambiguous.
5. **Live staged:** read-only dump → dry-run → supervised một mission L1 cụ thể, verify mọi transition → sau đó mở rộng mỗi template/level. L2, L3, L4 đều cần fixture/mission thực riêng; L1 xanh không chứng minh L4.
6. **Completion metric:** offer accepted, mission objective complete, reward collected, mission entry gone, ship state safe. Mỗi chỉ số đọc lại từ game, không tính theo số lần click.

## 8. Trạng thái xác minh trong lượt này

- Đã đọc CCP SDE build 3682781 và parse số lượng/biến thể nêu trên; manifest và dữ liệu giải nén được lưu ở Hermes scratch, không đưa file raw 53 MB vào repo.
- Đã replay offline nhánh Cargo Delivery offer; quyết định hiện tại là `BLOCKED` trước Accept.
- Đã chạy full offline suite: **539 PASS, 0 FAIL**. Suite chưa kiểm tra lỗi taxonomy nêu trên.
- Không chạy hoặc điều khiển client EVE trong lượt này; không tuyên bố auto-run mission đã hoàn thành.
- Runtime code chưa sửa. Chỉ thêm audit warning vào `docs/MISSION_RESEARCH.md` để người sau không dùng bảng wave/damage cũ làm quyền bắn.

## Sources

[1] https://www.eveonline.com/eve-academy/careers/enforcer — EVE Academy: Enforcer
[2] https://support.eveonline.com/hc/en-us/articles/203217152-Standings — CCP Support: Standings
[4] https://support.eveonline.com/hc/en-us/articles/203344892-Missing-Mission-Item — CCP Support: Missing Mission Item
[6] https://developers.eveonline.com/docs/services/static-data — EVE Developer Docs: Static Data
[7] https://developers.eveonline.com/static-data/tranquility/eve-online-static-data-3682781-jsonl.zip — CCP SDE JSONL build 3682781
[8] https://developers.eveonline.com/static-data/tranquility/latest.jsonl — CCP SDE latest build manifest
[9] https://support.eveonline.com/hc/en-us/articles/203280501-Damage-Types-and-Resistances — CCP Support: Damage Types and Resistances


---

## 9. Cập nhật chiều 11-11: đã sửa P0 + chạy vòng lặp E2E (offline)

Báo cáo ở §8 ghi "Runtime code chưa sửa" — phần này ghi nhận các thay đổi ĐÃ làm
sau đó. Nghiệm thu vẫn theo nguyên tắc: SIM/dump không được gọi là live E2E.

### Đã sửa (code + test)
- **`agent.py::read_offer()`**: bỏ suy luận `courier` từ cặp từ `cargo`+`deliver`.
  Thay bằng bằng chứng objective đọc được từ briefing TQ thật:
  `Transport Objective` = courierMission (`g2_offer_v3_165506.json`),
  `Bring Item Objective / Acquire these goods` = killMission có item objective
  (`g10_turnin_dialog.json`). Thêm `objective_kind`, `template_kind`.
- **`missions_db.py`**: bảng `SDE_TEMPLATES` chỉ chứa title được nêu rõ trong báo
  cáo SDE build 3682781 (Cargo Delivery → `kill_item`, Counter-Attack → `kill`,
  Anomic* → `burner`); `normalize_title()` cắt chain `(1 of 5)`; so khớp ĐÚNG title
  thay vì substring. `classify_security_mission("Cargo Delivery")` giờ trả
  `item_objective`, không còn `courier`.
- **`live_security.py::refresh()`**: `mission_is_courier` không còn lấy từ
  `cargo_m3`/`dropoff`/keyword title; thêm `active_mission_title`,
  `mission_support`, `mission_panel_observed`; `drones_in_space = None` thay vì bịa `2`.
- **`security.py`**: xoá block courier ĐỨNG TRƯỚC nhánh Accept (P0); tách
  `accepted_but_unsupported` (giữ tàu ở trạm, không Quit/bắn mù); turn-in chỉ tăng
  counter sau **read-back** (`mission_panel_observed=True` + entry biến mất); phát
  hiện modal `Cannot Complete Mission` → BLOCKED, không dismiss-OK rồi bấm Complete
  lặp vô hạn; thêm `_was_in_space` (vừa nhận → undock, đi làm về → mở chat trả),
  `_site_visited` (beacon trước warp_home), và không áp wave-wait trước khi tới site.
- **`sim_worlds.py::SecurityE2ESim`** cắm vào `build_supervisor(sim=True)` theo đúng
  hợp đồng `refresh → tick → execute`, có đồng hồ ảo để vượt wave-wait/grace.
- **`cli.py`**: dòng tổng kết dùng `completed/done` thay vì `runs`.
- **`LAUNCHER.bat`**: option 12 = Security E2E SIM 1 mission.

### Đo được (tool output thật)
- `python tests/run_all.py`: **36 files, 579 PASS, 0 FAIL** (~12 s).
- `python -m fila_bot.cli security --max-missions 1 --tick 0.15` → exit **0**,
  `phase IDLE_DONE`, `xong 1`, trace đủ 9 hành động (open_agent_chat → accept →
  undock → warp_beacon → lock/fire → recall_drones → warp_home → complete → read-back).
- `cli distribution --max-missions 1` → exit 0, `IDLE_DONE`, 1 mission.
- `cli abyss --max-runs 1` → exit 0, `DOCKED`, 1 run.
- Replay offline qua `LiveSecurityRunner.refresh() → SecurityMode.tick()` trên 5
  dump TQ thật (đã copy vào `tests/fixtures/ui_tree_e2e_*.json`): offer courier
  được Accept, Cargo Delivery không bị gán courier, modal "Cannot Complete Mission"
  (objective: 1 x Crates of Synthetic Oil) bị chặn fail-closed, Connection Lost →
  E-STOP, panel mission không đọc được → KHÔNG tự xác nhận turn-in.

### Vẫn CHƯA xác minh (không được gọi là E2E live)
- Client EVE chưa mở/đăng nhập: `find_client_window()` = `None`,
  `cli status` / `cli security --live` trả exit 2 (`DLL initialize fail`). Các tiến
  trình `eve-online.exe` đang chạy là launcher/updater, không phải `exefile.exe`.
- Chưa có dump **sau turn-in** có Job Board được quan sát và rỗng → read-back tích
  cực chỉ mới chứng minh bằng SIM; live cần dump này để xác nhận.
- Chưa ground:objective-complete (green check), ship/fit/module/drone window,
  lock indicator, wave trigger, faction ID từ target. Vì thế live vẫn fail-closed
  đúng thiết kế; chưa thể khẳng định bot tự chạy mission thật không giám sát.
- Lệnh chờ Boss mở client: `python -m fila_bot.cli security --live --max-missions 1`
  (DRY, chỉ đọc) rồi mới tính tới `--confirm-input` có giám sát.


---

## 10. LIVE có giám sát 11-11 (client TQ `EVE - Kompi Yaken`, acc alpha)

Boss mở client, đăng nhập và quan sát. Đây là **lần chạy live có bấm phím/click thật
đầu tiên** sau các fix ở §9. Không phải tự chạy không giám sát.

### Đo được
- `find_client_window()` = `EVE - Kompi Yaken`, pid 9744, origin (2,31), 1024×1018.
- `cli status`: DOCKED tại `New Caldari Prime - Moon 1 - Poksu Mineral Group Mineral
  Reserve`, sec 0.9, agent `Inikko Samanuni` (Security L1), Job Board observed &
  rỗng, không dialog/kho/route. Cold-start reader ~6–10 s.
- LIVE DRY-RUN 45 s: đọc client thật, quyết `open_agent_chat` mỗi tick, **0 crash,
  0 FAIL/MAYDAY, 0 E-STOP** (dry không đổi thế giới nên lặp quyết định — đúng kỳ vọng).
- LIVE `--confirm-input` lần 1 (`scratch/live_confirm_security.log`, exit 3):
  1. click chat agent Inikko Samanuni → hội thoại mở, load ~1 s;
  2. đọc offer thật **"What's in a Name – Change of Address (1 of 5)"**, policy → ACCEPT;
  3. bấm Accept → mission xuất hiện (`Accepted` trong dialog);
  4. EVE hiện luôn nút **Complete Mission** dù objective chưa xong → bot bấm →
     modal **"Cannot Complete Mission / One or more mission objectives have not
     been completed"**;
  5. guard fail-closed chặn: BLOCKED có lý do thật, **không dismiss-OK rồi bấm lại,
     không Quit mission**.
- Dump UI tree ngay lúc modal còn mở → `tests/fixtures/ui_tree_e2e_06_live_cannot_complete.json`
  (1110 node, mission active, Job Board observed, modal text thật). Đã đóng modal OK
  bằng control layer để trả client về trạng thái sạch.
- **Bug mới tìm thấy trực tiếp trên live:** nút `Complete Mission` KHÔNG phải bằng chứng
  objective xong. Đã sửa: `SecurityMode` chỉ bấm Complete khi `_was_in_space=True`
  (từng rời trạm đi làm) — nếu chưa rời trạm → `OBJECTIVE_UNVERIFIED`, giữ tàu ở
  trạm, báo rõ, không Quit. Regression nằm ở `test_g10_mission_loop.py` (4e) và
  `test_e2e_mission_loop.py` (4a, replay 5 dump).
- LIVE `--confirm-input` lần 2 sau fix (`scratch/live_confirm_security_v2.log`, exit 3):
  bot đọc đúng mission đang active, **KHÔNG bấm Complete**, không tạo modal mới,
  dừng với lý do "chưa rời trạm". Screenshot xác nhận client sạch, mission vẫn
  `Accepted`, không bị Quit.

### Kết luận trung thực
- Đã chứng minh **live**: đọc UI tree thật, mở hội thoại, đọc offer thật, nhận mission
  thật bằng click thật, và dừng đúng khi thiếu bằng chứng objective.
- **CHƯA** chứng minh live: undock → warp site → combat → về trạm → turn-in →
  read-back. Mission hiện tại đòi "Give the diplomats enough time to escape. Engage
  any hostiles" tại Hirtamon 0.9, tàu đang là corvette; ship/fit/module/drone,
  objective-complete, faction ID và beacon/site đều chưa ground → bot fail-closed
  đúng thiết kế, không bắn/undock mù.
- Hệ quả của guard `_was_in_space`: mission do Boss làm tay xong rồi mở bot ở phiên
  mới cũng sẽ bị giữ lại cho đến khi có tín hiệu objective-complete thật. Đây là
  đánh đổi có chủ đích (fail-closed), không phải bug; cần ground tín hiệu đó để mở.
- Mission "What's in a Name – Change of Address (1 of 5)" vẫn đang **Accepted** trong
  client (expires 2026.11.18 11:16). Bot không Quit theo đúng policy nhận offer.


---

## 11. Sửa sai: active hull là **Gila - Kompi Yaken**, KHÔNG phải corvette

Boss phản hồi: "tao đang bay gila chu bay pod đéo đâu". Đúng. Ở §10 em đã suy
"corvette" từ label `Board my Corvette` trong LobbyWnd — **đó chính là suy luận bị
cấm** (`eye.py::active_ship_observation()` docstring và handoff 11-11 đều cảnh báo:
nút lobby là candidate, không phải bằng chứng hull đang active). Xin nhận lỗi, đã
sửa cả code lẫn tài liệu.

### Ground bằng live-probe (không phải screenshot, không đoán)
- Bot click thật nút `StationServiceBtn _name=fitting` tại (925,194) client qua
  `control.execute(dry=False, win=find_client_window())` → `FittingWindow` mở
  (Boss nhìn thấy cửa sổ Fitting hiện ra).
- Dump UI tree → `tests/fixtures/ui_tree_live_gila_fitting.json` (1316 node).
  `EveLabelMedium _name=nameCaption` = **`Gila - Kompi Yaken`**.
- Fit đọc được từ cùng dump: 674.0 dps + 489.1 dps drone, 31.920 ehp, 86 hp/s,
  cap ổn định 1680 GJ / 6m7s, 243.8 m/s, targeting 69.60 km / 7 targets,
  cargo 148.7 / 440.0 m³, drone bay 100.0 / 100.0 m³, giá fit 391.1M ISK.
- `cli status` chạy lại trên client thật giờ in: `Active ship: Gila`,
  `Ship name: Gila - Kompi Yaken`, `Ship panel observed: True`.

### Fix perception
- `eye.py::active_ship_observation()`: ưu tiên `ShipsPanel` card `Active`; nếu
  không có, đọc `FittingWindow` → `nameCaption`. Không có panel nào → `(False, None)`
  (UNKNOWN), `FittingWindow` đang load → `(True, None)`. Tuyệt đối không đọc
  `Board my <ship>`.
- `tests/test_live_gila_fitting.py`: 5 PASS, gồm counter-example cho chính cái
  bẫy nút lobby và case panel đang load.
- Suite: **37 files, 587 PASS, 0 FAIL**.

### Về `computer_use`
3 lần gọi `computer_use` đều là `action='capture'` (chụp màn hình **read-only**,
0 click / 0 phím). Cửa sổ `Cua.AgentCursorOverlay.default` Boss thấy là overlay
của tool đó. Mọi input thật vào EVE đều đi qua `control.py` + `input.py`
(SendInput) — bằng chứng là chính UI tree của game đổi trạng thái (hội thoại mở,
offer xuất hiện, mission `Accepted`, modal `Cannot Complete Mission`). Từ nay
ground bằng DLL reader, không chụp desktop nữa.


---

## 12. "Bắt đầu như nào?" — AUTO.bat và 2 lý do bot đứng im

Boss chốt: code cả ngày nhưng cái đơn giản nhất là **bắt đầu** chưa ai làm xong.
Câu trả lời: **bấm đúp `D:/fila-bot/AUTO.bat`** (hoặc `AUTO.bat 3` = 3 mission).
Không menu, không flag, không `set PYTHONPATH`. File tự tìm Python, tự set env, chạy
`cli security --live --confirm-input`, in trace, Ctrl+C dừng an toàn.

Em đã chạy thật file này qua `cmd /c AUTO.bat 1` (log `scratch/auto_run.log`):
banner → DLL init 13s → `RUNNING | phase TRAVEL_SITE` → chạy liên tục tới khi
timeout 90s cắt (exit 143). **Bot có khởi động và chạy trên client thật.**
Lúc đó client đang ở space tại **Hirtamon 0.9** (Boss đang bay Gila), overview có
mission beacon **`Avalon Flotilla` (Celestial Beacon) 27.0 AU**, route 1 jump,
không có hostile trong overview (`scratch/probe_space.py`). Bot phát lệnh warp tới
beacon. Chưa hoàn thành mission.

### 2 lý do "đứng im" đã sửa
1. **Tự thêm biên độ an toàn (= policy sai, nhìn như bug kỹ thuật).** Mission
   "What's in a Name - Change of Address (1 of 5)" có objective đọc trực tiếp từ
   briefing live: *"Give the diplomats enough time to evacuate. **Engage any
   hostiles.** Location 0.9 Hirtamon"*. Nhưng `mission_support` = `unknown` (title
   không có trong catalog) nên bot giữ tàu ở trạm. Đã tách 2 lớp:
   - `GROUNDED_COMBAT_OBJECTIVES` (có `evidence` + `source` fixture) →
     `mission_travel_support=True` → **được phép undock/di chuyển** kể cả khi
     dialog đã đóng (cold start).
   - Quyền **bắn** vẫn nằm ở `authorize_security_targets()`: cần title trong
     catalog + faction ID dương tính; title này vẫn bị từ chối. Regression:
     `test_e2e_mission_loop.py` mục 4c.
2. **Spam lệnh warp.** Nhánh `TRAVEL_SITE` phát `warp_beacon` MỖI tick (kèm
   `sleep(3)`), warp 27 AU không bao giờ kịp xong → đứng 75s. Đã thêm
   `WARP_COOLDOWN_S=60`, tối đa 3 lần, quá → `BLOCKED` có lý do; reset khi thấy
   hostile (đã tới site). Regression: mục 4d.

Suite sau fix: **37 files, 591 PASS, 0 FAIL**.

### Còn đúng 3 node để gọi là "auto hoàn toàn"
| Node | Cần để | Trạng thái |
|---|---|---|
| Warp tới site + xác minh đã tới | thay beacon-distance/overview bằng chứng arrival | chưa ground |
| Faction ID của target | cấp quyền `lock/fire/launch`; chống bắn Empire/CONCORD | chưa ground |
| Objective-complete (green check) | trả mission + read-back | chưa ground |

Em **không nới** quyền bắn: bắn nhầm Empire Navy/CONCORD là mất standing / ăn
CONCORD. Bot vẫn fail-closed trước mọi weapon action. Khi có 3 dump trên (Boss bay
tới site cho em đọc overview + dump objective xong) em nốt combat + turn-in.

`AUTO.bat` chạy không giới hạn khi Boss tự bấm đúp; em chỉ chạy có `timeout` để
soi log, không để bot bấm phím thật không giám sát qua đêm.
