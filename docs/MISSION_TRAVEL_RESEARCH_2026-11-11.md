# Mission-site travel: nghiên cứu từ cộng đồng + EVE-Master / Sanderling (11-11)

> Boss yêu cầu: *"lên internet tìm hiểu thật kỹ các chú nó làm đi — eve-master miễn phí đó"*.
> Báo cáo này trả lời trực tiếp lỗi **"warp đến chỗ làm mission sai mẹ rồi"**.
>
> **Hạn chế nguồn (đã cập nhật 19:5x):** backend `web_extract` của phiên này là
> search-only nên phần lớn trích dẫn lấy từ **search snippet**. Đã lấy thêm **toàn
> văn** qua `curl` cho: trang Node Store của EVE-Master (node anomaly, 40 KB),
> `eve-master.com/pricing`, `wiki.eveuniversity.org/Missions` (92 KB). ISXEVE wiki
> trả 403, forum-archive trả 503, TinyMissionsRunner chặn Cloudflare — các trang
> đó chỉ có snippet. Khẳng định chỉ đi xa tới những gì nguồn nói rõ.

## 1. Cái em làm sai (đo được trên client thật)

- `MissionEye.mission_beacons()` trả **bất kỳ** entry overview có `beacon` trong
  `Type`. Client TQ lúc đó có `Derelict Ruins | Celestial Beacon | 0.6 AU` → bot
  warp tới đó. Đó là **cosmic anomaly / exploration site**, không phải mission
  site. Warp xong `Derelict Ruins` còn 5.800 m, `SelectedItemWnd` hiện
  `Gallente Broadcast Tower` (tên structure trong objective) — sai địa điểm.[1][2]
- Em cũng right-click link `Location 0.9 New Caldari` trong AgentDialogueWindow rồi
  bấm `Add Waypoint`. Menu của link đó thực tế là `Show Info / Add Waypoint /
  Show on Map / Show in Mapbrowser (Solar System) / Avoid New Caldari (Solar
  System)` — tức link trỏ tới **solar system**, không phải site. CCP từng ghi nhận
  đúng thay đổi này: *"I cannot warp to the mission locations anymore from the
  agent conversation page. Looks like the mission location has been replaced by
  the solar system location"* và câu trả lời là *"Have to use the 'Warp to' button
  under Agent Missions"*.[3] Nói cách khác, `Add Waypoint` chỉ đưa tàu tới **đúng
  hệ**, không giải quyết bước warp tới pocket.

## 2. Cơ chế đúng theo CCP / người chơi

- **Right-click vào khoảng trống trong space** → `Agent Missions` → tên mission →
  `Encounter (Deadspace)` → `Warp to Location`. Hướng dẫn career agent ghi rõ:
  *"Warping to mission sites - You can right click in space on nothing, a context
  menu will come up. You can warp off of there, under Agent / Deadspace"*.[1]
  Một guide khác mô tả chuỗi *"right click any where in space, go down to
  **Covering the Basics** and **Encounter(Deadspace)**, **Warp To Location**"*.[2]
  Người chơi khác xác nhận *"R click in space and see if it gives you an option
  under mission part of the r click menu. Sometimes you have to do that instead
  of a warp to if its a deadspace pocket"*.[11]
- **Panel `Agent Missions` góc trên-trái** có nút/link `Warp to Location`
  (đôi khi `Warp to Destination`): *"On the left side of your screen you wil see
  Agent Missions. One of the options will be Encounter. Click the link below it
  and you will warp to the place your agent wants you to mine"*.[4] Nút này đổi từ
  `Set Destination` sang `Warp to Location` **khi tàu đã ở đúng hệ**.[4][5]
- **Điều kiện tiên quyết:** *"A bookmark to the mission will only show up on the
  right click menu if you are in the correct system. If you are not, then right
  click on the system name ... hit 'set destination', and go to the stargates
  specified until you're there"*.[5] và CCP ghi nhận lỗi *"When I get a mission
  which takes me to a different system, about half the time, the prompt ... never
  appears (warp to location)"*.[12] Tức: **set destination → nhảy gate → rồi mới
  warp to location**.
- Một số mission tutorial/AIR dùng **Probe Scanner** (`Alt-P`) với site tên
  `Anomaly Training Site`, nhưng đây là ngoại lệ của career program, không phải
  luồng agent mission thường.[1]

## 3. Các bot miễn phí làm gì

