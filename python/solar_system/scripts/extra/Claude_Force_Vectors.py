"""
3D Force Vector Visualizer — pyray (raylib-python)
Controls:
  Mouse drag       — orbit camera
  Scroll wheel     — zoom
  A                — add a random force
  C                — clear all forces
  1-9              — toggle force visibility
  R                — reset camera
"""

import pyray as rl
import math
import random

# ── window / camera ──────────────────────────────────────────────────────────
W, H = 1100, 700
rl.init_window(W, H, "3D Force Vector Visualizer")
rl.set_target_fps(60)

camera = rl.Camera3D(
    rl.Vector3(12, 10, 12),   # position
    rl.Vector3(0, 0, 0),      # target
    rl.Vector3(0, 1, 0),      # up
    45.0,
    rl.CAMERA_PERSPECTIVE,
)

# ── colour palette ────────────────────────────────────────────────────────────
PALETTE = [
    rl.Color(70,  130, 220, 255),   # blue
    rl.Color(220,  80,  80, 255),   # red
    rl.Color( 60, 190, 110, 255),   # green
    rl.Color(220, 160,  40, 255),   # amber
    rl.Color(160,  90, 220, 255),   # purple
    rl.Color( 40, 195, 195, 255),   # teal
    rl.Color(220, 100, 160, 255),   # pink
    rl.Color(200, 130,  60, 255),   # orange
    rl.Color(100, 180,  60, 255),   # lime
]

BG        = rl.Color(245, 244, 240, 255)
AXIS_X    = rl.Color(220,  70,  70, 220)
AXIS_Y    = rl.Color( 60, 190,  90, 220)
AXIS_Z    = rl.Color( 70, 120, 220, 220)
GRID_COL  = rl.Color(180, 178, 170, 100)
RESULT_C  = rl.Color(255, 255, 255, 255)
RESULT_BG = rl.Color( 40,  40,  40, 200)


# ── force data ────────────────────────────────────────────────────────────────
class Force:
    def __init__(self, fx, fy, fz, label, color):
        self.vec    = rl.Vector3(fx, fy, fz)
        self.label  = label
        self.color  = color
        self.visible = True

forces: list[Force] = []

def add_force(fx, fy, fz, label=None):
    idx   = len(forces)
    color = PALETTE[idx % len(PALETTE)]
    if label is None:
        label = f"F{idx + 1}"
    forces.append(Force(fx, fy, fz, label, color))

# seed with a couple of forces
add_force( 3,  2,  1, "F1")
add_force(-1,  3,  2, "F2")


# ── helpers ───────────────────────────────────────────────────────────────────
def vec3_add(a, b):
    return rl.Vector3(a.x + b.x, a.y + b.y, a.z + b.z)

def vec3_scale(v, s):
    return rl.Vector3(v.x * s, v.y * s, v.z * s)

def vec3_len(v):
    return math.sqrt(v.x**2 + v.y**2 + v.z**2)

def vec3_norm(v):
    l = vec3_len(v)
    if l < 1e-9:
        return rl.Vector3(0, 0, 0)
    return vec3_scale(v, 1.0 / l)

def perpendicular(v):
    """Return an arbitrary vector perpendicular to v."""
    n = vec3_norm(v)
    ref = rl.Vector3(0, 1, 0)
    if abs(n.x * ref.x + n.y * ref.y + n.z * ref.z) > 0.9:
        ref = rl.Vector3(1, 0, 0)
    # cross product
    cx = n.y * ref.z - n.z * ref.y
    cy = n.z * ref.x - n.x * ref.z
    cz = n.x * ref.y - n.y * ref.x
    return vec3_norm(rl.Vector3(cx, cy, cz))

def draw_arrow(origin, vec, color, shaft_r=0.045, head_r=0.13, head_len_ratio=0.22):
    """Draw a 3-D arrow from origin along vec."""
    length = vec3_len(vec)
    if length < 1e-6:
        return
    shaft_len = length * (1 - head_len_ratio)
    head_len  = length * head_len_ratio

    direction = vec3_norm(vec)
    shaft_end = rl.Vector3(
        origin.x + direction.x * shaft_len,
        origin.y + direction.y * shaft_len,
        origin.z + direction.z * shaft_len,
    )
    tip = rl.Vector3(
        origin.x + vec.x,
        origin.y + vec.y,
        origin.z + vec.z,
    )

    rl.draw_cylinder_ex(origin, shaft_end, shaft_r, shaft_r, 16, color)
    rl.draw_cylinder_ex(shaft_end, tip, head_r, 0.0, 16, color)

def draw_axis_arrow(axis_vec, length, color):
    origin = rl.Vector3(0, 0, 0)
    tip    = vec3_scale(axis_vec, length)
    draw_arrow(origin, tip, color, shaft_r=0.03, head_r=0.09, head_len_ratio=0.18)

def world_to_screen(world_pos):
    """Project a 3D world position to 2D screen coords."""
    return rl.get_world_to_screen(world_pos, camera)

