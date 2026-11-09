# COMPETITOR INTEL — nghiên cứu đối thủ & môi trường (cập nhật 2026-11-10)

Kỷ luật repo: **mỗi cái chết của đối thủ = 1 guard cho mình** (mục llm-fc-bot skill).
Doc này ghi intel định kỳ + nguồn; guard/code tương ứng ghi ngay tại chỗ.

> Nguồn đối thủ bot EVE nằm ở nơi CÔNG KHAI: forum BotLab + abyssbot.com, Reddit
> r/Eve, GitHub (Viir/Sanderling), YouTube (Gustav Mannfred...). Cộng đồng bot
> không hoạt động trên darkweb — không có gì ở đó và không cần đến đó.

---

## 1. Đối thủ thương mại: AbyssBot (abyssbot.com)

| Mốc | Phiên bản | Nội dung | Bài học cho fila-bot |
|---|---|---|---|
| 2024-03 | v1.04x (t.496) | sửa đọc bookmark menu để warp, bug break | — |
| 2024-05 | v1.05x (t.728) | — | **5 Gila T3 chết trong 2 tháng: bot đứng im khi overview rỗng** (lag server) + orbit icon không tìm thấy. Guard `overview_empty` của mình ra đời từ đây ✓ |
| 2024-05 | t.728 reply | **v1.05 hứa ưu tiên Marshal nhưng Attacker Marshal bị đánh CUỐI** — dev "sẽ kiểm tra lại" | Override priority phải có test integration theo room — mình test `lock_order` + `HIGH_THREAT_DPS` trực tiếp ✓ |
| 2024-10 | t.728 | loop "Failed to activate abyss" sau filament — không thấy popup | Filament flow fail-closed của mình: FILA_SPOOL chỉ confirm khi eye thấy dialog, timeout → MAYDAY ✓ |
| 2025-03 | **v1.06x** (t.860) | audio chime phút thứ 5 + cargo/ore hold | Idea M6: thêm beep cảnh báo timer lên UI tkinter (chưa làm) |
| 2025→ | **v1.069** (hiện tại) | dòng v1.06 tiếp diễn, không thấy release 2026 | Đối thủ chậm lại 2026 — cơ hội; cũng có nghĩa meta farm ổn định |

Tổng hợp xác tàu đối thủ: 5 Gila (overview empty), Gilas tiếp tiếp tục loop filament,
Marshal priority bug. → guards.py DEATH #1/#2/#10.

## 2. BotLab / Viir / Sanderling (open-source lineage mình vendored)

- [Viir/bots](https://github.com/Viir/bots) — repo chính, BotLab client 2026-08-11,
  Sanderling mới; A-Bot (anomaly ratting) đã merge vào repo này.
- [Arcitectus/Sanderling](https://github.com/Arcitectus/Sanderling) — memory reader
  gốc (tổ tiên eve-memory-reader.dll của mình) vẫn maintained ✓ — `ParseUserInterface.elm`
  vẫn là mỏ vàng semantics attrs (skill llm-fc-bot §6).
- **Thread "UI changes 3/21/26" (forum.botlab.org, 2026-03)**: ban đầu nghi EVE đổi
  UI tree — hoá ra **bot đọc nhầm client vì check PID fail SILENT khi mở nhiều client**
  ("multiple clients open and the pid check I was using was failing silently").
  Bài học: *triệu chứng giống đổi-UI-tree nhiều khi là đọc-sai-client*.
  → **DEATH #10 `MultiClientGuard`** (2026-11-10): >1 exefile.exe mà chưa pin pid → MAYDAY
  fail-closed. Việc mở: Eye/DLL chưa nhận tham số pid — làm khi setup multibox trio.

## 3. Môi trường CCP / enforcement (rủi ro acc — Boss quyết sách)

- **[Monthly Ban Report Sep 2026](https://www.eveonline.com/news/view/monthly-ban-report-september-2026)**:
  CCP vẫn đăng báo cáo ban hàng tháng; đã bỏ graph "ship flown by temp-banned".
- **[T4 abyss in 0.9 sec (r/Eve, 2026)](https://www.reddit.com/r/Eve/comments/1sn3d7k/t4_abyss_in_09_sec)**:
  xác nhận **filament KHÔNG kích được ở 1.0/0.9** (biện pháp chống bot — khớp precheck
  skill eve-abyss-mechanics); cộng đồng nói "abyssals got completely removed (from
  hisec) because of botting".
- **[Bot bị ban khi farm T0 10-12h/ngày (r/Eve)](https://www.reddit.com/r/Eve/comments/vifxgz/got_banned_for_grinding_t0_abyss_sites)**:
  ban của người CHƠI THẬT kiểu máy móc — humanize + max_session 4h của mình là bắt buộc.
- **[Số bot trong game (r/Eve, 2025)](https://www.reddit.com/r/Eve/comments/1ii5np4/the_number_of_bots_in_this_game_is_unreal)**:
  án đầu thường 2 tuần temp-ban → acc alpha bỏ đi là đúng sách của Boss.
- Kỷ luật mình: chỉ Singularity + acc test, dry-input khi ground, session ≤4h ✓.

## 4. Guides/meta còn sống (YouTube + written)

- [Gustav Mannfred — Abyssal Tutorials playlist](https://www.youtube.com/playlist?list=PLU8XY9tEgSMbPRrCwSv6PcLKxsV50UPne)
  + [Multibox Frigate playlist](https://www.youtube.com/playlist?list=PLU8XY9tEgSMbaHaxu2QI5_Ig2PzJGGIls):
  nguồn ramp-rate / no-switch / trio đã dùng trong rats/trio. Video "2x Rocket Hawk &
  Kirin T5/T6 Exotic" — ~800M ISK/h (meta mục tiêu cho multibox sau M5).
- [T6 Abyss — EVE Nomad](https://wayspider.space/t6-abyss) + [WCKG wiki Abyssals](https://www.wckg.net/PVE/abyssals):
  fits/tactics viết — đối chiếu khi làm M5.

## 5. Việc rút ra (checklist)

1. ✅ `overview_empty` guard (DEATH #1) — đã có
2. ✅ Kill-order priority test trực tiếp (AbyssBot v1.05 bug) — test_rats + test_tactics
3. ✅ Filament confirm fail-closed (P0-1) — đã có
4. ✅ **`multi_client` guard (DEATH #10)** — mới thêm 2026-11-10
5. ⏳ Eye/DLL pin PID cho multibox — chờ setup trio (cùng G8-G10)
6. ⏳ Audio chime phút thứ 5 trên UI — M6 idea từ v1.06x
7. ⏳ Đổi đạn theo tier Overmind — VERIFY in-game khi có client (mâu thuẫn nguồn
   UniWiki vs AbyssTracker trong ROOM_PLAYBOOKS — kiểm thực tại client, không tin 1 bên)

*Đợt quét tiếp theo: khi có client live (đối chiếu dump thật với meta videos), hoặc
sau mỗi CCP patch note lớn.*
