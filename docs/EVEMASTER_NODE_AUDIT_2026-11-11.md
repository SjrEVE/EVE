# EVE-Master Node audit — 2026-11-11

## Scope and method

- Read the public Node Store listing HTML: 1,046,016 bytes, 1,002 anchors, **984 unique node detail pages**.
- Retrieved and reviewed a focused batch of public node detail pages covering fit/modules, objective approach, waits, UI discovery, and reusable composite flows. Detail pages expose description, input/output properties, version and a list of internal node types/versions. They do **not** expose the actual graph wiring or executable node payload.
- Sources are linked by exact Node Store IDs below. No account/login, paywall, private endpoint, or access-control bypass was used.
- Result: enough useful design patterns were found; did not download the full EVE-Master application for REA. This audit is based on the public pages and declared internal-node inventories, **not** reverse-engineering the closed executable and not a claim that every child connection was inspected.

## Highest-value findings

### 1. Fit-specific in-space preparation

**Module - In Space Preparation** — `b284f0e3-3b9f-4f11-a96b-baf967424bf1`, v4, public, 1,384 downloads.

Its declared inputs separate:
- `Slots - Always Active (if not in Warp)`
- `Slots - Always Active`
- low shield / armor / structure thresholds and corresponding slot lists
- drone count, optional probe scanner and hangar setup.

Its internal-node inventory includes `Activate slots by name` (v13), local state variables, flow splits, and `Message Alert Last Error`. This is a much better pattern for fila-bot than one hard-coded “turn on AB”: configure the ship's actual fitted module names by state/phase, then report errors. **Do not copy the default thresholds or slot names blindly**; they are user-configurable and not a verified Gila fit mapping.

### 2. Idempotent slot activation by name

**Activate slots by name** — `4f770117-d13b-440d-9669-cb009600b8ab`, v13, public, 8,186 downloads.

Inputs: `Slots` as names such as `MediumSlot1,MediumSlot2`; optional `Rescan`. Its 14-node inventory includes `UI.Find Slot by Name (HUD)`, `UI.Find Slot Glow by Name (HUD)`, `UI.Find Slot Busy by Name (HUD)`, optional `EVE UI Scan`, `Mouse Click`, and `Message Alert Last Error`.

**Portable design lesson:** address modules by configured HUD slot names, inspect module state/glow and busy state, click only when a state transition is needed, and surface a named error. The public page lists components but not their edges, so exact click/guard ordering remains unverified until the official node artifact or a live trace is available.

Related small nodes:
- **ABYSS: Check active slots by name** — `3d8d7673-73c1-466f-a114-4db86893ee33`, v2, public/no-Pro; accepts a slot-name list and uses slot lookup/glow plus array iteration.
- **Wait while Slots active** — `56b65d29-507c-410b-a90a-5021cfabd5ed`, v1, public/no-Pro; loops over configured slot names and checks HUD glow. This is the useful “wait until observed active” complement to issuing a toggle.
- **ABYSS: Activate Missiles** — `a3649653-8f7d-43ff-9f23-a44c58249945`, v4; composed with a `Get Missiles Status` child and a flow split. Supports state-check-then-act as a pattern, though exact graph edges are not visible in the page.

### 3. Trigger modules on ship state, not on mission phase guesses

**BOT Autopilot - Overview + Slots** — `895d65c8-9e59-4e89-9a65-7445b7502738`, v63, public, 1,930 downloads.

The description explicitly offers independent activation/deactivation lists for **warp**, **approaching**, **scrambled/disrupted**, and **bubble** states. It recommends fit-specific slot lists (examples mention propulsion and active tank modules). This directly addresses “entered mission grid with modules off”: create a node reacting to the ship's observed maneuver/conditions, not a one-time assumption immediately after arriving. Keep activation and deactivation policies separate and verify the HUD state after issuing input.

### 4. Wait for state evidence instead of timing/click counters

**Wait while ship indicator** — `c4de2fac-3564-4074-8952-8c5c4e320503`, v16, public, 8,404 downloads.

Inputs include substring (default `JUMP`), optional rescan, and optional neutral-abort; output `Aborted`. Internal-node inventory includes repeated UI scan, string normalization/contains, flow splits, local state, and explicit success/error exits. This matches a reusable `WaitForEvidence(predicate, timeout)` node better than “click three times then BLOCKED.” Port the predicate, bounded wait, and readable failure; do not copy the unrelated neutral policy without owner approval.

### 5. Approach by target name, not “first object”

**ABYSS: Approach by Name** — `ab86eb98-bdee-497d-851e-408efbf5e06b`, v2, public, 1,017 downloads.

