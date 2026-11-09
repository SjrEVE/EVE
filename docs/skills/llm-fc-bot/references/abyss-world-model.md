# EVE Abyss World Model (distilled)

Sources: wiki.eveuniversity.org/Abyssal_Deadspace + CCP keybind docs + real failure
logs from competing bots' forums. Verify against the wiki before coding anything
new against it. Implementation: `D:/fila-bot` (v2 autonomous; contract `docs/OPERATOR_PROTOCOL.md`).

## Mechanics that constrain the bot FSM
- 3 pockets/rooms, 20-minute total timer; timeout destroys ship AND pod. Budget
  < 6:40 per room.
- Gate to the next room opens only when the room is fully cleared; enemies sit on
  the gate (own spawn 35-70 km out).
- NO escape from inside: no warp-out, no cloak, no fleet assist, no local chat.
  "Safe exit" inside = SURVIVAL mode (tank + keep killing), never a warp.
- Red danger boundary destroys the ship on contact — keep orbit inside the pocket.
- Weather (Dark/Electrical/Exotic/Firestorm/Gamma) penalizes BOTH sides; +50%
  bonus is constant. Parse weather from the filament name before activating; FC
  picks ammo/modules from it.
- Entry preconditions: >= 1000 km from gates/stations/depots, not in deadspace, no
  logoff timer. No filament in cargo -> FILA_MISSING event, no retry loop.
- Filament spool-up 15 s + confirmation dialog -> wait out, confirm once.
- Bioadaptive/Biocombinative caches always drop loot — loot before leaving.

## Keybinds (defaults; keyboard-only play is viable)
Q approach | W orbit | E keep-at-range | D dock/jump | S warp-to | A align
Ctrl+click (overview) lock target | F1-F8 module slots | Ctrl+Space stop ship
Alt+Space focus overview (enables arrow-key targeting without mouse)

## fila-bot command DSL (v1, 21 commands)
TARGET nearest|0-11, APPROACH, ORBIT <m>, KEEP_RANGE <m>, ACTIVATE/DEACTIVATE 1-8,
RELOAD, STOP, SPEED 0-100, GATE, DOCK, UNDOCK, JUMP <dest>, FILA <name>, CONFIRM,
LOOT, SET <param value>, SET_PHASE <*_CLEARED>, HOLD, ABORT, STATUS.
Params: escape_hp 0.25, unknown_timeout 45s, orbit_default 2500m, humanize,
tick_interval 0.3s, warn_timer_left 300s.
Phases: DOCKED -> TRAVEL_ENTRY -> FILA_SPOOL -> ROOM1..3_FIGHT -> *_CLEARED ->
GATE_TRANSIT -> EXIT -> LOOT -> WARP_HOME -> DOCKED (+ SURVIVAL, UNKNOWN).

## Vision layer (vendored memory reading)

- Route chosen: memory reading (UI-tree JSON via `eve-memory-reader.dll`, Sanderling
  lineage) over screenshot+template matching — theme/resolution independent, lower
  CPU, and elements carry exact coordinates for clicking (no pixel guessing).
- Vendor: `D:/fila-bot/vendor/eve-memory-reader`, cloned from the
  `chengyus/eve-memory-reader` fork (the `jamesalbert` original is gone — forks
  survive). Derived from Arcitectus/Sanderling; Viir/bots (BotLab) documents the
  event-loop architecture.
- Build: `bash dist/fila-bot-portable/dll-source/build_mingw.sh` (mingw-w64) or
  MSBuild `eve-memory-reader.sln /p:Configuration=Release /p:Platform=x64`.
  ctypes exports: initialize, read_ui_trees, get_ui_json, free_ui_json, cleanup.
  Verify SHA256 against `dll-source/PROVENANCE.md`; the tracked binary lives in
  `dist/fila-bot-portable/src/`, the runtime copy in `vendor/...`. The test vcxproj
  may fail on a missing include path — harmless; only the DLL project matters.
- Wrapper `src/fila_bot/eye.py`: `refresh()` → tree dict, `find(type, contains,
  **attrs)`, `center_xy(node)` (local) / `abs_center(node)` (accumulated real
  click coordinates). It reads the grounded Photon-HUD schema — see
  `references/abyss-ui-tree-attrs.md`. Unreadable numeric sensors return `None`,
  never a guessed default.
- Legacy node names from the vendor's mining bot (`selectedItemLockTarget`,
  `Damaged` Label) are ungrounded — the live-client table in
  `references/abyss-ui-tree-attrs.md` wins. Keep upstream *semantics*, not node
  type names; verify any new attr on a real dump first.
