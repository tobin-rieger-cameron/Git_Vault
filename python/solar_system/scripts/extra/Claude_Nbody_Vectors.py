"""
N-Body Gravity Simulator — pyray
Three spheres attract each other via Newtonian gravity.
Force vectors are drawn live on each body.

Controls:
  Mouse drag        — orbit camera
  Scroll wheel      — zoom
  Space             — pause / resume
  R                 — reset to initial conditions
  T                 — toggle trails
  V                 — toggle force vectors
  C                 — toggle component projections
  +/-               — speed up / slow down simulation
  G                 — nudge gravity constant up/down (Shift+G down)
"""

import pyray as rl
import math
import random

# ── window ────────────────────────────────────────────────────────────────────
W, H = 1200, 750
rl.init_window(W, H, "N-Body Gravity — Force Vectors")
rl.set_target_fps(60)

# ── colours ───────────────────────────────────────────────────────────────────
BG       = rl.Color(18,  18,  22,  255)
GRID_COL = rl.Color(50,  50,  60,  120)

BODY_COLS = [
    rl.Color( 70, 140, 230, 255),   # blue
    rl.Color(220,  80,  80, 255),   # red
    rl.Color( 55, 200, 120, 255),   # green
]
FORCE_COLS = [
    rl.Color(120, 190, 255, 220),
    rl.Color(255, 140, 140, 220),
    rl.Color(120, 240, 170, 220),
]
TRAIL_COLS = [
    rl.Color( 70, 140, 230, 120),
    rl.Color(220,  80,  80, 120),
    rl.Color( 55, 200, 120, 120),
]
RESULTANT_COL = rl.Color(255, 220,  50, 255)
WHITE         = rl.Color(255, 255, 255, 255)
DARK_OVERLAY  = rl.Color(  0,   0,   0, 140)

# ── physics constants ─────────────────────────────────────────────────────────
G_BASE   = 2.0          # gravitational constant (tweakable)
SOFTENING = 0.5         # softening length to avoid singularity
TRAIL_LEN = 300         # max trail points per body

# ── camera orbit state ────────────────────────────────────────────────────────
orbit_yaw   = 30.0
orbit_pitch = 25.0
orbit_dist  = 28.0

camera = rl.Camera3D(
    rl.Vector3(0, 0, 28),
    rl.Vector3(0, 0, 0),
    rl.Vector3(0, 1, 0),
    45.0,
    rl.CAMERA_PERSPECTIVE,
)

def update_camera():
    yr = math.radians(orbit_yaw)
    pr = math.radians(orbit_pitch)
    camera.position = rl.Vector3(
        orbit_dist * math.cos(pr) * math.sin(yr),
        orbit_dist * math.sin(pr),
        orbit_dist * math.cos(pr) * math.cos(yr),
    )
    camera.target = rl.Vector3(0, 0, 0)

update_camera()

# ── vector math ───────────────────────────────────────────────────────────────
def v3(x, y, z):           return rl.Vector3(x, y, z)
def vadd(a, b):            return v3(a.x+b.x, a.y+b.y, a.z+b.z)
def vsub(a, b):            return v3(a.x-b.x, a.y-b.y, a.z-b.z)
def vscale(v, s):          return v3(v.x*s, v.y*s, v.z*s)
def vlen(v):               return math.sqrt(v.x**2 + v.y**2 + v.z**2)
def vnorm(v):
    l = vlen(v)
    return vscale(v, 1/l) if l > 1e-12 else v3(0, 0, 0)

def w2s(world_pos):
    """World → screen (2-D)."""
    return rl.get_world_to_screen(world_pos, camera)

# ── body definition ───────────────────────────────────────────────────────────
class Body:
    def __init__(self, pos, vel, mass, radius, color, force_color, trail_color, name):
        self.pos         = v3(*pos)
        self.vel         = v3(*vel)
        self.mass        = mass
        self.radius      = radius
        self.color       = color
        self.force_color = force_color
        self.trail_color = trail_color
        self.name        = name
        self.forces: list[rl.Vector3] = []   # per-pair forces (reset each frame)
        self.trail: list[rl.Vector3]  = []

INITIAL_STATES = [
    # pos              vel              mass  radius
    (( 5.0, 0.0,  2.0), (-0.3,  0.2, -0.1), 3.0,  0.55),
    ((-4.0, 1.0, -3.0), ( 0.4, -0.1,  0.3), 2.5,  0.50),
    (( 0.0,-3.0,  4.0), (-0.1,  0.3, -0.2), 2.0,  0.45),
]

