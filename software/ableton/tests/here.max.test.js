/* Load here.js the way Max's `v8` object does — evaluate it in a global
 * context with the Max globals (outlet/post) present — and assert the
 * message handlers exist AND emit the right OSC.
 *
 * This is the test that would have caught "v8: no function note": the
 * handlers must be TOP-LEVEL (global) functions. require('../here.js')
 * only sees module.exports, so we use vm to get the real global surface.
 */
const fs = require('fs');
const vm = require('vm');
const path = require('path');

function loadInMaxContext() {
  const code = fs.readFileSync(path.join(__dirname, '..', 'here.js'), 'utf8');
  const calls = [];
  const sandbox = {
    outlet: (...args) => calls.push(args),
    post: () => {},
    error: () => {},
    module: { exports: {} },
  };
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox);
  return { sandbox, calls };
}

describe('v8 message handlers (Max-facing surface)', () => {
  const REQUIRED = ['note', 'noteoff', 'knob', 'bpm', 'tap', 'palette', 'reset'];

  test('all required handlers are global functions', () => {
    const { sandbox } = loadInMaxContext();
    for (const name of REQUIRED) {
      expect(typeof sandbox[name]).toBe('function');
    }
  });

  test('note(pitch, vel) emits a note_on OSC list', () => {
    const { sandbox, calls } = loadInMaxContext();
    sandbox.note(36, 1.0);
    expect(calls).toContainEqual([0, '/here/scene/note_on/36', 1.0]);
  });

  test('palette(n) emits a palette OSC list', () => {
    const { sandbox, calls } = loadInMaxContext();
    sandbox.palette(2);
    expect(calls).toContainEqual([0, '/here/scene/palette', 2]);
  });

  test('knob master/key/val emits a synth OSC list', () => {
    const { sandbox, calls } = loadInMaxContext();
    sandbox.knob('master', 'radius_min', 0.5);
    expect(calls).toContainEqual([0, '/here/scene/synth/radius_min', 0.5]);
  });

  test('noteoff(pitch) emits a note_off OSC list', () => {
    const { sandbox, calls } = loadInMaxContext();
    sandbox.note(40, 1.0);   // mark active so release is clean
    calls.length = 0;
    sandbox.noteoff(40);
    expect(calls).toContainEqual([0, '/here/scene/note_off/40']);
  });
});
