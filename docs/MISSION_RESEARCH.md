# MISSION RUNNING — cơ chế game (nghiên cứu 2026-11-09)

> **AUDIT WARNING — 2026-11-11:** This is a historical/community-derived draft (EVE UniWiki/BotLab), not a verified runtime mission database. Wave counts, trigger rules, damage tables, the 18-second clear timer, and the old Empire-decline policy must not authorize live combat. The current official SDE contradicts the old title heuristic: **Cargo Delivery is a `killMission` template with an item objective, not a pure courier template.** Use [`MISSION_RESEARCH_DEEP_2026-11-11.md`](MISSION_RESEARCH_DEEP_2026-11-11.md) for the audited facts, code gaps, and safe build plan.

Nguồn: EVE University Wiki (Missions, Security_missions, Agent, NPC_standings, Deadspace,
Acceleration_gate, Npc_damage, Career_Agents, The_Agency, Agent_Finder, + 4 mission report L1),
Sanderling `read-memory-64-bit/EveOnline64.cs` + `ParseUserInterface.elm`, BotLab forum.

Mục đích: trước khi viết bot phải hiểu **luật chơi**, vì mọi sai lầm ở đây đều là mất tàu thật.

---

## 1. Vòng đời một mission (bắt buộc đúng thứ tự)

```
DOCKED tại trạm agent
  → mở Agents panel → right-click agent → "Start Conversation"
  → AgentDialogueWindow: đọc offer → Accept / Decline / Delay
  → mission xuất hiện: InfoPanelAgentMissions (MissionEntry) + beacon trong space
  → undock
  → warp tới mission location (beacon; KHÔNG phải warp tự do)
  → [deadspace] clear pocket → acceleration gate → pocket 2 → ...
  → objective hoàn thành (icon mission chuyển green check; local chat báo "Objective complete")
  → về trạm agent → dock → Start Conversation → "Complete" → nhận ISK + LP
```

**Hệ quả cho bot:** 4 trạng thái phải phân biệt được bằng mắt: `có offer chưa accept`,
`đã accept – chưa tới site`, `đang trong site`, `objective xong – chưa trả`.
Không phân biệt được = bot kẹt vòng lặp hoặc bỏ mission.

---

## 2. Deadspace — luật warp (QUAN TRỌNG NHẤT, sai là mất tàu)

| Tình huống | Kết quả |
|---|---|
| Warp từ ngoài vào complex | Warp tới **acceleration gate** ở entry pocket (Pocket 0) |
| Warp trong cùng complex (pocket→pocket) | **KHÔNG warp được** — "natural phenomena are disrupting the ship" |
| Warp từ trong ra ngoài | Bình thường (đây là đường thoát duy nhất) |
| Sau khi mission xong | Complex despawn sau ~2 phút khi người cuối rời đi; gate + structure biến mất, **wreck vẫn ở lại** |

→ Bot **tuyệt đối không** thử warp giữa các pocket. Đi tiếp = warp tới gate rồi activate.
→ Thoát hiểm = warp ra ngoài (khác abyss: abyss không warp ra được).
→ Muốn loot sau khi trả mission: phải bookmark pocket từ trước (gate despawn → không vào lại được
bằng gate).

## 3. Acceleration gate

- Activate được khi cách **≤ 2.500 m** (vòng tròn xanh); một số gate cho tới 100 km.
- **Không activate được khi đang bị warp disrupt/scrAM.**
- Có thể bị khoá bởi: giết hết quái trong pocket / giết commander cụ thể / có item trong cargo
  (Keycard, Tag — có loại bị tiêu thụ khi dùng).
- Có **ship restriction**: cấm capsule, capital, có khi cấm BS/strategic cruiser. Sai loại tàu →
  popup thông báo, gate không mở.
- Biến thể: `Spatial Rift` (không có vòng xanh), gate hỏng = "Large Collideable Structure"
  (không dùng được).

→ Bot phải: (1) warp tới gate, (2) bay vào ≤2500 m, (3) activate, (4) **verify đã sang pocket mới**
(overview đổi hoàn toàn) trước khi coi là thành công. Nếu popup restriction → dừng, báo.

## 4. Trigger — bẫy chết người phổ biến nhất

Mission có **wave spawn theo trigger**, thường là "giết/bắn con X". Nếu bắn hết cùng lúc → ăn
nhiều wave một lúc → chết.

Ví dụ thật (L1):
- `Alluring Emanations (L1)`: bắn con Drone đầu tiên → **43 drone** reinforce ở 70 km, auto-aggro.
  (Giết chúng không bắt buộc để hoàn thành.)