def make_bodies():
    return [
        Body(pos, vel, mass, radius, BODY_COLS[i], FORCE_COLS[i], TRAIL_COLS[i], f"m{i+1}")
        for i, (pos, vel, mass, radius) in enumerate(INITIAL_STATES)
    ]

bodies = make_bodies()

# ── simulation state ──────────────────────────────────────────────────────────
paused          = False
show_trails     = True
show_vectors    = True
show_components = False
time_scale      = 1.0
G               = G_BASE
sim_time        = 0.0

# ── arrow drawing ─────────────────────────────────────────────────────────────
def draw_arrow(origin, vec, color, shaft_r=0.045, head_r=0.13, head_ratio=0.22):
    length = vlen(vec)
    if length < 1e-6:
        return
    direction = vnorm(vec)
    shaft_end = vadd(origin, vscale(direction, length * (1 - head_ratio)))
    tip       = vadd(origin, vec)
    rl.draw_cylinder_ex(origin, shaft_end, shaft_r, shaft_r, 12, color)
    rl.draw_cylinder_ex(shaft_end, tip, head_r, 0.0, 12, color)

def draw_axis(direction, length, color):
    origin = v3(0, 0, 0)
    tip    = vscale(direction, length)
    draw_arrow(origin, tip, color, shaft_r=0.025, head_r=0.07, head_ratio=0.18)

# ── physics step ──────────────────────────────────────────────────────────────
def compute_forces(bodies, G):
    """Compute gravitational force vectors for each body. Returns list of net forces."""
    n = len(bodies)
    # per-pair forces so we can draw them individually
    pair_forces = [[v3(0,0,0)] * n for _ in range(n)]

    for i in range(n):
        for j in range(i+1, n):
            r    = vsub(bodies[j].pos, bodies[i].pos)
            dist = math.sqrt(vlen(r)**2 + SOFTENING**2)
            mag  = G * bodies[i].mass * bodies[j].mass / (dist**2)
            fdir = vnorm(r)
            f    = vscale(fdir, mag)
            pair_forces[i][j] =  f
            pair_forces[j][i] = vscale(f, -1)

    return pair_forces

def step(bodies, dt, G):
    pair_forces = compute_forces(bodies, G)
    n = len(bodies)

    # store per-pair forces on each body for vector drawing
    for i, b in enumerate(bodies):
        b.forces = [pair_forces[i][j] for j in range(n) if j != i]

    # integrate (symplectic Euler)
    for i, b in enumerate(bodies):
        net = v3(0, 0, 0)
        for f in b.forces:
            net = vadd(net, f)
        accel = vscale(net, 1.0 / b.mass)
        b.vel = vadd(b.vel, vscale(accel, dt))

    for b in bodies:
        b.pos = vadd(b.pos, vscale(b.vel, dt))
        if show_trails:
            b.trail.append(v3(b.pos.x, b.pos.y, b.pos.z))
            if len(b.trail) > TRAIL_LEN:
                b.trail.pop(0)

# ── label helper ──────────────────────────────────────────────────────────────
screen_labels = []   # filled during 3D pass, drawn after end_mode_3d

def queue_label(world_pos, text, color, font_size=14, bg=True):
    sc = w2s(world_pos)
    screen_labels.append((int(sc.x), int(sc.y), text, color, font_size, bg))

def flush_labels():
    for sx, sy, text, color, fs, bg in screen_labels:
        if bg:
            tw = rl.measure_text(text, fs)
            rl.draw_rectangle(sx-3, sy-2, tw+6, fs+4, DARK_OVERLAY)
        rl.draw_text(text, sx, sy, fs, color)
    screen_labels.clear()

# ── main loop ─────────────────────────────────────────────────────────────────
prev_mouse = rl.get_mouse_position()
dragging   = False

