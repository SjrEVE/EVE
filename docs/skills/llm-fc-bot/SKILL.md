---
name: llm-fc-bot
description: "Use when building a bot commanded by an LLM (FC pattern)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [bot, architecture, realtime, game, automation, fsm]
---

## When to Use

Load when building any bot where an LLM issues commands to a local reflex script
(game automation, trading bot, realtime agent loop), when designing a text DSL
between an LLM and a runtime, or when asked to extend/audit `D:/fila-bot`.

> `D:/fila-bot` v2 has **no FC/LLM at all** — the bot decides everything itself
> and `bus/` is a log-only event stream. For that repo the current contract is
> `docs/OPERATOR_PROTOCOL.md`; `FC_PROTOCOL.md` is archived design history. The
> FC pattern below still applies to other bots — do not re-introduce an FC bus
> into v2 unless the Boss asks for it.

# LLM-FC Bot Architecture

How to build a bot (game / realtime / automation) where an LLM commands a reflex
script. Current live implementation: `D:/fila-bot` (EVE abyss bot, **v2 = fully
autonomous pure Python**, tactics hardcoded in tables — Boss's cost bar: no paid
LLM in the production loop; vision layer vendored from the Sanderling lineage;
runnable entrypoint `python -m fila_bot.main --mode sim|live [--confirm-input]`;
combat-brain wiring + fail-closed actions). Tests are standalone script files, not
pytest-discoverable — run the whole `tests/test_*.py` loop, never one file.
Domain depth: `references/abyss-world-model.md` (mechanics/DSL),
`references/abyss-ui-tree-attrs.md` (grounded client schema + reader build/dump
recipe), `references/portable-packaging.md` (USB build). Load the UI-tree reference
before touching perception or the vendored DLL.

## Architecture invariants (standing Boss decisions — never violate)

1. **The LLM is never in the input loop.** LLM latency is seconds; the game needs
   millisecond actions. LLM = FC (fleet commander): reads numeric telemetry, issues
   TEXT macro commands, decides on MAYDAY/UNKNOWN. Python script = captain: runs a
   3Hz+ reflex loop, owns every click/keypress, owns safety. Any design that needs
   the LLM to click within a second is wrong — reject it before prototyping.

2. **Learn the world model BEFORE writing the command DSL.** Derive commands and
   phases from primary sources: the official wiki, the official keybind list, and
   real user logs (forums of competing bots list real failure strings). A DSL
   invented from model memory encodes fictional game facts — the sim tests then
   "pass" against a world that does not exist. Concretely: (a) write the real
   phase machine from sources; (b) map every command to a real keybind or UI
   action; (c) encode irreversible mechanics (timers, no-escape zones, entry
   preconditions) as state constraints, not just events.

3. **The safety floor never depends on the LLM.** Escape/survival thresholds are
   evaluated every tick inside the bot; the LLM may change thresholds (SET), never
   disable them. In no-escape contexts (timed instances, one-way zones), the safe
   action is a SURVIVAL mode that keeps fighting — check what "exit" actually does
   in the domain before naming the command; an exit that kills the run is suicide,
   not safety.

4. **Whitelist DSL with REJECT events.** Unknown command or bad arg → REJECT event
   with reason; never a crash, never best-effort interpretation. Keep a
   `NO_ARG_CMDS` set so argless commands skip arg validation cleanly.