**EVE-Master** (Boss nhắc, miễn phí, ~10.000 "Nodes"): không đoán beacon. Node
Store có các khối rõ ràng: `Warp to random Anomaly filtered by substring`,
`Bookmarks Sequence Dock / Warp`, `UI.Find Locations Window (bookmarks)`,
`Open Locations Window (bookmarks)`.[9] Mô tả của `Bookmarks Sequence Dock / Warp`:
*"Bot will do a right mouse click on each bookmark in this order and try to Dock
first, if the dock button doesn't exist it tries to Warp To. If neither exists
throws an error"*.[10] Nghĩa là **chọn đích theo TÊN đã cấu hình + đọc menu**, rồi
fail có lý do — không warp vào beacon đầu tiên.

**Sanderling / Viir / BotLab** (framework đọc UI tree, cùng họ với
`.hermes/research/viir/ParseUserInterface.elm`):
- Autopilot warp-to-0: lấy `InfoPanelRoute.RouteElementMarker`, right-click marker,
  rồi chọn entry menu chứa `dock|jump` theo **text**, không tin timer.[8]
- Warp theo bookmark: right-click `InfoPanelCurrentSystem.ListSurroundingsButton`
  → submenu → tìm entry khớp tên, rồi `dock` hoặc `warp.*within\s*0`.[7][13]
- Menu entry được khớp **nguyên văn**: *"Travel to asteroid belt: click menu
  entry to start warp"* → `menuEntryInLastMenuContainingTextIgnoringCase "Warp to
  Location Within 0 m"`; và bài học: *"the program was not designed to handle the
  disappearing menu"* → phải **chờ Overview window** trước khi click tiếp.[6]
- `ParseUserInterface.elm` của Viir định nghĩa `InfoPanelAgentMissions` /
  `MissionEntry` và `ContextMenu` / `ContextMenuEntry` — tức cộng đồng cũng mô
  hình hoá mission site như **panel + context menu**, không phải overview
  beacon.[file: .hermes/research/viir/ParseUserInterface.elm:241-249, 959-981]

**Kết luận chung:** cả EVE-Master lẫn Sanderling đều (a) chọn đích theo **tên/label
đã biết**, (b) thao tác qua **context menu / info panel** với text khớp rõ, (c)
fail-closed khi menu không có entry mong đợi. Không ai warp vào `Celestial
Beacon` bất kỳ.

## 4. Thiết kế sửa cho fila-bot (theo đúng bằng chứng trên)

1. **Dập ngay lỗi đang làm Boss bực:** `mission_beacons()` không được trả generic
   `Celestial Beacon`. Chỉ trả entry khi tên khớp **mission-site label đã ground**
   (từ objective/Job Board); không có → `[]` → bot KHÔNG warp mù.
2. **Tách 2 bước rõ ràng:**
   - `Set Destination` / `Add Waypoint` trên link `Location <sec> <system>` =
     **đi tới đúng hệ** (giữ lại, nhưng đổi tên/log cho đúng nghĩa).[3][5]
   - `Warp to Location` = **vào pocket**, chỉ gọi khi tàu đã ở đúng hệ và có
     bằng chứng menu `Agent Missions / Encounter (Deadspace) / Warp to
     Location`.[1][2][4]
3. **Thao tác menu theo cơ chế đã ground:** right-click `eye.empty_point()` → poll
   `eye.context_menus()` (menu 1-2s mới hiện) → tìm entry theo text đầy đủ →
   hover cha mở submenu (`act_submenu_select`, KHÔNG click cha) → click `Warp to
   Location`.[6][7] Menu không có entry → `BLOCKED` có lý do, không fallback warp
   beacon.[10]
4. **Xác minh tới nơi** bằng bằng chứng game (tên site/structure trong
   `SelectedItemWnd` hoặc overview gần), không tin timer — đúng nguyên tắc
   `ManeuverWarp`/`ManeuverJump` của Sanderling.[8]
5. **Cần 1 dump live** để chốt text menu chính xác của client TQ hiện tại (menu
   `Agent Missions` khi tàu đang ở đúng hệ, mission active). Hiện client đang
   dock nên chưa lấy được; không bịa text menu.

## 5. Việc đã làm / chưa làm

- Đã làm: báo cáo nghiên cứu 2 vòng độc lập (§1–§6); khoá blind-warp trong
  `mission.py::mission_beacons()` (thiếu `site_hint` → `[]`); ground nút
  `missionObjective_button_location_<id>` từ 4 dump TQ (§6.1); nối nút vào
  `live_security.py::apply()` nhánh `warp_to_mission` theo NHÃN đọc được;
  cập nhật skill `game-bot-ui-automation` §14 (v1.5.0).
