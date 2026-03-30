# Bench / Electronics Enclosure

The bench is a **plywood box** (4ft long, 30cm wide, 35cm tall) oriented **diagonally (45 degrees)** on the LED platform. It sits on two 4x4 lumber legs (~3.5" actual), giving a total seat height of ~439mm (~17.3").

The box houses 2x LiFePO4 batteries (end-to-end), speakers, ventilation fan, RPi 4, and WLED controller.

## 3D Model

Open `assembly.scad` in OpenSCAD for the full parametric source. Re-render PNGs with `./render.sh`.

### Closed

![[closed_iso.png]]

### Open — isometric

![[open_iso.png]]

### Open — front

![[open_front.png]]

### Open — top view

![[open_top.png]]

### Open — side

![[open_side.png]]

### Open — close-up

![[open_close.png]]

### With Dimensions

![[dims_iso.png]]
![[dims_top.png]]

## Dimensions

| Part | Dimension | mm | imperial |
|------|-----------|----|----------|
| Box length | L | 1219 | 4 ft |
| Box width | W | 300 | ~12 in |
| Box height | H | 350 | ~14 in |
| Plywood thickness | t | 19 | 3/4 in |
| Leg height (4x4 lumber) | | 89 | 3.5 in |
| **Total seat height** | | **439** | **~17.3 in** |
| Interior length | | 1181 | ~46.5 in |
| Interior width | | 262 | ~10.3 in |
| Interior height | | 312 | ~12.3 in |

## Fan Placement

The 120mm fan mounts in the **bottom sheet, directly under the battery**. The battery sits on small plywood risers (~45mm tall), creating an air gap. Air is sucked in through a dust filter below the fan, flows up around the battery (which also benefits from cooling), and pressurizes the enclosure. Playa dust is pushed out through gaps, not pulled in.

## Speakers

- 2x speakers (~5" drivers) mounted **facing down** at each end of the bench
- Sound projects downward and outward from under the bench
- Driven by a small Class D amplifier inside the enclosure

## Bottom Sheet Cutouts

```
┌──────────────────────────────────────────┐
│                                          │
│   ○          ▢▢            ○             │
│  speaker   fan vent(s)   speaker         │
│  ~120mm    under batt    ~120mm          │
│                                          │
└──────────────────────────────────────────┘
```

## Construction Notes

- All joints: wood glue + screws
- Lid: rests on cleats inside the box, removable for access
- Cable pass-throughs: grommeted holes in bottom sheet for LED data + power lines
- Bench surface: sand smooth, possibly add a cushion or non-slip coating
- Consider weatherproofing the exterior (marine varnish or paint)