while not rl.window_should_close():

    dt_real = rl.get_frame_time()

    # ── input ─────────────────────────────────────────────────────────────────
    mouse     = rl.get_mouse_position()
    mouse_btn = rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT)
    scroll    = rl.get_mouse_wheel_move()

    if mouse_btn:
        if dragging:
            dx = mouse.x - prev_mouse.x
            dy = mouse.y - prev_mouse.y
            orbit_yaw   += dx * 0.4
            orbit_pitch  = max(-89, min(89, orbit_pitch - dy * 0.4))
        dragging = True
    else:
        dragging = False

    orbit_dist = max(6, min(80, orbit_dist - scroll * 0.8))
    update_camera()
    prev_mouse = mouse

    if rl.is_key_pressed(rl.KEY_SPACE):
        paused = not paused
    if rl.is_key_pressed(rl.KEY_R):
        bodies    = make_bodies()
        sim_time  = 0.0
        time_scale = 1.0
        G          = G_BASE
    if rl.is_key_pressed(rl.KEY_T):
        show_trails = not show_trails
        if not show_trails:
            for b in bodies:
                b.trail.clear()
    if rl.is_key_pressed(rl.KEY_V):
        show_vectors = not show_vectors
    if rl.is_key_pressed(rl.KEY_C):
        show_components = not show_components
    if rl.is_key_pressed(rl.KEY_EQUAL):
        time_scale = min(8.0, time_scale * 1.25)
    if rl.is_key_pressed(rl.KEY_MINUS):
        time_scale = max(0.05, time_scale / 1.25)
    if rl.is_key_pressed(rl.KEY_G):
        if rl.is_key_down(rl.KEY_LEFT_SHIFT) or rl.is_key_down(rl.KEY_RIGHT_SHIFT):
            G = max(0.1, G - 0.25)
        else:
            G = min(20.0, G + 0.25)

    # ── physics ───────────────────────────────────────────────────────────────
    if not paused:
        SUB = 8
        sub_dt = dt_real * time_scale / SUB
        for _ in range(SUB):
            step(bodies, sub_dt, G)
        sim_time += dt_real * time_scale

    # ── draw ──────────────────────────────────────────────────────────────────
    rl.begin_drawing()
    rl.clear_background(BG)

    rl.begin_mode_3d(camera)

    # grid
    gs = 10
    for i in range(-gs, gs+1):
        rl.draw_line_3d(v3(-gs, -8, i), v3(gs, -8, i), GRID_COL)
        rl.draw_line_3d(v3(i, -8, -gs), v3(i, -8, gs), GRID_COL)

    # axis indicators (small, bottom corner of scene)
    ax_origin = v3(-8.5, -7.5, -8.5)
    ax_len    = 1.2
    ax_cols   = [rl.Color(220,70,70,200), rl.Color(60,190,90,200), rl.Color(70,120,220,200)]
    ax_dirs   = [v3(1,0,0), v3(0,1,0), v3(0,0,1)]
    ax_names  = ["X", "Y", "Z"]
    for d, c, name in zip(ax_dirs, ax_cols, ax_names):
        tip_w = vadd(ax_origin, vscale(d, ax_len + 0.3))
        draw_arrow(ax_origin, vscale(d, ax_len), c, shaft_r=0.02, head_r=0.06, head_ratio=0.2)
        queue_label(tip_w, name, c, font_size=13, bg=False)

    # trails
    if show_trails:
        for b in bodies:
            for k in range(1, len(b.trail)):
                alpha = int(180 * k / len(b.trail))
                tc = rl.Color(b.trail_color.r, b.trail_color.g, b.trail_color.b, alpha)
                rl.draw_line_3d(b.trail[k-1], b.trail[k], tc)

    # force vectors & bodies
    for i, b in enumerate(bodies):
        # draw per-pair force arrows from body centre
        if show_vectors:
            # scale arrows for readability (don't draw raw Newtons — too large/small)
            for j, fvec in enumerate(b.forces):
                flen = vlen(fvec)
                if flen < 1e-6:
                    continue
                # display length: logarithmic scale capped at 3 units
                display_len = min(3.0, 0.8 * math.log1p(flen))
                fdir  = vnorm(fvec)
                fdisplay = vscale(fdir, display_len)
                # colour from the OTHER body that's pulling
                other_idx = [k for k in range(len(bodies)) if k != i][j if j < i else j]
                fc = rl.Color(
                    FORCE_COLS[other_idx].r,
                    FORCE_COLS[other_idx].g,
                    FORCE_COLS[other_idx].b,
                    200,
                )
                draw_arrow(b.pos, fdisplay, fc, shaft_r=0.035, head_r=0.10, head_ratio=0.22)

                # component projections from arrow tip
                if show_components:
                    tip = vadd(b.pos, fdisplay)
                    cc  = rl.Color(fc.r, fc.g, fc.b, 70)
                    rl.draw_line_3d(tip, v3(tip.x, b.pos.y, tip.z), cc)
                    rl.draw_line_3d(tip, v3(tip.x, tip.y, b.pos.z), cc)
                    rl.draw_line_3d(tip, v3(b.pos.x, tip.y, tip.z), cc)

            # resultant force arrow
            if b.forces:
                net = v3(0,0,0)
                for f in b.forces:
                    net = vadd(net, f)
                net_len = vlen(net)
                if net_len > 1e-6:
                    display_len = min(3.5, 0.9 * math.log1p(net_len))
                    net_display = vscale(vnorm(net), display_len)
                    draw_arrow(b.pos, net_display, RESULTANT_COL,
                               shaft_r=0.055, head_r=0.14, head_ratio=0.22)
                    tip_w = vadd(b.pos, vscale(net_display, 1.1))
                    queue_label(tip_w, "R", RESULTANT_COL, font_size=13)

        # body sphere
        rl.draw_sphere(b.pos, b.radius, b.color)
        rl.draw_sphere_wires(b.pos, b.radius + 0.04,
                             8, 8, rl.Color(b.color.r, b.color.g, b.color.b, 80))

        # body label
        label_w = v3(b.pos.x, b.pos.y + b.radius + 0.3, b.pos.z)
        queue_label(label_w, b.name, b.color, font_size=15)

    # gravity lines between bodies (thin)
    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            r = vsub(bodies[j].pos, bodies[i].pos)
            dist = vlen(r)
            alpha = int(max(20, min(120, 1200 / (dist**2 + 1))))
            lc = rl.Color(150, 150, 160, alpha)
            rl.draw_line_3d(bodies[i].pos, bodies[j].pos, lc)

    rl.end_mode_3d()

    flush_labels()

    # ── HUD ───────────────────────────────────────────────────────────────────
    # left panel
    px, py = 14, 14
    panel_h = 36 + len(bodies) * 68 + 20
    rl.draw_rectangle(px-6, py-6, 330, panel_h, rl.Color(10, 10, 18, 200))
    rl.draw_rectangle_lines(px-6, py-6, 330, panel_h, rl.Color(70, 70, 90, 180))

    rl.draw_text("N-Body Gravity", px, py, 17, WHITE)
    py += 26

    for i, b in enumerate(bodies):
        speed  = vlen(b.vel)
        net    = v3(0,0,0)
        for f in b.forces:
            net = vadd(net, f)
        net_mag = vlen(net)

        col = b.color
        rl.draw_rectangle(px-2, py-2, 10, 10, col)
        rl.draw_text(b.name, px+14, py-2, 14, col)
        rl.draw_text(
            f"  pos ({b.pos.x:+.1f}, {b.pos.y:+.1f}, {b.pos.z:+.1f})",
            px, py+14, 12, rl.Color(180,180,190,220))
        rl.draw_text(
            f"  vel ({b.vel.x:+.2f}, {b.vel.y:+.2f}, {b.vel.z:+.2f})  |{speed:.2f}|",
            px, py+28, 12, rl.Color(180,180,190,220))
        rl.draw_text(
            f"  |Fnet| = {net_mag:.3f}",
            px, py+42, 12, RESULTANT_COL)
        py += 68

    # right panel — sim info
    rx = W - 230
    rl.draw_rectangle(rx-6, 8, 228, 160, rl.Color(10, 10, 18, 200))
    rl.draw_rectangle_lines(rx-6, 8, 228, 160, rl.Color(70, 70, 90, 180))

    status = "PAUSED" if paused else f"t = {sim_time:.1f}s"
    rl.draw_text(status, rx, 16, 14, rl.Color(200, 200, 100, 255) if paused else WHITE)
    rl.draw_text(f"Speed:  x{time_scale:.2f}", rx, 36, 13, rl.Color(170,170,180,220))
    rl.draw_text(f"G:      {G:.2f}",           rx, 52, 13, rl.Color(170,170,180,220))
    rl.draw_text(f"Trails: {'ON' if show_trails else 'OFF'}",     rx, 68,  13, rl.Color(170,170,180,220))
    rl.draw_text(f"Vectors:{'ON' if show_vectors else 'OFF'}",    rx, 84,  13, rl.Color(170,170,180,220))
    rl.draw_text(f"Comps:  {'ON' if show_components else 'OFF'}", rx, 100, 13, rl.Color(170,170,180,220))

    # controls footer
    controls = [
        "Drag/Scroll — orbit/zoom",
        "Space — pause   R — reset",
        "T — trails   V — vectors   C — comps",
        "+/- — time scale   G/Shift+G — gravity",
    ]
    fy = H - len(controls) * 17 - 14
    rl.draw_rectangle(8, fy-6, 310, len(controls)*17+12, rl.Color(10,10,18,190))
    for i, ctrl in enumerate(controls):
        rl.draw_text(ctrl, 14, fy + i*17, 12, rl.Color(130, 130, 145, 220))

    rl.end_drawing()

rl.close_window()
