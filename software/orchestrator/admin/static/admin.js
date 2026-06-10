// HERE Admin Panel

let config = {};

// WLED tab status-poll handle. Declared up here (not by the WLED block
// below) because _activateTab — which runs during the synchronous
// hash-honoring block at the bottom of this file — calls openWled/
// closeWled, which read this. A `let` declared later would be in its
// temporal dead zone at that point and throw, aborting the rest of
// script evaluation (including the mode-button handler binding).
let _wledStatusTimer = null;

// ── Tabs ───────────────────────────────────────────────────
function _activateTab(id) {
  document.querySelectorAll('.tab').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === id));
  document.querySelectorAll('.pane').forEach(p =>
    p.classList.toggle('active', p.id === `tab-${id}`));
  if (id === 'telemetry') {
    refreshTelemetry();
    refreshScale();
    refreshHistory();
    refreshClockStatus();
  }
  if (id === 'sim') openSimulator();
  else closeSimulator();
  if (id === 'wled') openWled();
  else closeWled();
  // MIDI tab: when becoming visible, run the auto-fit zoom. The
  // init-time fit bails when the tab is display:none (clientWidth=0).
  // CRITICAL: reference `_pianoRoll` only INSIDE the rAF callback —
  // it's a `let` declared further down in the file, and the
  // synchronous hash-honoring block at the bottom of this IIFE calls
  // _activateTab BEFORE that declaration. rAF runs on the next paint,
  // by which time the whole script has finished evaluating.
  if (id === 'scene') {
    requestAnimationFrame(() => {
      if (typeof zoomFitWithCap === 'function' && _pianoRoll) {
        zoomFitWithCap(8);
      }
    });
  }
}
document.querySelectorAll('.tab').forEach(btn => {
  btn.onclick = () => {
    const id = btn.dataset.tab;
    _activateTab(id);
    // Reflect the choice in the URL so a fresh reload / screenshot
    // tooling can land on the same tab.
    history.replaceState(null, '', '#' + id);
  };
});
// Honor #tab in the URL on first load (useful for screenshot scripting
// and bookmarks). Runs synchronously since the script tag is at the
// end of body, so all .tab elements are already in the DOM.
{
  const hash = (location.hash || '').replace(/^#/, '');
  if (hash && document.querySelector(`.tab[data-tab="${hash}"]`)) {
    _activateTab(hash);
  }
}

// ── Simulator iframe (lazy-load so WebGL doesn't run when hidden) ──
function openSimulator() {
  const f = document.getElementById('sim-iframe');
  if (!f.src || f.src === 'about:blank') f.src = '/sim/';
}
function closeSimulator() {
  const f = document.getElementById('sim-iframe');
  f.src = 'about:blank';
}
document.getElementById('sim-reload').onclick = () => {
  const f = document.getElementById('sim-iframe');
  f.src = '/sim/?t=' + Date.now();
};
// (Leaving the sim tab is handled in _activateTab.)

// ── WLED native UI (re-served through the Pi at /wled/) ────────────
// Lazy-load the iframe so the WLED WebSocket only connects while the
// tab is open. A small status poll reminds the user whether the Pi or
// WLED is currently driving the LEDs (mode === 'wled' ⇒ WLED).
// (_wledStatusTimer is declared at the top of this file — see note there.)
function openWled() {
  const f = document.getElementById('wled-iframe');
  if (f && (!f.src || f.src === 'about:blank')) f.src = '/wled/';
  if (!_wledStatusTimer) {
    updateWledStatus();
    _wledStatusTimer = setInterval(updateWledStatus, 2000);
  }
}
function closeWled() {
  const f = document.getElementById('wled-iframe');
  if (f) f.src = 'about:blank';   // drop the proxied WS when hidden
  if (_wledStatusTimer) { clearInterval(_wledStatusTimer); _wledStatusTimer = null; }
}
async function updateWledStatus() {
  const el = document.getElementById('wled-status');
  if (!el) return;
  try {
    const s = await api('status');
    if (s.mode === 'wled') {
      el.innerHTML = '✅ WLED is driving the LEDs — pick any effect below.';
      el.style.color = 'var(--ok, #4caf50)';
    } else {
      el.innerHTML = '⚠️ The Pi is currently driving the LEDs (mode: <b>' +
        s.mode + '</b>). Click <b>Use WLED effects</b> to hand over — ' +
        'WLED effects won’t show until you do.';
      el.style.color = '';
    }
  } catch { /* leave last message */ }
}
const _wledReload = document.getElementById('wled-reload');
if (_wledReload) _wledReload.onclick = () => {
  const f = document.getElementById('wled-iframe');
  f.src = '/wled/?t=' + Date.now();
};

// ── Monitor audio (live tap of the bench speaker stream) ──────
// Off by default. One press opens /api/audio/monitor.mp3 — a never-
// ending MP3 of the post-volume/mix engine output — into a hidden
// <audio>. Volume already lives in the stream, so we just play at 1.0:
// what you hear == what the speakers play. The button gesture also
// satisfies the browser autoplay-with-sound policy.
{
  const btn = document.getElementById('sim-audio-btn');
  const el = document.getElementById('sim-audio');
  const statusEl = document.getElementById('sim-audio-status');
  let on = false;
  let reconnectTimer = null;
  let lastConnect = 0;
  const setStatus = t => { if (statusEl) statusEl.textContent = t || ''; };
  const paint = () => {
    btn.textContent = on ? '🔊 Monitor audio' : '🔇 Monitor audio';
    btn.classList.toggle('active', on);
  };
  function stopAudio(msg) {
    on = false;
    clearTimeout(reconnectTimer); reconnectTimer = null;
    el.pause();
    el.removeAttribute('src');
    el.load();           // drop the HTTP connection so the engine isn't fed a dead reader
    setStatus(msg);
    paint();
  }
  // Open (or re-open) the live stream. cache-bust so we always get a fresh,
  // frame-aligned stream rather than a closed/mid-frame one.
  function connect() {
    lastConnect = Date.now();
    el.src = '/api/audio/monitor.mp3?t=' + Date.now();
    return el.play();
  }
  // A live MP3 over <audio> can hiccup (the browser buffers ahead, the
  // socket backpressures, and the server drops chunks to keep the speaker
  // branch flowing — which splits an MP3 frame and trips a decode error).
  // Instead of giving up, reconnect — unless the Pi's engine is actually
  // off (then it's an intentional stop, so don't loop).
  function scheduleReconnect(reason) {
    if (!on || reconnectTimer) return;
    setStatus(reason + ' — reconnecting…');
    // Back off a little if we *just* connected, so a genuinely-off engine
    // doesn't spin; otherwise recover fast.
    const delay = (Date.now() - lastConnect < 3000) ? 1500 : 300;
    reconnectTimer = setTimeout(async () => {
      reconnectTimer = null;
      if (!on) return;
      try {
        const s = await api('audio');
        if (!s || !s.running) { stopAudio('no audio playing'); return; }
      } catch { /* network blip — try the stream anyway */ }
      if (!on) return;
      connect().then(() => setStatus('live'))
               .catch(() => scheduleReconnect('stalled'));
    }, delay);
  }
  async function startAudio() {
    on = true;
    paint();
    setStatus('connecting…');
    try {
      await connect();
      setStatus('live');
    } catch (e) {
      // Only a genuine autoplay block needs another tap; anything else
      // (slow first bytes, a transient stream hiccup) should retry rather
      // than dead-end at "blocked".
      if (e && e.name === 'NotAllowedError') {
        stopAudio('tap again to allow audio');
      } else {
        scheduleReconnect('starting');
      }
    }
  }
  btn.onclick = () => { on ? stopAudio('') : startAudio(); };
  // Only REAL failures reconnect: 'error' (decode/network) and 'ended'
  // (server closed the stream). 'stalled'/'waiting' are NORMAL for a live
  // stream — the player catches up to the live edge and waits a beat for
  // the next chunk — so we just show "buffering…" and let the browser
  // resume on its own (reconnecting on those tore down a healthy stream).
  el.addEventListener('ended',   () => scheduleReconnect('stream ended'));
  el.addEventListener('error',   () => scheduleReconnect('audio error'));
  el.addEventListener('waiting', () => { if (on) setStatus('buffering…'); });
  el.addEventListener('stalled', () => { if (on) setStatus('buffering…'); });
  el.addEventListener('playing', () => { if (on) setStatus('live'); });
  el.addEventListener('canplay', () => { if (on) setStatus('live'); });
}

// ── UI primitives ─────────────────────────────────────────
// Two-button (or N-button) "toggle picker" pattern. We use it for
// scale auto-engage, weight overlay, and the three spin toggles —
// each is a row of `<button data-val="…">` elements where exactly one
// has class `.active` based on the current backend value. Before this
// helper, each callsite open-coded a `querySelectorAll(...).forEach(…
// classList.toggle('active', String(val) === b.dataset.val))` plus a
// `.onclick` binding.
//
//   bindToggle(selector, valueClicked)
//       Wire the click handlers. `valueClicked(stringVal, btn)` runs
//       on every click — the caller is responsible for the side
//       effect (api PUT, config update, etc.).
//
//   refreshToggle(selector, currentValue)
//       Sync the `.active` class to whichever button's data-val
//       matches `String(currentValue)`. No-op when currentValue is
//       null/undefined so a partial server response doesn't briefly
//       drop the highlight.
function bindToggle(selector, valueClicked) {
  document.querySelectorAll(selector).forEach(b => {
    b.onclick = () => valueClicked(b.dataset.val, b);
  });
}
function refreshToggle(selector, currentValue) {
  if (currentValue === undefined || currentValue === null) return;
  const target = String(currentValue);
  document.querySelectorAll(selector).forEach(b =>
    b.classList.toggle('active', b.dataset.val === target));
}

// Update an <input>/<select> value from a poll, but skip the write if
// the user is currently focused on it (otherwise we stomp their typing
// — they can't clear the field, the next poll snaps it back, etc.).
// Pass either an id string or the element itself.
function setInputIfNotFocused(elOrId, value) {
  const el = (typeof elOrId === 'string')
    ? document.getElementById(elOrId) : elOrId;
  if (!el || el === document.activeElement) return;
  el.value = value;
}

// ── API helpers ────────────────────────────────────────────
async function api(path, opts = {}) {
  const r = await fetch('/api/' + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  return r.json();
}

// ── Targets ────────────────────────────────────────────────
async function loadTargets() {
  const targets = await api('targets');
  const el = document.getElementById('targets');
  el.innerHTML = '';

  targets.forEach((t, i) => {
    const row = document.createElement('div');
    row.className = 'target-row';
    row.innerHTML = `
      <span class="target-dot ${t.status}"></span>
      <span class="target-name">${t.name}</span>
      <span class="target-addr">${t.ip}:${t.port}</span>
      <label><input type="checkbox" ${t.enabled ? 'checked' : ''} onchange="toggleTarget(${i}, this.checked)"> On</label>
      <button onclick="editTarget(${i})">Edit</button>
      <button class="delete" onclick="deleteTarget(${i})">×</button>
    `;
    el.appendChild(row);
  });
}

window.toggleTarget = async (i, enabled) => {
  await api(`targets/${i}`, { method: 'PUT', body: JSON.stringify({ enabled }) });
  loadTargets();
};

window.editTarget = async (i) => {
  const targets = await api('targets');
  const t = targets[i];
  const name = prompt('Name:', t.name);
  if (!name) return;
  const ip = prompt('IP:', t.ip);
  if (!ip) return;
  const port = parseInt(prompt('Port:', t.port));
  if (isNaN(port)) return;
  await api(`targets/${i}`, { method: 'PUT', body: JSON.stringify({ name, ip, port }) });
  loadTargets();
};

window.deleteTarget = async (i) => {
  if (!confirm('Remove this target?')) return;
  await api(`targets/${i}`, { method: 'DELETE' });
  loadTargets();
};

document.getElementById('add-target-btn').onclick = async () => {
  const name = prompt('Target name:', 'WLED Controller');
  if (!name) return;
  const ip = prompt('IP address (just the IP, no path):', '192.168.10.20');
  if (!ip) return;
  const cleanIp = ip.split('/')[0].trim();
  const port = parseInt(prompt('UDP DNRGB port:', '21324'));
  if (isNaN(port)) return;
  await api('targets', { method: 'POST', body: JSON.stringify({ name, ip: cleanIp, port }) });
  loadTargets();
};

// ── Mode ───────────────────────────────────────────────────
// Bind ONLY the real mode-picker buttons. `.mode-btn` is also worn (for
// styling) by other controls — the two-way toggles, the sim reload, the
// monitor-audio button — which set their own onclick elsewhere. A bare
// `.mode-btn` selector would clobber those handlers and POST
// `mode/undefined` (no data-mode → 400). Hence the [data-mode] filter,
// mirroring updateModeButtons below.
document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
  btn.onclick = async () => {
    await api(`mode/${btn.dataset.mode}`, { method: 'POST' });
    updateModeButtons(btn.dataset.mode);
  };
});

function updateModeButtons(mode) {
  // Restrict to actual mode-picker buttons: `.mode-btn` is also worn by
  // the various two-way toggles (scale auto-engage, weight overlay,
  // spin direction, …), so a bare `.mode-btn` selector would race them
  // and clobber their `active` class every poll.
  document.querySelectorAll('.mode-btn[data-mode]').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
}

// ── Sensor ─────────────────────────────────────────────────
window.sensor = async (state) => {
  const r = await api(`sensor/${state}`, { method: 'POST' });
  updateModeButtons(r.mode);
};

// ── Parameter sliders ──────────────────────────────────────
function rgbToHex(arr) {
  return '#' + arr.map(v => v.toString(16).padStart(2, '0')).join('');
}

function hexToRgb(hex) {
  const m = hex.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
  return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [0, 0, 0];
}

const TRANSPORT_SLIDERS = [
  { key: 'fps', label: 'FPS', min: 5, max: 60, step: 1 },
  { key: 'inter_packet_ms', label: 'Inter-packet delay (ms)', min: 0, max: 20, step: 0.5 },
];

const BREATHING_SLIDERS = [
  { key: 'inhale_ms', label: 'Inhale (ms)', min: 500, max: 10000, step: 100 },
  { key: 'hold_top_ms', label: 'Hold Top (ms)', min: 0, max: 5000, step: 100 },
  { key: 'exhale_ms', label: 'Exhale (ms)', min: 500, max: 10000, step: 100 },
  { key: 'hold_bottom_ms', label: 'Hold Bottom (ms)', min: 0, max: 5000, step: 100 },
  { key: 'min_radius', label: 'Min Radius', min: 0, max: 20, step: 0.5 },
  { key: 'max_radius', label: 'Max Radius', min: 5, max: 30, step: 0.5 },
  { key: 'rim_width', label: 'Rim Width', min: 0.5, max: 8, step: 0.1 },
  { key: 'inner_blur', label: 'Inner Blur', min: 0.5, max: 10, step: 0.1 },
  { key: 'outer_blur', label: 'Outer Blur', min: 0.5, max: 10, step: 0.1 },
  { key: 'trail_delay_ms', label: 'Trail Delay (ms)', min: 0, max: 2000, step: 50 },
  { key: 'trail_blur', label: 'Trail Blur', min: 0.5, max: 8, step: 0.1 },
  { key: 'trail_opacity', label: 'Trail Opacity', min: 0, max: 1, step: 0.05 },
  { key: 'brightness', label: 'Brightness', min: 0, max: 2, step: 0.05 },
];

const PALETTE_COLOR_KEYS = [
  'rim_color', 'inner_color', 'outer_color', 'trail_color',
  'color4', 'color5', 'color6', 'color7',
];
const PALETTE_COLOR_LABELS = {
  rim_color: 'rim', inner_color: 'inner', outer_color: 'outer', trail_color: 'trail',
  color4: 'col 4', color5: 'col 5', color6: 'col 6', color7: 'col 7',
};

const SPIN_SLIDERS = [
  { key: 'arms', label: 'Arms (symmetry)', min: 1, max: 12, step: 1 },
  { key: 'depth', label: 'Depth', min: 0, max: 1, step: 0.05 },
  { key: 'constant_speed', label: 'Constant Speed (rps)', min: 0.05, max: 10, step: 0.05 },
  { key: 'yoyo_speed', label: 'Yo-Yo Speed', min: 0.1, max: 20, step: 0.1 },
  { key: 'yoyo_inertia', label: 'Yo-Yo Inertia', min: 0.9, max: 0.999, step: 0.001 },
];

const STANDBY_SLIDERS = [
  { key: 'sparkle_density', label: 'Density', min: 0.005, max: 0.15, step: 0.005 },
  { key: 'fade_speed', label: 'Fade Speed', min: 0.005, max: 0.1, step: 0.005 },
  { key: 'max_brightness', label: 'Max Brightness', min: 0.05, max: 1, step: 0.05 },
  { key: 'spawn_rate', label: 'Spawn Rate', min: 1, max: 10, step: 1 },
];

// Session phase durations. Drive future orchestration (timed
// intro voice → loop → outro voice → chill → fade-out). Today they
// just live in config; the engine honors `preview_phase` only.
const BREATHING_SESSION_SLIDERS = [
  { key: 'intro_voice_s', label: 'Intro voice (s)', min: 0, max: 120, step: 1 },
  { key: 'outro_voice_s', label: 'Outro voice (s)', min: 0, max: 120, step: 1 },
  { key: 'chill_s',       label: 'Chill (s)',       min: 0, max: 300, step: 5 },
  { key: 'loop_min_s',    label: 'Loop min (s)',    min: 30, max: 600, step: 10 },
  { key: 'loop_max_s',    label: 'Loop max (s)',    min: 60, max: 1800, step: 30 },
];

// Knobs for the fireplace mode. Keep names in sync with DEFAULT_PARAMS
// in animations/fireplace.py — sliders pump through PUT /api/config.
const FIREPLACE_SLIDERS = [
  { key: 'core_radius',         label: 'Core Radius',         min: 1,    max: 12,   step: 0.2 },
  { key: 'outer_radius',        label: 'Body Radius',         min: 4,    max: 18,   step: 0.2 },
  { key: 'brightness',          label: 'Brightness',          min: 0,    max: 1.5,  step: 0.05 },
  { key: 'shimmer_amount',      label: 'Shimmer (grain)',     min: 0,    max: 0.8,  step: 0.02 },
  { key: 'shimmer_speed',       label: 'Shimmer Speed',       min: 0.1,  max: 3,    step: 0.05 },
  { key: 'pulse_amp',           label: 'Breath Depth',        min: 0,    max: 0.4,  step: 0.01 },
  { key: 'pulse_period_s',      label: 'Breath Period (s)',   min: 2,    max: 20,   step: 0.5 },
  { key: 'turb_amp',            label: 'Turbulence Amount',   min: 0,    max: 0.5,  step: 0.01 },
  { key: 'turb_speed',          label: 'Turbulence Speed',    min: 0.1,  max: 3,    step: 0.05 },
  { key: 'flicker_amp',         label: 'Flicker Amount',      min: 0,    max: 0.2,  step: 0.005 },
  { key: 'flicker_smoothing',   label: 'Flicker Smoothing',   min: 0.01, max: 0.5,  step: 0.01 },
  { key: 'heat_smoothing',      label: 'Heat Smoothing',      min: 0,    max: 0.85, step: 0.02 },
  { key: 'flare_max',           label: 'Max Flares',          min: 0,    max: 12,   step: 1 },
  { key: 'flare_spawn_hz',      label: 'Flare Spawn Rate',    min: 0,    max: 10,   step: 0.1 },
  { key: 'flare_speed_mean',    label: 'Flare Speed',         min: 1,    max: 30,   step: 0.5 },
  { key: 'flare_life_mean',     label: 'Flare Duration (s)',  min: 0.2,  max: 3.5,  step: 0.05 },
  { key: 'flare_reach_mean',    label: 'Flare Reach',         min: 1,    max: 25,   step: 0.5 },
  { key: 'flare_base_width',    label: 'Flare Base Width',    min: 0.02, max: 0.5,  step: 0.01 },
  { key: 'flare_tip_width',     label: 'Flare Tip Width',     min: 0.01, max: 0.3,  step: 0.005 },
  { key: 'flare_curl_amp',      label: 'Flame Curl',          min: 0,    max: 0.5,  step: 0.01 },
  { key: 'flare_curl_freq',     label: 'Curl Frequency',      min: 0.2,  max: 5,    step: 0.1 },
  { key: 'flare_inner_factor',  label: 'Burst Origin (× rim)', min: 0.4,  max: 1.4,  step: 0.02 },
  { key: 'flare_base_heat',     label: 'Flare Base Heat',     min: 0,    max: 1.2,  step: 0.02 },
  { key: 'flare_tip_heat',      label: 'Flare Tip Heat',      min: 0,    max: 1.2,  step: 0.02 },
  { key: 'flare_detach_prob',   label: 'Detach Chance',       min: 0,    max: 1,    step: 0.02 },
  { key: 'flare_detach_factor', label: 'Detach Distance',     min: 1.0,  max: 2.5,  step: 0.05 },
  { key: 'ember_max',           label: 'Max Embers',          min: 0,    max: 15,   step: 1 },
  { key: 'ember_spawn_hz',      label: 'Ember Spawn Rate',    min: 0,    max: 10,   step: 0.1 },
  { key: 'ember_life_mean',     label: 'Ember Duration (s)',  min: 0.1,  max: 4,    step: 0.05 },
  { key: 'ember_radius_mean',   label: 'Ember Distance',      min: 6,    max: 22,   step: 0.5 },
];

