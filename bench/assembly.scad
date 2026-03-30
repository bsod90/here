// HERE — Burning Man 2026 Breathing Meditation Installation
// Full assembly: platform + LED matrix + bench enclosure
//
// Open in OpenSCAD → use Customizer panel (Window > Customizer) to toggle views.
// Render with F6, preview with F5.
// Export PNGs: run ./render.sh from the bench/ directory.

// ═══════════════════════════════════════════════════════════
//  VIEW CONTROLS (toggle in Customizer)
// ═══════════════════════════════════════════════════════════

/* [View] */
lid_open        = true;   // false = closed, true = open with lid beside + internals
two_batteries   = true;   // Show 2-battery configuration
show_platform   = true;
show_leds       = true;
show_bench      = true;
show_dimensions = true;   // Show dimension lines and labels
show_desert     = true;   // Desert ground plane background
cross_section   = false;
for_export      = false;  // true = disable text for clean renders
compare_mode    = false;  // Show 4ft/5ft/6ft variants side by side

// ═══════════════════════════════════════════════════════════
//  DIMENSIONS (mm)
// ═══════════════════════════════════════════════════════════

/* [Platform] */
sheet_l   = 2438;  // 8 ft
sheet_w   = 1219;  // 4 ft
ply       = 19;    // ¾″ plywood

/* [LED Matrix] */
led_sp    = 50;    // 5 cm pitch
led_n     = 44;    // 44 × 44
led_d     = 8;     // pebble dia

/* [Bench Box — exterior] */
bench_l   = 1219;  // 4 ft (48 in)
bench_w   = 300;   // 30 cm
bench_h   = 350;   // 35 cm (fits battery 254mm + risers 45mm + clearance)

/* [Legs — 4×4 lumber on their side] */
leg_dim   = 89;    // 3.5″ actual (4×4 nominal)
leg_len   = 300;   // matches bench width
leg_inset = 250;   // from each end of bench

/* [Battery — ECO-WORTHY LiFePO4] */
batt_l = 384;  // 15.12″
batt_w = 194;  // 7.64″
batt_h = 254;  // 10.00″

/* [Strip / ridge stock — 1″ × ½″ ] */
strip_w  = 25.4;  // 1″
strip_t  = 12.7;  // ½″

/* [Lid ridge] */
ridge_inset = 22; // inset from lid edge (ply + 3mm gap)
ridge_pad   = 5;  // padding from strip to wall

/* [Bottom rails — replace risers] */
rail_spacing = 160;  // distance between rail centers (inside battery width)
shelf_w      = 25.4; // shelf cross-piece width (same strip stock)

/* [Fasteners] */
lag_d    = 10;   // lag screw shaft diameter
lag_len  = 200;  // length into playa below platform
bolt_d   = 10;   // through-bolt diameter
nut_d    = 18;   // nut across-flats
nut_h    = 8;    // nut height

/* [Speakers] */
spk_dia   = 130;  // 5″ driver
spk_depth = 50;

/* [Fan — 120 mm, mounts under battery] */
fan_sz    = 120;
fan_dp    = 25;

/* [Electronics] */
rpi_l = 85;  rpi_w = 56;  rpi_h = 20;
gled_l = 129; gled_w = 50; gled_h = 23;

/* [Power supply / inverter box] */
psu_l = 200;  psu_w = 150;  psu_h = 60;

/* [Speaker holes] */
spk_hole_d  = 10;   // individual hole diameter
spk_hole_sp = 18;   // hole spacing
spk_hole_r  = 50;   // pattern radius

/* [Underglow LED channels] */
chan_w    = 15;   // channel width
chan_d    = 8;    // channel depth
chan_inset = 30;  // inset from bench long edge

