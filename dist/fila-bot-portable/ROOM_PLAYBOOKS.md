# ROOM × WEATHER × LOOT — playbook từng tình huống (nguồn: minmatar trio guide, Goon,
# BushidoMaru, Four Ohm video, eveworkbench notes, abysstracker loot data, 2026-11-07)

> Code: fila_bot/rooms.py (31 test). detect_room(names) → entry move + kill order.
> Trong Abyss CÓ 18 room types × 5 weather — cùng room type khác weather = chiến thuật khác.

## Cơ chế giây 0 mà wiki hay bỏ (FOUR OHM video + xác nhận cộng đồng)
- **GRACE 15–20s** sau khi vào room: KHÔNG ra lệnh/kích module → rats không aggro
  (như gate invul). Prop mod BẬT trước khi qua gate → giữ cycle, drift tự tới conduit
  mà không tính là "lệnh" → dùng grace drift để lướt sát mục tiêu MIỄN PHÍ.
- Exit abyss: invul 60s nếu KHÔNG move (transfer cargo được); gankers camp trace
  + drop depot chặn filament — warp off ngay khi hết invul.

## Entry move + kill order per room (tóm tắt — full ở rooms.py)
| Room | Entry giây 0 | Kill order khác biệt |
|---|---|---|
| Kikimora swarm | KITE chéo >20km | Tangling > Starving > Ghosting > Striking > Damavik > Kiki |
| Vedmak | Orbit CACHE (trig lao vào vì no-switch) | Tangling > Starving > Ghosting > Rodiva > Damavik > Vedmak |
| Leshak | APPROACH ASAP (spawn HP thấp + starburst) | **Starving (neut 80km!) > Blinding > Tangling > Renewing > Striking** |
| Overmind | Approach cache, ĐỢI aggro mới drop drone | web/logi frigs trước, orbit BS 500m under guns |
| Tessera BC | GIỮ >12km (tracking cực, optimal ngắn) | web/logi > spotlighter > lance > needle |
| Deepwatcher | **LOOT TRƯỚC** rồi orbit <10km MWD-off | burn-to-you frigs > Up/Sentinel > Watchman > BS (room dễ 3-5') |
| Karen | Spiral 45° vào <30km (đích <10km); KHÔNG orbit cache khi Karen sống; KHÔNG để Karen sống cuối (self-rep) | web > neut > scram > escorts > Karen |
| Marshal | BAY XA NGAY 60km (DLA); Drainer neutron range khủng | **Drainer Marshal > Marshal khác > Thunderchild > EDENCOM** |
| Sansha | Kite rộng >25km (chậm hơn mình) | Fisher > Trapper > Smith > **Knight (orbit 500 quá close web không bắt)** > Priest... |
| Angel | Kite + EM resist; T4+ đừng speed-tank (web) | Echo > Cynabal > Fury > Swordspine > Ixion > Medusa |
| Scylla | Kite; phân loại bằng TYPE column | Entanglement > Nullcharge > Nullwarp > Confuser > Illuminator |

## Weather × room — combo đổi chiến thuật (không phải chỉ trừ resist)
| Combo | Đổi gì |
|---|---|
| Leshak + Firestorm | NGUY HIỂM NHẤT: +40% armor Leshak × +50% weather = TTK nổ gấp 3 → chain gate sớm |
| Deepwatcher + Firestorm/Gamma | BS HP +50/65% → timeout risk tăng → bỏ node, bắn liền |
| Angel + Electrical | XẤU NHẤT: Angel damage EM × weather phá EM resist → hardener EM bắt buộc |
| Marshal room (mọi weather) | Toàn explosive → giữ speed MAX; missile-based → angular vô nghĩa |
| Karen + Dark | Tachyon cloud phổ biến → không MWD vào cloud khi spiral |
| Overmind + Gamma | Shield +50% → timeout killer → đổi đạn Exp/Therm đúng tier |
| Vedmak + Firestorm | Trig +40% armor × +50% → kill Damavik trước (giảm ramp DPS) |

## Kill order KHÔNG CỨNG — theo fit của MÌNH (reddit "cheat sheet with killorder")
"web trước neut" là guideline, không phải giáo trình tuyệt đối: cùng room Vedmak
lần này là Starving, lần sau Harrowing — thứ tự đổi theo fit + weather + clouds.
Nguyên tắc đúng: **đánh giá threat lớn nhất cho FIT CỦA MÌNH**, với cruiser
(CErberus/Sacrilege/Gila): bắn con NHỎ trước vì chúng MWD lao vào → sig to →
application tốt (Starving Damavik 2-3 phát thay vì 6-8).

## LOOT — giá trị thật + policy (abysstracker run data 2026)
| Item | Giá | Bán | Drop rate |
|---|---|---|---|
| **Triglavian Survey Database** (red loot) | **100K cố định/cái** | NPC buy order unlimited | 98% |
| Crystalline Isogen-10 | ~47K | market (biến động) | ~85% |
| Zero-Point Condensate | ~36K | market | ~60% |
| Filament cùng tier | 8–17M | market | ~14% |
| Mutaplasmid | lottery 0–2.8B | market | ~3% |

Red loot = 1 run T3+ ~471 cái ≈ 46M chỉ từ Survey DB → **cache là 80% giá trị,
node là vật phẩm phụ + null chance**. Policy bot (`loot_plan()`):
- Cache: phá khi thuận đường (<15km) hoặc timer dư >4'
- Node: chỉ khi timer dư >7' + nằm ≤12km trên đường
- Run trung bình ≥15' → room 1 bỏ node (đừng tham đầu trận)
- Room 3 (Origin Conduit): loot tất cả những gì an toàn — hết timer về nhà rồi

## Multibox loot split
- Bioadaptive/Biocombinative Cache (3 frigs = Biocombinative) chứa ×3 loot — CẦN loot
- Node/SubNode loot KHÔNG nhân theo số filament (chỉ theo tier) → giá trị/ effort giảm với frig fleet → multibox ưu tiên cache-only trừ khi room 3