5. **Ship a runnable entrypoint, not a library.** Boss judges progress by "does
   the software run standalone without the agent" — an entrypoint like `python
   -m fila_bot.main --mode sim|live` that boots, ticks, and shuts down cleanly
   with the LLM offline. FC is optional by design: no bus writer = bot runs
   defaults + guards. CLI flags first; a local dashboard only when asked.
   When PRESENTING the bot, walk through the turn-on lifecycle in user terms
   ("you press X, the bot then does Y, you watch Z") — architecture diagrams
   and module lists do not answer "what happens when I turn it on", and the
   Boss will ask until he gets that answer. Propose the UI mockup (ASCII, in
   his language) before building any UI; he decides by looking at the mock.

## Workflow (in order)

1. **Research world model** (sources above) → write it as a numbered "World model"
   section at the top of the protocol doc. Every later design decision cites it.
2. **Design the DSL table**: command | arg | real keybind | game note. A command
   with no real keybind/UI mapping is fiction — cut it.
3. **File bus**: 2 JSONL files (`fc_to_bot`, `bot_to_fc`), tail-trimmed ~500
   lines; LLM reads the tail, bot polls incrementally with a byte offset.
4. **Event schema**: STATE = numeric snapshot only (no images — cheap on tokens),
   plus phase events, MAYDAY, SAFE_EXIT with an explicit mode, REJECT.
5. **Sim executor first**: full end-to-end tests run WITHOUT the game client (fake
   state object + recorded actions list). Only after sim green, build the real
   adapter (capture + match + input) behind the same executor interface.
6. **Reuse community components for perception.** Before writing a vision/input
   adapter from zero, survey the game's bot-framework lineage and vendor the working
   one (for EVE: Sanderling / BotLab / eve-memory-reader) — the Boss explicitly
   prefers building on proven community nodes over reinventing them. If the
   canonical repo 404s, search GitHub forks for a surviving one; the fork network
   outlives the original. Wrap the vendor behind the same executor interface as
   the sim so tests never require the vendor to be present.
   When the vendored reader has an empty/stub decoder for an opaque Python type,
   find the upstream project's implementation of that type BEFORE probing raw
   memory: use the GitHub tree API to locate the source file, fetch it raw, and
   read the parsing function completely. Implement from that layout, emit the same
   attribute shape the upstream parser expects, rebuild, and verify on a live
   client dump. Full recipe: `references/abyss-ui-tree-attrs.md`.
7. Ship the protocol doc (`FC_PROTOCOL.md`) as the contract between FC and bot.
8. **Ship a portable Windows build when the Boss wants to test on other
   machines** — embedded Python + .bat launchers + stdlib-only code, zipped to
   USB size. Full recipe (the `._pth` edit, verify-before-zip checklist,
   same-machine rule for memory readers): `references/portable-packaging.md`.
9. **Planning a new mode or end-to-end loop (new activity, UI, "run it properly").**
   - Measure first: run the full test loop, read the existing FSM and the UI-tree doc.
   - Build a table with one row per node or action the mode needs: grounded (dump plus fixture exists) or not, and which modes need it. The bottleneck is almost always ungrounded nodes, not FSM logic. Every ungrounded node costs one live-client dump.
   - Order milestones as follows:
     - (a) Offline supervisor and UI in sim first.
     - (b) One grounding sweep listing the context to stand in, the node to dump, and the fixture name for each node.
     - (c) Shared blocks (travel, agent, inventory).
     - (d) The non-combat mode first, because it forces the shared blocks.
     - (e) No-escape or irreversible modes last.
   - Give each milestone a live acceptance criterion: at least 3 consecutive hands-off cycles on the real client, with screenshots and the events log.
   - Run the tick loop in a supervisor thread. The UI talks to it only through command and event queues, so a hung UI cannot freeze the bot.
   - Define button semantics per context:
     - **Pause** stops new input.
     - **Stop** runs to the nearest safe point. In a no-escape instance that means finishing the run, so warn that the timer keeps running.
     - **E-STOP** releases all held keys and modifiers within one tick and has a hotkey independent of the UI.
   - Keep UI logic in a widget-free model class so it can be tested without a display.
   - Before touching code, ask about the base location, the available ship, and the milestone order, and show the ASCII UI mockup.

## Grounding & Perception Architecture (Batch over Single-Step Probe)

⚠️ **CẤM dò từng click, từng screenshot live ("5 năm không xong"):** Không bao giờ làm
kiểu "gửi 1 click → chụp ảnh → gọi Vision xem trúng đâu → sửa 1 hàm". Cách làm chuẩn:

1. **Catalog-first từ dump thật:** Quét toàn bộ kho dump JSON hiện có (`dumps/ui_catalog.py`)
   kết hợp đối chiếu source cộng đồng (Sanderling/Viir `ParseUserInterface.elm`, eve-master).
   Tập trung vào `_name` ổn định thay vì type (DLL thường decode sai type, nhưng `_name`
   như `selectedItemDock`, `AcceptMission_Button`, `ItemHangar` luôn đúng).
2. **Visual DOM Inspector thay cho Vision API/Screenshot:** Dùng web tool offline
   (`tools/inspector.html`) kéo thả JSON dump để vẽ toàn bộ bounding box trên Canvas,
   hover xem `type`, `_name`, `text`, tọa độ center `(x,y)` ngay lập tức — không tốn token,
   không delay.
3. **Single-pass Perception (`WorldSnapshot`):** Toàn bộ cây UI mỗi tick chỉ parse qua
   1 hàm duy nhất (`parse_world(eye) -> WorldSnapshot`) ra struct tĩnh (docked, station,
   route, selected_buttons, agent_dialog, inventory, connection_lost).
   Test 100% OFFLINE bằng dump fixtures, không cần client mở.
4. **Triệt tiêu Context Menu (Zero-Menu Interaction):** Menu chuột phải EVE trễ 1-2s,
   lưu vết trong UI tree sau click gây spam, và submenu dễ trượt. Thay bằng:
   - **Native Hotkeys:** Giữ `D` + Click (Dock/Jump stargate, station, route marker);
     Giữ `S` + Click (Warp to 0); Giữ `Ctrl` + Click (Lock).
   - **`SelectedItemButton`:** Click object 1 lần → cụm nút cố định hiện ở góc trên
     (`selectedItemDock`, `selectedItemJump` tại (914,148)), click 1 hit là ăn ngay.
5. **Kéo thả hàng (Inventory Drag-Drop):** Target thả là `topCont_<Hangar>` trên cây
   `TreeViewEntryWithTag` bên trái (vùng tĩnh 160x24px, trúng 100%), không kéo vào khoảng trống.
6. **In-Process Test Runner:** Gom toàn bộ test suite vào 1 runner Python (`tests/run_all.py`),
   chạy 360+ tests trong <10s thay vì chạy bash script lặp tốn 2 phút.
7. **E-STOP khi mất kết nối:** Modal `MessageBox` ("Connection Lost" với nút Quit
   `ok_dialog_button`) phải bật cờ dừng khẩn cấp ngay; tuyệt đối không click Quit hay đoán pass login lại.
8. **Phát hiện người can thiệp:** So sánh state trước khi click; nếu state đổi bất thường
   khi bot không gửi lệnh → NGỪNG BẤM, hỏi Boss qua `clarify`.

Click pitfalls (each cost a live retry):
- **A window on top eats the click.** Large dialogs (agent conversation) cover the
  info panel; `execute` still reports ok. Close covering windows via their
  `CloseButtonIcon` (never ESC — it opens Settings) before clicking under them.
- **Coordinates move while layout settles** (right after undock/session change):
  re-read the node position in the same tick you click, never reuse one from a
  previous read.
- **A clicked menu stays in the tree for seconds.** After clicking an entry,
  ignore menus for a cool-down (dismiss once, never re-click), and end the
  cool-down early on observed progress (system name change, warp) — a pure timer
  never expires in a sim that ticks faster than real time.
- **A menu missing the expected entry is often transient** (mid-warp the station
  menu shows only Track/Show Info): dismiss and retry a bounded number of times
  before BLOCKED.
- **Modal "Connection Lost" `MessageBox` has a single Quit button.** Any modal
  `MessageBox` the bot does not recognize = E-STOP; never click its button, never
  re-login (needs the Boss's credentials).

## Resuming from a handoff bundle

- **Upstream GitHub beats the bundle.** A handoff zip is a snapshot; the repo it
  came from is the source of truth and may be a whole generation ahead (docs,
  architecture). After checking the bundle, `git ls-remote`/clone the upstream
  (`https://github.com/SjrEVE/EVE`) into a fresh dir, `diff -rq` against the
  local tree, then swap: back up the old dir (`mv fila-bot fila-bot.bak-handoff`),
  move the clone into place, and re-run the tests. Never report the bundle as
  "current" without this check — the Boss will say "pull github về".
