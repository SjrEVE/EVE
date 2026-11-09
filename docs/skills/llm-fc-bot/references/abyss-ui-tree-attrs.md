# EVE client UI tree — grounded schema + reader build/dump recipe

Nguồn ưu tiên: dump JSON từ client thật (`ui_dump*.json`) > source upstream
Sanderling (`implement/read-memory-64-bit/EveOnline64.cs`,
`implement/alternate-ui/source/src/EveOnline/ParseUserInterface.elm`) > Viir/bots
framework (`ParseUserInterface.elm`, `Bot.elm` warp-to-0 — tóm tắt ở
`D:/fila-bot/docs/VIIR_FRAMEWORK_NOTES.md`) > docs cộng đồng.
File docs đồng bộ: `D:/fila-bot/docs/EVE_UI_TREE_ATTRS.md`,
`dist/fila-bot-portable/dll-source/PROVENANCE.md`.

## Schema đã ground trên client (Photon HUD)

| Cần đọc | Node thật | Attr |
|---|---|---|
| Overview | `OverviewWindow` (name=`overview`) | `_display` |
| Text entry | `OverviewScrollEntry` → `OverviewLabel` | `_text` (KHÔNG phải `_setText`) |
| Cột | `EveLabelSmall` cùng hàng entry đầu | `_setText` → map theo toạ độ x |
| Selected | `SelectedItemWnd` (name=`selecteditemview`) | `_setText` |
| HP | `ShipHudSpriteGauge` | `_name=shieldGauge/armorGauge/structureGauge`, `_lastValue` float 0..1 |
| Speed | `SpeedGauge` → label `_name=speedLabel` | `_setText="600 m/s"` |
| Cap | `CapacitorContainer` → `Sprite _name=pmark` | `_color` = object `aPercent/rPercent/gPercent/bPercent` |
| Module rack | `SlotsContainer` (+ `OverloadBtn` hi/med/lo) | `ModuleButton` chỉ có khi tàu FIT module |
| Confirm popup | `KeyActivationWindow` / `MessageBox` | `_setText` |
| Station window | `LobbyWnd` → `UndockButton` | label `Undock`; tabs `Tab _name=stationInformationTabAgents/guestsPanel/officesPanel/Button_InventoryPanel` |
| Agents trong station | `AgentsPanel` → `AgentEntry` (`_name` = tên agent) | xem mục dưới |
| Context menu | `ContextMenu` (name=`menuview`) → entry có `_name=context_menu_<Text>` | Nhận entry theo `_name`, KHÔNG theo type (DLL decode sai type entry thành `PyColor`/`Sprite`/`PyChildrenList`, chỉ vài entry là `MenuEntryView`); text = `_setText` đầu tiên trong subtree, bất kể type. Submenu chỉ bung khi HOVER; menu hiện sau 1–2 s → poll |
| Agent dialog | `AgentDialogueWindow` → `ButtonGroup` → `Button _name=AcceptMission_Button/DeclineMission_Button/DeferMission_Button`; sau Accept có label `Complete Mission`/`Quit Mission` | nội dung offer ở `Edit _name=briefing_browser/objective_browser` `_sr.htmlstr` (cần DLL decode Bunch); có `LoadingWheel` khi chưa load → chờ |
| Pickup/Drop-off link | `objective_browser` → `VirtualTable` → `Cell _name='tablecell R-C'` → `Link _name=textlink` | Link KHÔNG có text; row 0 = Pickup, row 1 = Drop-off (tên wrap nhiều dòng = nhiều Link, lấy Link trên cùng); right-click → `Set Destination` |
| Mission đang nhận | `InfoPanelJobBoard` → `AgentMissionInfoPanelEntry` (`_name=agent_missions:<agentID>`) → `EveLabelLarge._setText` = tiêu đề | `InfoPanelAgentMissions/MissionEntry` là layout cũ; left-click tiêu đề KHÔNG bung entry; right-click → Agent/Location/Start Conversation/View Details/Untrack |
| Inventory | `ButtonInventory` (Neocom) mở `InventoryPrimary` → `InvContCapacityGauge` (`capacityText` = `used/max m `), container `ShipCargo`, tree `TreeViewEntryWithTag _name=ItemHangar/StationShips` | item: `Label _name=itemNameLabel`; cargo rỗng = text `Nothing Found` |
| Route | `InfoPanelRoute`: caption `Route <fontsize=12>N Jump(s)`; tên hệ kế tiếp ở `alt= Next System in Route >Tên<`; `AutopilotDestinationIcon` = marker | caption KHÔNG phải tên đích; right-click marker = menu của stargate/station (Jump/Dock) |
| Modal | `MessageBox` (layer `LayerCore`) → `TextHeadline` + `TextBody` + `Button _name=ok_dialog_button` | `Connection Lost` chỉ có nút Quit → E-STOP, không bấm |

### AgentsPanel (ground khi dock ở trạm có agent)
- Con của `AgentEntry`: `EveLabelMedium _name=nameLabel` = `"Tên <color=…>Level N</color>"`,
  `_name=levelLabel` = **division** (vd `Distribution`, dù tên là levelLabel),
  `missionLabel`/`timerLabel` (rỗng khi chưa có mission), `AgentConversationIcon
  _name=agentChatBtn` = nút mở hội thoại.
- Khả dụng: header label KHÔNG có `_name`, text `Available to you` / `Not available
  to you`; entry thuộc header gần nhất có y NHỎ hơn nó (so `abs_center`).
- Không phải trạm nào cũng có agent; một trạm có thể chỉ có 1 division → kiểm
  division trước khi chọn base cho mode cần division khác.
