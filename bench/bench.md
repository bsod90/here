# Bench + Side Electronics Box

The installation is split into two pieces:

1. **Bench** — a solid plywood **slab (~4″ thick glue-up)** on two short 4×4 legs. Sits on the LED platform, oriented diagonally (default) across the 44×44 LED matrix. No internals.
2. **Electronics box** — a separate plywood enclosure that **stands directly against one edge of the platform** on the desert floor (no feet). Houses the LiFePO4 battery, RPi 4, WLED controller, amp, fan, and 2× speakers that face the seated person on the bench.

## 3D Model

Open `assembly.scad` in OpenSCAD for the full parametric source. Re-render PNGs with `./render.sh`.

### Closed (everything assembled)

![[closed_iso.png]]

### Open — isometric (electronics box lid removed, internals visible)

![[open_iso.png]]

### Open — front

![[open_front.png]]

### Open — top view

![[open_top.png]]

### Open — side

![[open_side.png]]

### Bench close-up

![[bench_close.png]]

### Electronics box close-up

![[elec_close.png]]

### With Dimensions

![[dims_iso.png]]
![[dims_top.png]]

## Bench dimensions

| Part | Dimension | mm | imperial |
|------|-----------|----|----------|
| Slab length | L | 1524 | 5 ft |
| Slab width | W | 305 | 12 in |
| Slab thickness | t | 102 | 4 in |
| Leg cross-section (4×4 lumber) | | 89 | 3.5 in |
| Leg height | | 233 | ~9.2 in |
| Leg inset (from each end) | | 250 | ~9.8 in |
| **Total seat height** | | **335** | **~13.2 in** |

The slab is a **glue-up of 4–5 layers of ¾″ plywood** (or solid hardwood). Each leg spans the full slab width and is anchored to the platform with lag screws driven up from below.

## Electronics box dimensions

| Part | Dimension | mm | imperial |
|------|-----------|----|----------|
| Box length | L | 610 | ~2 ft |
| Box width | W | 305 | 12 in |
| Box height | H | 280 | ~11 in |
| Plywood thickness | t | 19 | 3/4 in |
| Interior length | | 572 | ~22.5 in |
| Interior width | | 267 | ~10.5 in |
| Interior height | | 242 | ~9.5 in |

The box stands on the desert floor with its long face pressed against the platform's edge (no gap, no feet). The face touching the platform is the speaker baffle — both speakers are mounted in this wall, firing toward the person seated on the bench.

## Speakers (electronics box)

- 2× speakers (~5″ drivers) mounted in the **long wall facing the platform/bench**
- Cones face the seated person; chassis extends back into the box
- Driven by a small Class D amplifier inside the enclosure

## Fan placement (electronics box)

The 120mm fan mounts in the bottom sheet directly under the battery. The battery sits on small plywood shelves creating an air gap; the fan pulls air in through a dust filter below and pressurizes the enclosure so playa dust is pushed out through gaps, not pulled in.

## Front face cutouts (electronics box, +Y / platform-facing wall)

```
┌──────────────────────────────────────────┐
│                                          │
│        ⊙                ⊙                │
│      speaker         speaker             │
│      grille          grille              │
│      ~130mm          ~130mm              │
│                                          │
└──────────────────────────────────────────┘
```

Bottom sheet has a fan vent under the battery, no speaker holes.

## Construction notes

- **Slab**: edge-glue + clamp 4–5 layers of ¾″ ply face-to-face; sand smooth; round-over the top edges; finish with marine varnish or oil. Could also be a single solid hardwood slab if available.
- **Legs**: 4×4 dimensional lumber, ~9″ long. Lag screws up through the platform plywood into each leg.
- **Electronics box**: plywood, wood glue + screws on all joints. Lid rests on cleats inside the box; removable for access. With the box pushed against the platform, the speaker face is sheltered from direct dust.
- **Battery layout**: a single 384×254×194 LiFePO4 battery laid flat on its largest face fits inside this shorter box; a second battery would not fit at this length.
- Weatherproof exterior (marine varnish or paint) on both pieces.
