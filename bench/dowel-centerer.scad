// HERE — Dowel Centerer
// 3D-printable tool for transferring 1″ dowel hole locations from the
// legs to the bench slab.
//
// Usage:
//   1. Drill a 1″ (25.4 mm) hole in each leg for the dowel.
//   2. Drop a centerer into each hole, BODY first. The cap rests flush
//      on the leg's top face; the pin points up.
//   3. Position the slab on top of the legs and press down firmly.
//      Each pin stamps a small dimple at the exact dowel location on
//      the slab's underside.
//   4. Drill a matching 1″ hole at each dimple.
//   5. Glue 1″ dowels into matching holes; clamp leg + slab together.
//
// Print orientation: body on the build plate, cap + pin pointing up.
// The cap's underside has a small 5 mm horizontal overhang (the lip
// around the body), which the Bambu Lab Mini bridges cleanly at this
// scale — no supports needed. Slight bridge roughness on that face is
// fine; in use it presses against the leg's top.
//
// Slicer settings (Bambu Lab Mini):
//   - PLA or PETG
//   - 0.2 mm layer height
//   - 30–50% infill (irrelevant for a part this small)
//   - No supports
//
// Tip: a 1″ FDM print typically comes out 0.1–0.3 mm oversized on
// outer dimensions. If the body won't drop into the leg's hole, sand
// it lightly or set `body_tol = 0.3` and reprint.

// ─── parameters ─────────────────────────────────────────────
inch = 25.4;

body_d   = inch;   // 1″ — matches the dowel hole
body_tol = 0.0;    // increase to undersize the body (shrinks both sides)
body_h   = inch;   // 1″ deep into the leg
cap_d    = 35;     // ≈ 1″ + 1 cm
cap_h    = 2;
pin_d    = 4;
pin_h    = 1;

$fn = 96;

// ─── geometry ───────────────────────────────────────────────
// Stack from bottom (deepest in the leg's hole) to top (marks slab):
//   body  →  cap  →  pin
// The cap and pin are on the same side, opposite the body.
union() {
    // body — fits the leg's dowel hole
    cylinder(d=body_d - body_tol, h=body_h);

    // cap — sits on the leg's top face
    translate([0, 0, body_h])
        cylinder(d=cap_d, h=cap_h);

    // pin — marks the slab (on the cap, opposite the body)
    translate([0, 0, body_h + cap_h])
        cylinder(d=pin_d, h=pin_h);
}
