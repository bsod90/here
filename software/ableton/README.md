# HERE — Max for Live MIDI Effect

`HERE.amxd` is a Max for Live MIDI Effect that drives the HERE LED
installation from Ableton Live. Drop it on a MIDI track, play notes,
and the Pi orchestrator (`here.local:9000`) renders the matching
animation events. Every knob is automatable so you can paint expand /
contract / palette swap / shimmer envelopes directly into clip
automation lanes.

## What ships in this folder

```
build_patcher.py     # generates HERE.maxpat from the metadata JSONs
build_amxd.py        # wraps HERE.maxpat into HERE.amxd (uses Live's blank MIDI Effect template)
gen_metadata.py      # exports here_events.json + here_knobs.json from the orchestrator's source-of-truth
here.js              # v8 logic — MIDI parsing, OSC formatting, sustain choke, knob dedup
here_events.json     # generated: 40 pad mappings (pitch 36..75 → event names)
here_knobs.json      # generated: 11 master + 10 physics + 18 per-ring dial specs
HERE.maxpat          # generated patcher (boxed UI + wiring)
HERE.amxd            # generated device (the file Live loads)
setup.sh             # build + symlink helper
tests/               # Jest tests for here.js + Python tests for metadata sync
README.md            # this file
```

## Install / iterate

```bash
./setup.sh           # links the .amxd into ~/Music/Ableton/User Library/Presets/MIDI Effects/HERE/
./setup.sh rebuild   # regenerates JSONs + .maxpat + .amxd, then re-links
./setup.sh unlink    # removes the symlink (leaves repo files alone)
```

The link target is `~/Music/Ableton/User Library/Presets/MIDI Effects/HERE/HERE.amxd`.
After `./setup.sh`, the device appears in Live's browser under
`User Library → MIDI Effects → HERE → HERE`.

Drop it on a MIDI track BEFORE any instrument. Play MIDI notes (or run
a clip with notes in the C1..D#4 range), and OSC flows to the Pi.

## Wire protocol (M4L → Pi)

All over UDP to `here.local:9000`. Receiver: `software/orchestrator/osc_input.py`.

```
/here/scene/note_on/<pitch>     <velocity:float>     # fires NOTE_LANES[pitch - 36]
/here/scene/note_off/<pitch>                          # releases sustain
/here/scene/synth/<key>         <value:float>         # master knob (radius_min, brightness, ...)
/here/scene/physics/<key>       <value:float>         # physics knob (damping, bounce, ...)
/here/scene/oval/<i>/<key>      <value:float>         # per-ring knob (oval_blur_2, oval_skew_0, ...)
/here/scene/palette             <int>                 # immediate palette swap
/here/scene/bpm                 <bpm:float>           # set tempo
/here/scene/beat                                      # tap-sync
```

Pitch 36 (C1) → first event (Expand) — Drum-Rack convention. Same list
as `NOTE_LANES` in `software/orchestrator/scene/animations/synth.py`.

## Sources of truth

| What | Where | How to regenerate |
|---|---|---|
| Pad pitch → event mapping | `SynthAnimation.NOTE_LANES` in `synth.py` | `./gen_metadata.py` |
| Knob list (master/physics/oval) | `gen_metadata.py` MASTER_KNOBS / PHYSICS_KNOBS / OVAL_KNOBS | edit + `./gen_metadata.py` |
| Patcher layout | `build_patcher.py` | `./build_patcher.py > HERE.maxpat` |
| OSC wire format | `here.js` `format*` functions | hand-edit |

If you change `NOTE_LANES` upstream, `test_metadata_sync.py` will fail
until you re-run `./gen_metadata.py`. CI runs both the Python and Jest
suites.

## Testing

```bash
# Jest tests for here.js (pure logic — MIDI/OSC formatting, sustain choke, dedup)
cd tests && npm install && npx jest

# Python tests for metadata sync (catches "added an event but forgot to regenerate JSON")
.venv/bin/python -m unittest tests.test_metadata_sync -v

# Pi-side OSC handler tests (note_on, knobs, sustain release)
cd ../orchestrator && .venv/bin/python -m unittest tests.test_osc_input -v
```

## Caveats

- **Editing in Max breaks the symlink.** Live's "Edit" button opens
  the patcher in Max; ⌘S in Max writes a real file, dropping the
  symlink. Re-run `./setup.sh` to restore it.
- **The auto-generated layout is functional, not pretty.** Layout
  tweaks (alignment, sizing, tab grouping) are easier in Max than in
  `build_patcher.py`. If you do this, commit the edited `.maxpat` and
  stop regenerating it from the script — or merge improvements back
  into the generator.
- **Max for Live is bundled with Live 12.** No separate Max install
  needed for use. Edit-in-Max requires Live's bundled Max.