// ═══════════════════════════════════════════════════════════
//  COLORS
// ═══════════════════════════════════════════════════════════
c_floor  = [0.55, 0.55, 0.55];
c_osb    = [0.78, 0.65, 0.40];  // OSB board — warm straw-yellow
c_osb2   = [0.72, 0.58, 0.35];  // OSB slight variation (end walls, strips)
c_batt   = [0.15, 0.15, 0.18];
c_spk    = [0.25, 0.25, 0.25];
c_fan    = [0.35, 0.35, 0.40];
c_filt   = [0.92, 0.90, 0.85, 0.6];
c_pcb    = [0.05, 0.45, 0.15];
c_pcb2   = [0.08, 0.08, 0.10];
c_psu    = [0.2, 0.2, 0.22];    // power supply box
c_dim    = [0, 0, 0];           // black dimension text
c_strip  = [0.72, 0.58, 0.35];  // strips/ridges
c_steel  = [0.6, 0.6, 0.65];
c_desert = [0.82, 0.73, 0.58];
c_led_ch = [0.1, 0.8, 0.3, 0.6]; // underglow LED channel

// ═══════════════════════════════════════════════════════════
//  DIMENSION LINES
// ═══════════════════════════════════════════════════════════
module dim_line(from, to, label, offset_dir=[0,0,1], offset_dist=40) {
    mid = (from + to) / 2;
    o = offset_dir * offset_dist;
    p1 = from + o;
    p2 = to + o;
    pm = mid + o;

    color(c_dim) {
        hull() {
            translate(p1) sphere(1, $fn=6);
            translate(p2) sphere(1, $fn=6);
        }
        hull() {
            translate(from + offset_dir*(offset_dist-10)) sphere(1, $fn=6);
            translate(from + offset_dir*(offset_dist+10)) sphere(1, $fn=6);
        }
        hull() {
            translate(to + offset_dir*(offset_dist-10)) sphere(1, $fn=6);
            translate(to + offset_dir*(offset_dist+10)) sphere(1, $fn=6);
        }
        translate(pm + offset_dir*15)
            linear_extrude(1) text(label, size=24,
                halign="center", valign="center");
    }
}

// ═══════════════════════════════════════════════════════════
//  PLATFORM
// ═══════════════════════════════════════════════════════════
module platform() {
    color(c_floor)
    translate([-sheet_l/2, -sheet_l/2, 0])
    union() {
        cube([sheet_l, sheet_w, ply]);
        translate([0, sheet_w, 0]) cube([sheet_l, sheet_w, ply]);
    }
    color(c_floor * 0.7)
    translate([-sheet_l/2, -0.5, 0]) cube([sheet_l, 1, ply + 0.1]);
}

// ═══════════════════════════════════════════════════════════
//  LED GRID
// ═══════════════════════════════════════════════════════════
module led_grid() {
    span = (led_n - 1) * led_sp;
    o    = -span / 2;
    for (x = [0 : led_n-1], y = [0 : led_n-1]) {
        dx = x - (led_n-1)/2;
        dy = y - (led_n-1)/2;
        r  = sqrt(dx*dx + dy*dy) / (led_n/2);
        color([0.1+r*0.4, 0.4+(1-r)*0.5, 0.9, 0.85])
        translate([o + x*led_sp - led_d/2, o + y*led_sp - led_d/2, ply + 1])
        cube([led_d, led_d, led_d/2]);
    }
}

// ═══════════════════════════════════════════════════════════
//  DESERT GROUND PLANE
// ═══════════════════════════════════════════════════════════
module desert_ground() {
    ground_size = sheet_l * 2.5;
    color(c_desert)
    translate([-ground_size/2, -ground_size/2, -2])
        cube([ground_size, ground_size, 2]);
}

// ═══════════════════════════════════════════════════════════
//  OSB TEXTURE — scattered strand pattern on a face
// ═══════════════════════════════════════════════════════════
module osb_strands(w, h, seed=42) {
    // Lightweight visual hint of OSB strand pattern
    n = min(floor(w * h / 3000), 40);  // scale count to surface area, cap at 40
    for (i = [0:n-1]) {
        sx = (sin(i*137.5 + seed*13) + 1) / 2 * (w - 30) + 5;
        sy = (cos(i*97.3 + seed*7) + 1) / 2 * (h - 10) + 2;
        sw = 15 + abs(sin(i*53 + seed)) * 25;
        sh = 2 + abs(cos(i*71 + seed)) * 4;
        rot = sin(i*47 + seed) * 30;
        c_var = 0.65 + abs(sin(i*31 + seed)) * 0.15;
        color([c_var, c_var*0.8, c_var*0.5, 0.3])
        translate([sx, sy, 0])
        rotate([0, 0, rot])
        translate([-sw/2, -sh/2, 0])
            cube([sw, sh, 0.5]);
    }
}

