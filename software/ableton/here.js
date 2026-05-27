/* here.js — v8 logic for the HERE Max for Live device.
 *
 * Loaded inside Max via `v8 here.js`. Receives Max messages from the
 * patcher and emits OSC-shaped lists (address + args) on outlet 0,
 * which the patcher pipes into a `udpsend host port` object.
 *
 * Wire protocol (Max → JS, all incoming):
 *   note    <pitch> <vel>         → /here/scene/note_on/<pitch>  <vel>
 *   noteoff <pitch>               → /here/scene/note_off/<pitch>
 *   knob master  <key> <val>      → /here/scene/synth/<key>      <val>
 *   knob physics <key> <val>      → /here/scene/physics/<key>    <val>
 *   knob oval <i> <key> <val>     → /here/scene/oval/<i>/<key>   <val>
 *   bpm <val>                     → /here/scene/bpm              <val>
 *   tap                           → /here/scene/beat
 *   palette <n>                   → /here/scene/palette          <n>
 *
 * Outgoing (JS → patcher), via outlet 0:
 *   <address> <arg1> [<arg2> ...]   — a Max list, ready for udpsend.
 *
 * Sustain choke: if `note <p> <v>` fires twice for the same pitch
 * without a `noteoff` between, we emit a synthetic noteoff first so
 * the Pi's router can free the prior sustain modulator. Mirrors the
 * sequencer's "choked retrigger" behaviour.
 *
 * Throttling: per-knob dedup. Identical consecutive values are dropped.
 * For very rapid changes, pair `change` + `speedlim` in the patcher;
 * the JS doesn't try to rate-limit beyond plain dedup.
 *
 * Testability: when imported under Node (typeof outlet === 'undefined'),
 * the Max handlers are not attached. The pure functions
 * (formatNoteOn / formatNoteOff / formatKnob / chokeIfActive) are
 * exported via module.exports so Jest can call them directly.
 */

// ── State (only meaningful inside Max — Node tests construct fresh
//     instances) ────────────────────────────────────────────────
function createState() {
    return {
        // Set of pitches we believe are currently "on" — used to emit
        // a synthetic noteoff when a note_on retriggers.
        activeNotes: new Set(),
        // Cache last-sent knob values for dedup. Keyed by full OSC addr.
        lastKnob: new Map(),
    };
}

// ── Address builders (pure) ─────────────────────────────────────
function formatNoteOn(pitch, velocity) {
    if (!Number.isInteger(pitch) || pitch < 0 || pitch > 127) return null;
    const vel = clamp01(velocity == null ? 1.0 : Number(velocity));
    return ['/here/scene/note_on/' + pitch, vel];
}

function formatNoteOff(pitch) {
    if (!Number.isInteger(pitch) || pitch < 0 || pitch > 127) return null;
    return ['/here/scene/note_off/' + pitch];
}

function formatKnob(category, keyOrIndex, keyOrVal, valOrUndef) {
    // category: 'master' | 'physics' | 'oval'
    // master/physics: (category, key, val)
    // oval:           ('oval', index, key, val)
    if (category === 'oval') {
        const i = Number(keyOrIndex);
        const key = String(keyOrVal);
        const val = Number(valOrUndef);
        if (!Number.isInteger(i) || i < 0 || i > 2) return null;
        if (!key || !/^[a-z_]+$/.test(key)) return null;
        if (!Number.isFinite(val)) return null;
        return ['/here/scene/oval/' + i + '/' + key, val];
    }
    const prefix = category === 'master' ? 'synth'
                 : category === 'physics' ? 'physics'
                 : null;
    if (prefix === null) return null;
    const key = String(keyOrIndex);
    const val = Number(keyOrVal);
    if (!key || !/^[a-z_]+$/.test(key)) return null;
    if (!Number.isFinite(val)) return null;
    return ['/here/scene/' + prefix + '/' + key, val];
}

function formatBpm(bpm) {
    const v = Number(bpm);
    if (!Number.isFinite(v) || v <= 0) return null;
    return ['/here/scene/bpm', v];
}

function formatTap() {
    return ['/here/scene/beat'];
}

function formatPalette(n) {
    const v = Number(n);
    if (!Number.isInteger(v) || v < 0) return null;
    return ['/here/scene/palette', v];
}