- `Cargo Delivery (Angel Cartel L1)`: **lấy cargo** → wave 1 (6-8 frig) → giết 1 con → wave 2.
- `The Blockade (Serpentis L1)`: aggro ngay khi warp in; 4 wave theo thứ tự, wave 4 ở 15 km
  (gần nhất, xuất hiện cuối).
- `The Angel Cartel Spies (L1)`: **auto-aggro ngay khi warp in**, 8-9 frig, giết hết là xong.

→ Bot KHÔNG được có logic "overview trống = pocket xong" một cách ngây thơ. Phải có
**wait window** sau khi clear (mặc định 15-20 s, giống `anomaly-wait-time` của BotLab) để bắt
wave đến muộn, và biết mission nào có trigger đặc biệt.

## 5. Mission completion — nhận biết thế nào

Có 3 tín hiệu độc lập (dùng nhiều cái để chắc):
1. `InfoPanelAgentMissions` → `MissionEntry` icon đổi thành **green checkmark**.
2. Local chat: `Objective complete` / `Mission completed`.
3. Reward popup / mission entry biến mất khỏi panel sau khi trả.

→ Ưu tiên (1) vì đọc được từ UI tree; (2) chỉ để xác nhận.

## 6. Standings — quyết định agent nào dùng được

| Level | Standing cần (agent HOẶC corp HOẶC faction) |
|---|---|
| 1 | bất kỳ |
| 2 | 1.00 |
| 3 | 3.00 |
| 4 | 5.00 |
| 5 | 7.00 |

- Alpha clone: **tối đa L3**. L4/L5 cần Omega.
- Điều kiện phụ: agent + corp + faction đều phải > −2.00 (trừ L1).
- Cứ **16 mission cùng level + cùng faction** → 1 storyline offer (tăng standing mạnh).
- Giết ship của empire faction → mất standing faction đó ("Combat - Ship Kill").
  → Bot nên **decline mission đánh empire faction** nếu muốn giữ standing cân bằng.
- Decline quá nhiều → có decline timer (không nhận mission mới trong X phút).
  **Delay** thì không phá mission chain (khác Decline).

## 7. Damage type theo faction — cần chọn ammo

| Faction | Yếu với | Gây ra | EWAR |
|---|---|---|---|
| Angel Cartel | Explosive / Kinetic | Exp 62% / Kin 22% | Target Painter |
| Blood Raiders | EM / Thermal | EM 50% / Thr 48% | Neut + TD |
| Guristas | Kinetic / Thermal | Kin 79% / Thr 18% | ECM |
| Sansha's Nation | EM / Thermal | EM 53% / Thr 47% | TD |
| Serpentis | Kinetic / Thermal | Thr 55% / Kin 45% | Sensor Dampener |
| Rogue Drones | EM / Thermal | varies | — |
| Mordu's Legion | Kinetic / EM | Kin 70% / Thr 30% | — |

→ Bot cần map faction → ammo, và **đổi ammo trước khi warp vào** (không đổi giữa combat).
Với acc alpha + L1/L2 thì thường không cần tối ưu, nhưng L3 thì cần.

## 8. Loot / salvage

- Wreck tồn tại sau khi mission xong và sau khi complex despawn → loot được nếu có bookmark.
- **MTU** (Mobile Tractor Unit, 100 m³): thả trong pocket, tự kéo loot trong 125 km.
  Khi scoop lại, cargo dư bị đổ ra container tạm.
- Chiến lược chuẩn: thả MTU + bookmark mỗi pocket → trả mission → quay lại salvage sau.
- Giá trị loot tăng theo level; L1 salvage ~1.2-1.5M ISK (Alluring Emanations).

→ Bot giai đoạn 1: **bỏ loot** (đơn giản, an toàn). Giai đoạn 2: MTU + bookmark.

## 9. UI tree — node đã ground / chưa ground

Đã ground **trên client TQ thật (2026-11-09, Photon UI)**:

| Thành phần | Node | Ghi chú |
|---|---|---|
| Station window | `LobbyWnd` (name=`lobbyWnd`) | có `UndockButton` (name=`undockButton`, label "Undock") |
| Tab agent trong station | `Tab` name=`stationInformationTabAgents` | click để mở AgentsPanel |
| Agents panel | `AgentsPanel` (name=`agentsPanel`) | **rỗng ở Jita III-1** (trạm này không có agent) |
| Context menu | `ContextMenu` (name=`menuview`) → `MenuEntryView` (name=`context_menu_Xxx`) → `TextBody` | text đọc từ TextBody |
| Overview | `OverviewWindow` → `OverviewScrollEntry` → `OverviewLabel._text` | 23 entry |
| Selected item | `SelectedItemWnd` (name=`selecteditemview`) | **chỉ là selection, không phải lock** |
| HP / cap / speed | `ShipHudSpriteGauge._lastValue` / `pmark._color` (PyColor) / `speedLabel._setText` | đã decode |
| Location / route | `InfoPanelLocationInfo` → `EveLabelMedium` `alt= Current Station >`; `InfoPanelRoute` → `noDestinationLabel` / `AutopilotDestinationIcon` | security: `headerLabelSecStatus` |