- **A fresh clone fails `dll_built_present` until `vendor/` is restored.**
  `.gitignore` excludes `vendor/`, so `vendor/eve-memory-reader/x64/Release/
  eve-memory-reader.dll` is absent after cloning. Copy the tracked binary from
  `dist/fila-bot-portable/src/eve-memory-reader.dll` into the vendor path and
  verify its SHA256 against `dist/fila-bot-portable/dll-source/PROVENANCE.md`
  before running the suite.
- **Diff the bundled tree against the local one before copying.** The bundle is
  often older than the work the target already has: after reading HANDOFF.md,
  `diff -rq` the bundled `fila-bot/` against `D:/fila-bot` ignoring `__pycache__`;
  identical sources plus a local-only `vendor/` means it is already applied.
  Report the diff — never re-copy over newer local work.
- **The suite is a set of standalone script files; `test_all.py` is only one.**
  Running only `python tests/test_all.py` exits 0 while the rest never runs, so a
  handoff's PASS count looks wrong and a real regression hides. Loop over every
  `tests/test_*.py`, sum `^\[PASS\]` lines, and require exit 0 per file
  (top-level asserts mean pytest discovery collects nothing — the loop is the
  runner). Never hardcode the expected total in docs or skills — it changes with
  every added test.
- **Items marked "waiting on the client" cannot be closed offline.** UI-node
  mapping (`eye.py` attr names) needs a real `ui_dump.json` from a running
  client; writing it ahead of the dump ships guesses that fail by returning
  empty. State the blocker and offer the client-free subset instead of claiming
  progress.
