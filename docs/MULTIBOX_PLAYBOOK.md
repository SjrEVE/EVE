# MULTIBOX FRIGATE PLAYBOOK (nguồn: Gustav Mannfred guide PYgxYxhekP8 + Setups Overview kNOCD7k8s5w + forum "Multi box abyssals what works")

> Endgame: 3 frigate multibox. Bot phải biết CHOREOGRAPHY, không chỉ solo combat.

## 1. Điểm số học quan trọng nhất (đừng tự tin)
- 3 frig T6 với người giỏi: **80% win / 20% mất fleet** — lợi nhuận đến từ khối lượng 100 runs, không phải 100% win.
- Setup 3 DPS cần micromanagement nhiều hơn **2 DPS + 1 Logi** — người mới (và bot v1) nên chạy 2DPS+1Logi.
- Cheap learning set: 3 throwaway Hawk ~50M mỗi con = 150M — mất không đau.

## 2. Setup meta (Gustav Setups Overview)
| Setup | Tier | Ghi chú |
|---|---|---|
| 2× Retribution + Deacon (logi) | T3 elec → T5/T6 Firestorm (beam) | chuẩn học, dễ nhất |
| 2 DPS + 1 Logi (bất kỳ) | mọi | LOGI: rep con đang bị aggro, set-and-forget phần lớn |
| 3× Hawk throwaway | T6 Dark | 150M set, Ibeast fit |
| Nergal + Retri + Deacon | T6 Firestorm/Gamma | |
| Hawk + Skybreaker + Kirin/Scalpel | T6 Dark | |
| 3× Vengeance 40M (đồ mới) | T6 Dark | EM resist tốt hơn Hawk, sig nhỏ hơn → sống Angel room |

Fits chính thức: gustavmannfred.streamlit.app/Firestorm_Frigates

## 3. Choreography mỗi room (bắt buộc cho FSM multibox — từ transcript guide)
1. **Fleet + Watchlist**: cả 3 vào fleet, watchlist members; lock đồng đội = Ctrl+click watchlist.
2. **Sequence tagging**: shortcut "tag 1..N" (default KHÔNG CÓ — phải setup client trước). Tag các con quái cùng thứ tự giữa 3 acc để focus fire đồng bộ.
3. **Regroup**: fleet window → Regroup; leader orbit cache 300–500m, 2 con kia orbit leader. (FSM: leader là acc 1; hai acc còn lại ORBIT_LEADER mặc định.)
4. **Vào room**: cả 3 regroup → chọn target theo cùng priority (rats.py) → DPS đánh, logi rep con bị aggro.
5. **Aggro management**: con bị aggro giữ orbit cache; logi activate remote rep lên nó rồi "quên" — chỉ micromanage khi burst.
6. **Reactive hardeners**: PHẢI RESET trước khi qua room mới (quên = dead slot).
7. **Remote reps on** để lấy cap lại giữa room.
8. **Gate transit**: leader activate trước; 2 con kia approach gate chờ; **Regroup trước gate** (leader nhanh sẽ bỏ xa — drop back over time).
9. **Room cuối**: regroup + exit; loot từ leader.

## 4. Tool thật của người chơi (bot thay bằng code)
- **EVE-O Preview**: preview window các client, click switch — bot thay bằng SetForegroundWindow scheduler.
- Broadcast/Input multiplexing (ISBoxer-like): bot thay bằng 3 bus riêng + shared lock decision.

## 5. Map choreography → FSM multibox (fila-bot endgame)
- Mỗi acc 1 Bot instance (eye/FSM/guards riêng) + bus riêng (bus/accA, accB, accC).
- ROLE trong config: leader/dps/logi — khác nhau ở room entry (leader orbit cache, kia orbit leader) và gate order.
- SHARED_LOCK: cả 3 FSM cùng rats.lock_order() + cùng sequence tag → focus fire đồng bộ (giết web 2s thay vì 6s solo).
- LOGI FSM đơn giản nhất — viết trước để test choreography.
- Scheduler input: ưu tiên acc có hp thấp nhất; round-robin 2-3s cho việc thường.
- Client chọn theo window title "EVE - <char>" (đúng pattern FUN_1400b5000 của AbyssBot).
- Chi phí chuẩn kế hoạch: 20% runs mất fleet ở T6 — profit = (win_rate × loot) − (lose_rate × ship_cost); không bao giờ tính 100% win.