// Weight-overlay knobs. Leg positions are in LED-grid coords (0..43).
// `scale.shadows` is read by the engine every frame, so slider edits
// are live with no restart.
const SHADOWS_SLIDERS = [
  { key: 'leg1_row',    label: 'Leg 1 row',     min: 0,  max: 43, step: 1 },
  { key: 'leg1_col',    label: 'Leg 1 col',     min: 0,  max: 43, step: 1 },
  { key: 'leg2_row',    label: 'Leg 2 row',     min: 0,  max: 43, step: 1 },
  { key: 'leg2_col',    label: 'Leg 2 col',     min: 0,  max: 43, step: 1 },
  { key: 'base_radius', label: 'Base radius',   min: 0.5, max: 12, step: 0.1 },
  { key: 'max_radius',  label: 'Max radius',    min: 1,   max: 18, step: 0.1 },
  { key: 'span_grams',  label: 'Full-scale (g)', min: 1000, max: 200000, step: 1000 },
  { key: 'brightness',  label: 'Brightness',    min: 0,   max: 1.5, step: 0.05 },
];

// Master sliders for the synth scene — radius defaults + brightness.
const SYNTH_MASTER_SLIDERS = [
  { key: 'radius_min',      label: 'Radius Min',     min: 0,   max: 12, step: 0.1 },
  { key: 'radius_max',      label: 'Radius Max',     min: 8,   max: 22, step: 0.1 },
  { key: 'radius_default',  label: 'Radius Default', min: 2,   max: 20, step: 0.1 },
  { key: 'brightness',      label: 'Brightness',     min: 0,   max: 2,  step: 0.05 },
  // Spread between outer / middle / inner — 0 collapses all 3 rings
  // onto the master radius. Larger values widen the gap (outer flies
  // out further) as the master radius grows.
  { key: 'gap_coefficient', label: 'Ring Gap',       min: 0,   max: 6,  step: 0.1 },
  // Dissolve dot-cloud orbital max speed (rad/s at dissolve_amount=0).
  // Lower = slow swirl, higher = fast comets.
  { key: 'dot_orbit_speed', label: 'Comet Spin',     min: 0.5, max: 8,  step: 0.1 },
  // Comet-tail length (# of past-position samples per particle).
  // Each step costs ~16 Gaussian blob draws/oval, so higher = prettier
  // but slower. Default 22 = ~1.87 s of tail at trail_dt=0.085.
  { key: 'trail_steps',     label: 'Tail Length',    min: 4,   max: 40, step: 1 },
  // Speed-vs-orbit-lock curve. Particle speed = MIN + (MAX-MIN) ×
  // orbit_lock^exp. Exp > 1 → speed grows slowly then accelerates as
  // particles lock onto rings (snap-into-orbit feel). Exp < 1 →
  // speed climbs fast early. Exp = 1 → linear.
  { key: 'dot_speed_min',    label: 'Speed Min',     min: 0,   max: 1,   step: 0.02 },
  { key: 'dot_speed_max',    label: 'Speed Max',     min: 0.3, max: 2.5, step: 0.05 },
  { key: 'dot_speed_lock_exp', label: 'Speed Curve', min: 0.3, max: 4,   step: 0.05 },
  // Voice-shimmer amplitude — radial wobble magnitude (× ring radius).
  // 0 = no wobble; 0.4 = strong "talking" vibration.
  { key: 'shimmer_intensity', label: 'Shimmer Amp', min: 0,   max: 0.6, step: 0.01 },
];

// Physics knobs — match PhysicsParams fields in scene/physics.py.
const PHYSICS_KNOBS = [
  { key: 'speed',            label: 'Impulse Speed',  min: 5,   max: 80,  step: 0.5,  default: 25  },
  { key: 'radial_offset',    label: 'Jitter',         min: 0,   max: 0.6, step: 0.01, default: 0.12 },
  { key: 'squishiness',      label: 'Squishiness',    min: 0,   max: 1,   step: 0.01, default: 0.35 },
  // "Damping" in the physics module — viscous drag on the ball motion.
  // Lower = ball coasts longer after a push. Default tuned light so
  // pushes have noticeable inertia.
  { key: 'damping',          label: 'Viscosity',      min: 0,   max: 5,   step: 0.05, default: 0.3 },
  { key: 'bounce',           label: 'Bounce',         min: 0.1, max: 1,   step: 0.01, default: 0.75 },
  { key: 'center_pull',      label: 'Center Pull',    min: 0,   max: 15,  step: 0.1,  default: 3 },
  { key: 'tau_squash',       label: 'Squash τ',       min: 0.05, max: 1,  step: 0.01, default: 0.25 },
  { key: 'max_velocity',     label: 'Max Velocity',   min: 10,  max: 120, step: 1,    default: 40 },
  // Angular friction — global decay rate for ring rotation. 0 = no
  // decay (rotates forever after a tap); higher = brakes faster once
  // the rotate event is released.
  { key: 'angular_friction', label: 'Rot Friction',   min: 0,   max: 4,   step: 0.05, default: 0.6 },
  // Squash damping (ζ for the wall-collision spring). < 1 = wobble +
  // overshoot — "jelly" feel. ≥ 1 = critically damped (no wobble).
  { key: 'squash_damping',   label: 'Squash ζ',       min: 0.05, max: 1.5, step: 0.05, default: 0.35 },
];

// Per-oval knobs. Default values are per-oval (rim/mid/outer) and applied
// by the dbl-click reset action.
const OVAL_KNOBS = [
  { key: 'skew',         label: 'Skew',  min: 0,    max: 0.5,    step: 0.01 },
  { key: 'phase',        label: 'Phase', min: 0,    max: 3.14159, step: 0.05 },
  { key: 'blur',         label: 'Blur',  min: 0.3,  max: 8,       step: 0.1 },
  // Per-ring radius scale — multiplies the master radius for this
  // oval only. 1.0 = no change; 0.5 = half-size; 1.5 = 1.5× larger.
  { key: 'radius_scale', label: 'Scale', min: 0.2,  max: 2.0,     step: 0.05 },
  { key: 'segments',     label: 'Dash',  min: 0,    max: 32,      step: 1 },
  { key: 'gap',          label: 'Gap',   min: 0,    max: 0.95,    step: 0.05 },
];
const OVAL_DEFAULTS = {
  skew:         [0.12, 0.18, 0.20],
  phase:        [0.0,  1.0,  2.1],
  blur:         [1.8,  2.5,  1.2],
  radius_scale: [1.0,  1.0,  1.0],
  segments:     [0,    0,    0],
  gap:          [0.4,  0.4,  0.4],
};

// `value` in beats, `label` for the dropdown
const DURATIONS = [
  { label: '1/16',   beats: 0.25 },
  { label: '1/8',    beats: 0.5  },
  { label: '1/4',    beats: 1    },
  { label: '1/2',    beats: 2    },
  { label: '1 bar',  beats: 4    },
  { label: '2 bars', beats: 8    },
  { label: '4 bars', beats: 16   },
];

let updateTimer = null;

// Resolve a dotted section path ("scene.breathing") to its config sub-object.
function getNested(path) {
  return path.split('.').reduce((o, k) => (o == null ? o : o[k]), config);
}

// Build a nested update body for a dotted path: ("scene.breathing", "rim_width", 1.8)
// → { scene: { breathing: { rim_width: 1.8 } } }
function nestedUpdate(sectionPath, key, value) {
  const parts = sectionPath.split('.');
  let body = { [key]: value };
  for (let i = parts.length - 1; i >= 0; i--) body = { [parts[i]]: body };
  return body;
}

function buildSliders(container, section, sliders, colors) {
  const el = document.getElementById(container);
  el.innerHTML = '';

  // Restore defaults — only for top-level sections; nested paths skip it
  // (`/api/defaults/restore/<section>` doesn't navigate dotted names).
  if (!section.includes('.')) {
    const restoreBtn = document.createElement('button');
    restoreBtn.textContent = 'Restore Defaults';
    // Position absolute so it sits in the top-right of the group
    // without participating in flex/grid flow (avoids overflow on narrow
    // viewports). The parent has position:relative below.
    restoreBtn.style.cssText = 'position:absolute;top:8px;right:8px;padding:3px 8px;background:#2a1a1a;border:1px solid #633;color:#a88;border-radius:3px;cursor:pointer;font-size:11px;z-index:1;';
    el.style.position = 'relative';
    el.style.paddingTop = '32px';
    restoreBtn.onclick = async () => {
      if (!confirm(`Restore ${section} parameters to defaults?`)) return;
      config = await api(`defaults/restore/${section}`, { method: 'POST' });
      buildSliders(container, section, sliders, colors);
    };
    el.appendChild(restoreBtn);
  }

  sliders.forEach(s => {
    const val = getNested(section)?.[s.key] ?? s.min;
    const row = document.createElement('div');
    row.className = 'param-row';
    row.innerHTML = `
      <label>${s.label}</label>
      <input type="range" min="${s.min}" max="${s.max}" step="${s.step}" value="${val}"
             data-section="${section}" data-key="${s.key}">
      <span class="val">${val}</span>
    `;
    const input = row.querySelector('input');
    const span = row.querySelector('.val');
    input.oninput = () => {
      const v = parseFloat(input.value);
      span.textContent = v;
      debouncedUpdateNested(section, s.key, v);
    };
    el.appendChild(row);
  });

  if (colors) {
    colors.forEach(c => {
      const val = getNested(section)?.[c.key] ?? [0, 0, 0];
      const row = document.createElement('div');
      row.className = 'param-row';
      row.innerHTML = `
        <label>${c.label}</label>
        <input type="color" value="${rgbToHex(val)}" data-section="${section}" data-key="${c.key}">
        <span class="val">${JSON.stringify(val)}</span>
      `;
      const input = row.querySelector('input');
      const span = row.querySelector('.val');
      input.oninput = () => {
        const rgb = hexToRgb(input.value);
        span.textContent = JSON.stringify(rgb);
        debouncedUpdateNested(section, c.key, rgb);
      };
      el.appendChild(row);
    });
  }
}

function debouncedUpdate(section, key, value) {
  clearTimeout(updateTimer);
  updateTimer = setTimeout(() => {
    api('config', {
      method: 'PUT',
      body: JSON.stringify({ [section]: { [key]: value } }),
    });
  }, 100);
}

function debouncedUpdateNested(sectionPath, key, value) {
  clearTimeout(updateTimer);
  updateTimer = setTimeout(() => {
    // For scene.synth keys, route through /api/scene/synth so the
    // live animation's meta + event catalog get refreshed. The
    // generic /api/config PUT only persists to disk — wouldn't take
    // effect until the next animation swap. (This was a silent dead-
    // knob bug for Radius Min/Max/Default/Brightness/RingGap and the
    // newly added Comet Spin.)
    if (sectionPath === 'scene.synth') {
      api('scene/synth', {
        method: 'PUT',
        body: JSON.stringify({ [key]: value }),
      });
      return;
    }
    api('config', {
      method: 'PUT',
      body: JSON.stringify(nestedUpdate(sectionPath, key, value)),
    });
  }, 100);
}