// ═══════════════════════════════════════════════════════════
//  SPEAKER HOLE PATTERN — grid of small holes
// ═══════════════════════════════════════════════════════════
module speaker_holes(center, thickness) {
    // circular grid of small holes
    for (dx = [-3:3], dy = [-3:3]) {
        px = dx * spk_hole_sp;
        py = dy * spk_hole_sp;
        if (sqrt(px*px + py*py) <= spk_hole_r)
            translate([center.x + px, center.y + py, -1])
                cylinder(d=spk_hole_d, h=thickness+2, $fn=12);
    }
}

// ═══════════════════════════════════════════════════════════
//  BENCH BOX — detailed OSB construction
//  (bl = override length, defaults to bench_l)
// ═══════════════════════════════════════════════════════════
module bench_box(bl=0) {
    _bl = bl > 0 ? bl : bench_l;
    iw  = bench_w - 2*ply;
    il  = _bl - 2*ply;
    wall_h = bench_h - 2*ply;

    // battery center X positions
    batt_cx = two_batteries
        ? [-batt_l/2 - 15, batt_l/2 + 15]
        : [0];

    // ── 1. BOTTOM SHEET ──
    color(c_osb)
    difference() {
        translate([-_bl/2, -bench_w/2, 0])
            cube([_bl, bench_w, ply]);

        // speaker hole patterns (grids of small holes)
        for (sx = [-1, 1])
            speaker_holes([sx * (_bl/2 - 120), 0], ply);

        // fan vents — centered under each battery
        for (bx = batt_cx)
            translate([bx, 0, -1])
                cube([fan_sz-10, fan_sz-10, ply+2], center=true);

        // through-bolt holes
        for (sx = [-1, 1])
            translate([sx * (_bl/2 - leg_inset), 0, -1])
                cylinder(d=bolt_d+2, h=ply+2, $fn=16);

        // underglow LED channels — 2 lengthwise grooves on bottom face
        for (sy = [-1, 1])
            translate([-_bl/2 + ply + 10,
                       sy * (bench_w/2 - chan_inset) - chan_w/2,
                       -0.1])
                cube([_bl - 2*ply - 20, chan_w, chan_d]);
    }

    // underglow LED strips visible in channels
    color(c_led_ch)
    for (sy = [-1, 1])
        translate([-_bl/2 + ply + 15,
                   sy * (bench_w/2 - chan_inset) - 3,
                   chan_d - 5])
            cube([_bl - 2*ply - 30, 6, 3]);

    // OSB texture on bottom (top face)
    translate([-_bl/2, -bench_w/2, ply])
        osb_strands(_bl, bench_w, 1);

    // ── 2. LONG SIDE WALLS ──
    color(c_osb)
    for (sy = [-1, 1])
        translate([-_bl/2,
                   sy > 0 ? bench_w/2 - ply : -bench_w/2,
                   ply])
            cube([_bl, ply, wall_h]);

    // OSB texture on outer wall faces
    for (sy = [-1, 1])
        translate([-_bl/2,
                   sy > 0 ? bench_w/2 : -bench_w/2 + ply,
                   ply])
            rotate([90, 0, 0])
                osb_strands(_bl, wall_h, sy*10 + 2);

    // ── 3. END WALLS ──
    color(c_osb2)
    for (sx = [-1, 1])
        translate([sx > 0 ? _bl/2 - ply : -_bl/2,
                   -bench_w/2 + ply,
                   ply])
            cube([ply, iw, wall_h]);

    // ── 4. BOTTOM RAILS ──
    color(c_strip)
    for (sy = [-1, 1])
        translate([-il/2 + ply, sy * rail_spacing/2 - strip_w/2, ply])
            cube([il - 2*ply, strip_w, strip_t]);

    // ── 5. BATTERY SHELVES ──
    color(c_strip)
    for (bx = batt_cx)
        for (edge = [-1, 1])
            translate([bx + edge * (batt_l/2 - shelf_w/2) - shelf_w/2,
                       -rail_spacing/2 - strip_w/2,
                       ply + strip_t])
                cube([shelf_w, rail_spacing + strip_w, strip_t]);