def resultant():
    r = rl.Vector3(0, 0, 0)
    for f in forces:
        if f.visible:
            r = vec3_add(r, f.vec)
    return r

def random_force():
    vals = [random.uniform(-4, 4) for _ in range(3)]
    # ensure it's not near-zero
    while max(abs(v) for v in vals) < 0.5:
        vals = [random.uniform(-4, 4) for _ in range(3)]
    idx   = len(forces)
    label = f"F{idx + 1}"
    add_force(*vals, label)


# ── mouse orbit state ─────────────────────────────────────────────────────────
orbit_yaw   = 45.0   # degrees
orbit_pitch = 30.0
orbit_dist  = 20.0
prev_mouse  = rl.get_mouse_position()
dragging    = False

def spherical_camera(yaw, pitch, dist):
    yr = math.radians(yaw)
    pr = math.radians(pitch)
    x  =  dist * math.cos(pr) * math.sin(yr)
    y  =  dist * math.sin(pr)
    z  =  dist * math.cos(pr) * math.cos(yr)
    camera.position = rl.Vector3(x, y, z)
    camera.target   = rl.Vector3(0, 0, 0)

spherical_camera(orbit_yaw, orbit_pitch, orbit_dist)


# ── UI state ──────────────────────────────────────────────────────────────────
show_components = True   # toggle dashed component projections
show_resultant  = True