- Verify: `tests/test_mission_travel_button.py` 15 PASS; full suite
  **38 files / 609 PASS / 0 FAIL**; `compileall` OK; live DRY 60 s trên client
  thật (`scratch/live_dry_after_fix.log`) chỉ `phase DOCKED / Mở đối thoại với
  Inikko Samanuni`, **0 lần `warp_beacon`**; probe read-only:
  `mission_beacons()` = `[]`, `mission_location_button()` = `None` (đang dock,
  không mission đang track → fail-closed đúng).
- Chưa làm (không giả vờ): chạy live luồng `Set Destination → gate → Warp to
  Location` tới đúng pocket. Nhãn `Warp to Location` vẫn **chưa có dump TQ**; cần
  tàu ở đúng hệ + 1 dump lúc nút đổi nhãn. Test xanh ≠ đã bay tới site.

## 6. Đối chiếu độc lập lần 2 (Boss nhắc "eve-master miễn phí đó")

Research lại từ đầu bằng web search + `curl` toàn văn, không dùng lại kết luận ở
§3. Kết quả **khớp** và bổ sung được bằng chứng cứng hơn:

**EVE-Master bản FREE là gì:** `eve-master.com/pricing` ghi rõ *"All nodes are
free. Exclude: Mouse (20 minutes limit), Keyboard (20 minutes limit)"* — tức bản
miễn phí bị giới hạn 20 phút input chuột/phím mỗi lần chạy, còn **toàn bộ node /
bot logic đọc UI tree là free**.[14] CLI chạy bằng `.bat` + PlayConfig, có
`CTRL+SHIFT+SPACE` để stop.[15] Đây đúng là cái Boss bảo "miễn phí đó".

**Cách nó chọn đích (đọc được toàn văn trang node):**
- Node `Warp To Anomaly at Range 20KM` (ID `d7c93f95…`): input `Substring`,
  `Index`; mô tả *"Filters anomalies by substring and warp to by index"*. Các node
  con bên trong (đọc được trong HTML): `Get UI Array of anomalies by Text`,
  `root.ui.tree.node.array.at.index`, `Click context menu item`,
  `root.ui.tree.get.data`, `root.mouse.click`.[16] → **lọc theo TÊN đã cấu hình +
  đọc UI tree + bấm entry context menu**, không phải "beacon đầu tiên".
- Node `Bookmarks Sequence Dock / Warp FIX` (ID `2e2c4333…`): *"Bot will do a
  right mouse click on each bookmark in this order and try to Dock first, if the
  dock button doesn't exist it tries to Warp To. If neither exists throws an
  error"*.[17] Node `Bookmark Click Context Menu Button by Name` (ID
  `5401a14a…`) có input `Button Name = "Dock", Warp to`.[18] → **đích là bookmark
  có tên**, thao tác qua menu, và **fail có lý do** thay vì fallback mù.
- Kiến trúc `bot.eve-master.com/bot-architecture-patterns`: vòng lặp Recycle
  Pattern *"logic parts will be executed again and again"*, mỗi vòng tự hỏi *"where
  is the bot now, in space or docked"* — không tin timer.[19]

**Bot mission khác (ISXEVE EVEBot Missioner):** *"To run combat missions, EVEBot
uses a preset list of commands that are executed once it warps to the **encounter
bookmark**"*; mission DB (`missiondatabase.xml`) key là *"the name of the mission
as it appears in your journal"*, lệnh `NextRoom` = *"fly to the nearest acceleration
gate and use it"*. → Đích = **encounter bookmark theo tên mission**, không phải
overview beacon.[20] (Trang 403 khi curl; lấy từ search index.)

**CCP / wiki xác nhận cơ chế 2 bước:** EVE University Wiki (Viridian) ghi mission
journal đã bị gỡ khỏi Neocom, luồng là *"Read the briefing, then warp to the
objective"*, phân loại `Encounter` / `Deadspace` rõ ràng.[21] Wiki Enforcer career
agent: *"Right click in space to warp to the mission location"* → *"Once you arrive
at the deadspace pocket"*, rồi acceleration gate.[22] Forum-archive 188979 ghi
nguyên chuỗi menu *"Agent Missions: [mission name] > Encounter (Deadspace) > Warp
to Location"*.[23] Forum `veldspar-asteroids` mô tả nút xanh góc trái đổi nhãn:
*"the text on the blue button should change either to 'warp to location' or 'set
destination'. If it's 'warp to location', just click it… If it's 'set destination',
click it and the autopilot will plot a route"*.[24]

### 6.1 Nút đó đã ground được trên chính client TQ của Boss