// ── Status polling ─────────────────────────────────────────
function fmtUptime(seconds) {
  if (seconds == null) return '—';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${s}s`;
  return `${s}s`;
}

async function pollStatus() {
  try {
    const s = await api('status');
    document.getElementById('s-mode').textContent = s.mode;
    document.getElementById('s-fps').textContent = s.fps;
    document.getElementById('s-uptime').textContent = fmtUptime(s.uptime_s);
    if (s.power) {
      document.getElementById('s-led-w').textContent = s.power.led_watts;
      document.getElementById('s-total-w').textContent = s.power.total_watts;
      document.getElementById('s-daily').textContent = s.power.daily_wh;
      document.getElementById('s-batt').textContent = s.power.battery_days;
    }
    updateModeButtons(s.mode);
    // Keep spin toggles in sync with the latest config (the click
    // handlers don't fire here — refreshToggle just mirrors the
    // .active class onto whichever button matches).
    const spin = config.breathing?.spin || {};
    refreshToggle('.spin-toggle',   spin.enabled || false);
    refreshToggle('.spin-mode-btn', spin.mode || 'constant');
    refreshToggle('.spin-dir-btn',  spin.yoyo_reverse ?? true);
  } catch {}
}

// ── Telemetry ──────────────────────────────────────────────
function fmtBytes(b) {
  if (b == null) return '—';
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return `${b.toFixed(b < 10 ? 1 : 0)} ${u[i]}`;
}

function tempClass(c) {
  if (c == null) return '';
  if (c >= 80) return 'bad';
  if (c >= 70) return 'warn';
  return '';
}

async function refreshTelemetry() {
  let snap, hist;
  try {
    [snap, hist] = await Promise.all([
      api('telemetry'),
      api('telemetry/temp-history'),
    ]);
  } catch { return; }

  // ── Topbar mini-display (always updated) ─
  if (snap.cpu_temp_c != null) {
    document.getElementById('s-temp').textContent = snap.cpu_temp_c;
  }
  const t = snap.throttle || {};
  const throttleNow = t.undervoltage_now || t.throttled_now || t.soft_temp_limit_now;
  const tEl = document.getElementById('s-throttle');
  if (throttleNow) {
    tEl.textContent = '⚠ throttling';
    tEl.className = 't-pill now';
    tEl.hidden = false;
  } else {
    tEl.hidden = true;
  }

  // If telemetry tab isn't visible, no need to redraw cards
  if (!document.getElementById('tab-telemetry').classList.contains('active')) return;

  // ── Temp card + sparkline ─
  const tempEl = document.getElementById('t-temp');
  tempEl.textContent = snap.cpu_temp_c ?? '—';
  tempEl.parentElement.querySelector('.card-val').className =
    `card-val ${tempClass(snap.cpu_temp_c)}`;
  drawSparkline(hist.samples || []);

  // ── Uptime ─
  document.getElementById('t-uptime').textContent = fmtUptime(snap.system_uptime_s);
  document.getElementById('t-loadavg').textContent =
    snap.loadavg ? `load ${snap.loadavg.map(x => x.toFixed(2)).join(' ')}` : '—';

  // ── Memory ─
  if (snap.mem_total_kb && snap.mem_avail_kb != null) {
    const usedKb = snap.mem_total_kb - snap.mem_avail_kb;
    const pct = Math.round(100 * usedKb / snap.mem_total_kb);
    document.getElementById('t-mem').textContent = `${pct}%`;
    document.getElementById('t-mem-total').textContent =
      `${fmtBytes(usedKb * 1024)} / ${fmtBytes(snap.mem_total_kb * 1024)}`;
  }

  // ── Disk ─
  if (snap.disk_total_b && snap.disk_free_b != null) {
    const used = snap.disk_total_b - snap.disk_free_b;
    const pct = Math.round(100 * used / snap.disk_total_b);
    document.getElementById('t-disk').textContent = `${pct}%`;
    document.getElementById('t-disk-total').textContent =
      `${fmtBytes(used)} / ${fmtBytes(snap.disk_total_b)}`;
  }

  // ── Throttle pills ─
  const tEl2 = document.getElementById('t-throttle');
  tEl2.innerHTML = '';
  const tt = snap.throttle;
  if (!tt) {
    tEl2.textContent = '—';
  } else {
    const items = [
      ['Undervolt now',   tt.undervoltage_now,    'now'],
      ['Throttled now',   tt.throttled_now,       'now'],
      ['Freq capped now', tt.freq_capped_now,     'now'],
      ['Soft temp now',   tt.soft_temp_limit_now, 'now'],
      ['Undervolt ever',  tt.undervoltage_ever,   'ever'],
      ['Throttled ever',  tt.throttled_ever,      'ever'],
    ];
    const anyFlag = items.some(([, v]) => v);
    if (!anyFlag) {
      tEl2.innerHTML = '<span class="t-pill ok">all clear</span>';
    } else {
      items.forEach(([label, v, sev]) => {
        if (v) {
          const span = document.createElement('span');
          span.className = `t-pill ${sev}`;
          span.textContent = label;
          tEl2.appendChild(span);
        }
      });
    }
  }

  // ── WiFi / AP / eth0 ─
  document.getElementById('t-wifi').textContent =
    snap.wifi_ssid ? snap.wifi_ssid : '—';
  document.getElementById('t-wifi-sub').textContent = [
    snap.wifi_signal_dbm != null ? `${snap.wifi_signal_dbm} dBm` : null,
    snap.addrs?.wlan0,
  ].filter(Boolean).join(' · ') || '—';

  // AP card uses live /api/ap (more authoritative than the cached snapshot)
  try {
    const ap = await api('ap');
    const valEl = document.getElementById('t-ap');
    const subEl = document.getElementById('t-ap-sub');
    const cardEl = document.getElementById('ap-card');
    const warnEl = document.getElementById('ap-warn');
    if (!ap.defined) {
      valEl.textContent = 'not configured';
      subEl.textContent = 'set AP_SSID/AP_PSK in .env, redeploy';
      cardEl.classList.remove('up');
      warnEl.hidden = true;
    } else if (ap.active) {
      valEl.textContent = `up (${snap.ap_clients ?? 0} client${snap.ap_clients === 1 ? '' : 's'})`;
      subEl.textContent = '192.168.50.1';
      cardEl.classList.add('up');
      warnEl.hidden = false;
    } else {
      valEl.textContent = 'dormant';
      subEl.textContent = 'tap "Bring Up" when home WiFi is gone';
      cardEl.classList.remove('up');
      warnEl.hidden = false;
    }
    document.getElementById('ap-up-btn').disabled = ap.active;
    document.getElementById('ap-down-btn').disabled = !ap.active;
  } catch {}

  document.getElementById('t-eth').textContent = snap.eth0_state || '—';
  document.getElementById('t-eth-sub').textContent = snap.addrs?.eth0 || '';

  // ── Recent boots ─
  const bootsEl = document.getElementById('t-boots');
  bootsEl.innerHTML = '';
  if (snap.recent_boots && snap.recent_boots.length) {
    snap.recent_boots.slice().reverse().forEach(b => {
      const row = document.createElement('div');
      row.className = 'b-row';
      row.innerHTML = `<span class="b-idx">${b.idx}</span><span class="b-range">${b.range}</span>`;
      bootsEl.appendChild(row);
    });
  } else {
    bootsEl.textContent = '—';
  }
}

// ── Bench scale (dual HX711) ────────────────────────────────
// Backend speaks grams; UI displays + accepts kg. fmtKg picks 1 decimal
// for typical bench weights, 2 decimals near zero so tare drift is visible.
function fmtKg(grams) {
  const kg = (grams || 0) / 1000;
  return Math.abs(kg) < 10 ? kg.toFixed(2) : kg.toFixed(1);
}
async function refreshScale() {
  let s;
  try { s = await api('scale'); } catch { return; }
  if (!s || s.error) return;

  // ── Topbar pill ─
  const pill = document.getElementById('s-scale');
  const val  = document.getElementById('s-scale-val');
  pill.hidden = !s.enabled;
  if (s.enabled) {
    val.textContent = fmtKg(s.total_grams);
    pill.classList.toggle('occupied', !!s.occupied);
    pill.classList.toggle('no-hw', !s.hardware);
    if (!s.hardware) pill.title = 'No HX711 hardware detected — readings are simulated';
    else pill.title = s.occupied
      ? `occupied (threshold ${fmtKg(s.threshold_grams)} kg)`
      : `idle${s.empty_for_s != null ? ` — empty for ${Math.round(s.empty_for_s)}s` : ''}`;
  }

  // ── Run-tab card ─
  document.getElementById('sc-state').textContent = s.occupied ? 'OCCUPIED' : 'idle';
  document.getElementById('sc-state-sub').textContent =
    s.occupied
      ? (s.auto_engage ? '' : '(auto off — manual control)')
      : (s.empty_for_s != null ? `empty ${Math.round(s.empty_for_s)}s` : '');
  document.getElementById('sc-total').textContent = fmtKg(s.total_grams);
  // Display order swapped to match physical labelling on the bench.
  document.getElementById('sc-leg1').textContent = fmtKg(s.legs[1]?.grams ?? 0);
  document.getElementById('sc-leg2').textContent = fmtKg(s.legs[0]?.grams ?? 0);
  refreshToggle('.scale-auto-btn',
                typeof s.auto_engage === 'boolean' ? s.auto_engage : null);
  refreshToggle('.scale-overlay-btn',
                typeof s.weight_overlay === 'boolean' ? s.weight_overlay : null);
  // Don't overwrite inputs the user is currently editing — otherwise
  // they can't clear the field (poll snaps it right back). focus-check
  // beats the old timestamp debounce because `input` events during
  // typing don't fire the existing `change` handler.
  setInputIfNotFocused('sc-threshold', (s.threshold_grams / 1000).toFixed(1));
  setInputIfNotFocused('sc-release', s.release_seconds);
  setInputIfNotFocused('sc-engage', s.engage_seconds);
  setInputIfNotFocused('sc-occ-mode', s.occupied_mode);
  setInputIfNotFocused('sc-idle-mode', s.idle_mode);

  // ── Telemetry-tab card (only when visible) ─
  if (document.getElementById('tab-telemetry').classList.contains('active')) {
    document.getElementById('t-scale-total').textContent = fmtKg(s.total_grams);
    document.getElementById('t-scale-sub').textContent = [
      s.hardware ? null : '(simulated — no HX711)',
      s.occupied ? `occupied${s.auto_engage ? '' : ' (auto off)'}`
                 : (s.empty_for_s != null ? `idle, empty ${Math.round(s.empty_for_s)}s` : 'idle'),
      `threshold ${fmtKg(s.threshold_grams)} kg, release ${s.release_seconds}s`,
    ].filter(Boolean).join(' · ');
    document.getElementById('t-scale-legs').textContent =
      `leg 1: ${fmtKg(s.legs[1]?.grams ?? 0)} kg · leg 2: ${fmtKg(s.legs[0]?.grams ?? 0)} kg · ` +
      `pins DT ${s.dt_pins?.join('/')}, SCK ${s.sck_pin}`;
  }
}

function bindScaleControls() {
  async function pushSettings(patch) {
    try { await api('scale', { method: 'PUT', body: JSON.stringify(patch) }); }
    catch {}
    refreshScale();
  }
  bindToggle('.scale-auto-btn',
             (v) => pushSettings({ auto_engage: v === 'true' }));
  bindToggle('.scale-overlay-btn',
             (v) => pushSettings({ weight_overlay: v === 'true' }));
  document.getElementById('sc-threshold').addEventListener('change', e => {
    const kg = parseFloat(e.target.value);
    if (!Number.isNaN(kg)) pushSettings({ threshold_grams: kg * 1000 });
  });
  document.getElementById('sc-release').addEventListener('change', e => {
    const v = parseFloat(e.target.value);
    if (!Number.isNaN(v) && v >= 1) pushSettings({ release_seconds: v });
  });
  document.getElementById('sc-engage').addEventListener('change', e => {
    const v = parseFloat(e.target.value);
    if (!Number.isNaN(v) && v >= 0) pushSettings({ engage_seconds: v });
  });
  document.getElementById('sc-occ-mode').onchange = e =>
    pushSettings({ occupied_mode: e.target.value });
  document.getElementById('sc-idle-mode').onchange = e =>
    pushSettings({ idle_mode: e.target.value });
  document.getElementById('sc-tare-btn').onclick = async () => {
    if (!confirm('Zero the scale at the current reading? (Bench should be empty.)')) return;
    try { await api('scale/tare', { method: 'POST' }); } catch {}
    refreshScale();
  };
  document.getElementById('sc-calib-btn').onclick = async () => {
    const raw = prompt(
      'Place a known weight on the centre of the bench, then enter its mass in kg:',
      '70'
    );
    if (!raw) return;
    const kg = parseFloat(raw);
    if (!(kg > 0)) { alert('Need a positive number of kg.'); return; }
    try {
      await api('scale/calibrate', { method: 'POST', body: JSON.stringify({ grams: kg * 1000 }) });
    } catch {}
    refreshScale();
  };
}

// ── Audio (per-track ambience loops + volume) ──────────────
// One block per track (ocean, fireplace, …) built from GET /api/audio.
// Each block has On/Off + a live volume slider that PUTs {track,…}. State
// is persisted server-side so toggles survive a restart.
let _audioBuilt = false;
const _audioVolLastEdit = {};   // per-track: ms of last slider edit

function _buildAudioTrackRow(name, tr) {
  const row = document.createElement('div');
  row.className = 'audio-track';
  row.dataset.track = name;
  row.innerHTML =
    `<div class="row-line">
       <label class="dim">${tr.label || name}</label>
       <button class="mode-btn at-on"  data-val="true">On</button>
       <button class="mode-btn at-off" data-val="false">Off</button>
       <span class="dim tiny at-status"></span>
     </div>
     <div class="row-line">
       <label class="dim">Volume</label>
       <input type="range" class="at-vol" min="0" max="100" step="1" style="flex:1;">
       <span class="dim tiny at-vol-val" style="min-width:38px; text-align:right;">—</span>
     </div>`;

  const put = (patch) =>
    api('audio', { method: 'PUT',
                   body: JSON.stringify({ track: name, ...patch }) })
      .catch(() => {});

  row.querySelector('.at-on').onclick  = async () => { await put({ enabled: true });  refreshAudio(); };
  row.querySelector('.at-off').onclick = async () => { await put({ enabled: false }); refreshAudio(); };

  // Live volume while dragging: throttle to ~8/sec + a final send on release.
  // Deliberately doesn't refreshAudio() per step (would snap the slider).
  const slider = row.querySelector('.at-vol');
  const valLabel = row.querySelector('.at-vol-val');
  let lastSent = 0, trailing = null;
  const sendVol = () => {
    lastSent = Date.now();
    const pct = parseInt(slider.value, 10);
    if (Number.isFinite(pct)) put({ volume: pct / 100 });
  };
  slider.addEventListener('input', () => {
    _audioVolLastEdit[name] = Date.now();
    valLabel.textContent = `${slider.value}%`;
    const wait = 120 - (Date.now() - lastSent);
    if (wait <= 0) { clearTimeout(trailing); trailing = null; sendVol(); }
    else if (!trailing) trailing = setTimeout(() => { trailing = null; sendVol(); }, wait);
  });
  slider.addEventListener('change', () => {
    clearTimeout(trailing); trailing = null; sendVol();
  });
  return row;
}

function _updateAudioTrackRow(name, tr, running) {
  const row = document.querySelector(`.audio-track[data-track="${name}"]`);
  if (!row) return;
  row.querySelector('.at-on').classList.toggle('active', tr.enabled === true);
  row.querySelector('.at-off').classList.toggle('active', tr.enabled === false);
  const slider = row.querySelector('.at-vol');
  const valLabel = row.querySelector('.at-vol-val');
  if (typeof tr.volume === 'number') {
    const pct = Math.round(tr.volume * 100);
    if (slider !== document.activeElement
        && Date.now() - (_audioVolLastEdit[name] || 0) > 1000) {
      slider.value = pct;
    }
    valLabel.textContent = `${pct}%`;
  }
  const status = row.querySelector('.at-status');
  if (tr.enabled && !tr.present)      status.textContent = `⚠ ${tr.file} missing on Pi`;
  else if (tr.enabled && !running)    status.textContent = '⚠ player not running';
  else                                status.textContent = '';
}

async function refreshAudio() {
  let s;
  try { s = await api('audio'); } catch { return; }
  if (!s || s.error || !s.tracks) return;
  const wrap = document.getElementById('audio-tracks');
  if (!wrap) return;
  if (!_audioBuilt) {
    wrap.innerHTML = '';
    for (const [name, tr] of Object.entries(s.tracks))
      wrap.appendChild(_buildAudioTrackRow(name, tr));
    _audioBuilt = true;
  }
  for (const [name, tr] of Object.entries(s.tracks))
    _updateAudioTrackRow(name, tr, s.running);
}

// Rows wire their own controls on build; kept for the init call site.
function bindAudioControls() {}

// Preview-phase dropdown for the breathing session. Persists to
// breathing.session.preview_phase via PUT /api/config; the engine
// reads it every frame and forces the matching render path so
// stubs can be eyeballed in the simulator while we tune them.
function bindBreathingPreviewPhase() {
  const sel = document.getElementById('breathing-preview-phase');
  if (!sel) return;
  const current = (config?.breathing?.session?.preview_phase) || 'auto';
  sel.value = current;
  sel.onchange = async () => {
    if (!config.breathing) config.breathing = {};
    if (!config.breathing.session) config.breathing.session = {};
    config.breathing.session.preview_phase = sel.value;
    try {
      await api('config', {
        method: 'PUT',
        body: JSON.stringify(nestedUpdate('breathing.session', 'preview_phase', sel.value)),
      });
    } catch {}
  };
}

// ── Telemetry history charts ───────────────────────────────
// SVG viewBox is fixed at 900×110; the chart resizes via CSS but the
// internal coordinate space stays constant so layout math is simple.
const TH_W = 900, TH_H = 110, TH_PAD = 4;
const TH_MODE_COLORS = {
  breathing: '#b58cff',   // accent purple
  standby:   '#5dc46d',   // green
  midi:      '#5ec8ff',   // cyan (inherited from the old "scene" color)
  fireplace: '#ff8a3a',   // orange
  debug:     '#e0654a',   // red
  off:       '#5a5a64',   // grey
  unknown:   '#8c8c95',
  // Legacy: pre-rename rows are remapped to "midi" by the backend
  // before this map is consulted, but keep the alias just in case.
  scene:     '#5ec8ff',
};
const TH_LEG_COLORS = {
  leg1:  '#e0a64a',
  leg2:  '#ff8a3a',
  total: '#d8d8df',
};
function thModeColor(name) {
  return TH_MODE_COLORS[name] || '#b58cff';
}

const _thState = {
  range: '1h',
  // modes the user has chosen to display (null = all). Persists across
  // refreshes within the session so toggling doesn't reset on every poll.
  visibleModes: null,
};

function fmtPST(unixSec, includeDate) {
  const d = new Date(unixSec * 1000);
  const opts = {
    timeZone: 'America/Los_Angeles',
    hour: '2-digit', minute: '2-digit', hour12: false,
  };
  if (includeDate) Object.assign(opts, { month: 'short', day: 'numeric' });
  return d.toLocaleString('en-US', opts);
}
function fmtDuration(seconds) {
  seconds = Math.round(seconds);
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return s ? `${m}m ${s}s` : `${m}m`;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return mm ? `${h}h ${mm}m` : `${h}h`;
}

function _svgClear(svg) {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
}
function _svgEl(name, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  return el;
}
function _svgEmpty(svg, msg) {
  _svgClear(svg);
  svg.appendChild(_svgEl('text', {
    x: TH_W / 2, y: TH_H / 2, 'text-anchor': 'middle',
    'dominant-baseline': 'middle', class: 'th-empty-msg',
  })).textContent = msg;
}

// ── Energy chart: simple line + soft fill ─
function thRenderEnergy(svg, samples, tMin, tMax) {
  _svgClear(svg);
  if (!samples.length) return _svgEmpty(svg, 'no data yet');
  const ys = samples.map(s => Math.max(0, s.energy_wh));
  const yMax = Math.max(0.01, Math.max(...ys) * 1.1);
  const tx = (t) => TH_PAD + (t - tMin) / Math.max(1, tMax - tMin) * (TH_W - TH_PAD * 2);
  const yy = (v) => TH_PAD + (1 - v / yMax) * (TH_H - TH_PAD * 2);
  let line = '';
  let fill = `M ${tx(samples[0].ts)} ${TH_H} `;
  samples.forEach((s, i) => {
    line += (i === 0 ? 'M ' : 'L ') + tx(s.ts).toFixed(1) + ' ' + yy(s.energy_wh).toFixed(1) + ' ';
    fill += `L ${tx(s.ts).toFixed(1)} ${yy(s.energy_wh).toFixed(1)} `;
  });
  fill += `L ${tx(samples[samples.length - 1].ts).toFixed(1)} ${TH_H} Z`;
  svg.appendChild(_svgEl('path', { d: fill, fill: '#b58cff', opacity: '0.18' }));
  svg.appendChild(_svgEl('path', { d: line, fill: 'none',
    stroke: '#b58cff', 'stroke-width': '1.3' }));
  // Axis hint
  svg.appendChild(_svgEl('text', {
    x: TH_W - TH_PAD - 2, y: TH_PAD + 8, 'text-anchor': 'end',
    class: 'th-empty-msg',
  })).textContent = `max ${yMax.toFixed(3)}`;
}

// ── Mode stacked-area chart ─
function thRenderModes(svg, samples, tMin, tMax) {
  _svgClear(svg);
  if (!samples.length) return _svgEmpty(svg, 'no data yet');
  // Stable mode order: by total seconds, descending.
  const totals = {};
  for (const s of samples) {
    for (const [m, sec] of Object.entries(s.mode_durations || {})) {
      totals[m] = (totals[m] || 0) + sec;
    }
  }
  const allModes = Object.keys(totals).sort((a, b) => totals[b] - totals[a]);
  const modes = (_thState.visibleModes == null)
    ? allModes
    : allModes.filter(m => _thState.visibleModes.includes(m));

  const tx = (t) => TH_PAD + (t - tMin) / Math.max(1, tMax - tMin) * (TH_W - TH_PAD * 2);
  const yy = (v, max) => TH_PAD + (1 - v / max) * (TH_H - TH_PAD * 2);
  // Y max = 60 s (a full minute). Keep this constant so chart heights
  // stay comparable across ranges.
  const yMax = 60;

  // Build cumulative stack per timestamp.
  const stacks = samples.map(s => {
    let cum = 0;
    const out = {};
    for (const m of modes) {
      const v = (s.mode_durations || {})[m] || 0;
      out[m] = { base: cum, top: cum + v };
      cum += v;
    }
    return out;
  });

  for (let i = 0; i < modes.length; i++) {
    const m = modes[i];
    let path = '';
    // Top edge L→R
    samples.forEach((s, j) => {
      path += (j === 0 ? 'M ' : 'L ') + tx(s.ts).toFixed(1) + ' ' + yy(stacks[j][m].top, yMax).toFixed(1) + ' ';
    });
    // Bottom edge R→L (the previous stack's top, or 0)
    for (let j = samples.length - 1; j >= 0; j--) {
      path += 'L ' + tx(samples[j].ts).toFixed(1) + ' ' + yy(stacks[j][m].base, yMax).toFixed(1) + ' ';
    }
    path += 'Z';
    svg.appendChild(_svgEl('path', {
      d: path, fill: thModeColor(m), opacity: '0.75',
    }));
  }
  // Legend chips (top-right)
  let xLeg = TH_W - TH_PAD;
  for (let i = modes.length - 1; i >= 0; i--) {
    const m = modes[i];
    const t = _svgEl('text', {
      x: xLeg, y: TH_PAD + 9, 'text-anchor': 'end',
      class: 'th-empty-msg', fill: thModeColor(m),
    });
    t.textContent = m;
    svg.appendChild(t);
    xLeg -= (m.length * 6 + 10);
  }
}

// ── Weight chart: 3 lines (leg1 / leg2 / total) ─
function thRenderWeight(svg, samples, tMin, tMax) {
  _svgClear(svg);
  if (!samples.length) return _svgEmpty(svg, 'no data yet');
  const series = [
    { key: 'leg1_g', label: 'leg 1', color: TH_LEG_COLORS.leg1 },
    { key: 'leg2_g', label: 'leg 2', color: TH_LEG_COLORS.leg2 },
    { key: 'total_g', label: 'total', color: TH_LEG_COLORS.total },
  ];
  // Y range: include 0 and the max of all series. In kg, with a little
  // headroom so the line doesn't kiss the top edge.
  let yMax = 1;  // kg, minimum range
  for (const s of samples) {
    for (const ser of series) {
      const v = (s[ser.key] || 0) / 1000;
      if (v > yMax) yMax = v;
    }
  }
  yMax *= 1.1;
  const tx = (t) => TH_PAD + (t - tMin) / Math.max(1, tMax - tMin) * (TH_W - TH_PAD * 2);
  const yy = (v) => TH_PAD + (1 - v / yMax) * (TH_H - TH_PAD * 2);
  // Zero line if data crosses zero (negative tare).
  svg.appendChild(_svgEl('line', {
    x1: TH_PAD, x2: TH_W - TH_PAD, y1: yy(0), y2: yy(0),
    stroke: '#25252e', 'stroke-width': '0.8', 'stroke-dasharray': '3 3',
  }));
  for (const ser of series) {
    let path = '';
    samples.forEach((s, i) => {
      const v = (s[ser.key] || 0) / 1000;
      path += (i === 0 ? 'M ' : 'L ') + tx(s.ts).toFixed(1) + ' ' + yy(v).toFixed(1) + ' ';
    });
    svg.appendChild(_svgEl('path', {
      d: path, fill: 'none', stroke: ser.color, 'stroke-width': '1.3',
    }));
  }
  // Legend
  let xLeg = TH_W - TH_PAD;
  for (let i = series.length - 1; i >= 0; i--) {
    const ser = series[i];
    const t = _svgEl('text', {
      x: xLeg, y: TH_PAD + 9, 'text-anchor': 'end',
      class: 'th-empty-msg', fill: ser.color,
    });
    t.textContent = ser.label;
    svg.appendChild(t);
    xLeg -= (ser.label.length * 6 + 10);
  }
  // Axis hint
  const tMax2 = _svgEl('text', {
    x: TH_PAD + 2, y: TH_PAD + 9,
    class: 'th-empty-msg',
  });
  tMax2.textContent = `${yMax.toFixed(1)} kg`;
  svg.appendChild(tMax2);
}

function thRenderXAxis(tMin, tMax) {
  const el = document.getElementById('th-xaxis');
  el.innerHTML = '';
  // 5 evenly spaced ticks.
  const span = tMax - tMin;
  const showDate = span > 6 * 3600;
  for (let i = 0; i < 5; i++) {
    const t = tMin + (i / 4) * span;
    const span_el = document.createElement('span');
    span_el.textContent = fmtPST(t, showDate);
    el.appendChild(span_el);
  }
}

function thRenderModeFilter(allModes) {
  const el = document.getElementById('th-mode-filter');
  el.innerHTML = '';
  const visible = _thState.visibleModes;
  for (const m of allModes) {
    const chip = document.createElement('span');
    chip.className = 'th-mode-chip active';
    if (visible != null && !visible.includes(m)) chip.classList.add('muted');
    chip.style.color = thModeColor(m);
    chip.textContent = m;
    chip.onclick = () => {
      const cur = (_thState.visibleModes == null) ? [...allModes] : [..._thState.visibleModes];
      const idx = cur.indexOf(m);
      if (idx >= 0) cur.splice(idx, 1);
      else cur.push(m);
      _thState.visibleModes = cur.length === allModes.length ? null : cur;
      refreshHistory();  // re-fetch + redraw
    };
    el.appendChild(chip);
  }
}

async function refreshHistory() {
  const range = _thState.range;
  let data;
  try {
    data = await api('telemetry/history?range=' + encodeURIComponent(range));
  } catch {
    return;
  }
  if (!data || data.error) return;
  const samples = data.samples || [];
  const tMin = data.range_start_ts;
  const tMax = data.range_end_ts;

  // Totals row. Standard energy notation:
  //   total energy   → Wh        (cumulative consumption over the range)
  //   average power  → Wh/hr     (= W; lets the user eyeball runtime:
  //                               battery_Wh ÷ Wh_per_hr = hours)
  // `avg_watts` is excluded for gaps (only counts time we actually
  // recorded), so a wide window with sparse coverage doesn't fake a
  // low average.
  const totals = data.totals || {};
  const totalEnergy = totals.energy_wh || 0;
  const avgPower = totals.avg_watts || 0;
  document.getElementById('th-total-energy').textContent =
    `${avgPower.toFixed(1)} Wh/hr avg`;
  const modeTotals = totals.mode_durations || {};
  const modeOrder = Object.keys(modeTotals).sort((a, b) => modeTotals[b] - modeTotals[a]);
  document.getElementById('th-total-modes').textContent =
    modeOrder.length
      ? modeOrder.map(m => `${m}: ${fmtDuration(modeTotals[m])}`).join(' · ')
      : '';

  // Per-chart titles get their own totals in-context — the user can
  // see "what's this chart showing + what does it add up to" at a glance
  // without scrolling back to the summary row.
  document.getElementById('th-label-energy').textContent =
    `Energy (Wh / min) — total ${totalEnergy.toFixed(3)} Wh (avg ${avgPower.toFixed(1)} Wh/hr)`;
  document.getElementById('th-label-modes').textContent =
    modeOrder.length
      ? `Time per mode (s / min) — ${modeOrder.map(m => `${m} ${fmtDuration(modeTotals[m])}`).join(', ')}`
      : 'Time per mode (s / min)';

  // Mode filter chips reflect the universe of modes seen in this range.
  thRenderModeFilter(modeOrder.length ? modeOrder : ['breathing', 'standby']);

  // Charts (energy + weight aren't affected by the mode filter; modes one is).
  thRenderEnergy(document.getElementById('th-chart-energy'), samples, tMin, tMax);
  thRenderModes(document.getElementById('th-chart-modes'), samples, tMin, tMax);
  thRenderWeight(document.getElementById('th-chart-weight'), samples, tMin, tMax);
  thRenderXAxis(tMin, tMax);
}

async function refreshClockStatus() {
  let c;
  try { c = await api('telemetry/clock'); } catch { return; }
  const el = document.getElementById('th-clock-warn');
  if (!c) return;
  if (c.ntp_synchronized === false) {
    el.textContent = '⚠ NTP not synced — timestamps may drift';
    el.hidden = false;
  } else {
    el.hidden = true;
  }
}

function bindHistoryControls() {
  const sel = document.getElementById('th-range');
  sel.addEventListener('change', e => {
    _thState.range = e.target.value;
    // Reset mode filter so we don't keep stale selections across ranges.
    _thState.visibleModes = null;
    refreshHistory();
  });
}

function drawSparkline(samples) {
  const svg = document.getElementById('temp-chart');
  const W = 200, H = 60, PAD = 4;
  if (!samples.length) {
    svg.querySelectorAll('path').forEach(p => p.setAttribute('d', ''));
    return;
  }
  const ys = samples.map(s => s.c);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  if (hi - lo < 5) { lo = Math.floor(lo) - 2; hi = Math.ceil(hi) + 2; }
  const sx = (i) => PAD + i * (W - PAD * 2) / Math.max(1, samples.length - 1);
  const sy = (c) => PAD + (1 - (c - lo) / (hi - lo)) * (H - PAD * 2);
  let line = '';
  let fill = `M ${sx(0)} ${H} L `;
  samples.forEach((s, i) => {
    line += (i === 0 ? 'M ' : 'L ') + sx(i).toFixed(1) + ' ' + sy(s.c).toFixed(1) + ' ';
    fill += sx(i).toFixed(1) + ' ' + sy(s.c).toFixed(1) + ' ';
  });
  fill += `L ${sx(samples.length - 1)} ${H} Z`;
  svg.querySelector('path').setAttribute('d', line);
  svg.querySelector('path.fill').setAttribute('d', fill);
}

// ── Logs ───────────────────────────────────────────────────
async function pollLogs() {
  try {
    const { logs } = await api('logs');
    const el = document.getElementById('log-viewer');
    el.textContent = logs.join('\n');
    el.scrollTop = el.scrollHeight;
  } catch {}
}

// ── Spin controls ──────────────────────────────────────────
function initSpinControls() {
  const spin = config.breathing?.spin || {};

  // All three rows follow the same toggle-picker pattern. The shared
  // click handler PUTs a single-key patch under `breathing.spin` and
  // re-fetches the full config so other readers stay in sync.
  async function pushSpin(patch) {
    await api('config', {
      method: 'PUT',
      body: JSON.stringify({ breathing: { spin: patch } }),
    });
    config = await api('config');
  }
  refreshToggle('.spin-toggle',   spin.enabled || false);
  refreshToggle('.spin-mode-btn', spin.mode || 'constant');
  refreshToggle('.spin-dir-btn',  spin.yoyo_reverse ?? true);
  bindToggle('.spin-toggle',   v => pushSpin({ enabled: v === 'true' }));
  bindToggle('.spin-mode-btn', v => pushSpin({ mode: v }));
  bindToggle('.spin-dir-btn',  v => pushSpin({ yoyo_reverse: v === 'true' }));

  // Sliders
  const el = document.getElementById('spin-params');
  el.innerHTML = '';
  SPIN_SLIDERS.forEach(s => {
    const val = spin[s.key] ?? s.min;
    const row = document.createElement('div');
    row.className = 'param-row';
    row.innerHTML = `
      <label>${s.label}</label>
      <input type="range" min="${s.min}" max="${s.max}" step="${s.step}" value="${val}">
      <span class="val">${val}</span>
    `;
    const input = row.querySelector('input');
    const span = row.querySelector('.val');
    input.oninput = () => {
      const v = parseFloat(input.value);
      span.textContent = v;
      clearTimeout(updateTimer);
      updateTimer = setTimeout(() => {
        api('config', {
          method: 'PUT',
          body: JSON.stringify({ breathing: { spin: { [s.key]: v } } }),
        });
      }, 100);
    };
    el.appendChild(row);
  });
}

// ── Palette selector ───────────────────────────────────────
function buildPaletteSelector() {
  const container = document.getElementById('palette-selector');
  const editor = document.getElementById('palette-editor');
  const palettes = config.breathing?.palettes || [];
  const active = config.breathing?.active_palette || 0;

  container.innerHTML = '';
  const btnRow = document.createElement('div');
  btnRow.style.cssText = 'display:flex;gap:8px;';

  palettes.forEach((pal, i) => {
    const btn = document.createElement('button');
    btn.className = 'palette-btn' + (i === active ? ' active' : '');
    btn.style.cssText = `
      flex:1; height:60px; border:2px solid ${i === active ? '#7744aa' : '#333'};
      border-radius:8px; cursor:pointer; position:relative;
      overflow:hidden; background:#111;
    `;
    // Color preview stripe — all 8 slots so the user sees the full palette.
    const colors = PALETTE_COLOR_KEYS.map(k => pal[k] || [60, 60, 60]);
    const gradient = colors.map((c, ci) => {
      const pct = (ci / (colors.length - 1)) * 100;
      return `rgb(${c[0]},${c[1]},${c[2]}) ${pct}%`;
    }).join(', ');
    btn.innerHTML = `
      <div style="position:absolute;inset:0;background:linear-gradient(90deg,${gradient});opacity:0.7;"></div>
      <div style="position:relative;color:#fff;font:bold 16px monospace;text-shadow:0 1px 3px #000;">${i + 1}</div>
    `;
    btn.onclick = async () => {
      await api('config', {
        method: 'PUT',
        body: JSON.stringify({ breathing: { active_palette: i } }),
      });
      config.breathing.active_palette = i;
      buildPaletteSelector();
    };
    btnRow.appendChild(btn);
  });
  container.appendChild(btnRow);

  // Editor for the active palette
  editor.innerHTML = '';
  const pal = palettes[active] || {};
  PALETTE_COLOR_KEYS.forEach(key => {
    const val = pal[key] || [0, 0, 0];
    const label = PALETTE_COLOR_LABELS[key] || key;
    const row = document.createElement('div');
    row.className = 'param-row palette-color-row';
    row.innerHTML = `
      <label>${label}</label>
      <input type="color" value="${rgbToHex(val)}">
      <span class="val">${JSON.stringify(val)}</span>
    `;
    const input = row.querySelector('input');
    const span = row.querySelector('.val');
    input.oninput = () => {
      const rgb = hexToRgb(input.value);
      span.textContent = JSON.stringify(rgb);
      const pals = config.breathing.palettes;
      pals[active][key] = rgb;
      debouncedUpdate('breathing', 'palettes', pals);
      // Update gradient previews + FX color swatches without rebuilding
      // the editor.
      updatePaletteGradients();
      refreshFxColorSwatches();
    };
    editor.appendChild(row);
  });
}

function updatePaletteGradients() {
  const palettes = config.breathing?.palettes || [];
  document.querySelectorAll('.palette-btn').forEach((btn, i) => {
    const pal = palettes[i];
    if (!pal) return;
    const colors = PALETTE_COLOR_KEYS.map(k => pal[k] || [60, 60, 60]);
    const gradient = colors.map((c, ci) => {
      const pct = (ci / (colors.length - 1)) * 100;
      return `rgb(${c[0]},${c[1]},${c[2]}) ${pct}%`;
    }).join(', ');
    const gradDiv = btn.querySelector('div');
    if (gradDiv) gradDiv.style.background = `linear-gradient(90deg,${gradient})`;
  });
}

// Refresh palette-tinted FX color picker options after user edits a slot.
function refreshFxColorSwatches() {
  const pcolors = _activePaletteColors();
  document.querySelectorAll('.event-color').forEach(sel => {
    Array.from(sel.options).forEach((o, k) => {
      const c = pcolors[k];
      if (!c) return;
      o.style.backgroundColor = `rgb(${c[0]},${c[1]},${c[2]})`;
      o.style.color = (c[0] + c[1] + c[2] > 380) ? '#000' : '#fff';
    });
  });
}

// ── Scene tab ──────────────────────────────────────────────
function nearestDurationLabel(beats) {
  // Pick the closest standard duration label for an arbitrary beat count.
  let best = DURATIONS[0];
  for (const d of DURATIONS) {
    if (Math.abs(d.beats - beats) < Math.abs(best.beats - beats)) best = d;
  }
  return best.label;
}

// (The per-event trigger row was removed — events are now driven solely by
// the sequencer's piano roll. The makeKnob widget above is kept; we'll use
// it for other parameters later.)

function buildScenePaletteSelector() {
  const container = document.getElementById('scene-palette-selector');
  if (!container) return;
  const palettes = config.breathing?.palettes || [];
  container.innerHTML = '';
  const btnRow = document.createElement('div');
  btnRow.style.cssText = 'display:flex;gap:8px;';
  palettes.forEach((pal, i) => {
    const btn = document.createElement('button');
    btn.className = 'palette-btn';
    btn.style.cssText = `
      flex:1; height:50px; border:2px solid #333;
      border-radius:8px; cursor:pointer; position:relative;
      overflow:hidden; background:#111; min-width:0;
    `;
    const colors = PALETTE_COLOR_KEYS.map(k => pal[k] || [60, 60, 60]);
    const gradient = colors.map((c, ci) => {
      const pct = (ci / (colors.length - 1)) * 100;
      return `rgb(${c[0]},${c[1]},${c[2]}) ${pct}%`;
    }).join(', ');
    btn.innerHTML = `
      <div style="position:absolute;inset:0;background:linear-gradient(90deg,${gradient});opacity:0.75;"></div>
      <div style="position:relative;color:#fff;font:bold 16px monospace;text-shadow:0 1px 3px #000;">${i + 1}</div>
    `;
    btn.title = `Trigger color_palette → palette ${i+1}`;
    btn.onclick = () => {
      const beats = config.scene?.default_durations?.color_palette ?? 2;
      api('scene/event/color_palette', {
        method: 'POST',
        body: JSON.stringify({ duration_beats: beats, params: { palette: i } }),
      });
    };
    btnRow.appendChild(btn);
  });
  container.appendChild(btnRow);
}

function bindSceneClock() {
  const bpmInput = document.getElementById('scene-bpm');
  const resetBtn = document.getElementById('scene-beat-reset');
  const tapBtn   = document.getElementById('scene-tap-tempo');
  if (bpmInput) {
    bpmInput.value = config.scene?.bpm ?? 120;
    bpmInput.onchange = async () => {
      const bpm = parseFloat(bpmInput.value);
      if (isNaN(bpm) || bpm <= 0) return;
      await api('scene/bpm', { method: 'POST', body: JSON.stringify({ bpm }) });
    };
  }
  if (resetBtn) {
    // "Set 1" — gradually drift the loop so the moment of tap becomes the
    // start of the loop (loop_pos = 0). The server compensates for the
    // JS-to-network gap using the timestamp pair we send.
    resetBtn.onclick = async () => {
      const clientTap = performance.now();
      const r = await api('scene/beat', {
        method: 'POST',
        body: JSON.stringify({
          client_tap_t_ms: clientTap,
          client_now_t_ms: performance.now(),
        }),
      });
      if (r && typeof r.correction_beats === 'number') {
        resetBtn.textContent = `Set 1 (Δ${r.correction_beats >= 0 ? '+' : ''}${r.correction_beats.toFixed(2)})`;
        clearTimeout(resetBtn._restoreTimer);
        resetBtn._restoreTimer = setTimeout(() => { resetBtn.textContent = 'Set 1'; }, 2500);
      }
    };
  }
  // Tap tempo — server-side BPM (median of rolling window) + phase alignment.
  if (tapBtn) {
    tapBtn.onclick = async () => {
      const clientTap = performance.now();
      const r = await api('scene/tap', {
        method: 'POST',
        body: JSON.stringify({
          client_tap_t_ms: clientTap,
          client_now_t_ms: performance.now(),
        }),
      });
      if (r && typeof r.bpm === 'number') {
        tapBtn.textContent = r.taps_in_window > 1 ? `Tap (${r.bpm.toFixed(1)})` : 'Tap…';
        if (bpmInput && r.bpm_updated) bpmInput.value = r.bpm.toFixed(1);
        clearTimeout(tapBtn._restoreTimer);
        tapBtn._restoreTimer = setTimeout(() => { tapBtn.textContent = 'Tap'; }, 2500);
      }
    };
  }
}

// ── VST-style rotary knob ───────────────────────────────────
// Discrete-value rotary control. Drag vertically to step through `values`.
// Snaps to allowed values; renders an arc filling proportional to position.
function makeKnob({ values, formatLabel, initial, onChange }) {
  const wrap = document.createElement('div');
  wrap.className = 'knob';
  wrap.innerHTML = `
    <svg viewBox="0 0 40 40">
      <circle class="knob-track" cx="20" cy="20" r="14"></circle>
      <path class="knob-fill" d=""></path>
      <line class="knob-pointer" x1="20" y1="20" x2="20" y2="9"></line>
    </svg>
    <div class="knob-label"></div>
  `;
  const fill = wrap.querySelector('.knob-fill');
  const pointer = wrap.querySelector('.knob-pointer');
  const label = wrap.querySelector('.knob-label');
  const svg = wrap.querySelector('svg');

  let idx = Math.max(0, values.findIndex(v => v === initial));
  if (idx < 0) idx = 0;

  // Knob arc spans 270° centered at the bottom (from 7:30 position to 4:30).
  const MIN_DEG = -135, MAX_DEG = 135;

  function render() {
    const v = values[idx];
    const t = values.length > 1 ? idx / (values.length - 1) : 0.5;
    const deg = MIN_DEG + t * (MAX_DEG - MIN_DEG);
    const rad = deg * Math.PI / 180;
    // Arc from MIN_DEG to current deg.
    const r = 14;
    const ax0 = 20 + r * Math.sin(MIN_DEG * Math.PI / 180);
    const ay0 = 20 - r * Math.cos(MIN_DEG * Math.PI / 180);
    const ax1 = 20 + r * Math.sin(rad);
    const ay1 = 20 - r * Math.cos(rad);
    const large = (deg - MIN_DEG) > 180 ? 1 : 0;
    fill.setAttribute('d', `M ${ax0.toFixed(2)} ${ay0.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${ax1.toFixed(2)} ${ay1.toFixed(2)}`);
    pointer.setAttribute('x2', (20 + 10 * Math.sin(rad)).toFixed(2));
    pointer.setAttribute('y2', (20 - 10 * Math.cos(rad)).toFixed(2));
    label.textContent = formatLabel ? formatLabel(v) : String(v);
  }
  render();

  // Drag handling: vertical mouse movement → step value. Coarse threshold so
  // each ~10px of drag picks the next value.
  let dragStartY = null, dragStartIdx = idx;
  const onDown = (e) => {
    e.preventDefault();
    dragStartY = e.clientY ?? (e.touches && e.touches[0].clientY);
    dragStartIdx = idx;
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    document.addEventListener('touchmove', onMove, { passive: false });
    document.addEventListener('touchend', onUp);
  };
  const onMove = (e) => {
    if (dragStartY == null) return;
    e.preventDefault?.();
    const y = e.clientY ?? (e.touches && e.touches[0].clientY);
    if (y == null) return;
    const dy = dragStartY - y;        // up = positive
    const step = Math.round(dy / 12); // 12 px per step
    const newIdx = Math.max(0, Math.min(values.length - 1, dragStartIdx + step));
    if (newIdx !== idx) {
      idx = newIdx;
      render();
      onChange?.(values[idx]);
    }
  };
  const onUp = () => {
    dragStartY = null;
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.removeEventListener('touchmove', onMove);
    document.removeEventListener('touchend', onUp);
  };
  svg.addEventListener('mousedown', onDown);
  svg.addEventListener('touchstart', onDown, { passive: false });
  // Scroll wheel as bonus input.
  svg.addEventListener('wheel', (e) => {
    e.preventDefault();
    const step = e.deltaY < 0 ? 1 : -1;
    const newIdx = Math.max(0, Math.min(values.length - 1, idx + step));
    if (newIdx !== idx) { idx = newIdx; render(); onChange?.(values[idx]); }
  }, { passive: false });

  return {
    el: wrap,
    get value() { return values[idx]; },
    setValue(v) {
      const i = values.findIndex(x => Math.abs(x - v) < 1e-6);
      if (i >= 0 && i !== idx) { idx = i; render(); }
    },
  };
}

// ── Piano roll (sequencer) ───────────────────────────────────
const LANE_HEIGHT = 22;
const RULER_HEIGHT = 18;
const LABEL_WIDTH = 110;
const PX_PER_BEAT_DEFAULT = 26;
const PX_PER_BEAT_MIN = 8;
const PX_PER_BEAT_MAX = 80;
const RESIZE_EDGE = 5;     // px from right edge that counts as "resize" zone
const MARQUEE_THRESHOLD = 4;  // px of movement before drag becomes marquee

let _pianoRoll = null;
// Set of lane events currently held down via piano-roll click — used to
// fire matching note_off on mouseup.
let _heldNoteEvents = new Set();

// Fire a sequencer note's bound event as note_on (mousedown). The router
// supports note_on/note_off semantics so events that sustain (Float
// Center, held expand/contract) auto-release on mouseup.
function triggerNoteEvent(note) {
  const r = _pianoRoll;
  if (!r || !note) return;
  const lane = (r.lanes || [])[note.pitch];
  if (!lane || !lane.event) return;
  fetch(`/api/scene/event/${encodeURIComponent(lane.event)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      duration_beats: note.length_beats,
      params: lane.params || {},
      event_type: 'note_on',
    }),
  }).catch(() => {});
  _heldNoteEvents.add(lane.event);
}

