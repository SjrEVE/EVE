# CÁCH KIẾM ISK TRONG EVE — RESEARCH TỔNG HỢP & RECOMMEND CHO FILA-BOT
# (2026-11-12, 23:3x–23:5x +07 — dùng đúng nguồn đã tải, không bịa số)

> Nguồn thật đã đọc lượt này:
> - EVE Uni Wiki: `Making_Money`, `Distribution_missions`, `Security_missions`, `Loyalty_Points`
>   (curl/browser, files: scratch/iskresearch/wiki_*.txt, sec.html, lp.html)
> - EVE-Survival: Mission Index → CategoryLevel1 (134 báo cáo) + 2 mission bot đã gặp
>   (`GoneBerserk1`, `EliminatethePirateCampers1`)
> - YouTube: transcript ĐẦY ĐỦ (yt-dlp, không phải đoán): "Most Players Skip This Easy ISK
>   Farm | Level 1 Missions" (Lynne Rankin, 33K views) và "Your First 1 Billion ISK Starts
>   Here | Level 4 Missions" (Lynne Rankin, 69K views)
> - Capability thật của fila-bot: 866 PASS, run1–26 live 11-12 (PROGRESS.md)

## 1. BẢN ĐỒ KIẾM ISK (từ EVE Uni "Making Money" — cập nhật 2026)

| Cách | Nhóm | Skill/Capital | Rủi ro | Bot làm được? |
|---|---|---|---|---|
| Missions (PVE từ NPC agent) | Combat | Thấp→Trung | Thấp (hisec) | **Có — 3 mode đã code** |
| Exploration (relic/data) | Scan | Thấp | Trung (lowsec tốt hơn) | Chưa (chưa ground scan UI) |
| Mining | Thu hoạch | Thấp | Thấp hisec | Chưa (chưa code mode) |
| Industry | Sản xuất | Trung | Thấp | Không phù hợp bot click |
| Planetary Industry | Passive | Thấp | Thấp | Không (về lâu dài có thể) |
| Trade | Market | Trung | Thấp | Không (market UI chưa ground) |
| Hauling | Vận chuyển | Thấp | Trung | Một phần (distribution mode) |
| Abyssal Deadspace | Combat | Trung | Cao (no-escape) | Code xong FSM nhưng **chưa ground live** |
| Incursions | Group PVE | Cao | Trung | Không (cần fleet) |
| Ratting nullsec | Combat | Cao | Cao | Không (rủi ro PvP) |

Kết luận wiki nguyên văn: *"Level 1–2 missions, career agents, distribution missions... provide
early ISK... but they are low ISK making activities. So you should move on from these once you
have the skills and experience."* → **Mission là đường khởi đầu chuẩn, nhưng mục tiêu tiền thật
là L3/L4 + blitz + LP store.**

## 2. CON SỐ THẬT TỪ VIDEO LYNNE RANKIN (transcript, không phải nghe đồn)

- **Mission trả 4 thứ**: ISK reward + bounty (kill) + loot + **Loyalty Points**. LP là phần
  bot hay bỏ qua — nhưng video chỉ rõ: LP → flip T1 ammo thành faction ammo → bán buy order
  = dòng tiền ổn định (vd 5.000 antimatter small → Caldari Navy antimatter).
- **Sec-status nhân thu nhập**: agent ở hệ 0.5 → **+50% ISK reward, +45% LP** so với 1.0
  (mỗi 0.1 giảm = +10% ISK). Alpha skill (Negotiation II, Security Connections II) cộng thêm
  ≈ +60% ISK / +65% LP tổng ở hệ 0.5.
- **L1 full-run** (video 1): Corax 3M ISK fit, mission The Blockade ≈ **130K ISK + 94 LP** một
  mission, kèm loot/salvage. Rõ ràng L1 là đào luyện standing, không phải máy in tiền.
- **L4 blitz** (video 2): target **100–200M ISK/h** blitz thường, **300–400M ISK/h** khi trộn
  Burner missions — nhưng cần battleship alpha-friendly, standings cao, và blitz = bỏ bounty/
  loot, chỉ giây trigger + turn-in nhanh.
- **Gank risk thật**: CONCORD = *"force of retribution, not protection"*. Hệ 0.8 → response
  6–9 s; hệ 0.5 → 19 s. Cách chống: local chat + ganker list red, d-scan (0.1 AU = đã trong
  pocket, warp out), bay tàu rẻ không bling.
- **Trigger discipline**: mỗi mission có NPC trigger (Plunderer/Wrecker/Infiltrator...) — bấm
  nhậy như bot từng bấm = nhận thêm wave. Video nói rõ: *dùng EVE Wiki/EVE-Survival tra
  mission TRƯỚC khi bay*.
