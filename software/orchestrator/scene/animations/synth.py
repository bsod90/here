"""SynthAnimation — the v2 visual.

Three independently-controllable oval rings (rim, mid, outer) drawn back-to-
front (rim on top), each with its own enable toggle, skew, blur, color slot,
and rotation. The geometry is centered on `(grid.center + ball.cx,
grid.center + ball.cy)` and stretched by the physics ball's squash tensor
`(sx, sy)`, so Float events visibly bounce/squash the whole scene.

A multi-frequency shimmer rotates slowly over lit pixels. Palette
crossfade is the same model as v1 (palette_idx + palette_target_idx +
palette_blend mixed by the Scene).

This module is pure rendering — it does not own state mutations. The
Scene drives state via modulators + physics. Required state keys are
listed in `initial_state()` and `STATE_KEYS`.

Pi 4 budget: numpy renders one 44×44 grid (1936 pixels) at 30 fps with
~12 numpy ops, comfortable margin.
"""
from __future__ import annotations

import time
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

from grid import DEFAULT_GRID, Grid


# State keys this animation reads from the Scene state dict, plus their
# default values. Kept here so the Scene knows what to seed.
STATE_KEYS = {
    # Geometry — driven by Expand/Contract/Blow Out/Regrow modulators.
    "radius": 8.0,
    "alpha": 1.0,
    # Per-oval state (i = 0..2). oval_velocity_* is in rad/s and gets
    # accumulated into oval_rotation_* by the Scene's tick. oval_side_*
    # is 'both' | 'inside' | 'outside' — controls which half of the
    # Gaussian ring is drawn. Inside-only / outside-only let you recreate
    # the classic "narrow rim with separate inner + outer halos" look.
    "oval_enabled_0": True,
    "oval_enabled_1": True,
    "oval_enabled_2": True,
    "oval_skew_0": 0.12,
    "oval_skew_1": 0.18,
    "oval_skew_2": 0.20,
    "oval_phase_0": 0.0,
    "oval_phase_1": 1.0,
    "oval_phase_2": 2.1,
    "oval_rotation_0": 0.0,
    "oval_rotation_1": 0.0,
    "oval_rotation_2": 0.0,
    "oval_velocity_0": 0.0,
    "oval_velocity_1": 0.0,
    "oval_velocity_2": 0.0,
    "oval_side_0": "both",
    "oval_side_1": "both",
    "oval_side_2": "both",
    # Dashed mode — per oval. segments=0 means continuous ring;
    # segments=N draws N dashes per revolution, gap is the fraction of
    # each segment that's dark (0=fully lit, 1=all gap).
    "oval_segments_0": 0,
    "oval_segments_1": 0,
    "oval_segments_2": 0,
    "oval_gap_0": 0.4,
    "oval_gap_1": 0.4,
    "oval_gap_2": 0.4,
    # Per-oval radius OFFSET — index meaning is now
    # 0 = outer (drawn back), 1 = middle (drawn on top),
    # 2 = inner (drawn between outer and middle). The final per-oval
    # radius is `radius + offset[i] * gap_coefficient`. With gap_coef=0
    # all three rings sit at exactly the same radius (no gap). Larger
    # gap_coef → outer spreads out, inner contracts inward.
    "oval_radius_offset_0":  1.0,   # outer
    "oval_radius_offset_1":  0.0,   # middle
    "oval_radius_offset_2": -1.0,   # inner
    # Per-oval palette-color index (0..7). Lets the user pick any of
    # the 8 palette slots per oval. Default: outer→outer_color,
    # middle→rim_color, inner→inner_color.
    "oval_color_0": 2,   # outer  → palette outer_color
    "oval_color_1": 0,   # middle → palette rim_color (on top, brightest)
    "oval_color_2": 1,   # inner  → palette inner_color
    # Palette crossfade.
    "palette_idx": 0,
    "palette_target_idx": 0,
    "palette_blend": 0.0,
    # Dissolve/respawn — 0 = solid ring, 1 = fully dispersed dots.
    # Drives the dot-cloud render path in render() (replaces the ring).
    # `dissolve_phase` tags whether we're going from solid→dispersed
    # (dissolve) or dispersed→solid (respawn); both drive the same
    # `dissolve_amount` state but choose direction implicitly via the
    # modulator's base/peak values.
    "dissolve_amount": 0.0,
    # 0 = renderer uses live radius for dot-cloud drift_max. Non-zero =
    # locked dispersal radius captured at dissolve/respawn trigger time
    # so a Contract/Expand mid-cycle can't snap the cloud.
    "dissolve_radius_lock": 0.0,
    # Particle motion knobs — orchestrated by DissolveAction /
    # RespawnAction modulators over the lifetime of the animation.
    # dot_speed: 0..1, multiplies a base forward speed (LED/sec).
    # dot_orbit_lock: 0..1 — how strongly the heading is steered toward
    #     the orbital tangent of the particle's assigned ring.
    #     1.0 = particle locked onto the ring (visually IS the ring).
    #     0.5 = wandering but biased toward circular motion.
    #     0.0 = pure forward wander, no orbital coherence.
    # dot_visibility: 0..1 — multiplier on rendered dot intensity.
    #     Drives a smooth fade-out at the end of respawn (particles
    #     dim as they hand off to ring rendering) rather than just
    #     vanishing when _pin_amount fires.
    "dot_speed": 0.5,
    "dot_orbit_lock": 1.0,
    "dot_visibility": 1.0,
    # Voice-shimmer amplitude — adds a high-frequency radial wobble
    # to the ring rendering. Driven by the `shimmer` event which
    # ramps it up on note_on and back down on note_off (sustain),
    # giving the rings a "talking" / vibrating-voice feel.
    "shimmer_amount": 0.0,
    # Multiplier on the wobble time-rate. ShimmerAction sets this
    # from the note's duration_beats: short notes = fast vibrato,
    # long notes = slow rumble. Default 1.0 = base frequencies.
    "shimmer_speed_mult": 1.0,
}


# Cached per-grid geometry: keyed by grid id() so different grid sizes
# get their own cache. Only computed once per (size, pitch) pair.
_GEOM_CACHE: dict[int, dict] = {}