function releaseHeldNoteEvents() {
  if (_heldNoteEvents.size === 0) return;
  const events = [..._heldNoteEvents];
  _heldNoteEvents.clear();
  for (const ev of events) {
    fetch(`/api/scene/event/${encodeURIComponent(ev)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_type: 'note_off' }),
    }).catch(() => {});
  }
}

// Lane label click — fire the lane's event with the lane's bound params.
// Held in _heldNoteEvents so mouseup → note_off cleans up sustained events.
function fireLaneEventDown(lane) {
  if (!lane || !lane.event) return;
  fetch(`/api/scene/event/${encodeURIComponent(lane.event)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      params: lane.params || {},
      event_type: 'note_on',
    }),
  }).catch(() => {});
  _heldNoteEvents.add(lane.event);
}

// ── Patch picker (synth + curves + physics snapshots) ─────────
let _activePatchName = null;

async function refreshPatchPicker() {
  const sel = document.getElementById('patch-picker');
  if (!sel) return;
  let list = [];
  try { list = (await api('scene/patches')).patches || []; } catch { list = []; }
  sel.innerHTML = '';
  if (list.length === 0) {
    const o = document.createElement('option');
    o.value = ''; o.textContent = '(none saved)';
    sel.appendChild(o);
  }
  for (const p of list) {
    const o = document.createElement('option');
    o.value = p.name; o.textContent = p.name;
    sel.appendChild(o);
  }
  if (_activePatchName && list.some(p => p.name === _activePatchName)) {
    sel.value = _activePatchName;
  }
}

