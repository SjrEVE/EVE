# Brain integration audit — v1.4.2 test-ready worktree update

> The detailed v1.4.1 notes below are historical where superseded by this current status.

## Current verified status — 2026-11-13

- Source suite: 87 test files, 959 PASS, 0 SKIP, 0 FAIL. Packaged suite: 87 files, 931 PASS, 3 SKIP, 0 FAIL; the skips require local-only UI dumps intentionally excluded from the ZIP.
- Release artifact is `dist/fila-bot-v1.4.2.zip`, label `test-ready-dirty`; it includes tests and the safe profile template, excludes the local character profile and raw dumps, and rewrites packaged `.bat` files to Windows CRLF.
- The real Windows menu launcher was exercised: Abyss SIM completed one bounded run; Security E2E SIM reached `IDLE_DONE` and returned exit 0. Console output is in `logs/live_latest.log`.
- Combat decisions now require the exact overview object ID to match an active target-bar object ID/state before offense. The reader-key changes are source/candidate-level only; the production DLL has not been replaced or validated against the client.
- CLI, `main`, and `mission_cli --go` route live work through the per-client OS lock. `single_instance.py` is now a compatibility shim. GUI live-reader/input starts are deliberately refused until that GUI path has ownership; GUI SIM remains available.

## Still not live-accepted

1. No client-side object-ID/active-target read-back has been verified with the shipped DLL against the current EVE client; the candidate DLL was not deployed.
2. No complete live mission trace at Nonni (accept → travel → objective → return/dock → turn-in/reward) has been captured. SIM/test completion is not live acceptance.
3. In-space module state is partly unreadable; drone health/behavior and module postconditions are not fully verified.
4. Mission tactics are not broadly grounded across mission template, level, faction, and pocket. `SecurityBrain.decide()` remains an unused legacy planner with unsupported action names (`orbit_out`, `cap_save`); production calls only its ranking method. Do not feed the legacy planner's action list to an executor.
5. Live preflight remains for the operator: create a private profile from the example and test against the current client; the distributable intentionally contains no character-specific profile.

---

## Historical v1.4.1 baseline

## Verified changes
- Production FSM now ranks the actual lowercase authorized `hostiles`; it no longer calls a planner using missing `overview`/`drones` keys.
- Ranking has no speculative lock side effects: repeated observations keep the same preferred non-trigger alive until it disappears.
- Brain exceptions produce explicit BLOCKED instead of silently falling back to a potentially wrong target.
- Selected target outside engagement range triggers throttled recall, not simultaneous launch/engage. Numeric legacy meter distances remain supported.
- Supported target-bar observation requires matching lock before weapon or drone-attack input. Initial activation resumes after delayed lock evidence without resetting the re-arm budget.
- Added `NPCState` with required object ID, mission context and freshness gate. This separates same-name NPCs in the process model; it is not yet populated from a live object-ID reader.
- Added `RuntimeClientLock`; callers that still use PID-only `single_instance` are not covered by the new lock.
- Gone Berserk tactics are split L1/L2 by trigger; 25 km is policy, not a game-imposed drone range.

Verification: `python tests/run_all.py`: 85 files, 913 PASS, 0 FAIL; local same-name NPC and stale-state probes pass. Live adapter wiring and postcondition readback remain unverified, so the bot is not complete or autonomous.

Verification: `python tests/run_all.py`: 84 files, 910 PASS, 0 FAIL. `cli --version`: 1.4.1. `git diff --check`: no errors.
Live read-only `cli status`: client connected, DOCKED at Nonni IV - Caldari Navy Assembly Plant; hull, system and active missions UNKNOWN. No combat input sent by this audit.

## Remaining acceptance blockers — NOT complete/autonomous
1. `security_brain.py:decide` remains an experimental legacy planner, NOT a production executor contract. It contains speculative lock/module flags, unsupported action names (`orbit_out`, `cap_save`), and title-only tactics. Production uses only its pure ranking method. Do not wire its action list directly into input.
2. Mission tactics require level/faction/pocket-specific sourced fixtures; current title-only mappings are insufficient for broad mission support.
3. Unknown target-bar fallback still permits historical one-shot offensive inputs. Full fail-closed autonomy requires reliable live lock observation and executor readback, not assuming inputs succeeded.
4. `single_instance.py` PID-file implementation is non-atomic, relative to CWD, and kills recorded live PID without validating identity. Replace with OS-backed exclusive ownership before unattended use.
5. No complete live mission trace after these changes: accept, travel, objective, combat, return, turn-in and observed reward/completion remain unverified.
6. Module readback is incomplete; avoid claims of verified module use or broad abyss readiness.

## Đã bổ sung — chưa bật live
- `NPCState` giữ object ID và mission context; state cũ bị từ chối hành động.
- `RuntimeClientLock` dùng lock OS theo vòng đời process, không dùng PID file.
- Tách tactics Gone Berserk L1/L2 theo trigger.

## Còn thiếu
- Chưa nối object ID từ reader thật vào NPCState.
- Chưa đọc/xác minh active target, module và drone bằng quan sát sau thao tác.
- Chưa có mission live hoàn tất.
- Chưa thay toàn bộ điểm gọi PID legacy bằng runtime lock.
- Chưa xác nhận focus/nhiều client trên desktop.

## Kết luận
Chưa hoàn thiện, chưa autonomous. Không bật vòng combat tự động cho tới khi các blocker trên có bằng chứng thật.
