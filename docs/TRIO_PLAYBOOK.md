# TRIO PLAYBOOK CHI TIẾT — Nergal/Retribution/Deacon T5/T6 Firestorm (nguồn: Gustav
# video GA7AGtHl1tI "up to 1 Bil/h" transcript + eveworkbench fleet b1055bb9, 2026-11-07)

> Đây là tầng chi tiết "người 20 năm" — từng room có checklist + con số ngưỡng.

## 1. Fits (giá thật từ eveworkbench: tổng fleet ~1.16B)
- **Nergal (Tank)**: disintegrator + RAR + AB + 2× battery + reactive hardener + Trig entropic sink;
  rigs kinetic+thermal (kinetic để tank wrecking Overmind + drone/EDENCOM rooms);
  drones: **Augmented Hornets** (shield tank tốt — giữ ngoài lâu, tank nổi 1 medium Suppressor).
- **Retribution (Main DPS)**: beam lasers + remote rep + AB + battery; multi-spectrum + thermal hardener;
  DPS đạt ~**480** (implants: SE-603, RF-903, EM-802, WU-1002 + Pyrolancea).
- **Deacon (Logi)**: 3× remote armor rep + AB + battery, low = tank + **cap brick** (cap stable
  cả 3 reps chạy, dư cap phòng bị neut; Improved Mindflood).
- Boosters cả fleet: Mindflood + Frentix (synth) + Pyrolancea (agency).

## 2. Room chart theo độ nguy hiểm (Gustav tự phân)
- 🟢 Xanh: Drekavac room, Drone Frigs, Sleeper cruisers, Deepwatcher, Drone BC — ít sai.
- 🟡 Vàng: Kikimora room, Vila Vedmak, Angel, Sansha, Overmind, Leshak — phải chú ý.
- 🔴 Đỏ: **Marshal + Vedmak** — khó nhất, phải để ý cả con rats lẫn fleet mình.

## 3. Checklist từng room (số ngưỡng cụ thể từ video)
| Room | Checklist |
|---|---|
| **Drekavac** | Kill Kikimora trước (poor tracking của Drek → đỡ tank); burn cache; loot; kill hết |
| **Rodiva+Kiki** | >6 Kiki → **mở CẢ 3 remote reps của Deacon lên Nergal**; kill Starving Damavik đầu tiên |
| **Sleeper Cruiser** | bình thường; reps on Nergal nếu cần |
| **Max Kikimora (T6, 13 con!)** | tất cả reps (Nergal RAR + Retri rep + Deacon 3 reps) lên Nergal; kill Starving đầu; burn in |
| **Vila Vedmak** | kill mothership đầu (drones tắt); Shining Vila là healer — kill sau web/neut |
| **Drone BC** | DPS ship brawl BC cận sát (fit cho phép), tank giữ range cache |
| **Deepwatcher** | loot first + orbit close, room dễ |
| **Drone Frigs** | dễ — bắn theo EWAR priority |
| **Angel** | Cynabal = web+neut — kill đầu; giữ EM resist; không speed-tank T6 |
| **Karen** | spiral 45° vào <30km; KHÔNG orbit cache khi Karen sống; không để sống cuối (self-rep shield) |
| **Vedmak** | ĐỎ: burn away; kill Damavik trước (giảm ramp); Vedmak trong 40km mới spool trên nó |
| **Marshal/EDENCOM** | ĐỎ: approach cache; kill neut trước; reactive hardener sẽ tự đổi theo dmg type — EDENCOM đánh EM/Kin + Marshal Therm/Exp (reactive đổi 1 lần đầu rồi EDENCOM đánh đau hơn — chú ý); Thunderchild alpha cao nhất |
| **Ephialtes/Sleeper frigs** | dễ |
| **Sansha** | kite >25km; Knight orbit 500 quá close web không bắt |
| **Overmind** | orbit 500 under guns; đổi đạn theo tier |
| **Leshak** | approach ASAP; Starving > Blinding > Renewing; giữ tụ về 1 hướng, KHÔNG cho starburst |

## 4. Triết lý fleet structure (why 2DPS+1Logi)
- Nergal gánh aggro (no-switch enemies cố định lên tank) → logi set-and-forget
- Reactive hardener = "auto-resist" — bot chỉ cần reset mỗi room (guard trong FSM)
- Cap brick Deacon: kể cả bị neut vẫn giữ reps chạy — vì neut-heavy room (10+ Starving Damavik) là xác xuất có ở T6

## 5. Maps cho fila-bot multibox (role FSM)
- ROLE=TANK (Nergal): entry luôn approach cache trước, aggro magnet; emit hp mỗi tick (logi dựa vào)
- ROLE=DPS (Retri): giữ orbit tank 2-5km, bắn theo rats.lock_order, KHÔNG tank aggro (dps thấp hơn)
- ROLE=LOGI (Deacon): lock TANK (Ctrl+click watchlist), reps on từ giây đầu room; "set-and-forget"
  trừ khi tank hp <60% → mở thêm reps; cap thấp → emit MAYDAY
- Scheduler ưu tiên focus: LOGI (set-and-forget) → TANK (đổi orbit) → DPS (đổi target)
