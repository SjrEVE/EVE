# Hoàn thiện fila-bot: nghiên cứu đối chiếu nguồn và kế hoạch nghiệm thu

## Phạm vi và độ tin cậy

Đây là nghiên cứu thiết kế, không phải chứng nhận bot đã tự chạy trọn mission. Đối chiếu baseline local v1.4.1 và báo cáo `BRAIN_INTEGRATION_AUDIT.md`.

- GitHub: đọc code combat-anomaly hiện tại của Viir; file ghi version 2026-09-27. Đối chiếu thêm hướng dẫn một bot/phiên game, điều phối focus nhiều phiên, và parser target/module/drone.[16][22][23][24]
- EVE-Survival L1 và L2 cho thấy trigger khác nhau theo cấp. L1 ghi Fiend là trigger, L2 ghi Demon; không dùng một bảng chung cho mọi cấp.[8][21]
- YouTube: lấy được transcript tiếng Anh của hai video; chỉ đọc transcript, không tuyên bố đã quan sát mọi hình ảnh. Video mission có 1.135 đoạn; video hybrid Gila có 273 đoạn.[13][14]
- Reddit: JSON và browser đều bị chặn; chỉ dùng snippet tìm kiếm, không coi là đã đọc toàn bộ thread.[15]
- UniWiki có cảnh báo cần cập nhật vì thay đổi game. EVE-Survival Gone Berserk L2 ghi lần sửa năm 2015: dùng làm nguồn giả thuyết, xác nhận lại trên client trước khi bật tự động.[6][8]
- Tìm thêm RU/CN: lượt tìm chưa cho thấy nguồn mission-runner tốt hơn; không suy ra rằng chúng không tồn tại. Không dùng kết quả lạc đề làm bằng chứng.

Raw code, trang đã lấy, API metadata và transcript nằm local trong `.hermes/research/`. Không cài bot bên ngoài, không chạy binary tải về, không đổi policy nhận/từ chối mission.

## Đã sửa trong lượt này

- Thêm `runtime_lock.py`: khóa độc quyền theo client bằng `msvcrt.locking` trên Windows hoặc `flock` trên POSIX. PID không còn là căn cứ để kill process. Hai owner cùng client bị từ chối; process thoát thì OS nhả lock. Chưa thay toàn bộ call site `single_instance` nên đây là bước nền, chưa phải hoàn tất chống trùng.
- Tách tactics Gone Berserk theo `(title, level)`: L1 Fiend/Imp, L2 Demon/Succubus. Không có level đã đọc thì brain không áp playbook trigger. Chưa xác nhận mọi faction/pocket.[8][21]
- Ghi rõ 25 km là range chiến thuật, không phải maximum control range của game.[18]

Kiểm chứng: 85 file / 913 PASS / 0 FAIL. Đây vẫn chỉ là offline acceptance, chưa phải mission live.

## Còn thiếu thật sau nghiên cứu

- Chưa đổi toàn bộ runtime sang `runtime_lock`; chưa chứng minh hai tiến trình thật tranh cùng một client PID.
- Chưa nối level thật từ offer/mission panel vào world; `mission_level` hiện là contract test, không phải live observation.
- Chưa có object identity bền; chưa ground module assignment/reload/busy và drone idle/fighting/returning/damaged.
- Chưa thay fallback offensive input khi không đọc được target bar bằng cơ chế an toàn hoàn chỉnh.
- Chưa thêm pending-action timeout, stale snapshot, focus ownership và combat-progress watchdog xuyên suốt executor.
- Chưa có trace một mission từ nhận đến trả; chưa được phép gọi bot là hoàn chỉnh.

## Kết luận chính

**Không cần LLM trong tick. Cần một bộ điều khiển phản hồi có trạng thái quan sát được.** Đây là đề xuất kiến trúc từ đối chiếu code của mình và nguồn dưới đây, không phải quảng cáo của đối thủ.

Viir tách memory, decision path và observation; đọc trạng thái targeting/targeted, maneuver, module và drone idle trước khi quyết định. Nó cũng có các default đơn giản mà ta không nên sao chép: trạng thái không biết đôi chỗ bị coi như false.[16]