Description: approaches a target in overview by name; configured input `Value` defaults to `Bioadaptive Cache`. Internal inventory has UI-array retrieval, array index access, UI tree data, a flow split, and a combined key+mouse click node. That is a useful shape for `FindNamedObjective → Approach → WaitForObjectiveChange`. For the Poke mission, resolve exact `Fire Cloud`; never copy “take first overview target” because it can select a Gallente exercise vessel or another irrelevant object.

### 6. Error and workflow instrumentation

Useful reusable building blocks also present in the audit batch:
- `Message Alert Last Error` child appears in module composites rather than silently swallowing failures.
- `EVE UI Scan (optional)` is reused by wait and module composites, suggesting a deliberate rescan step when cached UI evidence is stale.
- Small nodes (`String Split+Trim`, `String Is Empty`, `String Is Not Empty`, `Flow Split`, `Loop Array`) make parsing and iteration explicit rather than hiding all behavior in a large opaque procedure.

## Project Discovery: promising income idea, but not yet safe to automate

Node **BOT Project Discovery** — `86b140b0-c3b3-406c-a744-e55ff66e73b1`, v1, public, Pro=Yes; current page lists 522 downloads. The public description says it opens Project Discovery, draws/submits each task, skips intermediate/reward screens, and loops; default task count is 100. Inputs include `Padding`, random offset, and fixed delays. Its 14-child inventory contains the single-task node, loop/counter/time nodes, but the public page does not expose the graph edges or show how it derives valid scientific classifications.

The single-task node's declared children include `Create Array of Square Rectangles` and `Mouse Click on Array of Rectangles`, with random offset and padding. This is a warning: metadata alone does not establish that submitted regions are scientifically valid. Project Discovery Phase Four is a citizen-science activity analyzing immune-system/flow-cytometry data. Do not build a bot that submits arbitrary/random labels merely to farm ISK; that can lower accuracy and contaminate research data. First inspect the full official node graph and test whether the geometry is derived from the visible sample by a valid rule, not random clicks.

EVE University currently lists up to 99,000 ISK per submission at 99% accuracy, a five-submission/minute limit, and historical per-character daily caps of 100 Alpha / 200 Omega (9.9M / 19.8M ISK). Its page itself warns it needs an update for Phase Four, so treat those caps as **unverified current rules**, not guaranteed earnings. The node's default `Tasks to resolve=100` is a task-loop count, not proof the game will accept 100 valid samples or pay the maximum.

**Decision: RESEARCH, do not integrate as an unattended earning mode yet.** Next inspect the official `Project Discovery (single task)` graph via the documented CLI if authorized, compare outputs against real game feedback/accuracy, and preserve human review. If it cannot produce evidence-based classifications, reject the auto-submit behavior; at most build a human-supervised UI helper that waits for explicit human approval before Submit.

## Apply to fila-bot (proposal derived from the audit)

First port a vertical slice, not the whole app:

```text
Reactive root (re-evaluate every snapshot)
├─ Emergency / connection-loss guard
├─ If docked: mission acceptance / undock nodes
├─ In-space preparation
│  ├─ resolve configured Gila module slots from verified fit data
│  ├─ EnsureModuleActive(slot) (read → act if needed → wait/read back)
│  └─ BLOCKED with slot-specific reason if state remains UNKNOWN/inactive
├─ Travel route → mission location → gate
├─ Objective branch from live mission-panel evidence
│  ├─ approach: find exact objective target → approach → wait for objective read-back
│  └─ combat: target policy + separately authorized combat nodes
└─ return → dock → turn-in → read-back
```

Acceptance checks before a live mission:
1. Real dump maps each configured Gila module name to HUD slot and `isActive`/glow observation; unknown state is not coerced to false/true.
2. Inactive slot produces one activation action; already-active slot produces none; busy slot waits; absent/unknown slot blocks with its name.
3. Trigger states (warp/approach/hostile pocket) exercise the intended slot sets without enabling every module indiscriminately.
4. Approach objective selects `Fire Cloud` by exact configured name, does not fire, and only marks success after mission-panel objective evidence changes.
5. Existing mission suite stays green; then a supervised live trace verifies module read-back before entering the pocket.

## Download / REA decision

The public Node Store pages give node metadata and child-node inventories, but **not graph connections or source payloads**. An official CLI command is displayed on each page (`EVE-Master node download <ID>`); obtaining complete graph data should use that supported download path, not scrape hidden endpoints. This batch already yielded directly applicable patterns, so the “if nothing useful, download the whole application and REA it” fallback was **not triggered**. If full wiring inspection is required, next safe step is to retrieve the official downloadable CLI/package and check whether public nodes can be downloaded without account/pro access; only then decide whether REA/Ghidra on the app binary is justified.