async function refreshAllSynthUI() {
  // Re-read config + re-build synth panes after a patch load.
  try { config = await api('config'); } catch {}
  buildSynthOvals();
  await loadEventDefaults();
  buildSynthEvents();
  await buildSynthPhysics();
  // Refresh palette selector + BPM input.
  if (typeof buildScenePaletteSelector === 'function') buildScenePaletteSelector();
  const bpmInput = document.getElementById('scene-bpm');
  if (bpmInput) bpmInput.value = config.scene?.bpm ?? 120;
}

function bindPatchPicker() {
  const sel = document.getElementById('patch-picker');
  const loadBtn = document.getElementById('patch-load');
  const saveBtn = document.getElementById('patch-save');
  const newBtn  = document.getElementById('patch-new');
  const delBtn  = document.getElementById('patch-delete');
  const resetBtn = document.getElementById('scene-reset');
  if (resetBtn) resetBtn.onclick = () => api('scene/reset', { method: 'POST' });
  if (sel) {
    sel.onchange = () => { _activePatchName = sel.value || null; };
  }
  if (loadBtn) loadBtn.onclick = async () => {
    if (!sel || !sel.value) return;
    await api(`scene/patches/${encodeURIComponent(sel.value)}/load`, { method: 'POST' });
    _activePatchName = sel.value;
    await refreshAllSynthUI();
  };
  if (saveBtn) saveBtn.onclick = async () => {
    let name = sel && sel.value;
    if (!name) {
      name = prompt('Patch name', 'untitled');
      if (!name) return;
    } else if (!confirm(`Overwrite "${name}"?`)) {
      return;
    }
    await api(`scene/patches/${encodeURIComponent(name)}/save`, { method: 'POST' });
    _activePatchName = name;
    await refreshPatchPicker();
  };
  if (newBtn) newBtn.onclick = async () => {
    const name = prompt('New patch name', 'untitled');
    if (!name) return;
    const r = await api('scene/patches/new', {
      method: 'POST', body: JSON.stringify({ name }),
    });
    if (r && r.name) _activePatchName = r.name;
    await refreshPatchPicker();
  };
  if (delBtn) delBtn.onclick = async () => {
    if (!sel || !sel.value) return;
    if (!confirm(`Delete patch "${sel.value}"?`)) return;
    await api(`scene/patches/${encodeURIComponent(sel.value)}`, { method: 'DELETE' });
    _activePatchName = null;
    await refreshPatchPicker();
  };
}

// MIDI tab sub-tab switching.
function buildSubtabs() {
  // Scope subtab toggling to the containing tab pane so MIDI's subtabs
  // and Tune's subtabs don't fight each other.
  document.querySelectorAll('.subtab').forEach(tab => {
    tab.addEventListener('click', () => {
      const name = tab.dataset.subtab;
      const scope = tab.closest('.pane') || document;
      scope.querySelectorAll('.subtab').forEach(t =>
        t.classList.toggle('active', t === tab));
      scope.querySelectorAll('.subpane').forEach(p =>
        p.classList.toggle('active', p.dataset.pane === name));
    });
  });
}

// Wrap a NexusUI Dial so mouse-wheel scrolling adjusts its value. Step is
// dial.step if set, else (max - min) / 100. Wheel direction: up = increase.
function attachWheel(dial, opts = {}) {
  const step = opts.step ?? dial.step ?? ((dial.max - dial.min) / 100);
  const el = dial.parent;   // NexusUI mounts inside the passed div
  if (!el) return;
  el.addEventListener('wheel', e => {
    e.preventDefault();
    // Bigger jumps when Shift is held.
    const factor = e.shiftKey ? 5 : 1;
    const delta = (e.deltaY < 0 ? +1 : -1) * step * factor;
    let v = dial.value + delta;
    v = Math.max(dial.min, Math.min(dial.max, v));
    dial.value = v;
  }, { passive: false });
}

// Convenience: build a Nexus.Dial with wheel support + double-click reset.
// `defaultValue` is the value the dial snaps back to on dblclick.
function makeDial(el, { min, max, step, value, size = [44, 44], defaultValue }, onChange) {
  const initial = Math.max(min, Math.min(max, value));
  const dial = new Nexus.Dial(el, {
    size, min, max, step,
    value: initial,
    mode: 'relative',
  });
  attachWheel(dial, { step });
  dial.on('change', onChange);
  // Double-click anywhere on the knob → reset to the default value.
  if (el) {
    const resetValue = (defaultValue == null) ? initial : defaultValue;
    el.addEventListener('dblclick', e => {
      e.preventDefault();
      dial.value = Math.max(min, Math.min(max, resetValue));
    });
  }
  return dial;
}

// ── Synth Ovals pane (compact row layout, knob trio per oval) ─
function buildSynthOvals() {
  const wrap = document.getElementById('synth-ovals');
  if (!wrap) return;
  wrap.innerHTML = '';
  // Index meaning (new): 0 = Outer, 1 = Middle (drawn on top), 2 = Inner.
  const titles = ['Outer', 'Middle', 'Inner'];
  for (let i = 0; i < 3; i++) {
    const cell = document.createElement('div');
    cell.className = 'oval-cell';

    const title = document.createElement('div');
    title.className = 'oval-title';
    title.textContent = titles[i];
    cell.appendChild(title);

    // Per-oval palette slot picker (0..7). Maps to state[oval_color_i]
    // which the renderer dereferences into the active palette. Tinted
    // option labels so the user sees the actual color swatches.
    const colorSel = document.createElement('select');
    colorSel.className = 'event-color oval-color';
    colorSel.title = 'Color slot';
    const pcolors = _activePaletteColors();
    const curColor = parseInt(config.scene?.synth?.[`oval_color_${i}`] ?? i, 10);
    for (let k = 0; k < 8; k++) {
      const o = document.createElement('option');
      o.value = String(k);
      o.textContent = COLOR_SLOT_NAMES[k];
      const c = pcolors[k];
      o.style.backgroundColor = `rgb(${c[0]},${c[1]},${c[2]})`;
      o.style.color = (c[0] + c[1] + c[2] > 380) ? '#000' : '#fff';
      colorSel.appendChild(o);
    }
    colorSel.value = String(curColor);
    colorSel.addEventListener('change', () => {
      const v = parseInt(colorSel.value, 10);
      if (!config.scene) config.scene = {};
      if (!config.scene.synth) config.scene.synth = {};
      config.scene.synth[`oval_color_${i}`] = v;
      api('scene/synth', {
        method: 'PUT',
        body: JSON.stringify({ [`oval_color_${i}`]: v }),
      });
    });
    cell.appendChild(colorSel);

    const enabled = !!(config.scene?.synth?.[`oval_enabled_${i}`] ?? true);
    const tgl = document.createElement('button');
    tgl.className = 'tiny-btn oval-toggle' + (enabled ? ' on' : '');
    tgl.textContent = enabled ? 'On' : 'Off';
    tgl.dataset.state = enabled ? 'on' : 'off';
    tgl.onclick = async () => {
      const next = tgl.dataset.state !== 'on';
      tgl.dataset.state = next ? 'on' : 'off';
      tgl.textContent = next ? 'On' : 'Off';
      tgl.classList.toggle('on', next);
      await api('scene/synth', { method: 'PUT', body: JSON.stringify({ [`oval_enabled_${i}`]: next }) });
      if (!config.scene) config.scene = {};
      if (!config.scene.synth) config.scene.synth = {};
      config.scene.synth[`oval_enabled_${i}`] = next;
    };
    cell.appendChild(tgl);

    const trio = document.createElement('div');
    trio.className = 'knob-trio';
    cell.appendChild(trio);

    for (const k of OVAL_KNOBS) {
      const kc = document.createElement('div');
      kc.className = 'knob-cell';
      const dialEl = document.createElement('div');
      kc.appendChild(dialEl);
      const lbl = document.createElement('div');
      lbl.className = 'knob-label';
      lbl.textContent = k.label;
      kc.appendChild(lbl);
      const val = document.createElement('div');
      val.className = 'knob-value';
      const cfgKey = `oval_${k.key}_${i}`;
      const cur = +(config.scene?.synth?.[cfgKey] ?? k.min);
      val.textContent = cur.toFixed(2);
      kc.appendChild(val);
      trio.appendChild(kc);
      let saveT = null;
      const defaultValue = OVAL_DEFAULTS[k.key]?.[i];
      makeDial(dialEl, { min: k.min, max: k.max, step: k.step, value: cur,
                          size: [38, 38], defaultValue }, v => {
        val.textContent = (+v).toFixed(2);
        if (!config.scene) config.scene = {};
        if (!config.scene.synth) config.scene.synth = {};
        config.scene.synth[cfgKey] = v;
        clearTimeout(saveT);
        saveT = setTimeout(() => {
          api('scene/synth', { method: 'PUT', body: JSON.stringify({ [cfgKey]: v }) });
        }, 100);
      });
    }
    wrap.appendChild(cell);
  }
}

// ── Synth Curves pane (NexusUI Envelope widgets + length) ──────
async function buildSynthCurves() {
  const wrap = document.getElementById('synth-curves');
  if (!wrap) return;
  wrap.innerHTML = '';
  let curves;
  try { curves = await api('scene/curves'); } catch { curves = {}; }
  for (const [name, env] of Object.entries(curves)) {
    const card = document.createElement('div');
    card.className = 'curve-card';

    const hdr = document.createElement('div');
    hdr.className = 'curve-header';
    const ttl = document.createElement('div');
    ttl.className = 'curve-name';
    ttl.textContent = name;
    hdr.appendChild(ttl);

    // Duration (beats) — drives the modulator length when an event uses
    // this curve without overriding its own duration.
    const durLabel = document.createElement('label');
    durLabel.className = 'dim tiny';
    durLabel.textContent = 'length (beats)';
    hdr.appendChild(durLabel);
    const durInput = document.createElement('input');
    durInput.type = 'number';
    durInput.className = 'tiny-num';
    durInput.min = '0.05'; durInput.max = '64'; durInput.step = '0.05';
    durInput.value = String(env.duration_beats ?? 1.0);
    hdr.appendChild(durInput);

    const interp = document.createElement('select');
    interp.className = 'tiny-sel';
    for (const opt of ['linear', 'cosine', 'ease_in_quad', 'ease_out_quad']) {
      const o = document.createElement('option');
      o.value = opt; o.textContent = opt;
      if (opt === (env.interp || 'linear')) o.selected = true;
      interp.appendChild(o);
    }
    hdr.appendChild(interp);
    card.appendChild(hdr);

    const canvas = document.createElement('div');
    canvas.className = 'curve-canvas';
    card.appendChild(canvas);
    wrap.appendChild(card);

    const widget = new Nexus.Envelope(canvas, {
      size: [Math.min(720, canvas.clientWidth || 320), 110],
      noNewPoints: false,
      points: (env.points || []).map(([t, v]) => ({ x: t, y: v })),
    });
    let saveT = null;
    const save = () => {
      const body = {
        points: widget.points.map(p => [p.x, p.y]),
        interp: interp.value,
        duration_beats: parseFloat(durInput.value) || 1.0,
      };
      clearTimeout(saveT);
      saveT = setTimeout(() => {
        api(`scene/curves/${encodeURIComponent(name)}`, {
          method: 'PUT', body: JSON.stringify(body),
        });
      }, 150);
    };
    widget.on('change', save);
    interp.onchange = save;
    durInput.onchange = save;
  }
}

// ── Synth Events pane ──────────────────────────────────────────
// Two classes of event in the catalog:
//   * "Modulator-style" events take a `duration_beats` parameter that
//     controls how long the envelope plays (Expand/Contract/Pulse/etc.).
//   * "Instant" events (push_*, rotate_*, stop_rotation_*, regrow) don't
//     have a duration — they're either single impulses, held torques, or
//     state-snap operations. The Length column is hidden for those so
//     the UI doesn't lie about what's tweakable.
const EVENTS_WITH_DURATION = new Set([
  'expand', 'contract', 'pulse', 'blow_out',
  'dissolve', 'respawn', 'regrow', 'color_palette',
  'pull_center', 'shimmer',
  'push_left', 'push_right', 'push_up', 'push_down', 'push_random',
  'meteors', 'dust', 'flash', 'wipe',
]);
// Pre-defined curve shapes the user can pick per-event. Maps the picker
// label to the params.ease value the backend expects.
const EASE_OPTIONS = [
  { label: '',           value: '' },           // = action's own default
  { label: 'linear',     value: 'linear' },
  { label: 'ease-in',    value: 'ease_in' },
  { label: 'ease-out',   value: 'ease_out' },
  { label: 'ease-i/o',   value: 'ease_in_out' },
];

// Events that hold a sustain — note_off releases the modulator.
// (No special UI yet; just here so the events row knows to fire
// note_off on mouseup.)
// SFX events that take a color (palette-slot index 0..7).
const FX_EVENTS = new Set(['meteors', 'dust', 'flash', 'wipe']);
// Per-FX extra params shown inline (dust density, etc.).
const FX_EXTRA_PARAM = {
  dust:    { key: 'cluster_count', label: 'count',  min: 5, max: 200, step: 1, default: 28 },
  meteors: { key: 'count',         label: 'count',  min: 1, max: 30,  step: 1, default: 6 },
  wipe:    { key: 'band_width',    label: 'width',  min: 1, max: 20,  step: 0.5, default: 6 },
};
const COLOR_SLOT_NAMES = [
  'rim', 'inner', 'outer', 'trail', 'col4', 'col5', 'col6', 'col7',
];

function _activePaletteColors() {
  const palettes = config.breathing?.palettes || [];
  const idx = config.breathing?.active_palette ?? 0;
  const pal = palettes[idx] || palettes[0] || {};
  const keys = [
    'rim_color', 'inner_color', 'outer_color', 'trail_color',
    'color4', 'color5', 'color6', 'color7',
  ];
  return keys.map(k => pal[k] || [200, 200, 200]);
}

// In-memory cache of /api/scene/event_defaults — keyed by event name.
// Populated by loadEventDefaults() at boot, mutated when the user changes
// a row, persisted via PUT /api/scene/event_defaults/{name}.
let _eventDefaultsCache = {};

async function loadEventDefaults() {
  try {
    _eventDefaultsCache = (await api('scene/event_defaults')) || {};
  } catch {
    _eventDefaultsCache = {};
  }
}

function _saveEventDefault(name, params) {
  _eventDefaultsCache[name] = params;
  api(`scene/event_defaults/${encodeURIComponent(name)}`, {
    method: 'PUT', body: JSON.stringify(params),
  }).catch(() => {});
}

function buildSynthEvents() {
  const wrap = document.getElementById('synth-events');
  if (!wrap) return;
  wrap.innerHTML = '';
  const events = [
    'expand', 'contract', 'pulse', 'blow_out', 'regrow', 'shimmer',
    'rotate_cw', 'rotate_ccw',
    'rotate_cw_outer', 'rotate_ccw_outer',
    'rotate_cw_middle', 'rotate_ccw_middle',
    'rotate_cw_inner', 'rotate_ccw_inner',
    'stop_rotation',
    'stop_rotation_outer', 'stop_rotation_middle', 'stop_rotation_inner',
    'dissolve', 'respawn',
    'push_left', 'push_right', 'push_up', 'push_down', 'pull_center',
    'push_random',
    'show_outer', 'hide_outer',
    'show_middle', 'hide_middle',
    'show_inner', 'hide_inner',
    'meteors', 'dust', 'flash', 'wipe',
    'color_palette',
  ];

  for (const ev of events) {
    const row = document.createElement('div');
    row.className = 'event-row';

    const nameEl = document.createElement('span');
    nameEl.className = 'event-name';
    nameEl.textContent = ev;
    row.appendChild(nameEl);

    // Loaded defaults for this event (persists across reload + applies to
    // MIDI playback, not just test button).
    const savedDefaults = _eventDefaultsCache[ev] || {};

    const hasDur = EVENTS_WITH_DURATION.has(ev);
    let durSel = null;
    let easeSel = null;
    if (hasDur) {
      durSel = document.createElement('select');
      durSel.className = 'event-len';
      durSel.title = 'Duration (beats)';
      for (const d of DURATIONS) {
        const o = document.createElement('option');
        o.value = String(d.beats); o.textContent = d.label;
        durSel.appendChild(o);
      }
      // Empty value = use the action's default duration.
      const optDef = document.createElement('option');
      optDef.value = ''; optDef.textContent = 'def';
      durSel.insertBefore(optDef, durSel.firstChild);
      // Read from event_defaults first (canonical since iter 1) and
      // fall back to the legacy default_durations dict for old patches
      // that pre-date event_defaults.
      let stored = savedDefaults?.duration_beats;
      if (stored == null) stored = config.scene?.default_durations?.[ev];
      durSel.value = stored == null ? '' : String(stored);
      row.appendChild(durSel);
      // duration_beats also lives in event_defaults so MIDI dispatch sees it.
      durSel.addEventListener('change', () => {
        const params = { ..._eventDefaultsCache[ev] };
        if (durSel.value === '') delete params.duration_beats;
        else params.duration_beats = parseFloat(durSel.value);
        _saveEventDefault(ev, params);
      });

      // Ease picker — pre-defined curve shape for this event.
      easeSel = document.createElement('select');
      easeSel.className = 'event-ease';
      easeSel.title = 'Curve shape';
      for (const opt of EASE_OPTIONS) {
        const o = document.createElement('option');
        o.value = opt.value; o.textContent = opt.label || 'def';
        easeSel.appendChild(o);
      }
      if (savedDefaults.ease != null) easeSel.value = savedDefaults.ease;
      easeSel.addEventListener('change', () => {
        const params = { ..._eventDefaultsCache[ev] };
        if (easeSel.value === '') delete params.ease;
        else params.ease = easeSel.value;
        _saveEventDefault(ev, params);
      });
      row.appendChild(easeSel);
    }

    // FX events get a color picker (palette slot 0..7) + any per-FX extra.
    let colorSel = null;
    let extraInput = null;
    if (FX_EVENTS.has(ev)) {
      colorSel = document.createElement('select');
      colorSel.className = 'event-color';
      colorSel.title = 'Color (palette slot)';
      const pcolors = _activePaletteColors();
      for (let k = 0; k < 8; k++) {
        const o = document.createElement('option');
        o.value = String(k); o.textContent = COLOR_SLOT_NAMES[k];
        const c = pcolors[k];
        // Color-tint the option label so the user sees the swatch.
        o.style.backgroundColor = `rgb(${c[0]},${c[1]},${c[2]})`;
        o.style.color = (c[0] + c[1] + c[2] > 380) ? '#000' : '#fff';
        colorSel.appendChild(o);
      }
      if (savedDefaults.color != null) colorSel.value = String(savedDefaults.color);
      colorSel.addEventListener('change', () => {
        const params = { ..._eventDefaultsCache[ev] };
        params.color = parseInt(colorSel.value, 10);
        _saveEventDefault(ev, params);
      });
      row.appendChild(colorSel);
      // Per-FX extra param (dust density, meteor count, wipe width).
      const xspec = FX_EXTRA_PARAM[ev];
      if (xspec) {
        extraInput = document.createElement('input');
        extraInput.type = 'number';
        extraInput.className = 'event-extra';
        extraInput.title = xspec.label;
        extraInput.min = String(xspec.min);
        extraInput.max = String(xspec.max);
        extraInput.step = String(xspec.step);
        const stored = savedDefaults[xspec.key];
        extraInput.value = (stored != null) ? String(stored) : String(xspec.default);
        extraInput.placeholder = xspec.label;
        extraInput.addEventListener('change', () => {
          const params = { ..._eventDefaultsCache[ev] };
          const v = parseFloat(extraInput.value);
          if (!isNaN(v)) params[xspec.key] = v;
          else delete params[xspec.key];
          _saveEventDefault(ev, params);
        });
        row.appendChild(extraInput);
      }
    }

    const btn = document.createElement('button');
    btn.className = 'event-trigger';
    btn.textContent = '▶';
    btn.title = (ev === 'pull_center') ? 'Pull ball to center'
              : (ev.startsWith('rotate_') ? 'Hold to apply torque' : 'Trigger');
    let held = false;
    const fire = (type) => {
      const body = { params: {}, event_type: type };
      if (durSel && durSel.value !== '') body.duration_beats = parseFloat(durSel.value);
      if (easeSel && easeSel.value !== '') body.params.ease = easeSel.value;
      if (colorSel) body.params.color = parseInt(colorSel.value, 10);
      if (extraInput) {
        const xspec = FX_EXTRA_PARAM[ev];
        const v = parseFloat(extraInput.value);
        if (xspec && !isNaN(v)) body.params[xspec.key] = v;
      }
      api(`scene/event/${encodeURIComponent(ev)}`, {
        method: 'POST', body: JSON.stringify(body),
      });
    };
    btn.addEventListener('mousedown', e => { e.preventDefault(); held = true; fire('note_on'); });
    btn.addEventListener('mouseup',   () => { if (held) { held = false; fire('note_off'); } });
    btn.addEventListener('mouseleave', () => { if (held) { held = false; fire('note_off'); } });
    btn.addEventListener('touchstart', e => { e.preventDefault(); held = true; fire('note_on'); }, { passive: false });
    btn.addEventListener('touchend',   () => { if (held) { held = false; fire('note_off'); } });
    row.appendChild(btn);

    wrap.appendChild(row);
  }
}