- **Unexpected new commits after a disconnect are usually your own lost session.**
  If `main` gained commits under the Boss's identity (or there is an uncommitted
  half-written file) that you do not remember, check `git reflog` timestamps and
  `session_search` for the previous session before calling it a concurrent agent
  and stalling with a menu of options. A running `codex.exe` app-server is not
  proof of authorship. Treat the dangling file as your unfinished work: read it,
  wire it in, run the full test loop, commit.
- Profile-level rules for the bundle's `config.yaml` / `auth.json` live in the
  `hermes-agent` skill (its profile-handoff reference) — load it before touching
  a transferred profile.

## Pitfalls

- **UNKNOWN must remember where it came from.** Track a prev-phase (last
  non-UNKNOWN phase) updated at the TOP of each tick; safety decisions need it
  (no-escape zone vs not). Update it only in the else-branch and a direct jump
  into UNKNOWN carries no context.
- **Test sequences must match reality.** If the real flow is FIGHT→UNKNOWN, test
  FIGHT (one tick, so prev-phase records) then UNKNOWN. Testing DOCKED→UNKNOWN
  validates a path that never happens and hides the context bug.
- **Phase transitions must be EYE-VERIFIED, never timer-confirmed.** After a
  timed spool-up (filament, warp, dialog), do NOT auto-confirm when the timer
  elapses — a timer says nothing about whether the client actually transitioned;
  bot can sit outside thinking it is in Room 1. Confirm only when perception
  sees the evidence (confirm dialog present, or post-transition signal); on
  timeout without evidence → MAYDAY + safe_exit (fail-closed). In sim, expose
  an explicit `sim_confirm` flag so tests can drive both branches.
- **Learn from other bots' wrecks**: study competitor bot changelogs/forums for
  their published bugs and user ship losses; turn each death into a GUARD class
  (stateless check → safe action + event) evaluated BEFORE FSM decisions every
  tick. See D:/fila-bot/src/fila_bot/guards.py (9 guards from AbyssBot changelog
  v1.019/v1.05x + forum t.728 + reddit losses). Guards are cheap (pure state
  checks) and catch what FSM logic alone misses: empty overview, action loops,
  drones-out-at-gate, cloud speed spikes, cap starvation, sensor damping,
  loot greed, wrong filament, drifting without maneuver.
- **Perception attr names are code until grounded.** Extractors that read client
  UI-tree attributes (HP ratios, overview entries, button `_name`s) must fail
  visibly — raise or return `None` — until verified against a real client UI-tree
  JSON dump. Guessed attr names pass fake-tree tests and then silently return empty
  on the real client — the failure mode is absence, not an exception. Community
  docs give semantics (colour percent keys, pmark alpha rule), not live node types:
  see `references/abyss-ui-tree-attrs.md` for the grounded schema.
- **Glue contract: refresh → tick → process_actions.** The real executor reads
  the eye snapshot BEFORE each tick and translates the bot's recorded actions
  AFTER it; the executor holds the bus and emits INPUT/FAIL events itself.
  Ship that sequence as the ONLY integration contract — tests that tick the
  bot directly without calling the executor's refresh/process steps validate
  a sequence that never runs in production.
- **Fail closed, never skip silently.** An action whose UI node is not yet
  grounded emits an explicit FAIL event with reason — a silent skip makes the
  bot (and the FC reading telemetry) believe the step happened. Same for
  movement without a verified target: orbit/approach into "the first overview
  entry" is blind clicking; require the locked-target name to match the entry
  text, and reject when there is no lock and no explicit label. Same for numeric
  telemetry: an unreadable sensor returns `None` and its guard emits a visible
  blind-warning once; a plausible default silently disables that guard.