# ── main loop ─────────────────────────────────────────────────────────────────
while not rl.window_should_close():

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

    orbit_dist = max(5, min(50, orbit_dist - scroll * 0.8))
    spherical_camera(orbit_yaw, orbit_pitch, orbit_dist)
    prev_mouse = mouse

    if rl.is_key_pressed(rl.KEY_A):
        random_force()
    if rl.is_key_pressed(rl.KEY_C):
        forces.clear()
    if rl.is_key_pressed(rl.KEY_R):
        orbit_yaw, orbit_pitch, orbit_dist = 45.0, 30.0, 20.0
    if rl.is_key_pressed(rl.KEY_S):
        show_components = not show_components
    if rl.is_key_pressed(rl.KEY_T):
        show_resultant = not show_resultant

    # toggle individual forces 1-9
    for k, key in enumerate([
        rl.KEY_ONE, rl.KEY_TWO, rl.KEY_THREE,
        rl.KEY_FOUR, rl.KEY_FIVE, rl.KEY_SIX,
        rl.KEY_SEVEN, rl.KEY_EIGHT, rl.KEY_NINE,
    ]):
        if rl.is_key_pressed(key) and k < len(forces):
            forces[k].visible = not forces[k].visible

    # ── draw ──────────────────────────────────────────────────────────────────
    rl.begin_drawing()
    rl.clear_background(BG)

    rl.begin_mode_3d(camera)

    # grid (XZ plane)
    grid_size = 8
    for i in range(-grid_size, grid_size + 1):
        rl.draw_line_3d(
            rl.Vector3(-grid_size, 0, i),
            rl.Vector3( grid_size, 0, i),
            GRID_COL,
        )
        rl.draw_line_3d(
            rl.Vector3(i, 0, -grid_size),
            rl.Vector3(i, 0,  grid_size),
            GRID_COL,
        )

    # axes
    axis_len = 6.0
    draw_axis_arrow(rl.Vector3(1, 0, 0), axis_len, AXIS_X)
    draw_axis_arrow(rl.Vector3(0, 1, 0), axis_len, AXIS_Y)
    draw_axis_arrow(rl.Vector3(0, 0, 1), axis_len, AXIS_Z)

    # collect screen-space label positions while still in 3D mode
    axis_labels = [
        (world_to_screen(rl.Vector3(axis_len + 0.5, 0, 0)), "X", AXIS_X),
        (world_to_screen(rl.Vector3(0, axis_len + 0.5, 0)), "Y", AXIS_Y),
        (world_to_screen(rl.Vector3(0, 0, axis_len + 0.5)), "Z", AXIS_Z),
    ]

    # origin sphere
    rl.draw_sphere(rl.Vector3(0, 0, 0), 0.12, rl.Color(80, 80, 80, 255))

    # individual force vectors
    origin = rl.Vector3(0, 0, 0)
    screen_labels = []   # (Vector2 screen_pos, text, color) collected for 2D pass
    for f in forces:
        if not f.visible:
            continue
        draw_arrow(origin, f.vec, f.color)

        # component projections (dashed via short cylinders)
        if show_components:
            cx = rl.Color(f.color.r, f.color.g, f.color.b, 80)
            ex = rl.Vector3(f.vec.x, 0, 0)
            ey = rl.Vector3(0, f.vec.y, 0)
            ez = rl.Vector3(0, 0, f.vec.z)
            tip = f.vec
            # project lines from tip to each axis plane
            rl.draw_line_3d(tip, rl.Vector3(tip.x, 0,     tip.z), cx)
            rl.draw_line_3d(tip, rl.Vector3(tip.x, tip.y, 0    ), cx)
            rl.draw_line_3d(tip, rl.Vector3(0,     tip.y, tip.z), cx)
            # foot dots
            for pt in [
                rl.Vector3(tip.x, 0, tip.z),
                rl.Vector3(tip.x, tip.y, 0),
                rl.Vector3(0, tip.y, tip.z),
            ]:
                rl.draw_sphere(pt, 0.07, cx)

        # collect tip label for screen-space rendering
        tip_pos = rl.Vector3(f.vec.x + 0.2, f.vec.y + 0.2, f.vec.z + 0.2)
        screen_labels.append((world_to_screen(tip_pos), f.label, f.color))

    # resultant vector
    if show_resultant and forces:
        r = resultant()
        r_len = vec3_len(r)
        if r_len > 0.01:
            r_col = rl.Color(255, 230, 50, 255)
            draw_arrow(origin, r, r_col, shaft_r=0.07, head_r=0.18, head_len_ratio=0.2)
            tip_pos = rl.Vector3(r.x + 0.2, r.y + 0.2, r.z + 0.2)
            screen_labels.append((world_to_screen(tip_pos), "R", r_col))

    rl.end_mode_3d()

    # ── screen-space labels (projected from 3D positions) ─────────────────────
    for sc, text, color in screen_labels:
        sx, sy = int(sc.x), int(sc.y)
        tw = rl.measure_text(text, 15)
        rl.draw_rectangle(sx - 2, sy - 2, tw + 4, 19, rl.Color(0, 0, 0, 100))
        rl.draw_text(text, sx, sy, 15, color)

    for sc, text, color in axis_labels:
        sx, sy = int(sc.x) - 5, int(sc.y) - 8
        rl.draw_text(text, sx, sy, 18, color)

    # ── HUD ───────────────────────────────────────────────────────────────────
    panel_x, panel_y = 16, 16
    line_h = 22

    # forces panel
    rl.draw_rectangle(panel_x - 6, panel_y - 6, 310, 28 + len(forces) * line_h + (60 if forces else 0), rl.Color(255, 255, 255, 210))
    rl.draw_rectangle_lines(panel_x - 6, panel_y - 6, 310, 28 + len(forces) * line_h + (60 if forces else 0), rl.Color(180, 178, 170, 200))

    rl.draw_text("Forces", panel_x, panel_y, 16, rl.Color(60, 60, 60, 255))
    y = panel_y + 26

    if not forces:
        rl.draw_text("No forces. Press A to add one.", panel_x, y, 13, rl.Color(140, 140, 140, 255))
        y += line_h
    else:
        for i, f in enumerate(forces):
            vis_mark = "●" if f.visible else "○"
            l = vec3_len(f.vec)
            label_str = f"{vis_mark} [{i+1}] {f.label}  ({f.vec.x:.1f}, {f.vec.y:.1f}, {f.vec.z:.1f})  |{l:.2f}|"
            col = f.color if f.visible else rl.Color(170, 170, 170, 200)
            rl.draw_text(label_str, panel_x, y, 13, col)
            y += line_h

        # resultant
        r = resultant()
        r_len = vec3_len(r)
        rl.draw_line(panel_x - 6, y, panel_x + 303, y, rl.Color(180, 178, 170, 200))
        y += 6
        r_str = f"R  ({r.x:.2f}, {r.y:.2f}, {r.z:.2f})  |{r_len:.2f}|"
        rl.draw_text(r_str, panel_x, y, 14, rl.Color(180, 160, 20, 255))
        y += line_h + 4

        # magnitude bar
        bar_w = 290
        max_l = max((vec3_len(f.vec) for f in forces if f.visible), default=1)
        if max_l < 0.01:
            max_l = 1
        fill = min(1.0, r_len / (max_l * math.sqrt(len(forces)) + 1e-9))
        rl.draw_rectangle(panel_x, y, bar_w, 8, rl.Color(220, 218, 210, 200))
        rl.draw_rectangle(panel_x, y, int(bar_w * fill), 8, rl.Color(180, 160, 20, 220))
        y += 14

    # controls panel (bottom-left)
    controls = [
        "Drag — orbit",
        "Scroll — zoom",
        "A — add random force",
        "1-9 — toggle force",
        "S — show/hide components",
        "T — show/hide resultant",
        "C — clear all",
        "R — reset camera",
    ]
    cx2 = 16
    cy2 = H - len(controls) * 18 - 20
    rl.draw_rectangle(cx2 - 6, cy2 - 6, 220, len(controls) * 18 + 14, rl.Color(255, 255, 255, 190))
    for i, ctrl in enumerate(controls):
        rl.draw_text(ctrl, cx2, cy2 + i * 18, 12, rl.Color(90, 90, 90, 255))

    # top-right: component toggle status
    comp_str = f"Components: {'ON' if show_components else 'OFF'}   Resultant: {'ON' if show_resultant else 'OFF'}"
    rl.draw_text(comp_str, W - rl.measure_text(comp_str, 13) - 16, 16, 13, rl.Color(100, 100, 100, 220))

    rl.end_drawing()

rl.close_window()