// ── Synth Physics pane ──────────────────────────────────────────
async function buildSynthPhysics() {
  const wrap = document.getElementById('synth-physics');
  if (!wrap) return;
  wrap.innerHTML = '';
  let phys;
  try { phys = await api('scene/physics'); } catch { phys = {}; }
  const grid = document.createElement('div');
  grid.className = 'physics-grid';
  for (const k of PHYSICS_KNOBS) {
    const cell = document.createElement('div');
    cell.className = 'knob-cell';
    const dialEl = document.createElement('div');
    cell.appendChild(dialEl);
    const lbl = document.createElement('div');
    lbl.className = 'knob-label';
    lbl.textContent = k.label;
    cell.appendChild(lbl);
    const val = document.createElement('div');
    val.className = 'knob-value';
    const cur = +(phys[k.key] ?? k.min);
    val.textContent = cur.toFixed(2);
    cell.appendChild(val);
    grid.appendChild(cell);
    let saveT = null;
    makeDial(dialEl, { min: k.min, max: k.max, step: k.step, value: cur,
                        size: [50, 50], defaultValue: k.default }, v => {
      val.textContent = (+v).toFixed(2);
      clearTimeout(saveT);
      saveT = setTimeout(() => {
        api('scene/physics', { method: 'PUT', body: JSON.stringify({ [k.key]: v }) });
      }, 100);
    });
  }
  wrap.appendChild(grid);
}

function buildPianoRoll() {
  const wrap = document.getElementById('piano-roll-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';
  const canvas = document.createElement('canvas');
  wrap.appendChild(canvas);
  _pianoRoll = {
    wrap,
    canvas,
    ctx: canvas.getContext('2d'),
    lanes: [],
    notes: [],
    selected: new Set(),     // set of note refs
    loopBeats: 16,
    playhead: 0,
    pxPerBeat: PX_PER_BEAT_DEFAULT,
    snapBeats: 0.25,          // 1/16, configurable via dropdown
    // Drag state
    drag: null,               // { mode, startX, startY, ... }
    hover: null,              // { x, y, beat, lane, note }
  };
  canvas.addEventListener('mousedown', onPianoMouseDown);
  canvas.addEventListener('mousemove', onPianoMouseMove);
  canvas.addEventListener('mouseleave', () => {
    if (!_pianoRoll) return;
    _pianoRoll.hover = null;
    drawPianoRoll();
  });
  document.addEventListener('mouseup', onPianoMouseUp);
  canvas.addEventListener('wheel', onPianoWheel, { passive: false });
  canvas.addEventListener('dblclick', onPianoDblClick);
  drawPianoRoll();
}

// Double-click a note → delete it. Quick way to clean up the roll without
// chord-selecting + Del.
function onPianoDblClick(e) {
  const r = _pianoRoll;
  if (!r) return;
  const c = pianoCoords(e);
  if (!c) return;
  const hit = pianoHitTest(c.x, c.y);
  if (!hit || !hit.note) return;
  // Release any pending hold from the mousedown that preceded this.
  releaseHeldNoteEvents();
  const idx = r.notes.indexOf(hit.note);
  if (idx >= 0) r.notes.splice(idx, 1);
  r.selected.delete(hit.note);
  pushPianoNotes();
  drawPianoRoll();
}

function resizePianoCanvas() {
  if (!_pianoRoll) return;
  const r = _pianoRoll;
  const rollWidth = Math.max(400, Math.round(r.loopBeats * r.pxPerBeat));
  r.canvas.width = LABEL_WIDTH + rollWidth + 1;
  r.canvas.height = RULER_HEIGHT + r.lanes.length * LANE_HEIGHT + 1;
}

function snapBeat(b, snapSize) {
  if (snapSize > 0) return Math.round(b / snapSize) * snapSize;
  return b;
}

function pianoCoords(e) {
  if (!_pianoRoll) return null;
  const rect = _pianoRoll.canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  return { x, y };
}

function pianoHitTest(x, y) {
  const r = _pianoRoll;
  if (!r) return null;
  const inRuler = y < RULER_HEIGHT;
  const laneY = y - RULER_HEIGHT;
  const lane = Math.floor(laneY / LANE_HEIGHT);
  const rollX = x - LABEL_WIDTH;
  const beat = rollX / r.pxPerBeat;
  const onLabel = !inRuler && rollX < 0 && lane >= 0 && lane < r.lanes.length;
  const onRoll = rollX >= 0 && lane >= 0 && lane < r.lanes.length;
  // Loop-handle hit: 6px on either side of the loop-end x line, anywhere
  // in the ruler row.
  const loopEndX = LABEL_WIDTH + r.loopBeats * r.pxPerBeat;
  const onLoopHandle = inRuler && Math.abs(x - loopEndX) <= 6;
  let note = null;
  if (onRoll && !inRuler) {
    note = r.notes.find(n =>
      n.pitch === lane &&
      beat >= n.start_beat &&
      beat < n.start_beat + n.length_beats
    ) || null;
  }
  return { x, y, beat, lane, onRoll, onLabel, inRuler, onLoopHandle, note };
}

function noteEndPx(n) { return LABEL_WIDTH + (n.start_beat + n.length_beats) * _pianoRoll.pxPerBeat; }
function noteStartPx(n) { return LABEL_WIDTH + n.start_beat * _pianoRoll.pxPerBeat; }

function onPianoMouseDown(e) {
  const r = _pianoRoll;
  if (!r) return;
  const c = pianoCoords(e);
  if (!c) return;
  const hit = pianoHitTest(c.x, c.y);
  if (!hit) return;
  // Loop-handle drag: grab the right edge of the loop bracket on the
  // ruler. Drag horizontally to resize. Alt to bypass snap.
  if (hit.onLoopHandle) {
    r.drag = {
      mode: 'loop-resize',
      startX: c.x, startY: c.y,
      origLoop: r.loopBeats,
      altSkipSnap: e.altKey,
    };
    return;
  }
  if (hit.inRuler) return;
  // Lane label click → fire the lane's event directly (mousedown = note_on).
  // The matching note_off fires from the global mouseup → releaseHeldNoteEvents().
  if (hit.onLabel) {
    const lane = (r.lanes || [])[hit.lane];
    if (lane && lane.event) {
      fireLaneEventDown(lane);
    }
    return;
  }
  if (!hit.onRoll) return;
  const altSkipSnap = e.altKey;
  const shiftMod = e.shiftKey;

  if (hit.note) {
    // Fire the lane event on push so the user can audition notes by
    // clicking. Don't fire when grabbing the resize handle.
    const endPx = noteEndPx(hit.note);
    const onResizeHandle = c.x >= endPx - RESIZE_EDGE;
    if (!onResizeHandle) {
      triggerNoteEvent(hit.note);
    }
    // Right-edge zone = resize
    if (onResizeHandle) {
      r.drag = {
        mode: 'resize',
        startX: c.x, startY: c.y,
        note: hit.note,
        origLength: hit.note.length_beats,
        altSkipSnap,
      };
      // Make sure the dragged note is selected.
      if (!r.selected.has(hit.note)) {
        if (!shiftMod) r.selected.clear();
        r.selected.add(hit.note);
      }
    } else {
      // Body of note: selection + start move-drag.
      if (shiftMod) {
        // toggle in/out of selection
        if (r.selected.has(hit.note)) r.selected.delete(hit.note);
        else r.selected.add(hit.note);
      } else if (!r.selected.has(hit.note)) {
        r.selected.clear();
        r.selected.add(hit.note);
      }
      r.drag = {
        mode: 'maybe-move',
        startX: c.x, startY: c.y,
        note: hit.note,
        origStarts: new Map([...r.selected].map(n => [n, n.start_beat])),
        origPitches: new Map([...r.selected].map(n => [n, n.pitch])),
        altSkipSnap,
      };
    }
  } else {
    // Empty area. Shift-drag = marquee; otherwise, click+drag = add+resize.
    if (shiftMod) {
      r.drag = {
        mode: 'marquee',
        startX: c.x, startY: c.y,
        curX: c.x, curY: c.y,
        priorSelection: new Set(r.selected),
      };
    } else {
      // Add a new note. Default length = the larger of (snap, 1/4 beat).
      const defaultLen = Math.max(r.snapBeats > 0 ? r.snapBeats : 1.0, 0.25);
      let startBeat = altSkipSnap ? hit.beat : snapBeat(hit.beat, r.snapBeats);
      startBeat = Math.max(0, Math.min(r.loopBeats - defaultLen, startBeat));
      const note = { pitch: hit.lane, start_beat: startBeat, length_beats: defaultLen };
      r.notes.push(note);
      r.selected.clear();
      r.selected.add(note);
      r.drag = {
        mode: 'resize',
        startX: c.x, startY: c.y,
        note,
        origLength: defaultLen,
        altSkipSnap,
        addedNote: true,
      };
    }
  }
  drawPianoRoll();
}

function onPianoMouseMove(e) {
  const r = _pianoRoll;
  if (!r) return;
  const c = pianoCoords(e);
  if (!c) return;

  // Always track hover for tooltip + cursor.
  r.hover = pianoHitTest(c.x, c.y);

  if (r.drag) {
    const altSkipSnap = e.altKey || r.drag.altSkipSnap;
    if (r.drag.mode === 'loop-resize') {
      const dx = c.x - r.drag.startX;
      const dbeats = dx / r.pxPerBeat;
      let newLoop = r.drag.origLoop + dbeats;
      newLoop = altSkipSnap ? newLoop : snapBeat(newLoop, r.snapBeats || 0.25);
      newLoop = Math.max(0.25, Math.min(256, newLoop));
      r.loopBeats = newLoop;
      drawPianoRoll();
      return;
    }
    if (r.drag.mode === 'resize') {
      const dx = c.x - r.drag.startX;
      const dbeats = dx / r.pxPerBeat;
      let newLen = r.drag.origLength + dbeats;
      newLen = Math.max(altSkipSnap ? 0.05 : (r.snapBeats || 0.05),
                        altSkipSnap ? newLen : snapBeat(newLen, r.snapBeats));
      const maxLen = r.loopBeats - r.drag.note.start_beat;
      if (newLen > maxLen) newLen = maxLen;
      r.drag.note.length_beats = newLen;
    } else if (r.drag.mode === 'maybe-move') {
      const dx = c.x - r.drag.startX;
      const dy = c.y - r.drag.startY;
      if (Math.abs(dx) > MARQUEE_THRESHOLD || Math.abs(dy) > MARQUEE_THRESHOLD) {
        r.drag.mode = 'move';
      }
    }
    if (r.drag.mode === 'move') {
      const dx = c.x - r.drag.startX;
      const dy = c.y - r.drag.startY;
      const dbeats = dx / r.pxPerBeat;
      const dlanes = Math.round(dy / LANE_HEIGHT);
      const laneCount = r.lanes.length;
      for (const [n, orig] of r.drag.origStarts.entries()) {
        let s = orig + dbeats;
        s = altSkipSnap ? s : snapBeat(s, r.snapBeats);
        s = Math.max(0, Math.min(r.loopBeats - n.length_beats, s));
        n.start_beat = s;
        const origPitch = r.drag.origPitches?.get(n) ?? n.pitch;
        let p = origPitch + dlanes;
        p = Math.max(0, Math.min(laneCount - 1, p));
        n.pitch = p;
      }
    } else if (r.drag.mode === 'marquee') {
      r.drag.curX = c.x;
      r.drag.curY = c.y;
    }
    drawPianoRoll();
    return;
  }

  // Cursor feedback (no drag).
  if (r.hover && r.hover.onLoopHandle) {
    r.canvas.style.cursor = 'ew-resize';
  } else if (r.hover && r.hover.note) {
    r.canvas.style.cursor = (c.x >= noteEndPx(r.hover.note) - RESIZE_EDGE) ? 'ew-resize' : 'move';
  } else if (r.hover && r.hover.onRoll && !r.hover.inRuler) {
    r.canvas.style.cursor = e.shiftKey ? 'crosshair' : 'cell';
  } else {
    r.canvas.style.cursor = 'default';
  }
  drawPianoRoll();
}

function onPianoMouseUp(e) {
  // Always release any held lane events on mouseup — even if we're not
  // mid-drag (e.g. a click on a note that didn't drag still needs its
  // note_off to fire).
  releaseHeldNoteEvents();
  const r = _pianoRoll;
  if (!r || !r.drag) return;
  const drag = r.drag;
  r.drag = null;

  if (drag.mode === 'loop-resize') {
    // Commit the new loop length to backend + sync the dropdown picker.
    syncLoopLengthPicker(r.loopBeats);
    api('scene/sequencer/loop_length', {
      method: 'PUT',
      body: JSON.stringify({ loop_length_beats: r.loopBeats }),
    });
  } else if (drag.mode === 'maybe-move') {
    // No drag occurred — selection already applied on mousedown, nothing more to do.
    // (Click without drag = select; multiple clicks just confirm selection.)
  } else if (drag.mode === 'move' || drag.mode === 'resize') {
    pushPianoNotes();
  } else if (drag.mode === 'marquee') {
    // Compute marquee rect, select notes intersecting.
    const x0 = Math.min(drag.startX, drag.curX);
    const x1 = Math.max(drag.startX, drag.curX);
    const y0 = Math.min(drag.startY, drag.curY);
    const y1 = Math.max(drag.startY, drag.curY);
    const sel = new Set(drag.priorSelection);  // additive over the prior selection
    for (const n of r.notes) {
      const nx0 = noteStartPx(n);
      const nx1 = noteEndPx(n);
      const ny0 = RULER_HEIGHT + n.pitch * LANE_HEIGHT;
      const ny1 = ny0 + LANE_HEIGHT;
      if (nx1 >= x0 && nx0 <= x1 && ny1 >= y0 && ny0 <= y1) sel.add(n);
    }
    r.selected = sel;
  }
  drawPianoRoll();
}

function onPianoWheel(e) {
  const r = _pianoRoll;
  if (!r) return;
  if (!e.ctrlKey && !e.metaKey) return;   // only Ctrl/Cmd+scroll zooms
  e.preventDefault();
  const c = pianoCoords(e);
  if (!c) return;
  const pivotBeat = (c.x - LABEL_WIDTH) / r.pxPerBeat;
  const factor = e.deltaY < 0 ? 1.18 : 1 / 1.18;
  const newPx = Math.max(PX_PER_BEAT_MIN, Math.min(PX_PER_BEAT_MAX, r.pxPerBeat * factor));
  r.pxPerBeat = newPx;
  drawPianoRoll();
  // Keep `pivotBeat` under the same screen position by scrolling the wrapper.
  const newPivotPx = LABEL_WIDTH + pivotBeat * r.pxPerBeat;
  const desiredScroll = newPivotPx - c.x;
  r.wrap.scrollLeft = Math.max(0, desiredScroll);
}

let _notesDebounce = null;
function pushPianoNotes() {
  clearTimeout(_notesDebounce);
  _notesDebounce = setTimeout(() => {
    if (!_pianoRoll) return;
    api('scene/sequencer/notes', {
      method: 'PUT',
      body: JSON.stringify({ notes: _pianoRoll.notes }),
    });
  }, 150);
}

function drawPianoRoll() {
  const r = _pianoRoll;
  if (!r) return;
  resizePianoCanvas();
  const ctx = r.ctx;
  const w = r.canvas.width, h = r.canvas.height;
  ctx.clearRect(0, 0, w, h);

  // Background
  ctx.fillStyle = '#0d0d12';
  ctx.fillRect(0, 0, w, h);

  // ── Ruler bar at top ──
  ctx.fillStyle = '#15151c';
  ctx.fillRect(LABEL_WIDTH, 0, w - LABEL_WIDTH, RULER_HEIGHT);
  ctx.font = '10px ui-sans-serif, -apple-system, BlinkMacSystemFont, Roboto, sans-serif';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = '#a8a8b5';
  // Bar numbers (every 4 beats); add beat numbers when zoomed in.
  const showSubBeats = r.pxPerBeat >= 30;
  for (let b = 0; b < r.loopBeats; b++) {
    const x = LABEL_WIDTH + b * r.pxPerBeat;
    if (b % 4 === 0) {
      ctx.fillStyle = '#d8d8df';
      ctx.fillText(String(Math.floor(b / 4) + 1), x + 3, RULER_HEIGHT / 2);
    } else if (showSubBeats) {
      ctx.fillStyle = '#7a7a82';
      ctx.fillText(`${Math.floor(b / 4) + 1}.${(b % 4) + 1}`, x + 3, RULER_HEIGHT / 2);
    }
  }
  ctx.strokeStyle = '#353541';
  ctx.beginPath();
  ctx.moveTo(0, RULER_HEIGHT + 0.5);
  ctx.lineTo(w, RULER_HEIGHT + 0.5);
  ctx.stroke();

  // ── Loop bracket on the ruler (Ableton-style draggable end) ──
  const loopEndX = LABEL_WIDTH + r.loopBeats * r.pxPerBeat;
  // Bracket fill (top of ruler)
  ctx.fillStyle = 'rgba(181, 140, 255, 0.18)';
  ctx.fillRect(LABEL_WIDTH, 0, loopEndX - LABEL_WIDTH, 4);
  // Bracket cap left
  ctx.fillStyle = '#b58cff';
  ctx.fillRect(LABEL_WIDTH, 0, 2, RULER_HEIGHT);
  // Bracket cap right — the draggable handle. Wider visual tab so it's
  // easy to grab; hit zone in pianoHitTest extends a few px on each side.
  ctx.fillRect(loopEndX - 1, 0, 2, RULER_HEIGHT);
  // Tab indicator at the top for visual affordance
  ctx.beginPath();
  ctx.moveTo(loopEndX - 5, 0);
  ctx.lineTo(loopEndX + 5, 0);
  ctx.lineTo(loopEndX, 6);
  ctx.closePath();
  ctx.fill();
  // Highlight when hovering the loop handle.
  if (r.hover && r.hover.onLoopHandle) {
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(loopEndX + 0.5, 0);
    ctx.lineTo(loopEndX + 0.5, RULER_HEIGHT);
    ctx.stroke();
  }

  // ── Lane label column ──
  ctx.fillStyle = '#0d0d12';
  ctx.fillRect(0, 0, LABEL_WIDTH, h);
  ctx.font = '11px ui-sans-serif, -apple-system, BlinkMacSystemFont, Roboto, sans-serif';
  for (let i = 0; i < r.lanes.length; i++) {
    const y = RULER_HEIGHT + i * LANE_HEIGHT;
    // Row background — alternate shades AND subtle bar stripes in the roll area.
    ctx.fillStyle = i % 2 === 0 ? '#13131a' : '#181820';
    ctx.fillRect(LABEL_WIDTH, y, w - LABEL_WIDTH, LANE_HEIGHT);
    ctx.strokeStyle = '#25252e';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, y + LANE_HEIGHT + 0.5);
    ctx.lineTo(w, y + LANE_HEIGHT + 0.5);
    ctx.stroke();
    ctx.fillStyle = '#c8c8d0';
    ctx.fillText(r.lanes[i].label, 6, y + LANE_HEIGHT / 2);
  }

  // ── Bar shading (every other bar slightly lighter) ──
  for (let bar = 0; bar < r.loopBeats / 4; bar++) {
    if (bar % 2 === 1) {
      ctx.fillStyle = 'rgba(255,255,255,0.012)';
      ctx.fillRect(LABEL_WIDTH + bar * 4 * r.pxPerBeat, RULER_HEIGHT, 4 * r.pxPerBeat, h - RULER_HEIGHT);
    }
  }

  // ── Grid lines: subdivision (subtle) → beats → bars (strong) ──
  const subdivStep = r.pxPerBeat >= 16 ? 0.25 : (r.pxPerBeat >= 8 ? 0.5 : 1);
  for (let b = 0; b <= r.loopBeats + 1e-9; b += subdivStep) {
    const x = LABEL_WIDTH + b * r.pxPerBeat;
    const isBar = Math.abs(b % 4) < 1e-6;
    const isBeat = !isBar && Math.abs(b % 1) < 1e-6;
    if (isBar) { ctx.strokeStyle = '#3a3a4a'; ctx.lineWidth = 1.5; }
    else if (isBeat) { ctx.strokeStyle = '#2c2c38'; ctx.lineWidth = 1; }
    else { ctx.strokeStyle = '#1f1f28'; ctx.lineWidth = 1; }
    ctx.beginPath();
    ctx.moveTo(x + 0.5, RULER_HEIGHT);
    ctx.lineTo(x + 0.5, h);
    ctx.stroke();
  }

  // ── Notes ──
  for (const n of r.notes) {
    if (n.pitch < 0 || n.pitch >= r.lanes.length) continue;
    const x = noteStartPx(n);
    const y = RULER_HEIGHT + n.pitch * LANE_HEIGHT + 2;
    const w_ = Math.max(3, n.length_beats * r.pxPerBeat - 1);
    const h_ = LANE_HEIGHT - 4;
    const isSelected = r.selected.has(n);
    ctx.fillStyle = isSelected ? '#e0c0ff' : '#b58cff';
    ctx.fillRect(x, y, w_, h_);
    ctx.fillStyle = isSelected ? '#a874dd' : '#7744aa';
    ctx.fillRect(x + w_ - 3, y, 3, h_);   // resize handle hint
    if (isSelected) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, w_ - 1, h_ - 1);
    }
  }

  // ── Marquee rect ──
  if (r.drag && r.drag.mode === 'marquee') {
    const x0 = Math.min(r.drag.startX, r.drag.curX);
    const y0 = Math.min(r.drag.startY, r.drag.curY);
    const dw = Math.abs(r.drag.curX - r.drag.startX);
    const dh = Math.abs(r.drag.curY - r.drag.startY);
    ctx.fillStyle = 'rgba(181, 140, 255, 0.18)';
    ctx.fillRect(x0, y0, dw, dh);
    ctx.strokeStyle = '#b58cff';
    ctx.lineWidth = 1;
    ctx.strokeRect(x0 + 0.5, y0 + 0.5, dw - 1, dh - 1);
  }

  // ── Playhead ──
  if (r.playhead != null) {
    const x = LABEL_WIDTH + r.playhead * r.pxPerBeat;
    ctx.strokeStyle = '#e0654a';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, h);
    ctx.stroke();
  }

  // ── Hover tooltip (beat + lane) ──
  if (r.hover && r.hover.onRoll && !r.hover.inRuler && !r.drag) {
    const bar = Math.floor(r.hover.beat / 4) + 1;
    const beatInBar = (r.hover.beat % 4) + 1;
    const txt = `${bar}.${beatInBar.toFixed(2)} · ${r.lanes[r.hover.lane]?.label || ''}`;
    ctx.font = '10px ui-sans-serif, monospace';
    const tw = ctx.measureText(txt).width + 8;
    const tx = Math.min(r.hover.x + 8, w - tw - 4);
    const ty = Math.max(RULER_HEIGHT + 2, r.hover.y - 18);
    ctx.fillStyle = 'rgba(20,20,28,0.92)';
    ctx.fillRect(tx, ty, tw, 16);
    ctx.strokeStyle = '#353541';
    ctx.strokeRect(tx + 0.5, ty + 0.5, tw - 1, 15);
    ctx.fillStyle = '#d8d8df';
    ctx.textBaseline = 'middle';
    ctx.fillText(txt, tx + 4, ty + 8);
  }

  // Label column right border
  ctx.strokeStyle = '#353541';
  ctx.beginPath();
  ctx.moveTo(LABEL_WIDTH + 0.5, 0);
  ctx.lineTo(LABEL_WIDTH + 0.5, h);
  ctx.stroke();
}