// ── Sustain choke ────────────────────────────────────────────────
// Returns:
//   { choke: <list-or-null>, fire: <list-or-null> }
// If the pitch is already active, choke is a synthetic noteoff that
// should be emitted before `fire`. Always updates state.
function chokeIfActive(state, pitch, velocity) {
    const fire = formatNoteOn(pitch, velocity);
    if (fire === null) {
        return { choke: null, fire: null };
    }
    let choke = null;
    if (state.activeNotes.has(pitch)) {
        choke = formatNoteOff(pitch);
    }
    state.activeNotes.add(pitch);
    return { choke: choke, fire: fire };
}

function releaseNote(state, pitch) {
    const msg = formatNoteOff(pitch);
    if (msg === null) return null;
    state.activeNotes.delete(pitch);
    return msg;
}

// Dedup helper. Returns the message to send (or null if duplicate).
function dedupKnob(state, msg) {
    if (msg === null) return null;
    const addr = msg[0];
    const val = msg[1];
    const prev = state.lastKnob.get(addr);
    if (prev !== undefined && prev === val) return null;
    state.lastKnob.set(addr, val);
    return msg;
}

// ── Utility ─────────────────────────────────────────────────────
function clamp01(x) {
    if (!Number.isFinite(x)) return 0.0;
    if (x < 0.0) return 0.0;
    if (x > 1.0) return 1.0;
    return x;
}

// ── Max integration (only when running inside v8) ──────────────
// `outlet` is a Max global; under Node it's undefined and we just
// expose the pure functions for testing.
if (typeof outlet !== 'undefined') {
    var _state = createState();

    function _emit(msg) {
        if (msg === null) return;
        // outlet(0, addr, arg1, arg2, ...) — Max expects spread args
        // so the patcher receives them as a proper list.
        outlet.apply(null, [0].concat(msg));
    }

    // Message handlers — Max calls the function whose name matches the
    // first symbol of the incoming message.

    // eslint-disable-next-line no-unused-vars
    function note(pitch, velocity) {
        var v = (velocity == null) ? 1.0 : Number(velocity);
        // MIDI convention: note_on with velocity 0 = note_off.
        if (v <= 0) {
            _emit(releaseNote(_state, Math.round(Number(pitch))));
            return;
        }
        var step = chokeIfActive(_state, Math.round(Number(pitch)), v);
        _emit(step.choke);
        _emit(step.fire);
    }

    // eslint-disable-next-line no-unused-vars
    function noteoff(pitch) {
        _emit(releaseNote(_state, Math.round(Number(pitch))));
    }

    // eslint-disable-next-line no-unused-vars
    function knob() {
        // Forms: knob master <key> <val>
        //        knob physics <key> <val>
        //        knob oval <i> <key> <val>
        var args = Array.prototype.slice.call(arguments);
        if (args.length < 3) return;
        var category = String(args[0]);
        var msg = null;
        if (category === 'oval') {
            if (args.length < 4) return;
            msg = formatKnob('oval', args[1], args[2], args[3]);
        } else {
            msg = formatKnob(category, args[1], args[2]);
        }
        _emit(dedupKnob(_state, msg));
    }

    // eslint-disable-next-line no-unused-vars
    function bpm(value) {
        _emit(formatBpm(value));
    }

    // eslint-disable-next-line no-unused-vars
    function tap() {
        _emit(formatTap());
    }

    // eslint-disable-next-line no-unused-vars
    function palette(n) {
        _emit(formatPalette(n));
    }

    // eslint-disable-next-line no-unused-vars
    function reset() {
        // Called on device load — clears sustain state so a stale
        // active-notes set from a prior session doesn't choke the first
        // legitimate note_on.
        _state = createState();
    }
}

// ── Node export for Jest ─────────────────────────────────────────
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        createState: createState,
        formatNoteOn: formatNoteOn,
        formatNoteOff: formatNoteOff,
        formatKnob: formatKnob,
        formatBpm: formatBpm,
        formatTap: formatTap,
        formatPalette: formatPalette,
        chokeIfActive: chokeIfActive,
        releaseNote: releaseNote,
        dedupKnob: dedupKnob,
        clamp01: clamp01,
    };
}