EVE-Master có node riêng cho weapon assigned to active target và drone fighting active locked target. Nghĩa là catalog của họ phân biệt **đã gửi F1/F** với **vũ khí/drone đang đánh đúng mục tiêu**. Chưa biết chính xác UI query/graph của các node này.[1][2][3]

## Hai giả định sai phải rút lại

### Gone Berserk L2

Báo cáo L2 ghi initial Succubus, wave có Succubus + Demon; Demon là trigger, sau đó thêm chain và cuối có Priest. Không khớp bảng hiện tại của ta ghi Fiend/Imp và hai wave.[8]

**Verdict: REJECT bảng tactics hiện tại như một nguồn game chính xác.** Test Fiend/Imp chỉ chứng minh thuật toán sắp thứ tự theo bảng đã nhập, không chứng minh bảng đúng. Không sửa bằng cách thay một token rồi tuyên bố hỗ trợ mọi level. Cần key `(mission template, level, faction, pocket, revision)`; trường chưa đọc được phải hiện UNKNOWN. Với báo cáo cũ, lấy dump mission thực để đối chiếu trước khi bật trigger automation.

### Drone leash 25 km

UniWiki mô tả control range mặc định 20 km, tăng theo Drone Avionics và Advanced Drone Avionics; có thể đạt 60 km bằng hai skill level V, và tăng thêm bằng module/rig. Khoảng cách dùng để ra lệnh tính từ tàu tới target.[18]

**Verdict: REJECT 25 km như giới hạn cơ chế chung.** Giữ nó chỉ như policy/fit hiện có cho đến khi đo fit thật. Tách `weapon_effective_range`, `locking_range`, `drone_control_range`, `preferred_engagement_range`, `drone_recovery_distance`. Không tự nới range chỉ vì đọc wiki.

## So sánh nguồn đáng học

| Nguồn | License/quyền truy cập | Điểm đáng học | Không nên lấy nguyên | Verdict |
|---|---|---|---|---|
| Viir/bots | MIT theo GitHub API; pushed 2026-09-27 | Reactive decision path, observed targeting, module/tooltip memory, idle drone handling | Elm stack; anomaly selection; default UNKNOWN→false; không có chứng cứ mission E2E trong file đã đọc | ADOPT pattern, không thay toàn bộ repo [10][16] |
| Arcitectus/Sanderling | Apache-2.0 theo API; pushed 2026-09-27 | Đối chiếu parser/reader khi mắt thiếu field | Không mặc định memory layout hợp client hiện tại; không tin tuyên bố undetectable | TRIAL từng parser trên dump thật [11] |
| darkmatter2222/EVE-Online-Bot | MIT theo API; pushed 2026-09-13 | Đầu mối Python để khảo sát thêm | Chưa đọc implementation trong đợt này; không lấy nhãn AI làm chứng cứ năng lực | HOLD, chưa đủ code-level evidence [12] |
| EVE-Master | Metadata/docs công khai; quyền tái sử dụng payload chưa xác minh | Recycle pattern, kiểm module/target/drone riêng biệt | Graph chưa được đọc; không sao chép node Pro/binary hoặc xem download count như success rate | ADOPT contract; TRIAL query [1][2][3][17] |

`pushed_at` phản ánh repo, không chứng minh từng bot con đã được chạy trên client mới.

## Gap backlog của fila-bot — thứ tự thực hiện

Đây là thiết kế đề xuất. Các field dưới đây là **contract mới cần làm**, không phải field đã đọc được.

