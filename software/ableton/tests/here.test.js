/* Tests for here.js — the pure logic the v8 object runs inside Max.
 *
 * These tests run under Node via Jest. They exercise the address
 * builders, sustain choke, and dedup logic without needing Max.
 */
const h = require('../here.js');

describe('formatNoteOn', () => {
    test('builds /here/scene/note_on/<pitch> with clamped velocity', () => {
        expect(h.formatNoteOn(36, 1.0)).toEqual(['/here/scene/note_on/36', 1.0]);
        expect(h.formatNoteOn(75, 0.5)).toEqual(['/here/scene/note_on/75', 0.5]);
    });
    test('clamps velocity to 0..1', () => {
        expect(h.formatNoteOn(36, -0.5)).toEqual(['/here/scene/note_on/36', 0.0]);
        expect(h.formatNoteOn(36, 1.5)).toEqual(['/here/scene/note_on/36', 1.0]);
    });
    test('defaults velocity to 1.0 when missing', () => {
        expect(h.formatNoteOn(36)).toEqual(['/here/scene/note_on/36', 1.0]);
        expect(h.formatNoteOn(36, null)).toEqual(['/here/scene/note_on/36', 1.0]);
    });
    test('rejects out-of-MIDI-range pitches', () => {
        expect(h.formatNoteOn(-1, 1.0)).toBeNull();
        expect(h.formatNoteOn(128, 1.0)).toBeNull();
        expect(h.formatNoteOn(36.5, 1.0)).toBeNull();
    });
});

describe('formatNoteOff', () => {
    test('builds /here/scene/note_off/<pitch>', () => {
        expect(h.formatNoteOff(36)).toEqual(['/here/scene/note_off/36']);
        expect(h.formatNoteOff(75)).toEqual(['/here/scene/note_off/75']);
    });
    test('rejects invalid pitches', () => {
        expect(h.formatNoteOff(-1)).toBeNull();
        expect(h.formatNoteOff(128)).toBeNull();
    });
});

describe('formatKnob', () => {
    test('master knobs go to /here/scene/synth/<key>', () => {
        expect(h.formatKnob('master', 'radius_min', 3.2))
            .toEqual(['/here/scene/synth/radius_min', 3.2]);
        expect(h.formatKnob('master', 'brightness', 1.5))
            .toEqual(['/here/scene/synth/brightness', 1.5]);
    });
    test('physics knobs go to /here/scene/physics/<key>', () => {
        expect(h.formatKnob('physics', 'damping', 0.3))
            .toEqual(['/here/scene/physics/damping', 0.3]);
    });
    test('oval knobs include the ring index', () => {
        expect(h.formatKnob('oval', 0, 'blur', 1.8))
            .toEqual(['/here/scene/oval/0/blur', 1.8]);
        expect(h.formatKnob('oval', 2, 'skew', 0.2))
            .toEqual(['/here/scene/oval/2/skew', 0.2]);
    });
    test('rejects invalid oval index', () => {
        expect(h.formatKnob('oval', 3, 'blur', 1.0)).toBeNull();
        expect(h.formatKnob('oval', -1, 'blur', 1.0)).toBeNull();
    });
    test('rejects unknown category', () => {
        expect(h.formatKnob('bogus', 'foo', 1.0)).toBeNull();
    });
    test('rejects malformed keys', () => {
        expect(h.formatKnob('master', '', 1.0)).toBeNull();
        // OSC keys are lower_snake_case only — reject anything else
        // (defensive: a stray non-ASCII char from the patcher would
        // otherwise leak into the wire format).
        expect(h.formatKnob('master', 'Foo Bar', 1.0)).toBeNull();
        expect(h.formatKnob('master', 'foo-bar', 1.0)).toBeNull();
    });
    test('rejects non-finite values', () => {
        expect(h.formatKnob('master', 'foo', NaN)).toBeNull();
        expect(h.formatKnob('master', 'foo', Infinity)).toBeNull();
        expect(h.formatKnob('master', 'foo', 'not_a_number')).toBeNull();
    });
});