// ── Saved sequences (picker / new / duplicate / rename / delete) ──
let _activeSequenceName = null;

async function refreshSequencePicker() {
  const sel = document.getElementById('seq-picker');
  if (!sel) return;
  const data = await api('scene/sequences');
  _activeSequenceName = data.active || null;
  sel.innerHTML = '';
  if (!data.sequences || data.sequences.length === 0) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '(none)';
    sel.appendChild(opt);
  }
  for (const s of (data.sequences || [])) {
    const opt = document.createElement('option');
    opt.value = s.name;
    opt.textContent = `${s.name}  ·  ${s.note_count} notes`;
    if (s.name === _activeSequenceName) opt.selected = true;
    sel.appendChild(opt);
  }
}

async function loadSequence(name) {
  if (!name) return;
  await api(`scene/sequences/${encodeURIComponent(name)}/load`, { method: 'POST' });
  // Refresh the piano roll from the backend's new state.
  try {
    const seq = await api('scene/sequencer');
    if (_pianoRoll) {
      _pianoRoll.notes = seq.notes || [];
      _pianoRoll.loopBeats = seq.loop_length_beats || 16;
      _pianoRoll.selected = new Set();
      syncLoopLengthPicker(_pianoRoll.loopBeats);
      zoomFitWithCap(8);
    }
  } catch {}
  await refreshSequencePicker();
}