    // ── 6. LID ──
    lid_z = bench_h - ply;
    lid_y = lid_open ? -bench_w/2 - bench_w - 60 : -bench_w/2;

    color(c_osb, lid_open ? 0.7 : 0.85)
    translate([-_bl/2, lid_y, lid_z])
        cube([_bl, bench_w, ply]);

    // OSB texture on lid top
    translate([-_bl/2, lid_y, lid_z + ply])
        osb_strands(_bl, bench_w, 5);

    // ── 7. LID RIDGES ──
    color(c_strip) {
        ri = ridge_inset;
        rz = lid_z - strip_t;

        for (sy = [-1, 1]) {
            ry = lid_y + (sy > 0 ? bench_w - ri - strip_t : ri);
            translate([-_bl/2 + ri, ry, rz])
                cube([_bl - 2*ri, strip_t, strip_t]);
        }
        for (sx = [-1, 1]) {
            rx = sx > 0 ? _bl/2 - ri - strip_t : -_bl/2 + ri;
            translate([rx, lid_y + ri, rz])
                cube([strip_t, bench_w - 2*ri, strip_t]);
        }
    }
}

// ═══════════════════════════════════════════════════════════
//  LEGS with fasteners (bl = override length)
// ═══════════════════════════════════════════════════════════
module legs(bl=0) {
    _bl = bl > 0 ? bl : bench_l;

    for (sx = [-1, 1]) {
        lx = sx * (_bl/2 - leg_inset);

        // ── leg block ──
        color(c_osb * 0.9)
        translate([lx - leg_dim/2, -leg_len/2, 0])
            cube([leg_dim, leg_len, leg_dim]);

        // ── 2× lag screws — through leg + platform floor into playa ──
        color(c_steel)
        for (sy = [-1, 1])
            translate([lx, sy * leg_len/4, -lag_len])
                cylinder(d=lag_d, h=lag_len + leg_dim, $fn=12);

        // lag screw heads (hex-ish)
        color(c_steel)
        for (sy = [-1, 1])
            translate([lx, sy * leg_len/4, leg_dim])
                cylinder(d=lag_d*2, h=4, $fn=6);

        // ── through-bolt — from below platform up into box ──
        color(c_steel)
        translate([lx, 0, -ply - 5])
            cylinder(d=bolt_d, h=ply + leg_dim + ply + 20, $fn=12);

        // bolt head (below platform)
        color(c_steel)
        translate([lx, 0, -ply - 5])
            cylinder(d=bolt_d*2, h=5, $fn=6);

        // nut inside box (top of bolt)
        color(c_steel)
        translate([lx, 0, leg_dim + ply + 5])
            cylinder(d=nut_d, h=nut_h, $fn=6);
    }
}

// ═══════════════════════════════════════════════════════════
//  INTERNAL COMPONENTS
// ═══════════════════════════════════════════════════════════

module battery_block(pos) {
    // battery sits on shelves (shelves are drawn in bench_box)
    shelf_top = ply + strip_t + strip_t;  // bottom sheet + rail + shelf
    color(c_batt)
    translate(pos)
    translate([-batt_l/2, -batt_w/2, shelf_top]) {
        cube([batt_l, batt_w, batt_h]);
        color([0.7, 0.1, 0.1])
        translate([batt_l*0.3, batt_w/2, batt_h])
            cylinder(d=12, h=8, $fn=16);
        color([0.1, 0.1, 0.1])
        translate([batt_l*0.7, batt_w/2, batt_h])
            cylinder(d=12, h=8, $fn=16);
    }
    if (!for_export) {
        color([0.9, 0.9, 0.9])
        translate([pos.x, pos.y, pos.z + shelf_top + batt_h + 10])
            linear_extrude(1) text("BATTERY", size=14,
                halign="center", valign="center");
    }
}