Không cần đoán text menu nữa. Dò lại các dump TQ đã lưu (`dumps/*.json`,
`tests/fixtures/*.json`):

| Dump | `_name` | Label `_name='label'` | Trạng thái |
|---|---|---|---|
| `dumps/g10_turnin_dialog.json` | `missionObjective_button_location_3016839` | `Undock` | đang dock |
| `tests/fixtures/ui_tree_e2e_06_live_cannot_complete.json` | `…_3010986` | `Undock` | đang dock |
| `tests/fixtures/ui_tree_e2e_05_security_cargo_delivery.json` | `…_3016839` | `Undock` | đang dock |
| `dumps/g11_docked_fresh.json` | `…_3016839` | `Set Destination` | cần đi tới đúng hệ |

Đây là **cùng một `StatefulButton`** trong mission tracker; nhãn đổi theo trạng
thái, đúng mô tả [24] và §2. Cùng dump còn có `selectedItemWarpTo` (label
`WarpTo`), `noDestinationLabel` = `No Destination`, `TrackJobButton` =
`Untrack`.[25] Nhãn `Warp to Location` (đã ở đúng hệ) **vẫn chưa có dump TQ** —
code chỉ bấm khi đọc được nhãn đó, không bịa.

### 6.2 Sửa tiếp so với §4

`Eye.mission_location_button()` đọc đúng node trên bằng `_name` prefix
`missionObjective_button_location_` + label con, trả `{center,label,name}`.
`LiveSecurityRunner.apply()` nhánh `warp_to_mission` ưu tiên nút này:
- `Warp to Location` → click (vào pocket),
- `Set Destination` → click (chỉ đặt route tới **hệ**), KHÔNG warp pocket,
- `Undock` → không warp, chờ lệnh undock riêng,
- không có nút → fallback right-click empty space tìm menu (vẫn fail-closed,
  **không** fallback `warp_beacon`).

`MissionEye.mission_beacons()` giờ yêu cầu `site_hint` (tên site đã ground),
thiếu → `[]`. Regression: `tests/test_mission_travel_button.py` (15 PASS).

**Chưa làm (không giả vờ):** vẫn chưa có 1 vòng live chạy tới đúng pocket trên
client thật. Cần tàu ở đúng hệ + 1 dump lúc nhãn nút là `Warp to Location`.

## Sources

[1] https://www.wckg.net/Newbie/career-agents
[2] https://evesimplified.blogspot.com/2013/03/starting-tutorial-missions-guide.html
[3] https://forums.eveonline.com/t/january-2020-release-known-issues/212009/9
[4] https://forums.eveonline.com/t/go-to-the-asteroid-belt-weve-entered/99026
[5] https://eve-search.com/thread/153895-1/page/1
[6] https://forum.botlab.org/t/how-to-automate-mining-asteroids-in-eve-online/628?page=4
[7] https://forum.botlab.org/t/please-i-need-help-with-coding-few-lines-of-code-useing-viires-version-of-sanderling/342
[8] https://elitepvpers.com/forum/eve-online/3892772-release-eve-online-botting-framework.html
[9] https://eve-master.com/nodestore
[10] https://eve-master.com/nodestore/b499e76d-adae-4e80-b00e-37361d14dbf5
[11] https://forums.eveonline.com/t/no-destination-given-where-to-go/386369
[12] https://forums.eveonline.com/t/minor-issue-with-missions-and-warping-to-location/216600
[13] https://forum.botlab.org/t/mission-mining-bot-or-how-to-edit-the-default-mining-bot-to-do-this/2437

[14] https://eve-master.com/pricing
[15] https://bot.eve-master.com/how-to-use-eve-master-cli
[16] https://eve-master.com/nodestore/d7c93f95-f50c-4877-a94d-c6cc93528d9e
[17] https://eve-master.com/nodestore/2e2c4333-09a4-41b3-90dc-f353e3874689
[18] https://eve-master.com/nodestore/5401a14a-f22e-45d2-8836-4155c1e849fd
[19] https://bot.eve-master.com/bot-architecture-patterns
[20] https://forge.isxgames.com/projects/isxeve/wiki/EVEBot_Missioner
[21] https://wiki.eveuniversity.org/Missions
[22] https://wiki.eveuniversity.org/Enforcer_(Career_Agent)
[23] https://forums-archive.eveonline.com/topic/188979
[24] https://forums.eveonline.com/t/veldspar-asteroids/256755/2
[25] dumps/g11_docked_fresh.json, dumps/g8_opportunities_open.json, dumps/g10_turnin_dialog.json (local TQ dumps)