- **Wire knowledge modules into the tick loop.** A rats/rooms/playbook library
  with green tests but no caller in `tick()` is dead code — an external review
  will catch it as "logic lying dead". After building any domain module, add
  the tick-loop caller in the same change and prove it with a test that shows
  the module's output becoming bot actions.
- **Modifier+click needs hold steps, not a combo.** Keybinds like Ctrl+click
  (lock target) cannot be expressed as a combo — emit three steps: keydown
  modifier, click, keyup modifier. A combo that taps the modifier after a
  click performs a different game action entirely (approach instead of lock).
- **Self-assessment must be layered and honest.** When asked "can it play yet
  / how good is it", score each layer (knowledge / harness / perception /
  actuation / autonomous combat) with what was actually exercised, not what
  is designed; say "not yet flying" plainly if no real client run happened.
  Overconfidence gets called out and erodes trust in the real numbers.
- **Shared fakes live in a helper module.** Test files with top-level asserts
  exit at import, so `from test_x import Fake` re-runs the entire file and
  aborts the importing test — put reusable fakes (FakeEye) in a helper
  (`tests/fake_eye.py`) and import from there.
- **Schemas describe text, not pixels.** Knowing UI-tree attr names from
  community docs is NOT having seen the client; when the user asks what the UI
  looks like, state exactly that distinction. Request screenshots early — they
  are cheap grounding and a client redesign (radial HUD replacing legacy
  gauges) invalidates community attr names long before any dump does.

- **Grep every test file for retired schema symbols after changing a perception
  extractor.** Hand-rolled fakes and older test files reimplement the previous node
  types; they pass in the shard you ran and fail in the ones you did not. Search
  the retired names across `tests/` and update every fake in the same change.
- **Shared state in script-style test files leaks into later sections.** When a new
  guard trips on leftover state from an earlier test (timers, phases, counters),
  reset that state at the start of the next section — do not weaken the guard to
  make the old test pass.
- **"State unchanged" watchdogs need a phase gate.** Idle/docked states repeat by
  design; a loop detector that fires on repeated state produces MAYDAY storms
  outside the instance. Restrict it to active phases and reset its counters when
  idle.
- **UI must refuse LIVE for modes whose nodes are not grounded, but allow SIM.**
  The supervisor factory raises a clear `ModeUnavailable("<mode> LIVE: chưa ground
  G…")` for live, while SIM wires the mode to a sim world so START works. A mode
  that silently runs live against ungrounded readers clicks blind; a mode that is
  refused even in SIM hides finished FSM work from the Boss.
- **A live dry run is the acceptance test.** Fake trees prove schema, not decoding.
  Boot `--mode live` without `--confirm-input`, then read the bus outbox for a
  STATE carrying real numeric fields and no FAIL/MAYDAY storm. If a manipulation
  meant to change state (warp, module activation) did not visibly fire, report the
  measurement as static-only — never claim dynamic verification.

## Skill safety
- Game automation on live official servers usually breaks the game's EULA
  (botting bans are enforcement waves, multi-account, asset confiscation). Default
  to the game's TEST server with a throwaway account and state the EULA risk in the
  plan. The Boss owns the risk decision: if he authorizes a different server (e.g.
  the test server is schedule-locked) with a fresh throwaway account, follow it —
  do not refuse, re-warn, or stall the work; dry-input mode stays the default for
  grounding runs until he says to press keys.
- Memory reading (read-only, không inject/ghi): không để dấu vết trong log
  client/server → không truy ngược được; EVE không có kernel anti-cheat nên
  phát hiện chủ yếu bằng HÀNH VI. Giữ dry-input mặc định khi ground perception.
- Vendor code đáng dùng: eve-memory-reader (C DLL, fork chengyus; build
  `bash dll-source/build_mingw.sh` hoặc MSBuild Release x64) + Sanderling source
  (ParseUserInterface.elm = mỏ vàng SEMANTICS attrs; `EveOnline64.cs` = layout
  object Python). Clone vendor vào D:/fila-bot/vendor/, không copy code vendor
  vào src. Source DLL đã fix stub float + decode PyColor — xem PROVENANCE.md.