def _geometry_for(grid: Grid):
    """Return (dist, angles, dx, dy) arrays for the given Grid."""
    key = id(grid)
    cached = _GEOM_CACHE.get(key)
    if cached is not None:
        return cached["dist"], cached["angle"], cached["dx"], cached["dy"]
    if np is None:
        raise RuntimeError("synth.render requires numpy")
    dx = np.array([c - grid.center for _, c in grid.positions], dtype=np.float32)
    dy = np.array([r - grid.center for r, _ in grid.positions], dtype=np.float32)
    dist = np.sqrt(dx * dx + dy * dy).astype(np.float32)
    angle = np.arctan2(dy, dx).astype(np.float32)
    _GEOM_CACHE[key] = {"dist": dist, "angle": angle, "dx": dx, "dy": dy}
    return dist, angle, dx, dy


def _safe_get(d: dict, key: str, default):
    """Convenience: dict.get with type-coerced default. Treats None as default."""
    v = d.get(key)
    return default if v is None else v


class SynthAnimation:
    """The v2 scene visual — 3 ovals + physics-ball overlay."""

    name = "synth"

    # Default lanes — matches old breathing order for back-compat, plus new
    # float lanes appended. Each entry is `{label, event, params?}`.
    NOTE_LANES = [
        {"label": "Expand",        "event": "expand"},
        {"label": "Contract",      "event": "contract"},
        {"label": "Rotate CW",     "event": "rotate_cw"},
        {"label": "Rotate CCW",    "event": "rotate_ccw"},
        {"label": "Pulse",         "event": "pulse"},
        {"label": "Blow Out",      "event": "blow_out"},
        {"label": "Regrow",        "event": "regrow"},
        {"label": "Dissolve",      "event": "dissolve"},
        {"label": "Respawn",       "event": "respawn"},
        # NOTE: do not insert new lanes here — pitches downstream of
        # this point shift, breaking saved sequences. Append to the
        # END of NOTE_LANES instead. Shimmer is appended below.
        {"label": "Palette 1",     "event": "color_palette", "params": {"palette": 0}},
        {"label": "Palette 2",     "event": "color_palette", "params": {"palette": 1}},
        {"label": "Palette 3",     "event": "color_palette", "params": {"palette": 2}},
        {"label": "Palette 4",     "event": "color_palette", "params": {"palette": 3}},
        {"label": "Push L",        "event": "push_left"},
        {"label": "Push R",        "event": "push_right"},
        {"label": "Push U",        "event": "push_up"},
        {"label": "Push D",        "event": "push_down"},
        {"label": "Pull Center",   "event": "pull_center"},
        # Per-ring rotation (outer / middle / inner; index 0/1/2).
        {"label": "Outer CW",      "event": "rotate_cw_outer"},
        {"label": "Outer CCW",     "event": "rotate_ccw_outer"},
        {"label": "Middle CW",     "event": "rotate_cw_middle"},
        {"label": "Middle CCW",    "event": "rotate_ccw_middle"},
        {"label": "Inner CW",      "event": "rotate_cw_inner"},
        {"label": "Inner CCW",     "event": "rotate_ccw_inner"},
        {"label": "Stop Rot All",  "event": "stop_rotation"},
        {"label": "Stop Outer",    "event": "stop_rotation_outer"},
        {"label": "Stop Middle",   "event": "stop_rotation_middle"},
        {"label": "Stop Inner",    "event": "stop_rotation_inner"},
        {"label": "Push Random",   "event": "push_random"},
        # Per-circle show / hide (outer / middle / inner).
        {"label": "Show Outer",    "event": "show_outer"},
        {"label": "Hide Outer",    "event": "hide_outer"},
        {"label": "Show Middle",   "event": "show_middle"},
        {"label": "Hide Middle",   "event": "hide_middle"},
        {"label": "Show Inner",    "event": "show_inner"},
        {"label": "Hide Inner",    "event": "hide_inner"},
        # SFX overlays.
        {"label": "Meteors",       "event": "meteors"},
        {"label": "Dust",          "event": "dust"},
        {"label": "Flash",         "event": "flash"},
        {"label": "Wipe",          "event": "wipe"},
        # Append-only zone: new lanes go here so existing saved
        # sequences keep mapping to the same pitches.
        {"label": "Shimmer",       "event": "shimmer"},
    ]

    def __init__(self, meta: dict | None = None):
        self.meta = dict(meta or {})
        # Stateful dot-particle simulation. Each particle owns position,
        # heading, and a deque-style trail buffer. Spawned lazily when
        # dissolve_amount transitions away from 0; cleared back to 0.
        # See `_advance_particles` for the motion model.
        self._dots_xy = None          # (N, 2) current positions
        self._dots_heading = None     # (N,)   heading angle rad
        self._dots_trail = None       # (N, MAX_TRAIL+1, 2) ring buffer
        self._dots_trail_head = 0     # index of newest sample in ring
        self._dots_seeds = None       # per-particle phase offsets
        self._dots_spawned_at_amount = 0.0
        self._dots_last_radius = 0.0

    def update_meta(self, meta: dict, *, replace: bool = False) -> None:
        """Update animation meta. Default: shallow-merge so partial
        updates (e.g. one blur knob change from the admin UI) preserve
        all other meta keys. `replace=True` wipes the dict — used when
        loading a patch where the user expects a clean slate."""
        if replace:
            self.meta = dict(meta or {})
        else:
            self.meta.update(meta or {})

    # ── Scene contract ──────────────────────────────────────────────
    def initial_state(self) -> dict[str, Any]:
        st = dict(STATE_KEYS)
        # Pull configured defaults from meta where they exist.
        st["radius"] = float(self.meta.get("radius_default", st["radius"]))
        st["alpha"]  = float(self.meta.get("alpha_default", st["alpha"]))
        for i in range(3):
            st[f"oval_skew_{i}"]     = float(self.meta.get(f"oval_skew_{i}",     st[f"oval_skew_{i}"]))
            st[f"oval_phase_{i}"]    = float(self.meta.get(f"oval_phase_{i}",    st[f"oval_phase_{i}"]))
            st[f"oval_enabled_{i}"]  = bool( self.meta.get(f"oval_enabled_{i}",  True))
            # Per-oval drift — same role as OG breathing's *_drift_rate.
            # When non-zero, the ovals slowly rotate even without a Rotate event.
            st[f"oval_velocity_{i}"] = float(self.meta.get(f"oval_velocity_{i}", 0.0))
            st[f"oval_side_{i}"]     = str(  self.meta.get(f"oval_side_{i}",     "both"))
            st[f"oval_segments_{i}"] = int(  self.meta.get(f"oval_segments_{i}", 0))
            st[f"oval_gap_{i}"]      = float(self.meta.get(f"oval_gap_{i}",      0.4))
            st[f"oval_radius_offset_{i}"] = float(
                self.meta.get(f"oval_radius_offset_{i}",
                              st[f"oval_radius_offset_{i}"]))
            st[f"oval_color_{i}"] = int(
                self.meta.get(f"oval_color_{i}", st[f"oval_color_{i}"]))
        return st

    # Max trail buffer slots — caps the longest tail the user can dial in.
    _MAX_TRAIL = 32

    # ── Particle lifecycle (called by DissolveAction / RespawnAction) ──
    def clear_particles(self) -> None:
        """Drop the particle simulation state. Called by DissolveAction's
        _pin_dark at the end of the fade — at that point alpha=0 so
        any particles still in flight are invisible, and we want to
        stop simulating them entirely (free the buffers; stop ticking)."""
        self._dots_xy = None
        self._dots_heading = None
        self._dots_trail = None

    def spawn_particles_on_rings(self, state: dict) -> None:
        """Place particles ON the three rings, headings = orbital tangent.
        Called by DissolveAction at trigger time so the dissolve starts
        with particles indistinguishable from the rings — they don't pop
        into existence."""
        if np is None:
            return
        n = int(self.meta.get("dot_count", 12))
        # Compute the three ring radii (matches the render loop).
        master_r = float(state.get("radius", self.meta.get("radius_default", 8.0)))
        master_r = max(1.0, master_r)
        gap_coef = float(self.meta.get("gap_coefficient", 1.0))
        radii = []
        for i in range(3):
            offset = float(state.get(f"oval_radius_offset_{i}", 0.0))
            radii.append(max(1.0, master_r + offset * gap_coef))
        radii = np.array(radii, dtype=np.float32)

        # Assign particles round-robin to rings.
        ring_idx = (np.arange(n) % 3).astype(np.int32)
        # Even angular spacing within each ring (offset by ring so they
        # don't all align radially).
        angles = np.empty(n, dtype=np.float32)
        for r in range(3):
            mask = ring_idx == r
            count = int(np.sum(mask))
            if count == 0:
                continue
            offsets = np.arange(count, dtype=np.float32) * (2 * np.pi / count)
            angles[mask] = offsets + r * (np.pi / 6.0)

        self._dots_ring = ring_idx
        self._dots_ring_radius = radii[ring_idx]
        self._dots_xy = np.stack([
            self._dots_ring_radius * np.cos(angles),
            self._dots_ring_radius * np.sin(angles),
        ], axis=1).astype(np.float32)
        # Tangent direction = angle + π/2 (CCW).
        self._dots_heading = (angles + np.pi * 0.5).astype(np.float32)
        self._dots_trail = np.tile(
            self._dots_xy[:, np.newaxis, :], (1, self._MAX_TRAIL + 1, 1))
        self._dots_trail_head = 0
        rng = np.random.default_rng(seed=42)
        self._dots_seeds = rng.uniform(0.0, 2.0 * np.pi, n).astype(np.float32)

    def spawn_particles_random(self, state: dict, grid=None) -> None:
        """Spawn particles BEYOND each grid edge with headings pointing
        inward. They fly IN from the four sides as the respawn
        orchestration drives their motion — matches the user's
        "particles enter from each boundary" spec."""
        if np is None:
            return
        n = int(self.meta.get("dot_count", 12))
        master_r = float(state.get("radius", self.meta.get("radius_default", 8.0)))
        master_r = max(1.0, master_r)
        gap_coef = float(self.meta.get("gap_coefficient", 1.0))
        radii = []
        for i in range(3):
            offset = float(state.get(f"oval_radius_offset_{i}", 0.0))
            radii.append(max(1.0, master_r + offset * gap_coef))
        radii = np.array(radii, dtype=np.float32)
        ring_idx = (np.arange(n) % 3).astype(np.int32)

        rng = np.random.default_rng(seed=int(time.time() * 1000) & 0xffff)

        # Grid half-width (in LED units relative to center). Spawn just
        # outside it. Falls back to a generous default if no grid passed.
        grid_half = float(getattr(grid, "center", 22.0)) if grid is not None else 22.0
        spawn_offset = max(2.0, grid_half * 0.18)  # how far outside the edge
        # Distribute particles round-robin across the 4 sides.
        sides = np.arange(n) % 4   # 0=left, 1=right, 2=top, 3=bottom
        # Position along the chosen edge — random along the perpendicular
        # axis, fixed position just outside the parallel axis.
        edge_pos = rng.uniform(-grid_half * 0.9, grid_half * 0.9, n).astype(np.float32)
        out_edge = grid_half + spawn_offset
        x = np.where(sides == 0, -out_edge,
            np.where(sides == 1, out_edge,
            np.where(sides == 2, edge_pos, edge_pos))).astype(np.float32)
        y = np.where(sides == 0, edge_pos,
            np.where(sides == 1, edge_pos,
            np.where(sides == 2, -out_edge, out_edge))).astype(np.float32)
        self._dots_xy = np.stack([x, y], axis=1).astype(np.float32)
        # Heading: aim toward origin with small per-particle jitter.
        inward = np.arctan2(-y, -x)
        deflection = rng.uniform(-0.35, 0.35, n).astype(np.float32)
        self._dots_heading = (inward + deflection).astype(np.float32)
        self._dots_ring = ring_idx
        self._dots_ring_radius = radii[ring_idx]
        self._dots_trail = np.tile(
            self._dots_xy[:, np.newaxis, :], (1, self._MAX_TRAIL + 1, 1))
        self._dots_trail_head = 0
        self._dots_seeds = rng.uniform(0.0, 2.0 * np.pi, n).astype(np.float32)

    def tick(self, state: dict, beat: float, dt_seconds: float) -> None:
        """Per-frame derived work — integrate per-oval rotation AND the
        dot-particle simulation. The motion model is:

          target_heading = orbital tangent at the particle's current
                           angular position on its assigned ring
                           (with a slight radial correction toward the
                           ring radius if the particle has wandered off)
          steer_strength = (1 - dissolve_amount)^2
          heading += diff_angle(target_heading - heading) * steer_strength * STEER_K * dt
          heading += smooth_random_wander * dissolve_amount^2 * dt
          position += (cos(h), sin(h)) * speed * dt

        At dissolve_amount=0 the particles lock perfectly to their rings;
        at dissolve_amount=1 they wander freely. Inspired by Reynolds-
        style steering behaviors but reduced to one steering target.
        """
        for i in range(3):
            v = float(state.get(f"oval_velocity_{i}", 0.0))
            state[f"oval_rotation_{i}"] = float(state.get(f"oval_rotation_{i}", 0.0)) + v * dt_seconds

        # Dot particle simulation.
        if np is None or dt_seconds <= 0:
            return
        dissolve_amount = float(state.get("dissolve_amount", 0.0))
        dissolve_amount = max(0.0, min(1.0, dissolve_amount))

        if dissolve_amount <= 0.001:
            # Cleared state — release buffers so next dissolve spawns fresh.
            self._dots_xy = None
            return

        # If particles haven't been seeded (e.g. first frame and the
        # actions didn't pre-seed), lazy-spawn on the rings.
        if self._dots_xy is None:
            self.spawn_particles_on_rings(state)

        # Refresh ring radii each tick — Expand/Contract may have moved
        # the rings since spawn. Particles steer to the LIVE radii.
        master_r = float(state.get("radius", self.meta.get("radius_default", 8.0)))
        master_r = max(1.0, master_r)
        gap_coef = float(self.meta.get("gap_coefficient", 1.0))
        radii_live = np.array([
            max(1.0, master_r + float(state.get(f"oval_radius_offset_{i}", 0.0)) * gap_coef)
            for i in range(3)
        ], dtype=np.float32)
        self._dots_ring_radius = radii_live[self._dots_ring]

        # Read the orchestration knobs.
        dot_orbit_lock = float(state.get("dot_orbit_lock", 1.0))
        dot_orbit_lock = max(0.0, min(1.0, dot_orbit_lock))
        # Optional global speed override; defaults to 1.0 (= follow
        # orbit_lock-derived speed). DissolveAction can boost above
        # 1.0 to push particles off-screen during the random phase.
        dot_speed_mult = float(state.get("dot_speed", 1.0))
        dot_speed_mult = max(0.0, min(2.5, dot_speed_mult))

        # Speed derived from orbit_lock: closer to orbit → faster.
        # Shape: speed = MIN + (MAX - MIN) * orbit_lock^exp
        # exp > 1 → speed grows slowly at first, accelerates as lock
        #          approaches 1 (matches "speed up into orbit" feel).
        # exp = 1 → linear.
        # exp < 1 → speed climbs fast early, levels off.
        speed_min = float(self.meta.get("dot_speed_min", 0.10))
        speed_max = float(self.meta.get("dot_speed_max", 1.30))
        curve_exp = float(self.meta.get("dot_speed_lock_exp", 1.6))
        lock_shaped = max(0.0, dot_orbit_lock) ** curve_exp
        BASE_SPEED = 36.0
        speed = BASE_SPEED * dot_speed_mult * (
            speed_min + (speed_max - speed_min) * lock_shaped
        )

        # Steering: compute target heading per particle.
        # We blend two unit vectors in CARTESIAN space (not angles!) —
        # adding a radial offset to an angle in radians doesn't give
        # the "tangent + a bit inward" direction one might expect.
        # tangent_vec = CCW orbital tangent
        # radial_vec  = unit vector pointing INWARD (toward center)
        #               if particle is outside its ring, OUTWARD if
        #               inside; magnitude scales with |r_err|.
        # target_vec  = tangent + RADIAL_WEIGHT * radial — then atan2.
        x = self._dots_xy[:, 0]
        y = self._dots_xy[:, 1]
        cur_r = np.sqrt(x * x + y * y) + 1e-6
        angle_p = np.arctan2(y, x)
        cos_p = np.cos(angle_p)
        sin_p = np.sin(angle_p)
        tan_x = -sin_p   # = cos(angle_p + π/2), CCW tangent
        tan_y =  cos_p
        # Inward direction = -(x,y)/r; magnitude proportional to err.
        r_err = cur_r - self._dots_ring_radius   # +ve = outside ring
        radial_pull = np.clip(r_err / 4.0, -1.0, 1.0)
        RADIAL_WEIGHT = 1.0   # higher = particles converge harder
        target_x = tan_x + RADIAL_WEIGHT * radial_pull * (-cos_p)
        target_y = tan_y + RADIAL_WEIGHT * radial_pull * (-sin_p)
        target_h = np.arctan2(target_y, target_x)
        diff = (target_h - self._dots_heading + np.pi) % (2 * np.pi) - np.pi

        # Steering strength driven directly by dot_orbit_lock.
        # Bumped from 9 → 14 so convergence is tight enough that
        # particles visibly lock onto rings within the locked phase
        # (was leaving stragglers off-ring at 70% of respawn).
        STEER_K = 14.0
        steer_strength = dot_orbit_lock * STEER_K
        # Wander strength = inverse of orbit_lock.
        WANDER_K = 4.5
        wander_strength = (1.0 - dot_orbit_lock) * WANDER_K
        seeds = self._dots_seeds
        wander = (np.sin(beat * 0.7 + seeds) +
                  0.6 * np.sin(beat * 1.6 + seeds * 1.7))

        self._dots_heading = (
            self._dots_heading
            + diff * steer_strength * dt_seconds
            + wander * wander_strength * dt_seconds
        ).astype(np.float32)

        cos_h = np.cos(self._dots_heading)
        sin_h = np.sin(self._dots_heading)
        self._dots_xy[:, 0] += cos_h * speed * dt_seconds
        self._dots_xy[:, 1] += sin_h * speed * dt_seconds

        # Soft boundary — large enough that particles at the END of
        # a dissolve can FLY OFF SCREEN entirely (not just bounce
        # against the visible edge). Default 80 LED ≈ 3.6× the half
        # of a 44-grid; particles travel beyond this only over many
        # seconds at peak speed, by which time alpha=0 has cleared
        # them via the pin_dark hook in DissolveAction.
        bound = max(
            float(self.meta.get("dot_bound", 80.0)),
            float(np.max(radii_live)) * 2.0,
        )
        dx = self._dots_xy[:, 0]
        dy = self._dots_xy[:, 1]
        dist = np.sqrt(dx * dx + dy * dy)
        out = dist > bound
        if np.any(out):
            twist = (np.random.rand(int(np.sum(out))).astype(np.float32) - 0.5) * 0.5
            self._dots_heading[out] = np.arctan2(-dy[out], -dx[out]) + twist
            scale = (bound - 0.05) / dist[out]
            self._dots_xy[out, 0] = dx[out] * scale
            self._dots_xy[out, 1] = dy[out] * scale

        # Record into ring buffer.
        self._dots_trail_head = (self._dots_trail_head + 1) % (self._MAX_TRAIL + 1)
        self._dots_trail[:, self._dots_trail_head, :] = self._dots_xy
        self._dots_last_radius = master_r

    # ── Dot-cloud renderer (used by dissolve / respawn) ─────────────
    def _render_dots(
        self, *, n_dots, radius, theta_off, skew, dissolve_amount, sigma,
        time_s, trail_steps, trail_dt, dx_base, dy_base,
        cx_ball, cy_ball, scale_x, scale_y, seed,
        drift_radius=None, ring_filter=None,
    ):
        """Render particles using the stateful simulation in
        self._dots_xy / self._dots_trail. When `ring_filter` is set,
        only particles whose `_dots_ring == ring_filter` are rendered
        — used by the render loop to color particles per-ring (each
        ring's particles inherit that ring's color)."""
        if np is None or self._dots_xy is None:
            return np.zeros_like(dx_base)
        # Per-ring filter: pick only particles assigned to ring_filter.
        if ring_filter is not None and self._dots_ring is not None:
            mask = self._dots_ring == ring_filter
            if not np.any(mask):
                return np.zeros_like(dx_base)
            dots_xy = self._dots_xy[mask]
            dots_trail = self._dots_trail[mask]
        else:
            dots_xy = self._dots_xy
            dots_trail = self._dots_trail
        n = dots_xy.shape[0]
        trail_steps = max(0, min(self._MAX_TRAIL, trail_steps))
        head_sigma = max(0.7, min(1.2, sigma * 0.7))
        head_intensity = 1.4

        # Build per-sample positions from the trail buffer. Newest is
        # at trail_head, older indices wrap backward. We sample every
        # other slot if trail_steps < MAX_TRAIL/2 so the tail spans a
        # longer time-window without rendering every slot.
        K = 1 + trail_steps
        all_px = np.empty((K, n), dtype=np.float32)
        all_py = np.empty((K, n), dtype=np.float32)
        per_step_sigma2 = np.empty(K, dtype=np.float32)
        per_step_alpha = np.empty(K, dtype=np.float32)

        head_idx = self._dots_trail_head
        ring = dots_trail   # (n, MAX_TRAIL+1, 2)
        # Spread the tail samples across the available buffer length
        # (older samples → further behind). Stride > 1 stretches the
        # tail across more frames; stride 1 keeps it tight.
        stride = max(1, self._MAX_TRAIL // max(1, trail_steps))

        # Head from current xy.
        all_px[0] = dots_xy[:, 0]
        all_py[0] = dots_xy[:, 1]
        per_step_sigma2[0] = 2.0 * head_sigma * head_sigma
        per_step_alpha[0] = head_intensity

        for k in range(1, K):
            idx = (head_idx - k * stride) % (self._MAX_TRAIL + 1)
            all_px[k] = ring[:, idx, 0]
            all_py[k] = ring[:, idx, 1]
            taper = 1.0 - k / float(trail_steps + 1)
            tail_sigma = head_sigma * (0.45 + 0.45 * taper)
            tail_alpha = taper ** 1.6
            per_step_sigma2[k] = 2.0 * tail_sigma * tail_sigma
            per_step_alpha[k] = tail_alpha

        all_px_w = (all_px * scale_x + cx_ball).reshape(-1)
        all_py_w = (all_py * scale_y + cy_ball).reshape(-1)
        sigma2_per_blob = np.repeat(per_step_sigma2, n)
        alpha_per_blob = np.repeat(per_step_alpha, n)
        dx = dx_base[np.newaxis, :] - all_px_w[:, np.newaxis]
        dy = dy_base[np.newaxis, :] - all_py_w[:, np.newaxis]
        d2 = dx * dx + dy * dy
        blobs = np.exp(-d2 / sigma2_per_blob[:, np.newaxis])
        dot_glow = (blobs * alpha_per_blob[:, np.newaxis]).sum(axis=0).astype(np.float32)
        return dot_glow

    # Legacy functional dot renderer — kept for unit tests that
    # exercise the old motion model. Not called from render anymore.
    def _render_dots_legacy(
        self, *, n_dots, radius, theta_off, skew, dissolve_amount, sigma,
        time_s, trail_steps, trail_dt, dx_base, dy_base,
        cx_ball, cy_ball, scale_x, scale_y, seed,
        drift_radius=None,
    ):
        """Render `n_dots` spermatozoa-like particles: each has a small
        round head + a tapering tail trailing behind its motion path.

        Motion model — orbital ↔ brownian blend driven by dissolve_amount:
          * dissolve_amount = 0 (fully on ring): particles march along
            the ring at a steady orbital rate; tails sweep along the
            curve. Brownian offset is zero, so no chaos.
          * dissolve_amount = 1 (fully dispersed): orbital motion stops,
            brownian noise (multi-freq sin/cos per particle) drives the
            head in seemingly random directions.
          * In between: smooth crossfade — orbital fades out as brownian
            fades in, so during respawn you see particles gradually
            "align" with the orbit and lock onto the ring.

        Tail rendering — past-position samples at fixed `trail_dt`
        intervals. The tail tapers in both size (σ shrinks toward the
        tip) AND alpha (each step dims), giving a comet-like feel.
        """
        n = n_dots
        thetas = np.arange(n, dtype=np.float32) * (2.0 * np.pi / n)
        seed_off = float(seed) * 1.7
        # Drift amplitude — bigger ring → wider dispersal range. When the
        # caller passes `drift_radius` (set by DissolveAction at trigger
        # time and read from state["dissolve_radius_lock"]), use that
        # instead of the live ring radius so a Contract/Expand fired
        # mid-dissolve doesn't make particles snap inward/outward.
        eff_radius = drift_radius if drift_radius is not None else radius
        drift_max = 1.6 * eff_radius * dissolve_amount
        # Global tempo for brownian + orbital motion. Lower = slower
        # swimming. Phases / cycle durations are independent (those are
        # set by the DissolveAction / RespawnAction modulator timings).
        motion_speed = float(self.meta.get("dot_motion_speed", 0.25))
        # Orbital rotation rate (rad/s). FAST at low dissolve_amount
        # (particles whip around the ring like comets) → STOPS as
        # dispersal grows. Quadratic falloff so the fast-spin phase
        # lingers visually before settling into pure brownian motion.
        # Tunable via `dot_orbit_speed` in synth meta (default 4.0).
        orbit_speed_max = float(self.meta.get("dot_orbit_speed", 4.0))
        orbit_speed = orbit_speed_max * (1.0 - dissolve_amount) ** 1.5
        # Ring shape function (oval via 2-fold skew).
        def _ring_xy(theta_at_particle):
            r = radius * (1.0 + skew * np.cos(2.0 * (theta_at_particle - theta_off)))
            return (r * np.cos(theta_at_particle + theta_off),
                    r * np.sin(theta_at_particle + theta_off))

        def _positions(t):
            """Particle positions at absolute time `t`. Vectorized over n."""
            # Orbital component — angle marches forward over time when
            # converged. Multiplied by (1 - dissolve_amount) means it
            # halts as dissolve takes over.
            theta_now = thetas + t * orbit_speed
            seat_x, seat_y = _ring_xy(theta_now)
            # Brownian component — multi-frequency sin/cos with unique
            # phase per particle. Two frequencies layered for organic
            # variation; the offsets between particles guarantee no two
            # heads drift in lockstep.
            t_eff = t * motion_speed
            phi_x = (t_eff * 0.7 + thetas * 2.1 + seed_off,
                     t_eff * 1.3 + thetas * 5.5 + seed_off + 1.7)
            phi_y = (t_eff * 0.5 + thetas * 3.3 + seed_off + 1.5,
                     t_eff * 1.1 + thetas * 4.7 + seed_off + 2.3)
            nx = (np.sin(phi_x[0]) + 0.6 * np.sin(phi_x[1])).astype(np.float32)
            ny = (np.cos(phi_y[0]) + 0.6 * np.cos(phi_y[1])).astype(np.float32)
            ox = drift_max * nx
            oy = drift_max * ny
            return seat_x + ox, seat_y + oy

        # Batch ALL positions (head + tail samples × n_dots) into a
        # single broadcasted exp() instead of one call per tail step.
        # On the Pi 4, separate calls were the bottleneck — the
        # per-call numpy setup + memory alloc dominated the actual
        # exp() math. With (n_dots * (1 + trail_steps)) blobs in a
        # single broadcast, we hit one allocation and one exp.
        #
        # Sigma + alpha vary per-sample (head sigma > tail sigma; head
        # alpha = 1.4 > tip alpha ≈ 0). We pre-build a length-K array
        # of per-sample intensity and per-sample sigma², broadcast it
        # against the (K, grid.total) distance grid, and sum.
        head_sigma = max(0.7, min(1.2, sigma * 0.7))
        head_intensity = 1.4

        # Tail SPACING scales gently with dissolve_amount — the tail
        # is VISIBLE from the start (30% spacing) so the spinning ring
        # of comets reads even before particles disperse. Grows to
        # full spacing as dispersal completes for the floaty
        # brownian-cloud feel.
        effective_dt = trail_dt * (0.3 + 0.7 * dissolve_amount)

        # Build per-sample (px, py, sigma, intensity) arrays. Layout:
        # K rows; each row holds (n_dots × 1) head/tail positions for
        # that sample step. We flatten to (K × n_dots) at the end.
        K = 1 + trail_steps
        all_px = np.empty((K, n), dtype=np.float32)
        all_py = np.empty((K, n), dtype=np.float32)
        per_step_sigma2 = np.empty(K, dtype=np.float32)
        per_step_alpha = np.empty(K, dtype=np.float32)

        # Head (k=0): full sigma + intensity 1.4.
        head_x, head_y = _positions(time_s)
        all_px[0] = head_x; all_py[0] = head_y
        per_step_sigma2[0] = 2.0 * head_sigma * head_sigma
        per_step_alpha[0] = head_intensity

        # Tail samples (k=1..trail_steps).
        for k in range(1, K):
            t_back = time_s - k * effective_dt
            taper = 1.0 - k / float(trail_steps + 1)
            tail_sigma = head_sigma * (0.45 + 0.45 * taper)
            tail_alpha = taper ** 1.6
            bx, by = _positions(t_back)
            all_px[k] = bx; all_py[k] = by
            per_step_sigma2[k] = 2.0 * tail_sigma * tail_sigma
            per_step_alpha[k] = tail_alpha

        # Flatten K × n → M positions. Build matching per-blob
        # intensity + sigma2 vectors so the exp() math can vectorize.
        all_px_w = (all_px * scale_x + cx_ball).reshape(-1)   # (M,)
        all_py_w = (all_py * scale_y + cy_ball).reshape(-1)
        # Per-blob sigma2 + intensity (broadcast K → M=K×n).
        sigma2_per_blob = np.repeat(per_step_sigma2, n)           # (M,)
        alpha_per_blob = np.repeat(per_step_alpha, n)             # (M,)

        # Single broadcast: (M, grid.total) distances, exp, then sum
        # weighted by alpha along the M axis.
        dx = dx_base[np.newaxis, :] - all_px_w[:, np.newaxis]   # (M, total)
        dy = dy_base[np.newaxis, :] - all_py_w[:, np.newaxis]
        d2 = dx * dx + dy * dy
        # Per-row sigma2 broadcast.
        blobs = np.exp(-d2 / sigma2_per_blob[:, np.newaxis])
        dot_glow = (blobs * alpha_per_blob[:, np.newaxis]).sum(axis=0).astype(np.float32)

        return dot_glow

    # ── Render ──────────────────────────────────────────────────────
    def render(
        self,
        frame: bytearray,
        state: dict,
        time_ms: float,
        params: dict,
        ball_state: dict | None = None,
        beat: float = 0.0,
        *,
        grid: Grid = DEFAULT_GRID,
    ) -> None:
        if np is None:
            return
        dist_base, angle_base, dx_base, dy_base = _geometry_for(grid)

        palettes = params.get("palettes") or []
        if not palettes:
            for i in range(len(frame)):
                frame[i] = 0
            return

        idx = int(state.get("palette_idx", 0)) % len(palettes)
        tgt = int(state.get("palette_target_idx", idx)) % len(palettes)
        blend = float(state.get("palette_blend", 0.0))
        pal_a = palettes[idx]
        pal_b = palettes[tgt]

        def _mix(key, default):
            a = np.asarray(pal_a.get(key, default), dtype=np.float32)
            b = np.asarray(pal_b.get(key, default), dtype=np.float32)
            return (1.0 - blend) * a + blend * b

        # Build an 8-slot palette swatch and let each oval pick by index
        # via state[oval_color_i]. Slots 0..7 map to rim_color, inner_color,
        # outer_color, trail_color, color4..color7 in the palette dict.
        _SLOTS = ["rim_color", "inner_color", "outer_color", "trail_color",
                  "color4", "color5", "color6", "color7"]
        _DEFAULTS_C = [[120, 80, 255], [40, 220, 220], [200, 40, 180],
                       [80, 50, 200], [255, 180, 100], [180, 255, 160],
                       [255, 60, 60], [255, 255, 255]]
        swatch = [_mix(_SLOTS[k], _DEFAULTS_C[k]) for k in range(8)]
        def _oval_color(i):
            idx = int(state.get(f"oval_color_{i}", i)) & 7
            return swatch[idx]

        # Ring geometry.
        radius = float(state.get("radius", self.meta.get("radius_default", 8.0)))
        radius = max(0.0, radius)
        ref_radius = float(self.meta.get("radius_default", 8.0)) or 8.0

        # Per-oval blur widths — passed in via meta.
        blur = [
            float(self.meta.get("oval_blur_0", 1.8)),
            float(self.meta.get("oval_blur_1", 2.5)),
            float(self.meta.get("oval_blur_2", 1.2)),
        ]
        # Sub-linear blur scaling with radius — big rings don't become fuzz balls.
        size_scale = max(0.1, radius / ref_radius) ** 0.5
        blur_eff = [b * size_scale for b in blur]

        # Pulse-driven brightness already lives in `state["alpha"]` because
        # the Pulse event modulates alpha additively. No separate pulse list.

        # Ball overlay — translate center, squash via per-axis scale.
        bs = ball_state or {}
        cx = float(bs.get("cx", 0.0))
        cy = float(bs.get("cy", 0.0))
        sx_val = float(bs.get("sx", 0.0))
        sy_val = float(bs.get("sy", 0.0))
        # ellipse axis scales (avoid zero/negative).
        scale_x = max(0.1, 1.0 + sx_val)
        scale_y = max(0.1, 1.0 + sy_val)

        # Shifted coords: relative distance/angle from the ball-translated
        # center, with the ellipse warp applied.
        dx = (dx_base - cx) / scale_x
        dy = (dy_base - cy) / scale_y
        dist = np.sqrt(dx * dx + dy * dy)
        angles = np.arctan2(dy, dx)

        # Dissolve amount: 0 = solid rings; 1 = fully dispersed dot cloud.
        # Renderer crossfades between the ring path and the dot-cloud path.
        dissolve_amount = float(state.get("dissolve_amount", 0.0))
        dissolve_amount = max(0.0, min(1.0, dissolve_amount))
        # Per-cycle "lock" for dot-cloud dispersal radius — set by
        # DissolveAction when it fires so a subsequent Contract/Expand
        # doesn't change drift_max mid-cycle and snap particles.
        # 0/missing means "use the live oval radius".
        dissolve_radius_lock = float(state.get("dissolve_radius_lock", 0.0))
        # Perf budget — dot rendering is the heaviest path. Defaults
        # tuned for ~30 fps on Pi 4 while keeping the spermatozoa look
        # readable. Trail length ≈ trail_steps × trail_dt × particle_speed.
        n_dots = int(self.meta.get("dot_count", 12))
        # Comet-tail length. Each blob is a numpy.exp() over the grid.
        # As of iter 31 only the TOP oval renders dots (i==1) so the
        # blob count is n_dots × (1 + trail_steps), not multiplied by
        # 3 ovals. Defaults: 12 × 15 = 180 blobs/frame ≈ 30 fps on Pi 4.
        # User can crank trail_steps via the Tail Length slider.
        trail_steps = int(self.meta.get("trail_steps", 14))
        trail_dt = float(self.meta.get("trail_dt", 0.10))
        t_s = time_ms * 0.001

        # Build the three ovals back-to-front. Index meaning:
        #   0 = outer (back)
        #   2 = inner (middle layer)
        #   1 = middle (top — drawn last)
        # `gap_coefficient` scales the per-oval radius offset, so 0 puts
        # all three at the same radius (no gap) and 1+ spreads them out.
        rgb = np.zeros((grid.total, 3), dtype=np.float32)
        gap_coef = float(self.meta.get("gap_coefficient", 1.0))
        for i in (0, 2, 1):
            if not bool(state.get(f"oval_enabled_{i}", True)):
                continue
            skew = float(state.get(f"oval_skew_{i}", 0.15))
            phase = float(state.get(f"oval_phase_{i}", 0.0))
            rot = float(state.get(f"oval_rotation_{i}", 0.0))
            theta = phase + rot
            sigma = blur_eff[i]
            if sigma <= 0:
                continue
            # Per-oval radius via offset × gap coefficient, then a
            # per-oval SCALE multiplier (oval_radius_scale_i, default
            # 1.0) so individual rings can be sized independently
            # without changing the master radius — e.g. inner ring at
            # half scale gives a tighter nested look.
            offset = float(state.get(f"oval_radius_offset_{i}", 0.0))
            scale = float(state.get(f"oval_radius_scale_{i}", 1.0))
            radius_i = max(0.0, (radius + offset * gap_coef) * scale)

            # ── Ring contribution ─────────────────────────────────
            # Rings are visible ONLY in a NARROW window near
            # orbit_lock=1. Smoothstep from 0.93 → 0.998 = ~7% band
            # of orbit_lock values where the ring fades in/out.
            # Combined with the dissolve's fast orbit_lock drop (1 →
            # 0.40 over 15% of total), this makes the rings snap OUT
            # within ~1-2% of total duration once the diverge phase
            # begins — i.e. they're "gone" almost immediately when
            # particles start veering off. Same width applies on the
            # way back during respawn — rings only materialize at
            # the very end after particles have locked.
            dot_orbit_lock = float(state.get("dot_orbit_lock", 1.0))
            dot_orbit_lock = max(0.0, min(1.0, dot_orbit_lock))
            _lock_t = (dot_orbit_lock - 0.93) / 0.068
            if _lock_t <= 0.0:
                ring_weight = 0.0
            elif _lock_t >= 1.0:
                ring_weight = 1.0
            else:
                ring_weight = _lock_t * _lock_t * (3.0 - 2.0 * _lock_t)
            glow = np.zeros(grid.total, dtype=np.float32)
            if ring_weight > 0.001:
                # 2-fold (cos(2x)) gives a pure oval; theta orients it.
                r_oval = radius_i * (1.0 + skew * np.cos(2.0 * (angles - theta)))
                # Voice-shimmer perturbation — multi-frequency radial
                # wobble that makes the ring look like it's "vibrating"
                # along its circumference. Driven by:
                #   shimmer_amount  — ramped by the Shimmer event
                #                     (sustain modulator on note_on/off)
                #   shimmer_speed_mult — set by ShimmerAction based on
                #                     note duration so short notes get
                #                     fast vibrato, long notes slow.
                #   meta.shimmer_intensity — UI knob, base amplitude.
                shimmer_amount = float(state.get("shimmer_amount", 0.0))
                if shimmer_amount > 0.001:
                    speed_mult = float(state.get("shimmer_speed_mult", 1.0))
                    speed_mult = max(0.1, min(6.0, speed_mult))
                    t_shim = time_ms * 0.001 * speed_mult
                    seed_phase = i * 1.3
                    wobble = (
                        0.55 * np.sin(angles * 11 + t_shim * 23.0 + seed_phase) +
                        0.30 * np.sin(angles * 17 - t_shim * 31.0 + seed_phase * 2.1) +
                        0.20 * np.sin(angles * 5  + t_shim * 47.0 + seed_phase * 0.7)
                    )
                    base_intensity = float(self.meta.get("shimmer_intensity", 0.18))
                    base_intensity = max(0.0, min(1.0, base_intensity))
                    amp = shimmer_amount * base_intensity * max(0.5, radius_i)
                    r_oval = r_oval + wobble * amp
                ring_glow = np.exp(-((dist - r_oval) ** 2) / (2.0 * sigma * sigma))
                side = state.get(f"oval_side_{i}", "both")
                if side == "inside":
                    ring_glow = ring_glow * (dist < r_oval)
                elif side == "outside":
                    ring_glow = ring_glow * (dist > r_oval)
                # Dashed mask — soft Gaussian falloff at the dash edges
                # so the blur applies in the angular direction too. Think
                # of it as "dash first (with the dash itself being a
                # blurred rectangle in arc-length space), then composite".
                # arc-length sigma matches the radial sigma so the dash
                # ends feather at the same softness as the ring's
                # inner/outer edges.
                segments = int(state.get(f"oval_segments_{i}", 0))
                if segments > 0:
                    gap = float(state.get(f"oval_gap_{i}", 0.4))
                    seg = 2.0 * np.pi / segments
                    # Distance from the center of the nearest dash, in
                    # radians, in [0, seg/2].
                    arc_local = ((angles - theta + seg / 2.0) % seg) - seg / 2.0
                    arc_dist = np.abs(arc_local)
                    dash_half = (1.0 - gap) * seg / 2.0
                    # Excess past the dash half-width, converted to
                    # LED-arc-length so the Gaussian uses the same σ as
                    # the radial blur.
                    excess = np.maximum(0.0, arc_dist - dash_half)
                    arc_offset = excess * max(0.1, radius_i)
                    dash_mask = np.exp(-(arc_offset * arc_offset) / (2.0 * sigma * sigma))
                    ring_glow = ring_glow * dash_mask
                glow = ring_glow * ring_weight

            # ── Dot-cloud contribution (when dissolving) ──
            # Each oval renders ONLY its own assigned particles via
            # ring_filter=i so they inherit that oval's color. The
            # particle simulation is shared (one state, one tick) but
            # rendering splits by ring assignment. Per-ring blob count
            # is roughly n_dots/3, so total rendering work is the
            # same as the previous "render once, color with middle"
            # approach — just split across 3 oval iterations.
            base_alpha_now = float(state.get("alpha", 1.0))
            if dissolve_amount > 0.001 and base_alpha_now > 0.001:
                drift_r = (dissolve_radius_lock
                           if dissolve_radius_lock > 0.0 else None)
                dot_glow = self._render_dots(
                    n_dots=n_dots, radius=radius_i, theta_off=theta,
                    skew=skew, dissolve_amount=dissolve_amount,
                    sigma=sigma, time_s=t_s,
                    trail_steps=trail_steps, trail_dt=trail_dt,
                    dx_base=dx_base, dy_base=dy_base,
                    cx_ball=cx, cy_ball=cy, scale_x=scale_x, scale_y=scale_y,
                    drift_radius=drift_r,
                    seed=i,
                    ring_filter=i,    # particles for THIS ring only
                )
                # dot_visibility multiplier — set to 1 normally, ramped
                # to 0 at the end of respawn so particles smoothly
                # fade out as the ring rendering takes over.
                dot_vis = float(state.get("dot_visibility", 1.0))
                dot_vis = max(0.0, min(1.0, dot_vis))
                glow = glow + dot_glow * dot_vis

            glow_a = np.clip(glow, 0.0, 1.0)
            color_layer = np.outer(glow_a, _oval_color(i))
            rgb = color_layer + rgb * (1.0 - glow_a)[:, np.newaxis]

        # Shimmer — gentle hue/brightness waves over lit pixels.
        shimmer_speed = time_ms * 0.0005
        shimmer = (
            0.08 * np.sin(angle_base * 3 + shimmer_speed) +
            0.05 * np.sin(angle_base * 5 - shimmer_speed * 1.3) +
            0.04 * np.sin(angle_base * 7 + shimmer_speed * 0.7)
        )
        # Mask shimmer to lit pixels — use the channel-sum as a rough alpha.
        total_alpha = np.minimum(rgb.sum(axis=1) / 255.0, 1.0)
        rgb = rgb * (1.0 + shimmer * total_alpha)[:, np.newaxis]

        # Master brightness + alpha multiplier (driven by Pulse, Blow Out,
        # Regrow modulators on the "alpha" state key).
        base_alpha = max(0.0, float(state.get("alpha", 1.0)))
        brightness = float(self.meta.get("brightness", 1.0))
        rgb = rgb * (base_alpha * brightness)

        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        frame[: grid.frame_bytes] = rgb.tobytes()