module fan_unit(pos) {
    translate(pos) {
        color(c_fan)
        difference() {
            cube([fan_sz, fan_sz, fan_dp], center=true);
            cylinder(d=fan_sz-12, h=fan_dp+2, $fn=32, center=true);
        }
        color(c_fan * 1.3)
        cylinder(d=fan_sz-20, h=fan_dp-8, $fn=5, center=true);
        // filter pad below
        color(c_filt)
        translate([0, 0, -fan_dp/2 - 4])
            cube([fan_sz+10, fan_sz+10, 5], center=true);
        if (!for_export) {
            color([1, 0.3, 0.1])
            translate([0, 0, fan_dp/2 + 3])
                linear_extrude(1) text("FAN", size=10,
                    halign="center", valign="center");
        }
    }
}

module speaker_unit(pos) {
    translate(pos) {
        color(c_spk)
        cylinder(d=spk_dia, h=spk_depth, $fn=32);
        color([0.5, 0.5, 0.5])
        translate([0, 0, -5])
            cylinder(d1=spk_dia*0.4, d2=spk_dia, h=15, $fn=32);
        if (!for_export) {
            color([0.8, 0.8, 0.8])
            translate([0, 0, spk_depth + 5])
                linear_extrude(1) text("SPK", size=10,
                    halign="center", valign="center");
        }
    }
}

module rpi_unit(pos) {
    translate(pos) {
        color(c_pcb) cube([rpi_l, rpi_w, rpi_h]);
        color([0.7, 0.7, 0.7])
        translate([rpi_l, 8, 0]) cube([3, 15, rpi_h]);
        color([0.7, 0.7, 0.7])
        translate([rpi_l, 30, 0]) cube([3, 15, rpi_h]);
        if (!for_export) {
            color([1,1,1])
            translate([rpi_l/2, rpi_w/2, rpi_h+1])
                linear_extrude(1) text("RPi4", size=8,
                    halign="center", valign="center");
        }
    }
}

module gledopto_unit(pos) {
    translate(pos) {
        color(c_pcb2) cube([gled_l, gled_w, gled_h]);
        color([0.6, 0.6, 0.6])
        translate([gled_l, 10, 0]) cube([3, 16, gled_h]);
        if (!for_export) {
            color([0, 1, 0])
            translate([gled_l/2, gled_w/2, gled_h+1])
                linear_extrude(1) text("WLED", size=8,
                    halign="center", valign="center");
        }
    }
}

module psu_unit(pos) {
    translate(pos) {
        color(c_psu) cube([psu_l, psu_w, psu_h]);
        // vents on side
        color(c_psu * 1.5)
        for (i = [0:4])
            translate([-1, 20 + i*25, 10])
                cube([psu_l+2, 2, psu_h-20]);
        if (!for_export) {
            color([0.9, 0.9, 0.9])
            translate([psu_l/2, psu_w/2, psu_h+1])
                linear_extrude(1) text("PSU", size=12,
                    halign="center", valign="center");
        }
    }
}

module internals(bl=0) {
    _bl = bl > 0 ? bl : bench_l;
    fz = ply;
    shelf_top = strip_t + strip_t;

    // battery center positions
    batt_cx = two_batteries
        ? [-batt_l/2 - 15, batt_l/2 + 15]
        : [0];

    // batteries
    for (bx = batt_cx)
        battery_block([bx, 0, fz]);

    // fans — centered under each battery
    for (bx = batt_cx)
        fan_unit([bx, 0, ply + fan_dp/2 + 2]);

    // ── right end: both computers grouped together ──
    rpi_unit([_bl/2 - ply - rpi_l - 15,
              -rpi_w/2,
              fz + shelf_top]);
    gledopto_unit([_bl/2 - ply - gled_l - 15,
                   bench_w/2 - ply - gled_w - 15,
                   fz + shelf_top]);

    // ── left end: PSU / inverter box ──
    psu_unit([-_bl/2 + ply + 15,
              -psu_w/2,
              fz + shelf_top]);

    // speakers at each end, facing down
    for (sx = [-1, 1])
        speaker_unit([sx * (_bl/2 - 120), 0, ply + spk_depth + 5]);
}