- **Decline 1/4h/agent**: mission đi lowsec hoặc bắn empire → decline (không mất standing) →
  "agent juggling": nhiều agent cùng trạm để không chết thời gian chờ.

## 3. EVE-SURVIVAL = ĐÚNG DỮ LIỆU BOT CẦN (134 mission L1 có sẵn, format máy đọc được)

Report `Gone Berserk L1` (nguyên văn rút gọn):
- Faction EoM, deadspace có gate, damage Kinetic/Thermal, frigate
- 3 group (30/20/50 km, auto-aggro), mỗi group 2x Imp + 1x **Fiend = Trigger** → Wave 1 (3x
  Fiend) → Wave 2 (2x Incubus)
- **Blitz**: giết Group 3 Fiend → Wave 1 → Wave 2 rồi về.

Report `Eliminate the Pirate Campers L1`: Sansha, single pocket, all-aggro, 5x Centii Servant
+ 1x Centii Minion — đúng mission trong ledger của bot (lock Centii Servant ở run22!).

→ Đây chính là bảng **"giết gì trước, gì là trigger, avoid gì"** mà bot hiện đang thiếu
(missions_db chỉ có faction/protected list).

## 4. BOT ĐANG Ở ĐÂU SO VỚI 3 CÁCH KHUYẾN NGHỊ

| Khả năng bot (bằng chứng) | Distribution (courier) | Security L1 combat | Abyss |
|---|---|---|---|
| Accept/turn-in qua agent dialog | có | **proven run12** | — |
| Undock/warp/set destination | có | proven run3, run8 | chưa ground |
| Load/unload cargo | có (drag topCont) | n/a | — |
| Gate activation | n/a | proven run8 | chưa ground |
| Clear pocket (lock/fire/drone) | n/a | proven run9/10 (4 Pithi) | BT sim |
| Về đúng nhà + repeat | **đang hở B1/B2/B3** | đang hở | — |

## 5. RECOMMEND — CÁCH LÀM ĐƯỢC NGAY VÀ DỄ NHẤT

### 🥇 Khuyến nghị số 1: **Distribution courier L1 hisec** (chọn agent cùng hệ/trạm, sec 0.8–0.9)
Vì sao dễ nhất cho bot:
1. **Không bắn** → không cần target/lock/fire/drone read-back (đúng chỗ đang hở B3/run22).
2. Không trigger discipline — không sợ spawn thêm wave như combat.
3. Chuỗi hành động ngắn: accept → load → set destination → jump/dock → unload → complete —
   **tất cả đã có code + đa số đã proven live** (distribution mode + G1–G11 dumps).
4. Không gank-value cao (hàng courier L1 rẻ) — chấp nhận rủi ro gank thấp.
5. Thu nhập khiêm tốn (~vài triệu ISK/h với L1) nhưng **chứng minh được vòng loop tự động
   hoàn chỉnh trước** — chính là DoD đang kẹt.

Công việc còn thiếu (đo được): đóng B1 (home-not-in-system), B2 (Complete đúng lúc), retry
bounded cho load cargo; thêm **sec-status bonus vào accept_rule** (chọn offer cùng hệ/trạm
0.8+ để ăn thêm % reward); sau đó 3 mission liên tiếp = chứng nhận.

### 🥈 Số 2: Security L1 combat (làm tiếp đường đã proven)
Chuỗi accept→undock→warp→gate→clear→dock đã chạy từng bước thật hôm nay; thiếu đúng 3 mắt
xích: về đúng hệ nhà (B1), turn-in đúng lúc objective-complete (B2), lock read-back (B3).
Thêm **EVE-Survival data** (trigger/avoid/blitz) vào `missions_db` để không bấm nhậy NPC
trigger. L1 cho standing → mở L2/L3 rồi tới mục tiêu L4 blitz của video 2.

### 🥉 Số 3: LP flip (bổ trợ, không phải mode mới)
Sau mỗi mission, bot **đọc LP trong dialog** (đã đọc được offer/complete evidence) và ghi vào
session ledger; việc đổi LP → faction ammo làm sau, ngườiBoss xác nhận 1 lần rồi bot lặp
(buy T1 ammo → LP store exchange → sell). Không cần skill UI phức tạp; chỉ market sell
đơn giản. (Để sau khi loop chính chạy.)

### ❌ KHÔNG khuyến nghị bây giờ
- Abyss (chưa ground live, no-escape — tàu thật chết là mất thật).
- Exploration (scan UI chưa ground; phải code toàn bộ probe flow).
- Nullsec ratting / Incursions (PvP rủi ro + cần fleet).
- Market/Industry bot (ngoài phạm vi click bot, dễ phạm policy).

## 6. VIỆC CỤ THỂ NGAY SAU ĐÂY (theo thứ tự)

