# CHECKLIST MẮT-MŨI-TAY-CHÂN-MIỆNG-SÚNG — fila-bot vs EVE (chốt 00:3x 13-11)

> Mỗi dòng = 1 giác quan, đánh dấu trạng thái ĐO ĐƯỢC lúc 00:3x 13-11 bằng probe read-only
> thật (không input) trên client `EVE - Kompi Yaken`. Chữ ✓ = đọc được số thật; ✗ = còn
> UNKNOWN/None; ⚠ = đọc được nhưng sai/không verify. File này là **bản đồ P0** trong
> `ISK_RESEARCH_AND_RECOMMEND_2026-11-12.md` — mũi giáp với thang luyện control P0–P6.

## 1. MẮT — NHÌN (perception)

| # | Giác quan | Đọc cái gì | Trạng thái 00:3x | Ghi chú / evidence |
|---|---|---|---|---|
| 1.1 | Mắt vị trí | Hệ sao, dock/space, trạm | ✓ IN_SPACE, hệ biết | `location_known=True` |
| 1.2 | Mắt tàu | Tên hull, panel tàu | ✗ active_ship=None, panel=False | B không biết mình bay tàu gì (run cũ: qua FittingWindow) |
| 1.3 | Mắt HUD | HP shield/armor/struct | ✓ 0.98/1.0/1.0 | |
| 1.4 | Mắt tốc độ | speed m/s | ⚠ 0.0 (nghi sai — tàu có thể đang đứng thật nhưng chưa cross-check) | P0: cross-check với HUD Overview |
| 1.5 | Mắt maneuver | orbit/approach/warp/stop | ✗ None | cần `maneuverType` (reader whitelist thiếu) |
| 1.6 | Mắt module | 14 nút module, on/off | ⚠ thấy nút, ✗ không biết bật/tắt (`module_activity_known=False`) | HUD chỉ xuất ramp_active lúc animation |
| 1.7 | Mắt drone | drone bay / trong bay | ✓ 2 / 8 | |
| 1.8 | Mắt overview | quái/gate/trạm trên overview | ⚠ (đã ground G6, nhưng không nằm trong probe này) | |
| 1.9 | Mắt target | selected/locked target | ⚠ SelectedItem có; **ActiveTarget chưa đọc được** | run22: lock 4 lần, không thấy |
| 1.10 | Mắt bracket tọa độ | vị trí thực trên màn hình | ✗ helper tự bịa (40,8) — REA: geometry ở TriStepRenderObject native | B02 |
| 1.11 | Mắt agent | agent panel, nhân vật đứng trạm nào | ✗ agents_known=False | |
| 1.12 | Mắt mission | mission active | ✓ "The Blockade" | |
| 1.13 | Mắt route | waypoints | ✓ 0 marker (hợp lệ) | |
| 1.14 | Mắt dialog | agent dialog mở/đóng, nút | ✓ open=False | |
| 1.15 | Mắt kho | inventory mở/closed | ✓ False | |
| 1.16 | Mắt cargo | cargo_free, hàng trong hold | ⚠ (G4 ground nhưng probe này không đo) | |
| 1.17 | Mắt chết còn lại | connection lost / popup lạ | ✓ False + guards 9 cái chết | |
| 1.18 | Mắt cap | capacitor % | ✗ **không có trong snapshot** | P0 mới — SURVIVAL cần |

## 2. MŨI — NGỬI (an toàn ngầm, đánh giá trước khi hành động)

| # | Giác quan | Làm gì | Trạng thái |
|---|---|---|---|
| 2.1 | Ngủi nguy hiểm | 9 guards (overview-empty, loop, drones-out, cloud, cap, damping, greed, wrong-filament, drift) chạy mỗi tick trước FSM | ✓ có (`guards.py`) |
| 2.2 | Ngủi người | state đổi bất thường khi bot không gửi lệnh → NGỪNG BẤM, hỏi Boss | ✓ có, đã proven run4 (INPUT_NOT_OWNED) |
| 2.3 | Ngủi mission lạ | mission từ agent khác profile → FOREIGN_MISSION block | ✓ có (run19) |
| 2.4 | Ngủi sec route | route không chắc hisec → fail-closed | ✓ có (`route_hisec_value`) |
| 2.5 | Ngủi protected | Empire Navy/CONCORD không bao giờ là hostile | ✓ có (run2/3 fix Navy structure) |
| 2.6 | Ngủi preflight | sai PID/window/client hash → không Start | ✓ code có; **đang exit 3 vì client patch 18:05 chưa re-pin** |
| 2.7 | Ngủi filamen | vào khi ≥1000km từ station/gate, không deadspace | ⚠ rule ghi trong protocol, chưa live-prove |

## 3. TAY — BẤM (actuation: 27 action specs đã có)

| # | Tay | Action | Trạng thái |
|---|---|---|---|
| 3.1 |_approach / orbit / keep_range | ✓ specs + proven live run9/10 |
| 3.2 | lock target | ⚠ specs có, **read-back ActiveTarget chưa chứng minh** (run22) |
| 3.3 | module on/off, overheat, reload | ✓ specs; module state UNKNOWN → bật/tắt mù |
| 3.4 | gate_jump, dock, undock | ✓ proven live run2/3/8/12 |
| 3.5 | warp_to, warp_route | ✓ proven live run3 |
| 3.6 | launch/engage/return drones | ✓ specs (keybind ground); drone FSM có (hp/leash/redbox) |
| 3.7 | context menu + submenu + dismiss | ✓ ground G6 |
| 3.8 | hotkey dock/jump (giữ D+click) | ✓ có |
| 3.9 | drag item (cargo) | ✓ proven G4/live distribution |
| 3.10 | confirm dialog | ✓ proven run3 (gate confirm bằng mắt) |
| 3.11 | stop / E-STOP nhả phím | ✓ có, hotkey Ctrl+Shift+Space |
| 3.12 | humanize (bezier, jitter, hover-settle) | ✓ có (`--no-humanize`) |