function bindSequencePicker() {
  const sel = document.getElementById('seq-picker');
  const newBtn = document.getElementById('seq-new');
  const dupBtn = document.getElementById('seq-duplicate');
  const renBtn = document.getElementById('seq-rename');
  const delBtn = document.getElementById('seq-delete');
  const saveBtn = document.getElementById('seq-save');
  if (sel) sel.onchange = () => loadSequence(sel.value);
  if (saveBtn) saveBtn.onclick = async () => {
    // Force-flush the debounced auto-save, then PUT immediately with the
    // current notes. The orchestrator mirrors them to the active sequence
    // file. Brief ✓ confirmation so the user knows it actually went through.
    clearTimeout(_notesDebounce);
    _notesDebounce = null;
    if (!_pianoRoll) return;
    const original = saveBtn.textContent;
    saveBtn.disabled = true;
    try {
      await api('scene/sequencer/notes', {
        method: 'PUT',
        body: JSON.stringify({ notes: _pianoRoll.notes }),
      });
      saveBtn.textContent = '✓ saved';
    } catch {
      saveBtn.textContent = '✗ failed';
    } finally {
      setTimeout(() => {
        saveBtn.textContent = original;
        saveBtn.disabled = false;
      }, 1200);
    }
  };
  if (newBtn) newBtn.onclick = async () => {
    const name = prompt('Name for the new sequence:', 'untitled');
    if (!name) return;
    await api('scene/sequences/new', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    await refreshSequencePicker();
    await loadSequence(document.getElementById('seq-picker').value);
  };
  if (dupBtn) dupBtn.onclick = async () => {
    if (!_activeSequenceName) return;
    const suggestion = `${_activeSequenceName}-copy`;
    const name = prompt('Name for the copy:', suggestion);
    if (!name) return;
    await api(`scene/sequences/${encodeURIComponent(_activeSequenceName)}/duplicate`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    await refreshSequencePicker();
  };
  if (renBtn) renBtn.onclick = async () => {
    if (!_activeSequenceName) return;
    const oldName = _activeSequenceName;
    const newName = prompt('New name for this sequence:', oldName);
    if (!newName || newName === oldName) return;
    // Implement rename = duplicate-into-new + switch + delete-original.
    const dup = await api(`scene/sequences/${encodeURIComponent(oldName)}/duplicate`, {
      method: 'POST',
      body: JSON.stringify({ name: newName }),
    });
    const actualName = dup?.name || newName;
    await loadSequence(actualName);
    await api(`scene/sequences/${encodeURIComponent(oldName)}`, { method: 'DELETE' });
    await refreshSequencePicker();
  };
  if (delBtn) delBtn.onclick = async () => {
    if (!_activeSequenceName) return;
    if (!confirm(`Delete sequence "${_activeSequenceName}"? This can't be undone.`)) return;
    await api(`scene/sequences/${encodeURIComponent(_activeSequenceName)}`, { method: 'DELETE' });
    await refreshSequencePicker();
    // Reload whatever the backend switched to.
    if (_activeSequenceName) await loadSequence(_activeSequenceName);
    else {
      if (_pianoRoll) { _pianoRoll.notes = []; _pianoRoll.selected = new Set(); drawPianoRoll(); }
    }
  };
}

// Reflect the active loop length in the picker. If the value matches one
// of the standard options, select it; otherwise switch to "custom…" and
// pre-fill the inline input with the corresponding bar count.
function syncLoopLengthPicker(beats) {
  const loopSel = document.getElementById('seq-loop-length');
  const customInput = document.getElementById('seq-loop-custom');
  if (!loopSel) return;
  const standard = ['4', '8', '16', '32', '64'];
  if (standard.includes(String(beats))) {
    loopSel.value = String(beats);
    if (customInput) customInput.hidden = true;
  } else {
    loopSel.value = 'custom';
    if (customInput) {
      customInput.hidden = false;
      customInput.value = String(beats / 4);
    }
  }
}

function bindSequencerControls() {
  const playBtn = document.getElementById('seq-play');
  const stopBtn = document.getElementById('seq-stop');
  const clearBtn = document.getElementById('seq-clear');
  const loopSel = document.getElementById('seq-loop-length');
  const snapSel = document.getElementById('seq-snap');
  const zoomInBtn = document.getElementById('seq-zoom-in');
  const zoomOutBtn = document.getElementById('seq-zoom-out');
  const zoomFitBtn = document.getElementById('seq-zoom-fit');
  const autoplayBox = document.getElementById('seq-autoplay');
  if (playBtn) playBtn.onclick = () => api('scene/sequencer/play', { method: 'POST' });
  if (stopBtn) stopBtn.onclick = () => api('scene/sequencer/stop', { method: 'POST' });
  if (autoplayBox) {
    // Initialize from saved config + persist on change.
    const cur = config.scene?.sequencer?.autoplay;
    autoplayBox.checked = (cur === undefined) ? true : !!cur;
    autoplayBox.onchange = () => {
      const v = autoplayBox.checked;
      api('config', {
        method: 'PUT',
        body: JSON.stringify({ scene: { sequencer: { autoplay: v } } }),
      });
      if (!config.scene) config.scene = {};
      if (!config.scene.sequencer) config.scene.sequencer = {};
      config.scene.sequencer.autoplay = v;
    };
  }
  if (clearBtn) clearBtn.onclick = async () => {
    if (!confirm('Clear all notes?')) return;
    if (_pianoRoll) {
      _pianoRoll.notes = [];
      _pianoRoll.selected.clear();
      drawPianoRoll();
      await api('scene/sequencer/notes', { method: 'PUT', body: JSON.stringify({ notes: [] }) });
    }
  };

  // ÷2 / ×2 — preserve the relative pattern but scale the clip length
  // (and every note's position + length) by a factor. ×2 = clip twice
  // as long, plays half as fast. ÷2 = clip half as long, plays twice
  // as fast. Loop-length picker syncs to the new value.
  async function scaleClip(factor) {
    if (!_pianoRoll) return;
    const newLoop = _pianoRoll.loopBeats * factor;
    if (newLoop < 0.5 || newLoop > 256) return;
    const newNotes = _pianoRoll.notes.map(n => ({
      pitch: n.pitch,
      start_beat:  n.start_beat  * factor,
      length_beats: n.length_beats * factor,
    }));
    _pianoRoll.notes = newNotes;
    _pianoRoll.loopBeats = newLoop;
    _pianoRoll.selected.clear();
    syncLoopLengthPicker(newLoop);
    drawPianoRoll();
    // Push loop length first, then notes (server filters notes outside
    // the new loop, so do this in the right order for both factors).
    if (factor > 1) {
      await api('scene/sequencer/loop_length', {
        method: 'PUT', body: JSON.stringify({ loop_length_beats: newLoop }),
      });
      await api('scene/sequencer/notes', {
        method: 'PUT', body: JSON.stringify({ notes: newNotes }),
      });
    } else {
      await api('scene/sequencer/notes', {
        method: 'PUT', body: JSON.stringify({ notes: newNotes }),
      });
      await api('scene/sequencer/loop_length', {
        method: 'PUT', body: JSON.stringify({ loop_length_beats: newLoop }),
      });
    }
  }
  const halfBtn = document.getElementById('seq-half');
  const dblBtn  = document.getElementById('seq-double');
  if (halfBtn) halfBtn.onclick = () => scaleClip(0.5);
  if (dblBtn)  dblBtn.onclick  = () => scaleClip(2.0);

  // Duplicate — double the loop length BUT keep tempo by copying the
  // pattern at +originalLength. Result is the same notes played twice
  // per loop iteration (e.g. 16-beat pattern → 32-beat loop with the
  // pattern at beats 0 and 16).
  const dupBtn = document.getElementById('seq-dup');
  if (dupBtn) dupBtn.onclick = async () => {
    if (!_pianoRoll) return;
    const oldLoop = _pianoRoll.loopBeats;
    const newLoop = oldLoop * 2;
    if (newLoop > 256) return;
    const newNotes = _pianoRoll.notes.map(n => ({
      pitch: n.pitch,
      start_beat: n.start_beat,
      length_beats: n.length_beats,
    }));
    for (const n of _pianoRoll.notes) {
      newNotes.push({
        pitch: n.pitch,
        start_beat: n.start_beat + oldLoop,
        length_beats: n.length_beats,
      });
    }
    _pianoRoll.notes = newNotes;
    _pianoRoll.loopBeats = newLoop;
    _pianoRoll.selected.clear();
    syncLoopLengthPicker(newLoop);
    drawPianoRoll();
    await api('scene/sequencer/loop_length', {
      method: 'PUT', body: JSON.stringify({ loop_length_beats: newLoop }),
    });
    await api('scene/sequencer/notes', {
      method: 'PUT', body: JSON.stringify({ notes: newNotes }),
    });
  };
  const customInput = document.getElementById('seq-loop-custom');
  const applyLoop = async (beats) => {
    await api('scene/sequencer/loop_length', {
      method: 'PUT',
      body: JSON.stringify({ loop_length_beats: beats }),
    });
    if (_pianoRoll) {
      _pianoRoll.loopBeats = beats;
      // Don't drop notes that fall past the new loop end — backend
      // preserves them too. Expanding the loop later brings them back.
      drawPianoRoll();
    }
  };
  if (loopSel) {
    loopSel.onchange = async () => {
      if (loopSel.value === 'custom') {
        if (customInput) {
          customInput.hidden = false;
          customInput.focus();
          customInput.select();
        }
        return;
      }
      if (customInput) customInput.hidden = true;
      const beats = parseFloat(loopSel.value);
      await applyLoop(beats);
    };
  }
  if (customInput) {
    customInput.onchange = async () => {
      const bars = parseFloat(customInput.value);
      if (!(bars > 0)) return;
      const beats = bars * 4;
      await applyLoop(beats);
    };
  }
  if (snapSel) {
    snapSel.onchange = () => {
      if (_pianoRoll) _pianoRoll.snapBeats = parseFloat(snapSel.value);
    };
  }
  if (zoomInBtn) zoomInBtn.onclick = () => zoomBy(1.25);
  if (zoomOutBtn) zoomOutBtn.onclick = () => zoomBy(1 / 1.25);
  if (zoomFitBtn) zoomFitBtn.onclick = () => zoomFit();
}

function zoomBy(factor) {
  const r = _pianoRoll;
  if (!r) return;
  r.pxPerBeat = Math.max(PX_PER_BEAT_MIN, Math.min(PX_PER_BEAT_MAX, r.pxPerBeat * factor));
  drawPianoRoll();
}

function zoomFit() {
  const r = _pianoRoll;
  if (!r) return;
  // Fit the loop into the wrapper's visible width.
  const visible = r.wrap.clientWidth - LABEL_WIDTH - 8;
  if (visible < 100 || r.loopBeats <= 0) return;
  r.pxPerBeat = Math.max(PX_PER_BEAT_MIN,
                          Math.min(PX_PER_BEAT_MAX, visible / r.loopBeats));
  r.wrap.scrollLeft = 0;
  drawPianoRoll();
}

// Default fit-on-load: show the whole clip if it's <= maxBars; otherwise
// cap the visible window to maxBars (the user can scroll/zoom from there).
function zoomFitWithCap(maxBars = 8) {
  const r = _pianoRoll;
  if (!r) return;
  const visible = r.wrap.clientWidth - LABEL_WIDTH - 8;
  if (visible < 100) return;
  const beatsToShow = Math.min(r.loopBeats, maxBars * 4);
  if (beatsToShow <= 0) return;
  r.pxPerBeat = Math.max(PX_PER_BEAT_MIN,
                          Math.min(PX_PER_BEAT_MAX, visible / beatsToShow));
  r.wrap.scrollLeft = 0;
  drawPianoRoll();
}

// ── Keyboard shortcuts (active when Scene tab is visible) ──
document.addEventListener('keydown', (e) => {
  const pane = document.getElementById('tab-scene');
  if (!pane || !pane.classList.contains('active')) return;
  // Don't intercept if a text input is focused.
  const active = document.activeElement;
  if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT')) return;
  const r = _pianoRoll;
  if (!r) return;
  const ctrl = e.ctrlKey || e.metaKey;

  if (e.code === 'Space') {
    e.preventDefault();
    // Toggle play/stop using current playing flag from last poll.
    if (r._playing) {
      api('scene/sequencer/stop', { method: 'POST' });
    } else {
      api('scene/sequencer/play', { method: 'POST' });
    }
  } else if (e.code === 'Delete' || e.code === 'Backspace') {
    if (r.selected.size > 0) {
      e.preventDefault();
      const toDel = r.selected;
      r.notes = r.notes.filter(n => !toDel.has(n));
      r.selected = new Set();
      drawPianoRoll();
      pushPianoNotes();
    }
  } else if (e.code === 'Escape') {
    r.selected = new Set();
    drawPianoRoll();
  } else if (ctrl && e.code === 'KeyA') {
    e.preventDefault();
    r.selected = new Set(r.notes);
    drawPianoRoll();
  } else if (ctrl && e.code === 'KeyD') {
    e.preventDefault();
    // Duplicate selection — shift by (max selected end - min selected start) so
    // the copy lines up immediately after the original block.
    if (r.selected.size === 0) return;
    const starts = [...r.selected].map(n => n.start_beat);
    const ends = [...r.selected].map(n => n.start_beat + n.length_beats);
    const span = Math.max(...ends) - Math.min(...starts);
    const dupes = [];
    for (const n of r.selected) {
      const ns = n.start_beat + span;
      if (ns + n.length_beats <= r.loopBeats) {
        dupes.push({ pitch: n.pitch, start_beat: ns, length_beats: n.length_beats });
      }
    }
    r.notes.push(...dupes);
    r.selected = new Set(dupes);
    drawPianoRoll();
    pushPianoNotes();
  } else if (e.code === 'ArrowLeft' || e.code === 'ArrowRight') {
    if (r.selected.size === 0) return;
    e.preventDefault();
    const step = (e.shiftKey ? 4 : (r.snapBeats || 0.25));
    const dir = e.code === 'ArrowLeft' ? -1 : 1;
    for (const n of r.selected) {
      let ns = n.start_beat + dir * step;
      ns = Math.max(0, Math.min(r.loopBeats - n.length_beats, ns));
      n.start_beat = ns;
    }
    drawPianoRoll();
    pushPianoNotes();
  }
});

let _lastBeatInt = -1;
async function pollSceneState() {
  // Only poll while the Scene tab is visible.
  const pane = document.getElementById('tab-scene');
  if (!pane || !pane.classList.contains('active')) return;
  try {
    const s = await api('scene/state');
    const beat = s.beat || 0;
    // Flash the indicator on each new integer beat.
    const beatInt = Math.floor(beat);
    if (beatInt !== _lastBeatInt) {
      _lastBeatInt = beatInt;
      const pulse = document.getElementById('scene-beat-pulse');
      if (pulse) {
        pulse.classList.add('on');
        setTimeout(() => pulse.classList.remove('on'), 80);
      }
    }
    // Sequencer playhead + status
    if (_pianoRoll && s.sequencer) {
      _pianoRoll.playhead = s.sequencer.playhead_beat || 0;
      drawPianoRoll();
      const seqInfo = document.getElementById('seq-info');
      if (seqInfo) {
        seqInfo.textContent = s.sequencer.playing
          ? `playing · ${(_pianoRoll.playhead).toFixed(2)} / ${s.sequencer.loop_length_beats}`
          : 'stopped';
      }
    }
  } catch {}
}

// ── Field-debug AP toggle ──────────────────────────────────
async function setApState(up) {
  if (up && !confirm(
    'Bringing up the field-debug AP will drop home WiFi.\n\n' +
    'Reconnect by joining "here-debug" on your phone, then SSH/dashboard at 192.168.50.1.\n\n' +
    'Proceed?'
  )) return;
  try {
    await api(`ap/${up ? 'up' : 'down'}`, { method: 'POST' });
  } catch {}
  // After taking down, refresh; after bringing up, the laptop loses
  // connectivity to the Pi anyway so just leave it.
  if (!up) refreshTelemetry();
}

document.getElementById('ap-up-btn').onclick   = () => setApState(true);
document.getElementById('ap-down-btn').onclick = () => setApState(false);

// ── Init ───────────────────────────────────────────────────
async function init() {
  config = await api('config');
  updateModeButtons(config.mode);
  buildSliders('breathing-params', 'breathing', BREATHING_SLIDERS);
  initSpinControls();
  buildPaletteSelector();
  buildSliders('standby-params', 'standby', STANDBY_SLIDERS);
  buildSliders('fireplace-params', 'fireplace', FIREPLACE_SLIDERS);
  buildSliders('shadows-params', 'scale.shadows', SHADOWS_SLIDERS);
  buildSliders('breathing-session-params', 'breathing.session', BREATHING_SESSION_SLIDERS);
  bindBreathingPreviewPhase();
  // MIDI tab (the synth-for-visuals scene engine)
  buildSubtabs();
  buildSliders('synth-master-params', 'scene.synth', SYNTH_MASTER_SLIDERS);
  buildScenePaletteSelector();
  bindSceneClock();
  buildSynthOvals();
  await loadEventDefaults();
  buildSynthEvents();
  buildSynthPhysics();
  buildPianoRoll();
  bindSequencerControls();
  bindSequencePicker();
  bindPatchPicker();
  await refreshSequencePicker();
  await refreshPatchPicker();
  // Seed piano roll from current backend state.
  try {
    const seq = await api('scene/sequencer');
    if (_pianoRoll) {
      _pianoRoll.lanes = seq.lanes || [];
      _pianoRoll.notes = seq.notes || [];
      _pianoRoll.loopBeats = seq.loop_length_beats || 16;
      syncLoopLengthPicker(_pianoRoll.loopBeats);
      // Default zoom: fit the whole clip, but cap at 8 bars worth of
      // beats so very long sequences don't squash to unreadable widths.
      zoomFitWithCap(8);
    }
  } catch {}
  loadTargets();

  setInterval(pollStatus, 1000);
  setInterval(loadTargets, 5000);
  setInterval(pollLogs, 2000);
  setInterval(pollSceneState, 100);
  // Telemetry: prime once now (so the topbar temp/throttle pill populates),
  // then refresh on a slow cadence and on tab activation.
  refreshTelemetry();
  setInterval(refreshTelemetry, 5000);
  // Scale: separate cadence (1 Hz). State changes happen on the server
  // side independently — this just keeps the UI live.
  bindScaleControls();
  refreshScale();
  setInterval(refreshScale, 1000);
  // Audio: poll less frequently — the only state that changes from
  // outside the user's click is `running` (ffplay died / no media file).
  bindAudioControls();
  refreshAudio();
  setInterval(refreshAudio, 3000);
  // History charts — bind controls, kick off the initial fetch so the
  // graphs are already populated whichever tab the user starts on
  // (the early #tab hash-activation path runs before _thState exists,
  // so its refreshHistory call no-ops — this is the canonical first
  // load). Polling continues every 10 s while telemetry is visible.
  bindHistoryControls();
  refreshClockStatus();
  refreshHistory();
  setInterval(() => {
    if (document.getElementById('tab-telemetry').classList.contains('active')) {
      refreshHistory();
    }
  }, 10000);
}

init();

// ════════════════════════════════════════════════════════════════
// Nadia's Playground — isolated tab (see docs/nadia_playground.md).
// Self-contained: own state, own /api/playground calls, hooks the tab
// without touching shared code. A lean SECONDS-based timeline.
// ════════════════════════════════════════════════════════════════
(function () {
  const LABEL_W = 92, RULER_H = 22, ROW_H = 30, RESIZE = 6;
  const COLORS = ['#7a5cff', '#28c8c8', '#e632b4', '#ff7a3c', '#5cff8a', '#ffd24a'];
  const pg = {
    snap: null, lanes: [], timeline: [],
    canvas: null, ctx: null, wired: false,
    totalSec: 60, minSec: 60, drag: null,
    playing: false, playStartMs: 0,
    cueSec: 0,            // where ▶ starts; set by clicking the ruler
    withRec: false,       // last play mode (kept across seeks)
    recDur: 0,            // uploaded recording length (drawn as a strip)
    seqDur: 0,            // server-computed sequence end (incl. fades/rec)
    defaultFade: 1.5,     // server default clip ease (for drawing fades)
    pollTimer: null,      // server-truth poll while playing
  };

  async function pgPost(path, body) {
    try {
      return await api('playground' + path, {
        method: 'POST',
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch { return null; }
  }
  async function pgRefresh() {
    let s;
    try { s = await api('playground'); } catch { return; }
    if (!s || s.error) return;
    pg.snap = s; pg.lanes = s.animations || []; pg.timeline = s.timeline || [];
    pg.playing = !!s.playing;
    pg.seqDur = s.duration_sec || 0;
    pg.defaultFade = (s.default_fade_sec != null) ? s.default_fade_sec : 1.5;
    pg.recDur = (s.recording && s.recording.loaded) ? s.recording.duration_sec : 0;
    updateTotalSec();
    if (pg.playing && s.position_sec != null) {
      pg.playStartMs = performance.now() - s.position_sec * 1000;
    }
    renderTriggerButtons();
    renderRecording();
    sizeCanvas(); drawTimeline();
    // Ocean state from the shared audio snapshot.
    try {
      const a = await api('audio');
      refreshToggle('.pg-ocean-btn',
        (a && typeof a.backdrop_enabled === 'boolean') ? a.backdrop_enabled : null);
    } catch {}
  }

  function renderTriggerButtons() {
    const wrap = document.getElementById('pg-anim-buttons');
    if (!wrap) return;
    wrap.innerHTML = '';
    pg.lanes.forEach(a => {
      const b = document.createElement('button');
      b.className = 'mode-btn';
      b.textContent = a.label;
      b.classList.toggle('active', !pg.playing && pg.snap && pg.snap.current === a.id);
      b.onclick = async () => { await pgPost('/trigger/' + a.id); pgRefresh(); };
      wrap.appendChild(b);
    });
  }

  function renderRecording() {
    const st = document.getElementById('pg-rec-status');
    if (st) st.textContent = pg.snap && pg.snap.recording_file
      ? `loaded: ${pg.snap.recording_file}` : 'no recording uploaded';
  }

  // The canvas always shows at least the dropdown length, stretching to
  // fit the recording / sequence end so nothing falls off the edge.
  function updateTotalSec() {
    const need = Math.max(pg.minSec, pg.seqDur, pg.recDur);
    pg.totalSec = Math.max(10, Math.ceil(need / 10) * 10);
  }

  // ── Timeline canvas ──────────────────────────────────────────
  function sizeCanvas() {
    const c = pg.canvas, wrap = document.getElementById('pg-timeline-wrap');
    if (!c || !wrap) return;
    const w = Math.max(320, wrap.clientWidth - 2);
    const h = RULER_H + Math.max(1, pg.lanes.length) * ROW_H + 4;
    c.width = w; c.height = h; c.style.width = w + 'px'; c.style.height = h + 'px';
  }
  const pxPerSec = () => (pg.canvas.width - LABEL_W) / pg.totalSec;
  const secToX = s => LABEL_W + s * pxPerSec();
  const xToSec = x => Math.max(0, (x - LABEL_W) / pxPerSec());
  const laneAtY = y => Math.floor((y - RULER_H) / ROW_H);
  const laneTop = i => RULER_H + i * ROW_H;

  function drawTimeline() {
    const c = pg.canvas, ctx = pg.ctx;
    if (!c || !ctx) return;
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.fillStyle = '#15151c'; ctx.fillRect(0, 0, c.width, c.height);
    // Ruler ticks (every 5s, label every 10s).
    ctx.fillStyle = '#2a2a34'; ctx.fillRect(LABEL_W, 0, c.width - LABEL_W, RULER_H);
    ctx.font = '9px Arial'; ctx.textBaseline = 'middle';
    for (let s = 0; s <= pg.totalSec; s += 5) {
      const x = secToX(s);
      ctx.strokeStyle = (s % 10 === 0) ? '#444' : '#2e2e38';
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, c.height); ctx.stroke();
      if (s % 10 === 0) { ctx.fillStyle = '#aaa'; ctx.fillText(s + 's', x + 2, RULER_H / 2); }
    }
    // Lanes + labels.
    pg.lanes.forEach((a, i) => {
      const y = laneTop(i);
      ctx.fillStyle = (i % 2) ? '#181820' : '#14141b';
      ctx.fillRect(LABEL_W, y, c.width - LABEL_W, ROW_H);
      ctx.fillStyle = '#cfcfe0'; ctx.font = '10px Arial'; ctx.textAlign = 'right';
      ctx.fillText(a.label.slice(0, 14), LABEL_W - 6, y + ROW_H / 2);
      ctx.textAlign = 'left';
    });
    // Recording strip — how far Nadia's audio extends. Clips should
    // cover this; the bare orange tail is what's still uncovered.
    if (pg.recDur > 0) {
      ctx.fillStyle = '#e6a23c'; ctx.globalAlpha = 0.9;
      ctx.fillRect(secToX(0), RULER_H - 5, pg.recDur * pxPerSec(), 4);
      ctx.globalAlpha = 1;
    }
    // Clips — with their ease ramps: attack triangle inside the head,
    // translucent release tail extending past the end (that's where a
    // butted neighbor crossfades in).
    pg.timeline.forEach(clip => {
      const li = pg.lanes.findIndex(l => l.id === clip.animation);
      if (li < 0) return;
      const fi = (clip.fade_in_sec != null) ? clip.fade_in_sec : pg.defaultFade;
      const fo = (clip.fade_out_sec != null) ? clip.fade_out_sec : pg.defaultFade;
      const x = secToX(clip.start_sec), w = Math.max(3, clip.duration_sec * pxPerSec());
      const y = laneTop(li) + 3, h = ROW_H - 6;
      const col = COLORS[li % COLORS.length];
      ctx.fillStyle = col;
      ctx.globalAlpha = 0.85; ctx.fillRect(x, y, w, h);
      // Release tail (past the clip's end).
      if (fo > 0) {
        const fw = fo * pxPerSec();
        const grad = ctx.createLinearGradient(x + w, 0, x + w + fw, 0);
        grad.addColorStop(0, col); grad.addColorStop(1, 'transparent');
        ctx.globalAlpha = 0.4; ctx.fillStyle = grad;
        ctx.fillRect(x + w, y, fw, h);
      }
      ctx.globalAlpha = 1;
      // Attack ramp drawn as a darker wedge over the head.
      if (fi > 0) {
        const fw = Math.min(w, fi * pxPerSec());
        ctx.fillStyle = '#0006';
        ctx.beginPath();
        ctx.moveTo(x, y); ctx.lineTo(x + fw, y); ctx.lineTo(x, y + h);
        ctx.closePath(); ctx.fill();
      }
      ctx.strokeStyle = '#0008'; ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
      ctx.fillStyle = '#000a'; ctx.font = '9px Arial';
      ctx.fillText(`${clip.duration_sec.toFixed(1)}s`, x + 3, y + h / 2);
    });
    // Cue marker (▶ starts here; click the ruler to move it).
    if (pg.cueSec > 0) {
      const x = secToX(Math.min(pg.cueSec, pg.totalSec));
      ctx.strokeStyle = '#e6a23c'; ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, c.height); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#e6a23c';
      ctx.beginPath(); ctx.moveTo(x - 4, 1); ctx.lineTo(x + 4, 1); ctx.lineTo(x, 8);
      ctx.closePath(); ctx.fill();
    }
    // Playhead.
    if (pg.playing) {
      const pos = (performance.now() - pg.playStartMs) / 1000;
      const x = secToX(Math.min(pos, pg.totalSec));
      ctx.strokeStyle = '#5cff8a'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, c.height); ctx.stroke();
      ctx.lineWidth = 1;
    }
  }

  function clipAt(x, y) {
    const li = laneAtY(y);
    if (li < 0 || li >= pg.lanes.length) return null;
    const laneId = pg.lanes[li].id;
    for (const clip of pg.timeline) {
      if (clip.animation !== laneId) continue;
      const x0 = secToX(clip.start_sec), x1 = secToX(clip.start_sec + clip.duration_sec);
      if (x >= x0 - 2 && x <= x1 + 2) return { clip, li, x0, x1 };
    }
    return null;
  }

  function evtXY(e) {
    const r = pg.canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function onDown(e) {
    const { x, y } = evtXY(e);
    // Clicking the ruler sets the cue point — and jumps there live if
    // a sequence is already playing.
    if (y < RULER_H && x >= LABEL_W) { seekTo(xToSec(x)); return; }
    if (x < LABEL_W || y < RULER_H) return;
    const li = laneAtY(y);
    if (li < 0 || li >= pg.lanes.length) return;
    const hit = clipAt(x, y);
    if (hit) {
      const onEdge = x >= hit.x1 - RESIZE;
      pg.drag = { mode: onEdge ? 'resize' : 'move', clip: hit.clip,
                  grabSec: xToSec(x) - hit.clip.start_sec };
    } else {
      const clip = { animation: pg.lanes[li].id, start_sec: xToSec(x), duration_sec: 0.2 };
      pg.timeline.push(clip);
      pg.drag = { mode: 'resize', clip, grabSec: 0 };
    }
    drawTimeline();
  }
  function onMove(e) {
    if (!pg.drag) return;
    const { x } = evtXY(e);
    const clip = pg.drag.clip;
    if (pg.drag.mode === 'move') {
      clip.start_sec = Math.max(0, Math.min(pg.totalSec - clip.duration_sec, xToSec(x) - pg.drag.grabSec));
    } else {
      clip.duration_sec = Math.max(0.2, Math.min(pg.totalSec - clip.start_sec, xToSec(x) - clip.start_sec));
    }
    drawTimeline();
  }
  function onUp() {
    if (!pg.drag) return;
    pg.drag = null;
    saveTimeline();
  }
  function onDbl(e) {
    const { x, y } = evtXY(e);
    const hit = clipAt(x, y);
    if (hit) { pg.timeline = pg.timeline.filter(c => c !== hit.clip); drawTimeline(); saveTimeline(); }
  }
  async function saveTimeline() {
    const clean = pg.timeline.map(c => {
      const out = {
        animation: c.animation,
        start_sec: Math.round(c.start_sec * 100) / 100,
        duration_sec: Math.round(c.duration_sec * 100) / 100,
      };
      // Preserve per-clip ease overrides if a clip carries them.
      if (c.fade_in_sec != null) out.fade_in_sec = c.fade_in_sec;
      if (c.fade_out_sec != null) out.fade_out_sec = c.fade_out_sec;
      return out;
    });
    try { await api('playground', { method: 'PUT', body: JSON.stringify({ timeline: clean }) }); } catch {}
  }

  // ── Cue + seek ────────────────────────────────────────────────
  async function seekTo(sec) {
    pg.cueSec = Math.max(0, Math.round(sec * 10) / 10);
    if (pg.playing) {
      await pgPost('/play', { with_recording: pg.withRec, start_sec: pg.cueSec });
      startPlayhead(pg.cueSec);
    }
    updateInfo(); drawTimeline();
  }

  function updateInfo() {
    const info = document.getElementById('pg-seq-info');
    if (!info) return;
    const cue = pg.cueSec > 0 ? ` · cue ${pg.cueSec.toFixed(1)}s` : '';
    info.textContent = (pg.playing ? 'playing' : 'stopped') + cue;
  }

  // ── Playhead: local clock anchored to server truth ────────────
  function startPlayhead(posSec) {
    pg.playing = true;
    pg.playStartMs = performance.now() - (posSec || 0) * 1000;
    updateInfo();
    const tick = () => {
      if (!pg.playing) return;
      drawTimeline(); requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    // Poll the server while playing: re-anchor the playhead (render
    // thread is the time authority) and notice the sequence ending.
    if (pg.pollTimer) clearInterval(pg.pollTimer);
    pg.pollTimer = setInterval(async () => {
      let s; try { s = await api('playground'); } catch { return; }
      if (!s || s.error) return;
      if (!s.playing) { stopLocal(); return; }
      if (s.position_sec != null) {
        pg.playStartMs = performance.now() - s.position_sec * 1000;
      }
    }, 750);
  }

  function stopLocal() {
    pg.playing = false;
    if (pg.pollTimer) { clearInterval(pg.pollTimer); pg.pollTimer = null; }
    updateInfo(); drawTimeline(); renderTriggerButtons();
  }

  function pgInit() {
    if (pg.wired) { sizeCanvas(); drawTimeline(); return; }
    pg.canvas = document.getElementById('pg-timeline');
    if (!pg.canvas) return;
    pg.ctx = pg.canvas.getContext('2d');
    pg.canvas.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    pg.canvas.addEventListener('dblclick', onDbl);

    const lenSel = document.getElementById('pg-length');
    if (lenSel) { pg.minSec = parseInt(lenSel.value, 10) || 60; updateTotalSec();
      lenSel.onchange = () => { pg.minSec = parseInt(lenSel.value, 10) || 60;
        updateTotalSec(); sizeCanvas(); drawTimeline(); }; }

    const play = async (withRec) => {
      pg.withRec = withRec;
      await pgPost('/play', { with_recording: withRec, start_sec: pg.cueSec });
      startPlayhead(pg.cueSec); renderTriggerButtons();
    };
    document.getElementById('pg-play').onclick = () => play(false);
    document.getElementById('pg-play-rec').onclick = () => play(true);
    document.getElementById('pg-stop').onclick = async () => { await pgPost('/stop'); stopLocal(); };
    document.getElementById('pg-clear').onclick = async () => {
      if (!confirm('Remove all clips from the timeline?')) return;
      pg.timeline = []; drawTimeline(); await saveTimeline();
    };

    // Recording.
    const fileInput = document.getElementById('pg-rec-file');
    if (fileInput) fileInput.onchange = async () => {
      const f = fileInput.files && fileInput.files[0];
      if (!f) return;
      const st = document.getElementById('pg-rec-status'); if (st) st.textContent = 'uploading…';
      try {
        await fetch('/api/playground/recording?name=' + encodeURIComponent(f.name),
                    { method: 'POST', body: f });
      } catch {}
      pgRefresh();
    };
    document.getElementById('pg-rec-play').onclick = async () => { await pgPost('/recording/play'); };
    document.getElementById('pg-rec-stop').onclick = async () => { await pgPost('/recording/stop'); };

    // Ocean.
    document.querySelectorAll('.pg-ocean-btn').forEach(b => {
      b.onclick = async () => {
        await pgPost('/ocean', { enabled: b.dataset.val === 'true' });
        refreshToggle('.pg-ocean-btn', b.dataset.val === 'true');
      };
    });

    pg.wired = true;
    sizeCanvas(); drawTimeline();
  }

  // Hook the tab (addEventListener doesn't clobber the existing onclick).
  const tabBtn = document.querySelector('.tab[data-tab="playground"]');
  if (tabBtn) tabBtn.addEventListener('click', () => { pgInit(); pgRefresh(); });
  // If we deep-link to #playground, init on load.
  if ((location.hash || '').replace(/^#/, '') === 'playground') { pgInit(); pgRefresh(); }
})();