describe('formatBpm', () => {
    test('emits /here/scene/bpm', () => {
        expect(h.formatBpm(120)).toEqual(['/here/scene/bpm', 120]);
    });
    test('rejects non-positive bpm', () => {
        expect(h.formatBpm(0)).toBeNull();
        expect(h.formatBpm(-1)).toBeNull();
    });
});

describe('formatTap', () => {
    test('emits address-only /here/scene/beat', () => {
        expect(h.formatTap()).toEqual(['/here/scene/beat']);
    });
});

describe('formatPalette', () => {
    test('emits /here/scene/palette with int', () => {
        expect(h.formatPalette(2)).toEqual(['/here/scene/palette', 2]);
        expect(h.formatPalette(0)).toEqual(['/here/scene/palette', 0]);
    });
    test('rejects negative palette index', () => {
        expect(h.formatPalette(-1)).toBeNull();
    });
});

describe('sustain choke', () => {
    test('first note_on fires without a choke', () => {
        const st = h.createState();
        const step = h.chokeIfActive(st, 36, 1.0);
        expect(step.choke).toBeNull();
        expect(step.fire).toEqual(['/here/scene/note_on/36', 1.0]);
        expect(st.activeNotes.has(36)).toBe(true);
    });
    test('second note_on without noteoff emits synthetic noteoff first', () => {
        const st = h.createState();
        h.chokeIfActive(st, 36, 1.0);
        const step = h.chokeIfActive(st, 36, 0.7);
        expect(step.choke).toEqual(['/here/scene/note_off/36']);
        expect(step.fire).toEqual(['/here/scene/note_on/36', 0.7]);
        // Pitch is still active after the retrigger.
        expect(st.activeNotes.has(36)).toBe(true);
    });
    test('releaseNote drops the pitch from active set', () => {
        const st = h.createState();
        h.chokeIfActive(st, 36, 1.0);
        const off = h.releaseNote(st, 36);
        expect(off).toEqual(['/here/scene/note_off/36']);
        expect(st.activeNotes.has(36)).toBe(false);
    });
    test('multiple pitches tracked independently', () => {
        const st = h.createState();
        h.chokeIfActive(st, 36, 1.0);
        h.chokeIfActive(st, 38, 1.0);
        expect(st.activeNotes.size).toBe(2);
        h.releaseNote(st, 36);
        expect(st.activeNotes.has(36)).toBe(false);
        expect(st.activeNotes.has(38)).toBe(true);
    });
});

describe('knob dedup', () => {
    test('first value passes through', () => {
        const st = h.createState();
        const msg = h.formatKnob('master', 'radius_min', 3.0);
        expect(h.dedupKnob(st, msg)).toEqual(['/here/scene/synth/radius_min', 3.0]);
    });
    test('identical consecutive value is dropped', () => {
        const st = h.createState();
        h.dedupKnob(st, h.formatKnob('master', 'radius_min', 3.0));
        const second = h.dedupKnob(st, h.formatKnob('master', 'radius_min', 3.0));
        expect(second).toBeNull();
    });
    test('different value passes through', () => {
        const st = h.createState();
        h.dedupKnob(st, h.formatKnob('master', 'radius_min', 3.0));
        const second = h.dedupKnob(st, h.formatKnob('master', 'radius_min', 3.1));
        expect(second).toEqual(['/here/scene/synth/radius_min', 3.1]);
    });
    test('different knobs are independent', () => {
        const st = h.createState();
        h.dedupKnob(st, h.formatKnob('master', 'radius_min', 3.0));
        const otherKnob = h.dedupKnob(st, h.formatKnob('master', 'brightness', 3.0));
        // Same value, different address — should NOT be deduped.
        expect(otherKnob).toEqual(['/here/scene/synth/brightness', 3.0]);
    });
    test('null input passes through as null', () => {
        const st = h.createState();
        expect(h.dedupKnob(st, null)).toBeNull();
    });
});

describe('clamp01', () => {
    test('clamps to [0, 1]', () => {
        expect(h.clamp01(0.5)).toBe(0.5);
        expect(h.clamp01(-0.1)).toBe(0.0);
        expect(h.clamp01(1.1)).toBe(1.0);
        expect(h.clamp01(NaN)).toBe(0.0);
    });
});