1. Re-pin `client_sha256` (7d466552…) → `--preflight` phải ok:true (chặn mọi nhánh cũ).
2. Distribution L1: chạy 1 mission có giám sát → sửa B1/B2 nếu gặp → 3 liên tiếp.
3. Chạy song song: add `evsurv` import (trigger/avoid) cho Security L1 — phục vụ 🥈.
4. Ghi LP vào ledger sau mỗi turn-in — chuẩn bị 🥉.
5. Khi 3-loop distribution xanh: bật Security L1 3-loop với evsurv data → sau đó L2.

> Lưu ý chính sách: mọi hoạt động vẫn tuân EULA CCP (rủi ro do Boss chấp nhận), bot chỉ
> chạy acc alpha đã chỉ định, hisec, không bấm vào gì ngoài profile/mission đã approve.

## 7. PHỤ LỤC — GIÁ FILAMENT JITA LIVE (ESI, pull 00:1x 2026-11-13, `jita_filament_prices.json`)

25/25 filament resolve được tên + giá live. Tier map: Agitated=T2, Calm=T1, Fierce=T3,
Raging=T4, Chaotic=T5 (đúng tài liệu repo `ECONOMICS_RNG.md`: Fierce Dark=T3, Chaotic Gamma=T5).

| Filament | Tier | Min sell Jita (live) | Volume | E[loot] (repo abysstracker 2026) |
|---|---|---:|---:|---|
| Calm Firestorm | T1 | 580 ISK | 119.861 | — |
| Calm Gamma | T1 | 1.412 ISK | 88.916 | — |
| Calm Dark | T1 | 7.020 ISK | 31.035 | — |
| Agitated Dark | T2 | 8.651 ISK | 4.843 | — |
| **Fierce Dark** | **T3** | **96.900 ISK** | 4.363 | **8,8M–36,3M** (9.062 runs) |
| Fierce Firestorm | T3 | 208.900 ISK | 5.167 | — |
| Fierce Exotic | T3 | 2.799.000 ISK | 3.001 | muta prop-mod lottery |
| Fierce Gamma | T3 | 2.993.000 ISK | 2.524 | — |
| Raging Dark | T4 | 745.500 ISK | 2.264 | ~50M? |
| Raging Firestorm | T4 | 395.900 ISK | 6.584 | — |
| **Chaotic Gamma** | **T5** | **16.860.000 ISK** | 518 | **107M avg** (29.815 runs) |
| Chaotic Firestorm | T5 | 8.694.000 ISK | 3.336 | — |
| Chaotic Exotic | T5 | 23.590.000 ISK | 830 | muta đắt nhất |

**ĐỌC KỸ: giá đã SỤP so với doc cũ.** `ECONOMICS_RNG.md` ghi "Filament T3 ~1-3M" — Fierce Dark
giờ chỉ **96,9K (−97%)**. ROI T3 Dark ≈ **90–370×** nếu tank nổi. T5 Gamma 16,9M vào → 107M
trung bình = **6,3×** (cần win-rate ≥60% + Gila không chết).

## 8. REVISED RECOMMEND — TỪ "DỄ NHẤT" SANG "ĐỦ TIỀN" (sau khi Boss chê L1 courier rẻ)

**Tiền thật của bot này = ABYSS, không phải missions.** Vì:
1. `ECONOMICS_RNG.md` + abysstracker: T3 Dark loot 8,8–36,3M/run, T5 Gamma 107M/run —
   missions L1 (130K) không cùng đẳng cấp; L4 blitz 100–200M/h của video cần battleship +
   standings cao (tháng skill), abyss Gila là **cây nhà có sẵn** trong profile.
2. Giá filament đang đáy: T3 Dark 97K = phá sản nếu chết; lãi một run gấp ~90× giá vé.
3. **Bot đã chứng minh live hôm nay gần hết cơ chế abyss cần**: undock (run2+), warp (run3),
   **Acceleration Gate activation 50m (run8)**, clear pocket lock/fire/drone (run9/10),
   dock (run12). Chỉ còn thiếu: **activate filament từ inventory** (G4 inventory đã ground —
   kéo vào cargo proven) + rule "≥1000km từ station/gate rồi activate".

### Ba giai đoạn (đổi thứ tự so với §5)

- **GĐ1 — Proving loop Security L1** (giữ nguyên): 3 mission liên tiếp để đóng DoD framework.
  Ít ISK nhưng chỉ vài giờ việc, mọi mắt xích đã proven trừ B1/B2/B3.
- **GĐ2 — Abyss T3 Fierce Dark**: grounding filament-activate → 1 run giám sát → win-rate
  5 run. ROI 90×, tàu rủi ro nên dùng fit rẻ trước (Kestrel/Punisher T0 community fits
  3–4,4M — đã có bảng trong `FILAMENT_MARKET.md` §5), Gila chỉ vào khi win-rate ≥80%.