// ═══════════════════════════════════════════════════════════
//  DIMENSION ANNOTATIONS
// ═══════════════════════════════════════════════════════════
module bench_dimensions(bl=0) {
    _bl = bl > 0 ? bl : bench_l;
    _ft = round(_bl / 304.8);
    dim_line(
        [-_bl/2, -bench_w/2, bench_h],
        [ _bl/2, -bench_w/2, bench_h],
        str(_bl, "mm / ", _ft, "ft"),
        [0, -1, 0], 50
    );
    dim_line(
        [_bl/2, -bench_w/2, bench_h],
        [_bl/2,  bench_w/2, bench_h],
        str(bench_w, "mm / 14in"),
        [1, 0, 0], 50
    );
    dim_line(
        [_bl/2, -bench_w/2, 0],
        [_bl/2, -bench_w/2, bench_h],
        str(bench_h, "mm / 14in"),
        [1, -1, 0], 70
    );
    dim_line(
        [-_bl/2, bench_w/2, -leg_dim],
        [-_bl/2, bench_w/2, bench_h],
        str(bench_h + leg_dim, "mm seat"),
        [-1, 0, 0], 50
    );
}

module platform_dimensions() {
    dim_line(
        [-sheet_l/2, -sheet_l/2, 0],
        [ sheet_l/2, -sheet_l/2, 0],
        str(sheet_l, "mm / 8ft"),
        [0, -1, 0], 80
    );
    dim_line(
        [-sheet_l/2, -sheet_l/2, 0],
        [-sheet_l/2,  sheet_l/2, 0],
        str(sheet_l, "mm / 8ft"),
        [-1, 0, 0], 80
    );
}

// ═══════════════════════════════════════════════════════════
//  SINGLE BENCH ON PLATFORM
// ═══════════════════════════════════════════════════════════
module bench_on_platform(bl=0, angle=45) {
    _bl = bl > 0 ? bl : bench_l;

    translate([0, 0, ply])
    rotate([0, 0, angle]) {
        legs(_bl);
        translate([0, 0, leg_dim]) {
            bench_box(_bl);
            if (lid_open) internals(_bl);
            if (show_dimensions && !for_export) bench_dimensions(_bl);
        }
    }
}

// ═══════════════════════════════════════════════════════════
//  FULL ASSEMBLY (single bench)
// ═══════════════════════════════════════════════════════════
module full_assembly() {
    if (show_desert) desert_ground();

    if (show_platform) {
        platform();
        if (show_leds) led_grid();
        if (show_dimensions && !for_export) platform_dimensions();
    }

    if (show_bench) bench_on_platform();
}

// ═══════════════════════════════════════════════════════════
//  COMPARISON MODE — 4ft / 5ft / 6ft side by side
// ═══════════════════════════════════════════════════════════
module comparison() {
    spacing = 2800;

    // desert ground
    color(c_desert)
    translate([-spacing, -3000, -4])
        cube([spacing*2, 6000, 4]);

    // ── diagonal (45°) ──
    translate([-spacing/2, 0, 0]) {
        color(c_floor, 0.3)
        translate([-sheet_l/2, -sheet_l/2, 0])
            cube([sheet_l, sheet_l, ply]);
        if (show_leds) led_grid();
        bench_on_platform(1219, 45);
        color([1, 0.3, 0.1])
        translate([0, -sheet_l/2 - 80, bench_h + leg_dim + ply + 30])
            linear_extrude(1)
                text("4ft diagonal", size=50,
                     halign="center", valign="center");
    }

    // ── parallel (0°) ──
    translate([spacing/2, 0, 0]) {
        color(c_floor, 0.3)
        translate([-sheet_l/2, -sheet_l/2, 0])
            cube([sheet_l, sheet_l, ply]);
        if (show_leds) led_grid();
        bench_on_platform(1219, 0);
        color([1, 0.3, 0.1])
        translate([0, -sheet_l/2 - 80, bench_h + leg_dim + ply + 30])
            linear_extrude(1)
                text("4ft parallel", size=50,
                     halign="center", valign="center");
    }
}

// ═══════════════════════════════════════════════════════════
//  RENDER
// ═══════════════════════════════════════════════════════════
if (compare_mode) {
    comparison();
} else if (cross_section) {
    difference() {
        full_assembly();
        translate([0, 0, ply])
        rotate([0, 0, 45])
        translate([-bench_l, 0, -1])
            cube([bench_l*2, bench_w, bench_h + leg_dim + 200]);
    }
} else {
    full_assembly();
}