| Ưu tiên | Gap trong code hiện tại | Cách hoàn thiện | Gate đo được |
|---|---|---|---|
| P0 | `single_instance.py` dùng PID file tương đối, check/write không atomic và kill PID không xác thực | OS-backed exclusive lock; refuse run thứ hai; PID chỉ để chẩn đoán | Hai process tranh lock: chỉ một vào executor; stale PID không giết process khác; crash nhả ownership |
| P0 | `security_brain.decide` là planner cũ, chứa action không cùng contract executor và speculative flags | Chỉ một production decision path; đánh dấu/deprecate planner cũ, không nối action của nó vào live | Mọi action production có handler và có test qua refresh→tick→apply(dry) |
| P0 | Mission tactics key theo title | Versioned playbook theo level/faction/pocket; giữ nguồn và confidence | Gone Berserk L2 không dùng tactics L1/L4; unknown level không chọn nhầm playbook |
| P0 | Target identity dựa tên, NPC cùng tên dễ lẫn | Ưu tiên object ID đã ground; nếu không có thì identity tạm theo observation và không giả bền qua reorder | Hai NPC cùng tên + sort đổi không đổi nhầm mục tiêu; không dùng tọa độ frame cũ |
| P0 | Missing/empty dễ bị lẫn; chưa có freshness contract xuyên suốt | Observation(value, observed, captured_at, source); khóa input khi stale/transition | Replay missing panel không thành cleared; tọa độ quá hạn không được click |
| P0 | Lock fallback vẫn cho gửi offensive input khi bar không đọc được | Bổ sung targeting/targeted/active-target evidence từ overview/bar; pending action có timeout | Lock sent≠locked; wrong target không fire; timeout có reason và không retry vô hạn |
| P1 | Module UNKNOWN còn re-arm theo timer | Module OFF/ON/RELOADING/BUSY/UNKNOWN; gắn active target assignment; đọc ammo/tooltip nếu có evidence | ON không toggle; reload không bị toggle; mất readback không giả thành OFF |
| P1 | Drone chỉ có count, chưa biết đang idle/fighting/returning hoặc bị thương | Per-drone observation + passive/focus-fire preflight; selected target assignment | Launch→count tăng; engage→fighting đúng target; recall→count về; damaged drone không tiếp tục thả mù |
| P1 | Một engagement range dùng cho nhiều hệ thống | Fit capability profile theo hull/modules/ammo/skill đã đo | Sai range chỉ approach/wait; policy range không bị ghi nhầm thành game maximum |
| P1 | Survival chỉ nhìn ngưỡng, chưa đủ ngữ cảnh | Giữ threshold owner; thêm HP trend, scram/neut/cap và khả năng warp, ưu tiên cleanup có deadline | Scrammed không lặp warp vô hạn; nguy cấp không chờ drone mãi; không tự tắt hardener theo cap đơn độc |
| P1 | Gate/mission completion chưa có chứng cứ toàn vòng | Pocket state + observed objective + delayed wave; gate rejection có retry budget | Gate locked không spam modal; clear không suy từ một frame rỗng; turn-in chỉ tăng counter sau readback |
| P1 | Thiếu tiến trình chiến đấu | Watchdog theo target HP, số rat, range, movement, objective; deadline theo action | Đứng im không damage/range progress → reason cụ thể + recovery giới hạn, không chạy mãi |
| P2 | Test xanh chưa có trace thực | Recorded trace replay + supervised live qualification | Một mission level/template thực: accept→travel→objective→dock→turn-in, không sửa state tay giữa vòng |

### Học gì từ video và Reddit?

Video mission, khoảng 18:43–20:26, người chơi điều chỉnh khoảng cách/orbit, quan sát wave và nói đang tìm trigger, theo dõi drones. Đây là ví dụ phải đánh giá lại tình huống, không phải bằng chứng mọi Gila nên orbit 100 km.[13]

Video hybrid Gila, khoảng 05:50–05:58, transcript ghi recall vì drone đang ăn damage rồi mất cả flight. Bài học: count-only chỉ phát hiện sau mất drone, không đủ bảo vệ; cần damage/returning observation. Đây là một tình huống trong video, không phải thống kê tỷ lệ thua.[14]

Snippet Reddit khuyên recall khi drone bị aggro rồi chờ red-box trước khi launch lại. Chỉ coi đây là kinh nghiệm người chơi để thiết kế thử nghiệm, không encode thành luật tuyệt đối do chưa đọc được full thread.[15]

## Kiến trúc đề nghị — không viết lại tất cả

```text
Client observation + timestamp + validity
    ↓
World reconciliation (UNKNOWN khác observed-empty)
    ↓
Reactive priority selector
  connection/input ownership → survival → pending-action verification
  → fit preparation → navigation/objective → combat → return/turn-in
    ↓
One bounded intent: precondition + target identity + expected postcondition
    ↓
Executor (only supported actions, fresh coordinates)
    ↓
Next observation verifies success / progress / bounded failure
```

Giữ FSM làm lifecycle. Tách target ranking, module policy, drone policy thành hàm pure. Pending action giữ **đã yêu cầu**, không giữ **đã thành công**. Planner không trực tiếp sửa cache để giả bằng chứng. Mỗi tick có decision reason và field thiếu; không xây thêm một FSM thứ hai cạnh FSM hiện tại.

