# CHANGELOG — fila-bot

> Mỗi lần nâng cấp PHẢI ghi 1 mục ở đây + tăng `VERSION` (SemVer).
> Nhãn build trong `BUILD_INFO.json` do `tools/build_release.py` sinh; chạy từ source thì không có.
> Định dạng: `[X.Y.Z] — ngày — tên bản` rồi bullet thay đổi. Mục mới nằm trên cùng.

## [1.4.5] — 2026-11-14 — Punisher fit-map + module read-back control

- Add `fit_map.py`: declarative fit registry (`ab_punisher` = Aceface 10M T1 Electrical: 4x Small Focused Beam II high, AB mid 1, cap battery mid 2, 2x SAR II low 1-2, RAH low 3, no drones) + `FitController` that presses modules from OBSERVED HUD state only — False presses, True never re-presses (double-press = module OFF mid-fight), unknown presses once per engagement.
- Two tank policies: `rep_always_on=True` (cap-stable fit — tank runs the whole room) and HP-hysteresis open/close for cap-hungry fits.
- Add `fleet.py` `FleetState`: multibox HP sharing via per-role bus files with freshness gate; tank HP is now read from the tank's own report, never fabricated from the local bot's HP (bug: logi read its own HP as `tank_hp` and opened reps on the wrong ship).
- `reflex.Bot` wires the fit registry: drone-less fits disable CombatBrain drone actions; per-room module state resets on observed room change (previous reset never ran — it was gated on the abyss timer and only "worked" through the HP bug).
- `RealExecutor.module_state_world()` feeds real HUD `module_buttons()` state to the controller; `cli abyss` gains `--fit-type ab_punisher` and `--resist-hole`.
- SIM evidence: one `--fit-type ab_punisher` run emits exactly the 8 module commands of the fit (4 guns F1-F4, Alt-F1 AB, Ctrl+F3 RAH, Ctrl+F1-F2 SARs) and zero drone events. This is offline/sim evidence, not live acceptance — filament/gate/dock remain ungrounded and live stays fail-closed.

## [1.4.4] — 2026-11-13 — Abyss-only operator flow

- Make Abyssal Deadspace the only activity exposed by the standard GUI and launcher; retain Security/Distribution code as legacy implementation.
- Remove mission-type tabs and the mission-count selector from the GUI; keep Abyss-specific filament/engine/session/run settings.
- Make `AUTO.bat` a hard-capped one-run Abyss SIM with a separate `abyss_sim_latest.log`; no live input or client connection.
- Disable old courier BAT wrappers and exclude them from the distributable package; legacy backend code remains available for development.
- Add UI, launcher, SIM-log, and package-boundary contract tests.
- Offline/SIM verification is not live acceptance.

## [1.4.3] — 2026-11-13 — Compact operator console

- Start the desktop operator console at 870×600, with state, actual phase, mode-specific settings, operation controls, and append-only event log visible together.
- Keep SIM/DRY safety explicit; the GUI blocks client/live starts, shows the requested safety state inline, and directs client access through the ownership-gated CLI.
- Wrap safety copy and keep phase-history text, E-STOP explanation, and footer inside the minimum viewport. UI/model tests are offline verification, not live acceptance.

## [1.4.2] — 2026-11-13 — Evidence and runtime foundations

- Add per-client OS-backed ownership primitives for Windows and POSIX; PID is diagnostics only.
- Key Gone Berserk tactics by level, with L1 and L2 separated; unknown level applies no trigger playbook.
- Mark 25 km explicitly as tactical policy, not a universal game range.
- Offline packaging gate: 959 PASS, 0 SKIP, 0 FAIL with local game-evidence dumps present; this is not live acceptance.
- GUI live-reader/input starts fail closed until that path has per-client ownership; use the locked CLI path. SIM remains available.
- Release packages include tests, ship only the public profile template, report missing local evidence as SKIP, and normalize `.bat` files to CRLF.
- Security LIVE launchers now require an explicit profile path; Abyss SIM is bounded to one run.

## [1.4.1] — 2026-11-13 — Production brain integration corrections

- Rank authorized lowercase `hostiles` directly; no speculative lock state from planner calls.
- Keep non-trigger selected across ticks while it remains present; brain errors stop with an explicit reason.
- Recall drones when the selected target is outside engagement range; throttle recalls and suppress contradictory launch/engage.
- When target-bar observation is supported, wait for a matching lock before weapon/engage input; resume initial weapon activation after delayed lock readback.
- Export observed capacitor through the live security adapter, preserving UNKNOWN.
- Add production-contract regressions. These are offline verification, not proof of a completed live mission.

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
