# Project Discovery AI: node audit and integration analysis

Date: 2026-11-11
Scope: EVE-Master node `86b140b0-c3b3-406c-a744-e55ff66e73b1`; public Project Discovery AI/model options; no in-game submission performed.

## Executive decision

**Use AI for this; the idea is technically well-founded. Do not copy the EVE-Master node's random-rectangle method.** There is a domain-specific model framework, `flowMagic`, trained with expert gating and the EVE Project Discovery annotation corpus. The sensible architecture is `read task image/data → infer candidate cell-population gate(s) → render proposed polygon(s) → confidence/shape checks → (initially) human approval`. The bot must not loop-submit guesses.

## What the EVE-Master node actually declares

Public detail page for `BOT Project Discovery` says: open Project Discovery, resolve task, submit, skip reward/intermediate screens, repeat; default `Tasks to resolve=100`. Its public parameters are padding, random offset from a “perfect rectangle,” and delays. It reports no outputs. The child inventory includes `Project Discovery (single task)` and loop/counter nodes.

The single-task public page (v4) likewise exposes padding, random offset from perfect-rectangle creation, delays, `Create Array of Square Rectangles`, and `Mouse Click on Array of Rectangles`. This is evidence of a geometric click script, **not an AI classifier**. Public detail pages omit graph edges, so don't claim the precise hidden wiring is fully proven; however, no visible node property indicates image inference, cluster detection, accuracy read-back, or confidence handling. Treat it as a fast blind-click implementation, not a sound model to port.

## Domain-specific AI evidence

- Official EVE material says Project Discovery Phase Four uses flow-cytometry plots; players draw polygons around cell clusters and contributions help train AI models. The game uses complex samples and X/Y density-curve hints, so a generic “draw a rectangle” policy misses the actual task.
- The public `semontante/flowMagic` R package is designed for automated bivariate flow-cytometry gating and includes a generalized model trained on EVE player annotations plus an expert-template model. Its README says generalized inference predicts number of gates and gate boundaries, works for abundant single-density peaks, and recommends template gating for complex or rare populations.
- The peer-reviewed paper, first published 2026-10-29, reports 839,199 player accounts, 52,000 plots, and 31,703 consensus annotations after quality control. It reports expert-template agreement of 90% for abundant and 65% for low-abundance populations; generalized model agreement was 78% and 42%, respectively. **The paper explicitly filters likely automated submissions; only about 6% of individual submissions passed its first QC filter.** This is promising for an AI-assisted solver, but argues strongly against unattended game submissions: they may be discarded by QC, and rare/complex samples remain weak. These are agreement figures against standardized reference gates, not guaranteed Project Discovery rewards/accuracy on current game tasks.

## Key integration gap

`flowMagic` consumes event-level flow-cytometry data (or tabular point coordinates), not an EVE screenshot. The game UI exposes rendered scatterplots plus density-curve hints. A usable bot therefore needs a perception bridge: detect plot bounds/axes, recover point/density geometry from pixels (or locate a legal/official data feed if one exists), normalize coordinates, run the model, then map its gate boundary back to UI coordinates. Screenshot pixel coordinates are not raw event data; quantization/overplotting, zoom, UI scaling, and ambiguous low-frequency populations can materially alter a gate.

## Practical next implementation

1. **Offline visual intake**: capture one real Project Discovery task (without submitting); calibrate plot rectangle and density curves; preserve exact screenshot and UI scale.
2. **Human-grounded annotation**: have the owner/experienced player mark expected gate(s) for a small held-out set; keep game submissions out of the validation loop.
3. **Model spike**: port/invoke flowMagic on an available public reference dataset; quantify how its outputs compare with expert/reference labels. Then compare screenshot-reconstructed coordinates against the same raw data where possible.
4. **Decision policy**: only propose polygons when model/data are in-domain and confidence/geometry checks pass. Abstain for multiple peaks, rare populations, unclear density curves, or low image reconstruction quality. Never convert model uncertainty into random clicks.
5. **Human review first**: render candidate polygons as overlay and require explicit approval. Only after a held-out validation and a deliberate owner decision should submit automation be considered.

## Local execution status

- Public `flowMagic` source cloned to `scratch/project_discovery_ai/flowMagic` (34 MB); inspected README, examples, and gating wrapper.
- This host currently has no R, Docker, NumPy, scikit-learn, OpenCV, or `flowutils` available. The repo recommends Docker and states 8 GB free memory minimum; this machine is known weak. **No model was installed, trained, or run.**
- Current EVE capture shows the client docking/agent UI, not a Project Discovery sample. No sample image was available for actual classification; no game input was sent and no data was submitted.
- Do not download the full FRDR benchmark/model archive yet. First confirm its size/runtime costs and whether the screenshot-to-event-data bridge is feasible.

## Source references

- EVE-Master node `86b140b0-c3b3-406c-a744-e55ff66e73b1` and single-task node `2e4685f3-a968-4ff8-ad7c-eaded4e6314f` (public Node Store details).
- Official Project Discovery: https://www.eveonline.com/discovery
- Official Phase Four announcement: https://www.eveonline.com/news/view/project-discovery-phase-four-begins
- flowMagic source: https://github.com/semontante/flowMagic (Apache-2.0 per repository).
- Published study DOI: https://doi.org/10.1002/cyto.a.70074 (first published 2026-10-29).
- Public model/dataset repository referenced by flowMagic README: https://www.frdr-dfdr.ca/repo/dataset/2cfd16c2-b0fd-484e-ad4a-38060e3b3ea9 (check current item/version and download size before fetching).
