// HERE Admin Panel

let config = {};

// ── Tabs ───────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(btn => {
  btn.onclick = () => {
    const id = btn.dataset.tab;
    document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b === btn));
    document.querySelectorAll('.pane').forEach(p =>
      p.classList.toggle('active', p.id === `tab-${id}`)
    );
    if (id === 'telemetry') refreshTelemetry();
    if (id === 'sim') openSimulator();
  };
});

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
// When leaving the sim tab, free the iframe (and its WebGL context).
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.dataset.tab !== 'sim') closeSimulator();
  });
});

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
  buildSliders('transport-params', 'transport', TRANSPORT_SLIDERS);
  buildSliders('breathing-params', 'breathing', BREATHING_SLIDERS);
  initSpinControls();
  buildPaletteSelector();
  buildSliders('standby-params', 'standby', STANDBY_SLIDERS);
  loadTargets();

  setInterval(pollStatus, 1000);
  setInterval(loadTargets, 5000);
  setInterval(pollLogs, 2000);
  // Telemetry: prime once now (so the topbar temp/throttle pill populates),
  // then refresh on a slow cadence and on tab activation.
  refreshTelemetry();
  setInterval(refreshTelemetry, 5000);
}

init();
