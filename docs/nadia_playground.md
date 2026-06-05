# Nadia's Playground

A deliberately **isolated enclave** in the HERE app where Nadia — a
non-technical collaborator — can experiment with breathing-meditation
animation ideas without risking the rest of the app.

## What it is
- A separate **mode** (`playground`) with its own **admin tab** ("Playground").
- Nadia works by **talking to Claude**: she describes animation ideas in
  her own words; Claude implements them as new playground animations and
  surfaces them as **trigger buttons** + new **lanes** on her sequencer.
- She's building a **breathing sequence** for a guided meditation.

## What it must do
1. **Seed content**: start with copies of the current **standby** and the
   **circle/breathing** animation so she has something to play with.
2. **Ocean toggle**: turn the ocean backdrop audio on/off from her page.
3. **Recording**: upload her own breathing-session **mp3/wav** and trigger
   it (play/stop), optionally synced with the sequence.
4. **Timeline sequencer** (borrowed from the MIDI piano-roll, simplified):
   - Plays over a **real timeline in SECONDS** (not bars/BPM).
   - She draws **rectangles** = which animation plays, when, for how long.
   - **Play** the sequence with or without the meditation recording.
   - Remembers the sequence (persisted); has **quick cleanup** buttons.
5. **New animations on request**: Claude adds animation implementations +
   trigger buttons + sequencer lanes as Nadia describes ideas.
6. **Everything persists** across restarts (settings + sequence).

## Design rules (READ BEFORE EDITING)
- **Isolation**: keep playground code in its own module(s) /
  `config.playground` namespace / `/api/playground/*` routes / its own
  admin tab + JS. Changes here MUST NOT affect breathing/standby/scene.
- **No major refactors** of the shared engine.
- **Optimize for a non-technical user**: big obvious controls, forgiving
  defaults, clear labels, hard to break.
- New playground animations register in the playground animation registry
  (so they auto-appear as trigger buttons + sequencer lanes).

(Implementation pointers live in the module docstrings; this file is the
"what & why" so the intent survives.)
