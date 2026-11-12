# CHANGELOG — fila-bot

> Mỗi lần nâng cấp PHẢI ghi 1 mục ở đây + tăng `VERSION` (SemVer).
> Nhãn build trong `BUILD_INFO.json` do `tools/build_release.py` sinh; chạy từ source thì không có.
> Định dạng: `[X.Y.Z] — ngày — tên bản` rồi bullet thay đổi. Mục mới nằm trên cùng.

## [1.4.0] — 2026-11-12 — "Có version, có log, Boss nhìn thấy"

**Bản đầu tiên có quản lý phiên bản.** Từ bản này: `VERSION` = nguồn sự thật; CLI/UI/launcher đều in `FILA-BOT vX.Y.Z`; mọi lần nâng phải ghi mục ở đây.

- Thêm `src/fila_bot/version.py` (một nguồn sự thật, đọc `VERSION` / env `FILA_BOT_VERSION` / `BUILD_INFO.json`).
- CLI: `python -m fila_bot.cli --version`; banner mỗi mode có `FILA-BOT v… (commit)`.
- UI (`ui.py` + `ui_redesign.py`): tiêu đề cửa sổ kèm `v…`.
- `XEM_LOG.bat` mới — cửa sổ xem log thời gian thực (`logs/live_latest.log`, UTF-8).
- `AUTO.bat` tee toàn bộ output ra `logs/live_latest.log` để Boss xem trực tiếp (PS5.1-safe `Out-File -Encoding utf8`).
- `tools/build_release.py` mới: đóng gói `dist/fila-bot-vX.Y.Z/` kèm gate: suite phải 0 FAIL, hash Python+DLL vào manifest, `BUILD_INFO.json` (commit/time).
- Nhận diện hiện trạng (không đổi code): MissionRunner V1 — 856 PASS/0 FAIL nhưng completed=0; REA native lưu bền tại `D:/EVE-REA/`.

## Trước 1.4.0 (tóm tắt theo git, chi tiết trong `git log`)

- 2026-11-10 `6036467`: Opportunities parser + probe jobboard; DLL rebuild O2 (4 bug NULL-deref); 79 test files / 856 PASS.
- 2026-11-10: Audit UI/UX + mechanic (512 tests); Auto-Control Layer merge (492); competitor intel.
- 2026-11-09: BT engine; run log JSONL; unified CLI/GUI + 1-click launchers; G1–G11 grounding (dumps thật TQ).
- 2026-11-07..09: Sanderling lineage vendor; eve-memory-reader DLL; sim executor; 332→369 tests.
- Trước đó: FC protocol v1 (archived) → v2 pure-Python autonomous; abyss FSM; guards từ AbyssBot changelog.
