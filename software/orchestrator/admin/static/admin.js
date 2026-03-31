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
  const ip = prompt('IP address:', '192.168.1.100');
  if (!ip) return;
  const port = parseInt(prompt('UDP port:', '21324'));
  if (isNaN(port)) return;
  await api('targets', { method: 'POST', body: JSON.stringify({ name, ip, port }) });
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

const BREATHING_COLORS = [
  { key: 'rim_color', label: 'Rim Color' },
  { key: 'inner_color', label: 'Inner Color' },
  { key: 'outer_color', label: 'Outer Color' },
  { key: 'trail_color', label: 'Trail Color' },
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

// ── Init ───────────────────────────────────────────────────
async function init() {
  config = await api('config');
  updateModeButtons(config.mode);
  buildSliders('breathing-params', 'breathing', BREATHING_SLIDERS, BREATHING_COLORS);
  buildSliders('standby-params', 'standby', STANDBY_SLIDERS);
  loadTargets();

  setInterval(pollStatus, 1000);
  setInterval(loadTargets, 5000);
  setInterval(pollLogs, 2000);
}

init();
