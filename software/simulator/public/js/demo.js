// Breathing meditation animation:
// - Expanding/contracting circle rim
// - Violet/magenta outer blur, turquoise inner blur
// - Thin ring with asymmetric glow

const BREATH_CYCLE = 8000;
const MIN_RADIUS = 3;
const MAX_RADIUS = 18;    // wide circle
const RIM_WIDTH = 1.8;    // thin sharp ring
const INNER_BLUR = 4.0;   // turquoise inner glow
const OUTER_BLUR = 1.2;   // magenta outer glow — 70% less than before

export function updateDemo(timeMs, leds) {
  const t = (timeMs % BREATH_CYCLE) / BREATH_CYCLE;
  const breath = (Math.sin(t * Math.PI * 2 - Math.PI / 2) + 1) / 2;

  const radius = MIN_RADIUS + breath * (MAX_RADIUS - MIN_RADIUS);

  // Trail
  const prevT = ((timeMs - 400) % BREATH_CYCLE) / BREATH_CYCLE;
  const prevBreath = (Math.sin(prevT * Math.PI * 2 - Math.PI / 2) + 1) / 2;
  const trailRadius = MIN_RADIUS + prevBreath * (MAX_RADIUS - MIN_RADIUS);

  const cx = (leds.GRID - 1) / 2;

  for (let i = 0; i < leds.TOTAL; i++) {
    const [row, col] = leds.gridPositions[i];

    const dx = col - cx;
    const dy = row - cx;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const distFromRim = dist - radius;
    const distFromTrail = dist - trailRadius;

    // Sharp rim
    const rimGlow = Math.exp(-(distFromRim * distFromRim) / (2 * RIM_WIDTH * RIM_WIDTH));

    // Inner blur (inside the ring, toward center) — turquoise
    const innerDist = Math.max(0, -distFromRim); // positive when inside ring
    const innerGlow = Math.exp(-(innerDist * innerDist) / (2 * INNER_BLUR * INNER_BLUR)) *
                      (distFromRim < 0 ? 1 : 0); // only inside

    // Outer blur (outside the ring, toward edge) — magenta
    const outerDist = Math.max(0, distFromRim); // positive when outside ring
    const outerGlow = Math.exp(-(outerDist * outerDist) / (2 * OUTER_BLUR * OUTER_BLUR)) *
                      (distFromRim > 0 ? 1 : 0); // only outside

    // Trail glow
    const trailGlow = Math.exp(-(distFromTrail * distFromTrail) / (2 * 3.0 * 3.0)) * 0.3;

    // Rim color: blend between inner turquoise and outer magenta
    // Rim itself is a mix (violet-ish)
    // Turquoise: (40, 220, 220)  Magenta: (200, 40, 180)  Rim: (120, 80, 255)

    const rimR = rimGlow * 120;
    const rimG = rimGlow * 80;
    const rimB = rimGlow * 255;

    const innerR = innerGlow * 40;
    const innerG = innerGlow * 220;
    const innerB = innerGlow * 220;

    const outerR = outerGlow * 200;
    const outerG = outerGlow * 40;
    const outerB = outerGlow * 180;

    const trailR = trailGlow * 80;
    const trailG = trailGlow * 50;
    const trailB = trailGlow * 200;

    const r = Math.min(255, rimR + innerR + outerR + trailR);
    const g = Math.min(255, rimG + innerG + outerG + trailG);
    const b = Math.min(255, rimB + innerB + outerB + trailB);

    leds.setLedColor(i, r, g, b);
  }

  // ── Underglow: warm amber-orange ────────────────────────
  if (leds.underglowMesh) {
    const ugTime = timeMs * 0.0002;
    for (let i = 0; i < leds.underglowCount; i++) {
      const wave = Math.sin(ugTime + i * 0.3) * 0.5 + 0.5;
      leds.setUnderglowColor(i, 400, 220 + wave * 80, 50 + wave * 40);
    }
  }

  leds.flush();
}