**ADOPT:** observation contract, pending-action verification, target identity, module/drone state, replay production glue.

**TRIAL:** tái dùng parser Sanderling/Viir theo license, đối chiếu source REA và dump hiện tại; không cài cả framework để né việc ground.

**REJECT:** LLM trong tick; rewrite toàn repo; tactics theo title đơn độc; hard-code range như luật game; coi gửi input là success; thêm random delay để quảng cáo undetectable.

## Trình tự nghiệm thu thực tế

1. Khóa ownership runtime và contract action trước; chưa combat.
2. Ground mắt còn thiếu: lock/active target, module reload/busy, drone state/HP. Dump có/không có evidence thành cặp regression.
3. Chạy một primitive ở điểm an toàn: đúng target, một action, postcondition thật, timeout rõ. Không suy speed tăng = đã orbit đúng.
4. Một mission level/template đã có playbook; chạy có giám sát từ dock tới dock rồi turn-in. Cấm sửa session để biến run đỏ thành xanh.
5. Replay failure: duplicate NPC name, stale root, lost focus, delayed lock, unknown module, drone returning, gate locked, objective chưa xong.
6. Chỉ mở unattended khi có nhiều trace độc lập, không cần agent chữa giữa vòng. Số run và ngưỡng tin cậy phải chốt trước, không chọn sau khi xem kết quả.

## Rủi ro tài khoản

Kết quả tìm kiếm trang chính thức CCP nêu botting bị cấm và có nguy cơ khóa tài khoản; trang trực tiếp chưa lấy được ở lần này. Không có cơ sở cho lời hứa “memory-read nên không bị phát hiện”. Nghiên cứu này không đề nghị né phát hiện hay che giấu automation.[19][20]

## Kết luận

Đề nghị: hoàn thiện **feedback controller**, không tiếp tục tăng bảng mẹo. Làm P0 theo từng lát end-to-end, rồi chứng nhận một mission thực; không mở thêm mode kiếm tiền trong lúc combat loop hiện tại chưa được nghiệm thu.

## Sources

[1] https://eve-master.com/nodestore/adc2dcb7-0f77-45fe-ab50-64b13006a7bb — master-fire
[2] https://eve-master.com/nodestore/53e2f7d4-094b-4bfc-b298-a1d0c0b384f2 — master-weapons
[3] https://eve-master.com/nodestore/43163514-465e-46ac-9cb6-52dec440fffb — master-drones
[6] https://wiki.eveuniversity.org/Drone_mechanics — drone-mechanics
[8] https://eve-survival.org/wikka.php?wakka=GoneBerserk2 — eve-survival
[10] https://api.github.com/repos/Viir/bots — repo-Viir
[11] https://api.github.com/repos/Arcitectus/Sanderling — repo-Arcitectus
[12] https://api.github.com/repos/darkmatter2222/EVE-Online-Bot — repo-darkmatter2222
[13] https://www.youtube.com/watch?v=-xJSKlvcako
[14] https://www.youtube.com/watch?v=rmAZwyS_Y3k
[15] https://www.reddit.com/r/Eve/comments/1lwtat3/help_drones_keep_getting_targeted
[16] https://raw.githubusercontent.com/Viir/bots/main/implement/applications/eve-online/eve-online-combat-anomaly-bot/Bot.elm
[17] https://bot.eve-master.com/bot-architecture-patterns
[18] https://wiki.eveuniversity.org/Drones
[19] https://support.eveonline.com/hc/en-us/articles/7370802950172-Botting
[20] https://support.eveonline.com/hc/en-us/articles/8564030965660-Third-Party-Policies
[21] https://eve-survival.org/wikka.php?wakka=GoneBerserk1
[22] https://raw.githubusercontent.com/Viir/bots/main/guide/running-bots-on-multiple-game-clients.md
[23] https://raw.githubusercontent.com/Viir/bots/main/guide/input-focus-scheduling-for-multiple-bot-instances.md
[24] https://raw.githubusercontent.com/Viir/bots/main/implement/applications/eve-online/eve-online-combat-anomaly-bot/EveOnline/ParseUserInterface.elm