- `InfoPanelLocationInfo` khi dock trả được station + sec nhưng `system` có thể
  `null` — đừng dựa vào system để xác nhận jump cho tới khi parser được sửa/ground.

### Chưa ground (fail-closed)
Nút `Request Mission` và vị trí nút `Complete Mission` dạng `Button._name`, kéo thả
item hangar → cargo, lock (`TargetInBar`), `ModuleButton` khi có fit,
`ActivateButton` filament. `InfoPanelLocationInfo.system` vẫn `null` → xác nhận
jump bằng security/route đổi, không bằng tên system.
Tên từ Viir/Sanderling chỉ là ứng viên — Photon đã lệch nhiều lần.

Tên Sanderling CŨ (`OverView`, `ActiveItem`, `ShipSlot→ModuleButton`, `_setText`
trong entry) KHÔNG còn đúng trên client này. Giữ lại từ upstream phần **semantics**:
- pmark `aPercent < 20` = đoạn cap CÒN; cap% = số pmark còn / tổng pmark × 100
  (`ParseUserInterface.elm`, `parseShipUICapacitorFromUINode`).
- parser màu đọc `aPercent/rPercent/gPercent/bPercent` (`jsonDecodeColorPercent`).

`_displayX/_displayY` là **toạ độ tương đối với node cha** — cộng dồn từ UIRoot để
ra toạ độ click tuyệt đối (`Eye.abs_center`); `Eye.center_xy` chỉ trả toạ độ local.

## Reader DLL: stub → decoder (đọc source upstream, không mò hex)

1. Tìm hàm rỗng trong `dist/fila-bot-portable/dll-source/`
   (`grep -n 'void read_python_type' *.c`). Stub trả null cho mọi attr kiểu đó.
2. `float`: `PyFloatObject` = refcnt(8) + ob_type(8) + `ob_fval` double tại +0x10;
   đọc 0x18 byte; struct field phải là `double`, không phải `FLOAT`.
3. `PyColor` (`EveOnline64.cs`, `ReadingFromPythonType_PyColor`): đọc 0x18 byte,
   pointer tại +0x10 trỏ tới dict; lấy entries có key string `_a/_r/_g/_b`,
   mỗi value là PyFloat 0..1 → percent = value×100. Emit object JSON đúng 4 key
   trên; `uitree.c` in object (không phải string), `cache.c` copy `bunch_value`.
4. Dispatch theo `get_python_type_name_from_python_object_address` == `"PyColor"`.
5. Fail-closed: thiếu kênh nào → không emit, `eye` trả `None`.

## Build + verify

```
cd dist/fila-bot-portable/dll-source
bash build_mingw.sh /c/w64devkit/w64devkit/bin/gcc.exe   # hoặc gcc trong PATH
sha256sum eve-memory-reader.dll
```
Lệnh gcc: `-O2 -DUNICODE -D_UNICODE -shared -o eve-memory-reader.dll
eve-memory-reader.c cache.c hashtable.c memory.c process.c python.c uitree.c
-lpsapi -static-libgcc` — build deterministic (hash lặp lại). Copy DLL vào
`dist/fila-bot-portable/src/` (tracked) VÀ `vendor/eve-memory-reader/x64/Release/`
(gitignored), cập nhật hash trong PROVENANCE.md; KHÔNG commit DLL build ra trong
`dll-source/` (thêm `dist/*/dll-source/*.dll` vào .gitignore).

Dump client thật (đường dẫn native Windows, không dùng `/d/...`):
```
cd dist/fila-bot-portable && python dump_ui.py --out 'D:/fila-bot/ui_dump.json'
```
Verify decoder: đếm số màu khác nhau trong dump (phải >1, không phải toàn null),
rồi chạy bot `--mode live` KHÔNG có `--confirm-input` và đọc `bus/bot_to_fc.jsonl`
→ STATE phải có số thật, không có FAIL/MAYDAY storm.

## Quy trình ground một node mới (1 bối cảnh = 1 vòng)

1. Boss đứng đúng bối cảnh (dock trạm có agent, mở dialog, có route…). Bot vẫn
   dry — chỉ đọc. Một lần đọc full memory mất ~20–30 s; gom mọi thứ cần vào 1 lệnh.
2. `e = Eye(); root = e.refresh()` → lưu `dumps/<gN>_<ctx>_<HHMMSS>.json`
   (`dumps/` không commit).
3. In `Counter(type)` lọc keyword liên quan, rồi walk subtree node đích in
   `type | _name | text | abs_center | keys` để thấy cấu trúc thật.
4. Copy dump vào `tests/fixtures/ui_tree_<ctx>.json`; viết extractor trả `None`
   khi không thấy node; test bằng `real = Eye.__new__(Eye); real.root =
   json.loads(FIX.read_text(encoding='utf-8'))` và assert đúng giá trị nhìn thấy
   (tên, level, toạ độ) + case không có panel → `None`.
5. Chạy full loop test, commit `G<n> ground: …`, báo Boss bảng kết quả + bối cảnh
   tiếp theo cần đứng. Click đầu tiên vào client: hỏi Boss tự bấm hay cho bot bấm
   1 click có verify; nhắc đưa cửa sổ EVE lên trên cùng (click rơi vào cửa sổ
   khác = báo ok giả).

Một trạng thái tĩnh (vd cap đầy) KHÔNG chứng minh công thức ở trạng thái khác:
nếu thao tác làm đổi state (warp, bật module) không visibly xảy ra, báo
"static-only", đừng claim dynamic verification.
