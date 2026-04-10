// HERE Admin Panel

let config = {};

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
document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.onclick = async () => {
    await api(`mode/${btn.dataset.mode}`, { method: 'POST' });
    updateModeButtons(btn.dataset.mode);
  };
});

function updateModeButtons(mode) {
  document.querySelectorAll('.mode-btn').forEach(b => {
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

const PALETTE_COLOR_KEYS = ['rim_color', 'inner_color', 'outer_color', 'trail_color'];

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

let updateTimer = null;

function buildSliders(container, section, sliders, colors) {
  const el = document.getElementById(container);
  el.innerHTML = '';

  // Restore defaults button
  const restoreBtn = document.createElement('button');
  restoreBtn.textContent = 'Restore Defaults';
  restoreBtn.style.cssText = 'float:right;padding:4px 10px;background:#2a1a1a;border:1px solid #633;color:#a88;border-radius:3px;cursor:pointer;font-size:12px;margin-bottom:8px;';
  restoreBtn.onclick = async () => {
    if (!confirm(`Restore ${section} parameters to defaults?`)) return;
    config = await api(`defaults/restore/${section}`, { method: 'POST' });
    buildSliders(container, section, sliders, colors);
  };
  el.appendChild(restoreBtn);

  sliders.forEach(s => {
    const val = config[section]?.[s.key] ?? s.min;
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
      debouncedUpdate(section, s.key, v);
    };
    el.appendChild(row);
  });

  if (colors) {
    colors.forEach(c => {
      const val = config[section]?.[c.key] ?? [0, 0, 0];
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
        debouncedUpdate(section, c.key, rgb);
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

// ── Status polling ─────────────────────────────────────────
async function pollStatus() {
  try {
    const s = await api('status');
    document.getElementById('s-mode').textContent = s.mode;
    document.getElementById('s-fps').textContent = s.fps;
    const m = Math.floor(s.uptime_s / 60);
    const sec = s.uptime_s % 60;
    document.getElementById('s-uptime').textContent = `${m}m ${sec}s`;
    if (s.power) {
      document.getElementById('s-led-w').textContent = s.power.led_watts;
      document.getElementById('s-total-w').textContent = s.power.total_watts;
      document.getElementById('s-daily').textContent = s.power.daily_wh;
      document.getElementById('s-batt').textContent = s.power.battery_days;
    }
    updateModeButtons(s.mode);
    updateProtoButtons(config.transport?.protocol || 'ddp');
    // Keep spin toggles in sync
    const spin = config.breathing?.spin || {};
    document.querySelectorAll('.spin-toggle').forEach(b =>
      b.classList.toggle('active', String(spin.enabled || false) === b.dataset.val)
    );
    document.querySelectorAll('.spin-mode-btn').forEach(b =>
      b.classList.toggle('active', (spin.mode || 'constant') === b.dataset.val)
    );
    document.querySelectorAll('.spin-dir-btn').forEach(b =>
      b.classList.toggle('active', String(spin.yoyo_reverse ?? true) === b.dataset.val)
    );
  } catch {}
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

  // On/Off toggle
  document.querySelectorAll('.spin-toggle').forEach(btn => {
    btn.classList.toggle('active', String(spin.enabled || false) === btn.dataset.val);
    btn.onclick = async () => {
      const enabled = btn.dataset.val === 'true';
      await api('config', {
        method: 'PUT',
        body: JSON.stringify({ breathing: { spin: { enabled } } }),
      });
      config = await api('config');
    };
  });

  // Mode toggle
  document.querySelectorAll('.spin-mode-btn').forEach(btn => {
    btn.classList.toggle('active', (spin.mode || 'constant') === btn.dataset.val);
    btn.onclick = async () => {
      await api('config', {
        method: 'PUT',
        body: JSON.stringify({ breathing: { spin: { mode: btn.dataset.val } } }),
      });
      config = await api('config');
    };
  });

  // Direction toggle
  document.querySelectorAll('.spin-dir-btn').forEach(btn => {
    btn.classList.toggle('active', String(spin.yoyo_reverse ?? true) === btn.dataset.val);
    btn.onclick = async () => {
      const rev = btn.dataset.val === 'true';
      await api('config', {
        method: 'PUT',
        body: JSON.stringify({ breathing: { spin: { yoyo_reverse: rev } } }),
      });
      config = await api('config');
    };
  });

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
    // Color preview stripe
    const colors = [pal.rim_color, pal.inner_color, pal.outer_color, pal.trail_color];
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
    const label = key.replace('_color', '').replace('_', ' ');
    const row = document.createElement('div');
    row.className = 'param-row';
    row.innerHTML = `
      <label>${label[0].toUpperCase() + label.slice(1)}</label>
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
      // Update gradient previews without rebuilding the editor
      updatePaletteGradients();
    };
    editor.appendChild(row);
  });
}

function updatePaletteGradients() {
  const palettes = config.breathing?.palettes || [];
  document.querySelectorAll('.palette-btn').forEach((btn, i) => {
    const pal = palettes[i];
    if (!pal) return;
    const colors = [pal.rim_color, pal.inner_color, pal.outer_color, pal.trail_color];
    const gradient = colors.map((c, ci) => {
      const pct = (ci / (colors.length - 1)) * 100;
      return `rgb(${c[0]},${c[1]},${c[2]}) ${pct}%`;
    }).join(', ');
    const gradDiv = btn.querySelector('div');
    if (gradDiv) gradDiv.style.background = `linear-gradient(90deg,${gradient})`;
  });
}

// ── Protocol buttons ───────────────────────────────────────
function initProtocolButtons() {
  const current = config.transport?.protocol || 'ddp';
  updateProtoButtons(current);
  document.querySelectorAll('.proto-btn').forEach(btn => {
    btn.onclick = async () => {
      const proto = btn.dataset.proto;
      await api('config', {
        method: 'PUT',
        body: JSON.stringify({ transport: { protocol: proto } }),
      });
      updateProtoButtons(proto);
      config.transport.protocol = proto;
    };
  });
}

function updateProtoButtons(active) {
  document.querySelectorAll('.proto-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.proto === active)
  );
}

// ── Init ───────────────────────────────────────────────────
async function init() {
  config = await api('config');
  updateModeButtons(config.mode);
  buildSliders('transport-params', 'transport', TRANSPORT_SLIDERS);
  initProtocolButtons();
  buildSliders('breathing-params', 'breathing', BREATHING_SLIDERS);
  initSpinControls();
  buildPaletteSelector();
  buildSliders('standby-params', 'standby', STANDBY_SLIDERS);
  loadTargets();

  setInterval(pollStatus, 1000);
  setInterval(loadTargets, 5000);
  setInterval(pollLogs, 2000);
}

init();