## 4. CHÂN — ĐI (navigation)

| # | Chân | Chuyện gì | Trạng thái |
|---|---|---|---|
| 4.1 | Đi trong hệ | warp tới beacon/gate/site đã ground | ✓ proven run3 |
| 4.2 | Đi giữa hệ | jump gate theo route | ⚠ specs có; HOME_NOT_IN_SYSTEM (run16/17) cho thấy chưa tự bay về hệ nhà |
| 4.3 | Đi vào pocket | activate Acceleration Gate đúng tầm | ✓ proven run8 |
| 4.4 | Về nhà đúng trạm | dock đúng agent station | ⚠ warp_home chọn đúng 1 entry khớp — chưa chứng minh cross-system |
| 4.5 | Đi courier | pickup → dropoff → dock | ⚠ code có, chưa 1 vòng live hoàn chỉnh |
| 4.6 | Đi abyss | undock → filamen → 3 room → dock | ✗ chưa ground (abyss.py:152 fail-closed) |

## 5. MIỆNG — NÓI (telemetry: Boss nghe thấy gì)

| # | Miệng | Kênh | Trạng thái |
|---|---|---|---|
| 5.1 | Nhắn cho Boss | `logs/live_latest.log` + `XEM_LOG.bat` xem thời gian thực | ✓ mới làm (v1.4.0) |
| 5.2 | Sự kiện có cấu trúc | `bus/bot_to_fc.jsonl` STATE/ROOM_CLEARED/GUARD/MAYDAY/SAFE_EXIT | ✓ chạy (seq 26–28 hôm nay) |
| 5.3 | Sổ runs | `runs/YYYY-MM-DD.jsonl` session_start/crash/session_end | ✓ có (crash TypeError đã ghi 20:39) |
| 5.4 | Báo blocker có lý do | BLOCKED kèm lý do cụ thể, không im lặng | ✓ proven (26 run đều nói vì sao dừng) |
| 5.5 | Version | `--version`, banner, UI title | ✓ v1.4.0 |
| 5.6 | Evidence lưu bền | `.hermes/evidence/` + `D:/EVE-REA/` | ✓ |
| 5.7 | Tiếng nói quyết định | hỏi Boss qua `clarify` khi policy, không tự thêm biên độ | ✓ có |

## 6. SÚNG — BẮN (combat)

| # | Súng | Chiều nào | Trạng thái |
|---|---|---|---|
| 6.1 | Nòng | weapons F1-F8 specs + module map theo fit profile | ⚠ specs có; activation chỉ "1 lần/mission" vì không đọc được state — bật mù |
| 6.2 | Đạn | đúng ammo theo weather/faction (rooms.py) | ✓ bảng có; reload spec có; chưa live-prove |
| 6.3 | Ống ngắm | lock-order rats.py (webbers trước, trigger sau) | ⚠ bảng có; **chưa wire evsurv kill-order vào tick** |
| 6.4 | Tether | drone FSM max/leash/hp/redbox/yellowbox | ✓ code; đọc drone count ✓; recall proven chưa |
| 6.5 | Tank | shield/armor booster logic, cap booster khi neut | ⚠ specs có; cap UNKNOWN → không biết khi nào pulse |
| 6.6 | SURVIVAL | hp < 25% → survival; abyss no-escape → đánh tiếp không warp-out | ⚠ rule có; cap missing làm SURVIVAL mù một nửa |
| 6.7 | Phân loại quái | rats.classify + protected/unknown không bắn | ✓ proven run2/3/13 |
| 6.8 | T4-T6 tactics | HIGH_THREAT_DPS, resist-hole, split-fire, bait, hazard | ✓ code + 54 test; **chưa live-prove** |

## 7. ĐIỂM CHẾT — MŨI TAY CHÂN SÚNG ĐỀU LỆN NHƯNG MẮT THIẾU (chốt) — CẬP NHẬT SAU P0

Ba mắt thiếu làm mọi thứ phía sau mù theo:

1. **Cap không đọc** → **ĐÃ MỞ (P0, 13-11)**: `capacitor_percent` wired vào snapshot + `status`.
2. **Module state không đọc** → **MỞ ĐÚNG NGHĨA (P0)**: `is_active=None`=UNKNOWN, code không
   bịa False; hành vi "1 lần/mission" + postcondition giữ nguyên (đúng thiết kế).
3. **ActiveTarget không đọc** → **MỞ MỘT NỬA**: fallback `targetHealthBars` từ source client
   (`targetInBar.py:841`); cần 1 dump live-locked (P1) để fixture non-empty.

2 mắt còn lại: `maneuverType` **không tồn tại trong UI tree** (0/12.948 file corpus — nó là
godma state); đường đúng = `indication_text` HUD + speed trend (P1, cần dump đang bay).
Bracket geometry giữ nguyên kế hoạch REA (native TriStepRenderObject — P5 nếu cần).

**P0 = DONE 00:4x 13-11.** Chi tiết: `P0_GROUNDING_REPORT_2026-11-13.md`.
Suite: 81 file / 876 PASS / 0 FAIL. P1 mở khi preflight ok:true.

---

*Cập nhật file này sau mỗi lần ground 1 mắt mới; ô ✗ về 0 thì P0 đóng, P1 mở.*
