"""Squishy-ball physics — position + velocity + a 2D squash tensor.

The Scene's visual is rendered with the ball's center as a translation
offset and its squash tensor as an ellipse stretch on the rings. This
module is pure dynamics — no rendering — so it's trivial to unit-test.

Model:
  • position (cx, cy) and velocity (vx, vy) in LED units from grid center.
  • Squash tensor (sx, sy) — additive deviation from 1.0 on each axis.
    sx = +0.3 → x-axis stretched (oval wider); sx = -0.3 → x-axis squashed.
    Renderer uses scale_x = 1 + sx, scale_y = 1 + sy.
  • Squash relaxes back to (0, 0) as a critically-damped second-order
    oscillator — no overshoot, smooth fade.
  • Wall collisions invert the perpendicular velocity (× bounce) and
    inject a squash kick into the squash-tensor derivatives:
      hit a vertical wall (cx hits ±bound_x):
        sx_dot -= kick      (compresses x — ball flattens against the wall)
        sy_dot += kick      (bulges y — perpendicular axis swells)
  • Optional center-pull spring (Float Center event) pulls (cx, cy) back
    to the origin; auto-anchors once the ball is close + slow for a few
    consecutive frames so it doesn't perpetually buzz around zero.

Equations confirmed against standard 2D verlet/spring-mass physics
references; chosen for stability with 30fps step.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# Auto-anchor — when the ball is within this many LED units of center
# AND moving slower than this many LED/s for this many consecutive
# frames, it snaps to exact (0, 0, 0, 0). Always-on so any motion that
# trails off near the origin (e.g. Float Center damping-asymptote) ends
# in a clean dead-stop instead of drifting forever near zero.
_ANCHOR_DISTANCE = 0.6
_ANCHOR_VELOCITY = 0.4
_ANCHOR_FRAMES = 3


@dataclass
class PhysicsParams:
    """User-tunable physics knobs (exposed in the UI's Physics tab)."""
    speed: float = 25.0             # impulse magnitude per Float event (LED/s)
    radial_offset: float = 0.12     # rad of random jitter on impulse direction
    squishiness: float = 0.35       # peak squash on a max-velocity collision
    damping: float = 0.3            # viscous drag (1/s) — lower = ball
                                    # coasts longer after a push event.
    bounce: float = 0.75            # wall restitution (0..1)
    center_pull: float = 3.0        # center-spring strength (1/s²)
    tau_squash: float = 0.25        # squash relaxation time constant (s)
    max_velocity: float = 40.0      # |v| clamp (LED/s)
    angular_friction: float = 0.6   # global rotation decay rate (1/s) —
                                    # higher = faster spin-down when no
                                    # rotate event is held; 0 = no decay.
    squash_damping: float = 0.35    # ζ for the squash spring. < 1 →
                                    # under-damped → wobbles after impact.
                                    # 0.3-0.5 gives a juicy "jelly" feel.

    @classmethod
    def from_dict(cls, data: dict | None) -> "PhysicsParams":
        d = data or {}
        return cls(**{
            k: float(d.get(k, getattr(cls, k, getattr(cls(), k))))
            for k in (
                "speed", "radial_offset", "squishiness", "damping",
                "bounce", "center_pull", "tau_squash", "max_velocity",
                "angular_friction", "squash_damping",
            )
        })

    def to_dict(self) -> dict:
        return {
            "speed": self.speed,
            "radial_offset": self.radial_offset,
            "squishiness": self.squishiness,
            "damping": self.damping,
            "bounce": self.bounce,
            "center_pull": self.center_pull,
            "tau_squash": self.tau_squash,
            "max_velocity": self.max_velocity,
            "angular_friction": self.angular_friction,
            "squash_damping": self.squash_damping,
        }


@dataclass
class BallPhysics:
    """Squishy-ball state — owns dynamics, knows nothing about rendering."""
    params: PhysicsParams = field(default_factory=PhysicsParams)
    cx: float = 0.0
    cy: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    sx: float = 0.0
    sy: float = 0.0
    sx_dot: float = 0.0
    sy_dot: float = 0.0
    center_lock: bool = False
    _settled_frames: int = 0
    # Deterministic-ish rng for the impulse jitter. The scene seeds this.
    _rng_state: float = 0.123456

    def _rng_next(self) -> float:
        # Tiny LCG — deterministic given seed, good enough for tiny jitter.
        self._rng_state = (self._rng_state * 1103515245 + 12345) % (2 ** 31)
        return (self._rng_state / 2147483648.0) * 2.0 - 1.0  # in (-1, 1)

    # ── External controls ────────────────────────────────────────────
    def set_center_lock(self, lock: bool) -> None:
        self.center_lock = bool(lock)
        if not lock:
            self._settled_frames = 0

    def impulse(self, dx: float, dy: float, *, magnitude: float | None = None) -> None:
        """Apply a Float impulse: direction (dx,dy) need not be normalized.
        Magnitude defaults to `params.speed`. A small random jitter is added
        so off-axis bounces don't all land symmetrically.
        """
        mag = float(self.params.speed if magnitude is None else magnitude)
        n = math.hypot(dx, dy)
        if n == 0:
            return
        # Normalize direction.
        ux, uy = dx / n, dy / n
        # Jitter by a small rotation (in rad).
        jitter = self._rng_next() * self.params.radial_offset
        c, s = math.cos(jitter), math.sin(jitter)
        ux, uy = ux * c - uy * s, ux * s + uy * c
        self.vx += ux * mag
        self.vy += uy * mag
        # The ball is no longer settled.
        self._settled_frames = 0

    def reset(self) -> None:
        self.cx = self.cy = 0.0
        self.vx = self.vy = 0.0
        self.sx = self.sy = 0.0
        self.sx_dot = self.sy_dot = 0.0
        self._settled_frames = 0

    # ── Per-frame integration ────────────────────────────────────────
    def tick(self, dt: float, bound_x: float, bound_y: float) -> None:
        """Advance one frame. `bound_x` / `bound_y` are the maximum |cx| /
        |cy| the ball center may occupy before hitting a wall."""
        if dt <= 0:
            return
        p = self.params

        # 1. Forces → acceleration.
        ax = -p.damping * self.vx
        ay = -p.damping * self.vy
        if self.center_lock:
            ax += -p.center_pull * self.cx
            ay += -p.center_pull * self.cy

        # 2. Velocity integration.
        self.vx += ax * dt
        self.vy += ay * dt

        # Clamp |v|.
        v_mag = math.hypot(self.vx, self.vy)
        if v_mag > p.max_velocity > 0:
            scale = p.max_velocity / v_mag
            self.vx *= scale
            self.vy *= scale

        # 3. Position integration.
        self.cx += self.vx * dt
        self.cy += self.vy * dt

        # 4. Wall collisions (axis-aligned). Physically-honest squash: the
        # ball's KE at the moment of contact goes into the squash spring
        # as initial velocity (kicks the s_dot only). The spring then
        # integrates that into peak compression and oscillates back —
        # so compression grows gradually during contact, not instantly,
        # and the wobble feel comes naturally from the under-damped spring.
        max_v = p.max_velocity if p.max_velocity > 0 else 1.0
        # Tuned multipliers: enough kick that peak compression is
        # visible (~30-50% scale change at high impact speeds).
        SQ_KICK = 6.0
        SQ_BULGE = 4.0
        if bound_x > 0 and abs(self.cx) > bound_x:
            pre_v = self.vx
            self.cx = math.copysign(bound_x, self.cx)
            self.vx = -p.bounce * pre_v
            impact = p.squishiness * (abs(pre_v) / max_v)
            self.sx_dot -= impact * SQ_KICK    # compress along impact axis
            self.sy_dot += impact * SQ_BULGE   # bulge perpendicular
        if bound_y > 0 and abs(self.cy) > bound_y:
            pre_v = self.vy
            self.cy = math.copysign(bound_y, self.cy)
            self.vy = -p.bounce * pre_v
            impact = p.squishiness * (abs(pre_v) / max_v)
            self.sy_dot -= impact * SQ_KICK
            self.sx_dot += impact * SQ_BULGE

        # 5. Squash spring — under-damped second-order oscillator.
        #    s_ddot = -ω² s - 2ζω s_dot. ζ < 1 → wobble + overshoot
        #    (the "jelly" feel); ζ = 1 critically damped (no wobble).
        if p.tau_squash > 0:
            omega = 1.0 / p.tau_squash
            zeta = max(0.05, float(p.squash_damping))
            sx_ddot = -omega * omega * self.sx - 2.0 * zeta * omega * self.sx_dot
            sy_ddot = -omega * omega * self.sy - 2.0 * zeta * omega * self.sy_dot
            self.sx_dot += sx_ddot * dt
            self.sy_dot += sy_ddot * dt
            self.sx += self.sx_dot * dt
            self.sy += self.sy_dot * dt
        else:
            self.sx = self.sy = self.sx_dot = self.sy_dot = 0.0

        # 6. Auto-anchor — always on. Snaps any tiny residual drift to
        # exact (0, 0). Float-impulse events keep the ball moving fast
        # enough to exit the window quickly so this only kicks in when
        # the ball is genuinely settling near the origin.
        close = abs(self.cx) < _ANCHOR_DISTANCE and abs(self.cy) < _ANCHOR_DISTANCE
        slow = abs(self.vx) < _ANCHOR_VELOCITY and abs(self.vy) < _ANCHOR_VELOCITY
        if close and slow:
            self._settled_frames += 1
            if self._settled_frames >= _ANCHOR_FRAMES:
                self.cx = self.cy = 0.0
                self.vx = self.vy = 0.0
        else:
            self._settled_frames = 0

    # ── Snapshot ─────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        return {
            "cx": self.cx,
            "cy": self.cy,
            "vx": self.vx,
            "vy": self.vy,
            "sx": self.sx,
            "sy": self.sy,
            "center_lock": self.center_lock,
        }