**Chưa ground (cần client có agent + mission thật):**
- `AgentDialogueWindow` — nút Request/Accept/Decline/Delay/Complete, cách đọc tên mission + reward.
- `InfoPanelAgentMissions` → `MissionEntry` — text, icon trạng thái (green check), toạ độ.
- Beacon mission trong overview (`OverviewScrollEntry` cho deadspace beacon có tên riêng).
- Popup ship restriction của acceleration gate.
- `MissionEntry` khi objective complete (khác gì lúc đang làm).

## 10. Thiết kế bot end-to-end (không LLM)

### Kiến trúc

```
eye (đọc UI tree, read-only)  ──┐
                                ├→ world_state (phase + dữ kiện)  →  policy (FSM, no LLM)  → control (keybind/click đã verify)
win (client→screen offset)    ──┘                                        │
                                                                         └→ guards (fail-closed, dừng khi mù)
```

### FSM mission

```
BOOT
 └→ DOCKED
     ├─ có offer chưa accept  → AGENT_OFFER   → accept/decline (theo rule) → MISSION_ACTIVE
     ├─ MISSION_ACTIVE        → UNDOCK
     └─ objective xong        → AGENT_TURNIN → complete → DOCKED (tick +1)
 └→ IN_SPACE
     ├─ chưa tới site         → WARP_SITE (menu → Warp to Within → 0)
     ├─ đang ở pocket         → FIGHT (lock theo priority → bật module → orbit)
     │                           └─ clear + wait 15-20s → GATE (nếu còn gate)
     ├─ popup restriction     → STOP, báo
     └─ hp thấp               → WARP_OUT (về station)
 └→ UNKNOWN 45s → MAYDAY, dừng
```

### Rule không dùng LLM mà vẫn "khôn"

1. **Mission whitelist**: chỉ chạy mission có trong `missions.py` DB (tên → pocket count,
   trigger, faction, damage). Mission lạ → **Decline** hoặc Delay (an toàn).
2. **Trigger-aware fight**: bảng `trigger` per mission: `kill_first` / `loot_triggers` /
   `none`. Mặc định: kill theo priority (web → neut → scram → logi → DPS), không AoE.
3. **Wave wait**: sau khi overview sạch, chờ `wave_wait=18s` + đọc lại; có quái mới → fight tiếp.
4. **Clear definition**: không quái **classify được** là hostile trong overview VÀ đã qua wave_wait.
5. **Gate verify**: sau activate, phải thấy overview khác hoàn toàn (so hash tên entry).
   Không đổi → thử lại 1 lần → MAYDAY.
6. **Abort rule**: hp < 25% → warp out; cap < 15% + đang bị neut → warp out.
   (Trong mission được warp out, khác abyss.)
7. **Decline rule**: faction thuộc empire (Amarr/Caldari/Gallente/Minmatar/CONCORD) → decline
   để giữ standing, trừ khi cấu hình cho phép.
8. **Fail-closed**: bất kỳ node nào không đọc được → dừng, log, không bấm mù.

### Việc phải làm tiếp (theo thứ tự)

1. **Ground AgentDialogueWindow** — cần trạm có agent. Jita III-1 không có.
   → dùng Agent Finder / The Agency tìm trạm L1 agent gần nhất, dock, mở conversation, dump.
2. Ground `MissionEntry` + beacon overview khi đang có mission active.
3. Viết `missions.py` DB: tên → pocket count, trigger type, faction, damage, notes.
4. Nối FSM vào `mission_cli.py`, thêm `--mission-auto` chạy full loop.
5. Test trên dump thật từng bước; chỉ chạy live khi mỗi bước đã ground.

---

## 11. Khác biệt với bot abyss hiện có

| | Abyss (`reflex.py`) | Mission (`mission.py`) |
|---|---|---|
| Timer | 20 phút, hết = chết | Không có |
| Warp out | KHÔNG được | Được (đường thoát) |
| Vào site | filament (item) | warp tới beacon + gate |
| Nhiều pocket | Không (1 pocket/room, gate = tiến) | Có, gate bắt buộc |
| Trả thưởng | Không | Có: dock + agent + Complete |
| Chain | Filament liên tục | Mission → mission (infinite với agent thường) |