- **GĐ3 — T5 Chaotic Gamma (Gila)**: chỉ khi T3 win-rate ≥80% đo được. 107M avg/run,
  6,3× ROI, theo mô hình "80% ok / 20% mất tàu" của repo.

### Vì sao KHÔNG nhảy thẳng abyss?
`abyss.py:152` đang fail-closed "undock/filament/gate/dock chưa ground" — đúng luật repo:
chưa ground thì không bấm mù. GĐ1 rẻ, đóng khung an toàn, và demo được cho Boss thấy bot
chạy thật; GĐ2 chỉ thêm 1 mắt xích filament là mở được con đường tiền thật.

## 9. SỬA ĐỔI SAU NHẬN XÉT BOSS (00:2x 13-11): "T3 cần control mượt" — ĐÚNG

§8 phía trên sai ở chỗ quy E[loot] của NGƯỜI CHƠI (fit + tay điều khiển) cho bot. Thực tế
control T3 đòi một vòng khép kín `nhìn → quyết → bấm → xác minh` mỗi tick 0,3s, và bot hiện
thiếu ĐÚNG các mắt perceive của vòng đó:

| Primitive control | T3 cần | Trạng thái bot (bằng chứng) |
|---|---|---|
| Tốc độ bản thân (kite) | orbit đúng range | **UNKNOWN** (`status`: "Ship speed: UNKNOWN") |
| Lock xác minh | bắn đúng mục tiêu | **run22: lock Centii 4 lần, không thấy ActiveTarget** |
| Trạng thái module (MWD on/off, hardener) | bật/tắt đúng chu kỳ, cap boost khi bị neut | **UNKNOWN** (HUD chỉ xuất ramp_active lúc animation) |
| Số drone bay / recall | redbox-recall, leash 20-25km | **B08: drone read-back None** |
| Cap/HP realtime | SURVIVAL đúng lúc | HP đọc được; **cap chưa thấy trong snapshot** |
| Kill-order/trigger discipline | webbers trước, trigger sau cùng | chưa wire EVE-Survival data vào tick |
| Thoát khẩn (abort trong pocket) | cap<X / quái Y → warp-out | chưa có nhánh; abyss no-escape nên phải SURVIVAL |

→ Kết luận sửa lại: **T3 không bị chặn bởi "thêm 1 mắt xích filament" mà bởi thiếu 6 mắt
perceive + 2 nhánh quyết định.** Chạy T3 lúc này = vé 97K mua số trúng gần 0, cộng rủi ro
không biết mình đang chết (perception hổng). ROI 90× chỉ đúng khi P(success)≈80% của người.

### Thang luyện control (mỗi bậc có gate đo được, live — không phải sim)

| Bậc | Nội dung | Gate nghiệm thu |
|---|---|---|
| P0 | **Perception sweep**: ground speed, module state (MWD cycle), cap, ActiveTarget, drone count từ dump thật | `status` in số THẬT, hết UNKNOWN; có test regression trên fixture dump |
| P1 | Gunnery L1 security: orbit theo lệnh (đo speed+distance N tick giữ ±10%), lock xác minh qua ActiveTarget, drone launch/recall đếm before/after | 5 orbit liền đúng range; 10/10 lock có read-back; drone count khớp |
| P2 | Trigger/wave + abort: wire evsurv kill-order; SURVIVAL cap<X → hành động đúng | The Blockade không bấm nhậy trigger; 1 lần abort có chủ đích được ghi log |
| P3 | Sim abyss worst-case matrix (Drifter BS + 8 neut, cloud hazard…) dùng ĐÚNG primitives đã proven live ở P1/P2 | ≥80% clear worst-case matrix trong sim, cùng code path live |
| P4 | **T1/T2 abyss** — vé 580–8,6K ISK, frig throwaway 3-4M: luyện control thật với timer/room/hazard thật, chết gần free | 5 run, win-rate ≥80%, có log loop control |
| P5 | T3 Fierce Dark (vé 97K) | chỉ mở khi P4 đạt; fit thùng thiếc trước, Gila chỉ khi 2 chuỗi P4 xanh |
| P6 | T5 Chaotic Gamma (16,9M) | theo mô hình 80/20 của repo, Gila, sau khi P5 ≥80% |

> Điểm mấu chốt: "control mượt" không phải thêm code chiến thuật — `rooms.py`/`trio.py` đã có
> từ trước — mà là **mắt đọc đủ + mỗi action có read-back**. Đó là lý do P0 là việc đầu tiên,
> và nó không cần gửi input nào vào game (chỉ dump + decode), rủi ro zero.
