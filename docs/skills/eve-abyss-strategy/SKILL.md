---
name: eve-abyss-strategy
description: "Chạy abyss hiệu quả: fits, ISK/h, room playbook, nguồn học."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [eve, abyss, tactics, fits, fila-bot]
---

# Chạy Abyss — chiến thuật + fits + kinh tế (có nguồn)

## When to Use
Load khi cần chọn ship/fit/tier để bot chạy, ước lượng ISK/h, xử lý từng loại room (Karen, web/neut), hoặc Boss hỏi chiến thuật chạy abyss.

> Nguồn: my.minmatar.org guide, Goon Wiki, Reddit r/Eve (2024–2026), Abyss Tracker, Cepheus guide, YouTube (Gustav Mannfred, Gildii Auscent).

## Chọn tier & kỳ vọng ISK/h (sau trừ chi phí filament/drugs — Reddit consensus 2025–2026)
| Setup | Tier | ISK/h ước | Ghi chú |
|---|---|---|---|
| Frigate (Kestrel/Hookbill) | T0–T2 | 60–90M | học game, Dark OK vì missile |
| Gila (~300–400M ISK) | T3–T4 | 85–130M | passive shield, dễ, drone xử mọi size |
| Gila bling + implants (~2B) | T5 | 190–250M | Gamma/Exotic trước, tránh Dark T5 |
| Ikitursa (~1.5B+, smartbomb) | T5–T6 Dark | 400–700M | cần skill cao, sợ alpha Karen |
| Nergal/Hawk 3 frig multibox | T5 | 500–700M | loot ×3, khó chơi |
| Frigate T6 multibox giỏi | T6 | 1.2–1.4B | đỉnh, rủi ro cao |

Chi phí chạy: filament T5 ~17M (Gamma ~8M), drugs ~15M/h. Kiểm tra stats từng fit ở abysstracker.com (median ISK/run, median duration, ISK/h theo tier/weather) — chọn fit CÓ SỐ LIỆU, không tự chế khi mới học.

## Fits khuyên dùng (từ nguồn)
- NEW: Povertila (Gila giá rẻ) — video Gustav Mannfred "5DFpBjmg9xA"; T3 là sweet spot.
- T4: passive-tank Gila "foolproof" (Reddit); Ikitursa cho Firestorm.
- T5: Gila T5 Exotic (Hardshell II + Standard Exile booster); Ikitursa Dark (Caldari Joans guide: caldarijoans.streamlit.app).
- T6: Stormbringer Electrical rẻ nhất, Vagabond/Cerberus/Ikitursa Dark (Gustav playlist PLU8XY9tEgSMbPRrCwSv6PcLKxsV50UPne).
- Module bắt buộc: Afterburner (MWD bị cloud phạt), web để bắt frigate, hardener đúng weather, cap booster/battery cho active tank, drone faction (HP+tracking).

## Room playbook (map thẳng sang FSM bot)
1. Vào phòng: bật prop + tank NGAY (đang ăn đòn từ frame đầu nếu Karen room); bay CHÉO khỏi hướng spawn, zoom+tactical xem ai đuổi.
2. Lock EWAR (web→neut→scram) từ overview — giết theo thứ tự; sau đó RR; sau đó DPS.
3. Giữ khoảng cách: orbit cache/gate 10–20 km hoặc keep-at-range theo fit; KHÔNG bay thẳng vào mặt battleship (Karen alpha), KHÔNG bay vào cloud, KHÔNG lấn vùng đỏ.
4. Phòng có swarm/drones: giết mothership trước, swarm tự tắt — đừng phí DPS.
5. Sau clear: phá Bioadaptive Cache (300 HP) + loot; bỏ extraction node khi thiếu giờ (chỉ loot khi còn >3 phút mỗi phòng & là cache).
6. Gate: approach + activate; sang phòng mới lặp. Phòng 3 xong = Origin Conduit về chỗ bật filament.
7. Nếu HP < escape_hp: SURVIVAL (đủ cache trước, giữ orbit max, overheat rep nếu cần) — KHÔNG có warp out.
8. Timer warn còn ~3–4 phút: bỏ loot phụ, lao thẳng chain gate.

## Chỗ chạy (Where to run — UniWiki)
- Hệ 0.5–0.8 an toàn (T4–T6 ở 0.8 → suspect flag; 1.0/0.9 cấm). Gần trade hub nhưng KHÔNG phải Jita/Amarr (đã cấm abyss ở 1.0/0.9).
- Safe spot bookmark cách mọi object warpable ≥14 AU (d-scan range); đừng bật filament lúc sắp downtime 11:00 EVE.
- Đặt múi giờ chạy tránh giờ đông người ghé thăm trace (trace scan được bằng probe — có kẻ ngồi câu acc chạy abyss).

## Nguồn học (dẫn Boss xem khi cần)
- Wiki: wiki.eveuniversity.org/Abyssal_Deadspace (+FAQ + Possible_rooms + Where_to_run + Abyssal_Community_Fits).
- Guide tổng: my.minmatar.org/learning/guides/abyssals ; cepheuscorp.com/guides/abyssals ; goon wiki Abyssal_Deadspace (Karen/herd chi tiết).
- Stats fits: abysstracker.com ; caldarijoans.streamlit.app (T5/T6).
- YouTube: Gustav Mannfred (fits từng tier), Gildii Auscent "Running Abyssals START HERE", Captain Benzie tổng quan.
- MULTIBOX endgame: docs/MULTIBOX_PLAYBOOK.md (choreography + setups + tỉ lệ 80/20 win/loss T6).
- TRIO chi tiết room-by-room: docs/TRIO_PLAYBOOK.md (Nergal/Retri/Deacon T5/T6 Firestorm — fits, ngưỡng >6 kiki, 13-kiki T6, room chart xanh/vàng/đỏ).
- KINH TẾ FILAMENT: docs/FILAMENT_MARKET.md (giá T6 từng weather, nguyên tắc 'giá filament quyết lợi nhuận', Community Fits T0 tested 4 con tàu).
- Convocation infographics (notion): NPC damage types — chart nguồn Gildii dùng.
- Proving Grounds: wiki.eveuniversity.org/Abyssal_Proving_Grounds — arena PvP theo event, fit restriction theo event, KHÔNG phải nội dung farm ISK chính.
- Destroyer duo: Jackdaw T4-T6 Dark (eveworkbench Agrippa Pullus), Draugur T5 Firestorm, Confessor T4 elec; 2 frig thường > 2 destroyer ở tier thấp. ALL CLOUDS đều hại Jackdaw.
- VN: chưa có guide VN chất lượng công khai; Steam có page tiếng Việt chính thức. Khoanh vùng FB "EVE Vietnam" group khi cần recruit — không phải nguồn kỹ thuật chính.
