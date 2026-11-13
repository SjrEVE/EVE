# Product

<!-- impeccable:product-schema 1 -->

## Platform

Native Windows desktop application using Python/Tkinter. (The Impeccable schema has no desktop value; this is the observed platform, not a web app.)

## Users

Primary user is Boss, an experienced EVE Online player and operator of fila-bot. The user wants both to configure a run and to operate/monitor it while it runs.

## Product Purpose

fila-bot's standard operator GUI and launchers focus on Abyssal Deadspace only. Security mission and Distribution/courier implementations remain in the repository as legacy code, but are not offered by the normal UI or packaged launcher. The operator surface configures an Abyss run, monitors its actual phase and any block/error, and stops it safely.

## Positioning

A local operator console for EVE automation. Its value is direct control and truthful visibility into the bot's actual state, not a marketing or game-client replacement. This positioning is inferred from the code and the user's stated workflow.

## Operating Context

The operator has the EVE client and fila-bot on a Windows desktop. The UI is used for both setup and run supervision. The operator is familiar with EVE and expects concise, operationally precise status rather than beginner explanations.

## Capabilities and Constraints

- Modes present in code: Abyss, Security mission, and Distribution; the standard UI/launcher exposes Abyss only, and the other implementations are legacy.
- The public GUI exposes SIM/DRY, maximum session hours, maximum Abyss runs, filament, and the Abyss engine choice (FSM/BT). Legacy CLI mission modes remain internal.
- Existing controls include Start, Pause/Resume, safe Stop, and E-STOP. Their semantics must remain truthful: SIM does not connect to EVE; DRY reads the client without sending input; disabling both can send real clicks/keys and requires explicit confirmation.
- The user selected phase/status/block reason, run limits, and append-only action history as important to keep visible. The user asked for additional research before deciding how to expose the SIM/DRY/E-STOP controls; do not silently remove or weaken their behavior.
- Mission/ship facts must not be fabricated. A blocked/unknown state must be visible and actionable.

## Evidence on Hand

`src/fila_bot/ui.py` (Tkinter controls and display) and `src/fila_bot/ui_model.py` (mode configuration, supervisor state, event log) are the existing implementation. No brand logo or approved image assets were found in the inspected target.

## Product Principles

- Show actual state and phase before decorative detail.
- Keep configuration and live-operation controls accessible without hiding the current run.
- Make safety mode and real-input consequences unmistakable.
- Preserve operational history and explain blocks in plain language.
- Do not imply a mission completed, an action succeeded, or a ship state was read unless the model confirms it.

## Accessibility & Inclusion

No product-specific standard was confirmed. Use readable text contrast and sizes, keyboard-operable controls, visible focus, and state cues that do not rely on color alone.
