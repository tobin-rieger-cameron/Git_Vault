"""
╔══════════════════════════════════════════════════════════════╗
║  render.py                                                   ║
║  3D draw calls — grid, bodies, trails, force vectors         ║
╚══════════════════════════════════════════════════════════════╝
"""

import pyray as rl
import math
from utils.colors   import *
from utils.vector3D import Vector3D


# ── to_rl ─────────────────────────────────────────────────────────
# convert Vector3D to rl.Vector3 for pyray draw calls
def to_rl(v):
    return rl.Vector3(v.x, v.y, v.z)


# ══ Scene ═══════════════════════════════════════════════════════════════════════════╗
                                                                                    # ║
def draw_grid():                                                                    # ║
    rl.draw_grid(100, 10)                                                           # ║
                                                                                    # ║
def draw_axes(queue_label, camera):                                                 # ║
    rl.draw_line_3d(rl.Vector3(0,0,0), rl.Vector3(100,0,0), X_AXIS_COLOR)           # ║
    rl.draw_line_3d(rl.Vector3(0,0,0), rl.Vector3(0,100,0), Y_AXIS_COLOR)           # ║
    rl.draw_line_3d(rl.Vector3(0,0,0), rl.Vector3(0,0,100), Z_AXIS_COLOR)           # ║
    queue_label(rl.Vector3(100,0,0), "X", camera)                                   # ║
    queue_label(rl.Vector3(0,100,0), "Y", camera)                                   # ║
    queue_label(rl.Vector3(0,0,100), "Z", camera)                                   # ║
                                                                                    # ║
# ════════════════════════════════════════════════════════════════════════════════════╝


# ══ Bodies ══════════════════════════════════════════════════════════════════════════════════╗
                                                                                            # ║
def draw_bodies(bodies, queue_label, camera):                                               # ║
    for body in bodies:                                                                     # ║
        rl.draw_sphere_ex(to_rl(body.position), body.radius, 128, 128, body.color)          # ║
        queue_label(to_rl(body.position), body.name, camera)                                # ║
                                                                                            # ║
def draw_trails(bodies):                                                                    # ║
    for body in bodies:                                                                     # ║
        for i in range(len(body.trail) - 1):                                                # ║
            rl.draw_line_3d(to_rl(body.trail[i]), to_rl(body.trail[i+1]), body.trail_color) # ║
                                                                                            # ║
def draw_gravity_lines(bodies):                                                             # ║
    # debug helper — draws a line between every pair of bodies                              # ║
    for i, b1 in enumerate(bodies):                                                         # ║
        for b2 in bodies[i+1:]:                                                             # ║
            rl.draw_line_3d(to_rl(b1.position), to_rl(b2.position), GRID_COLOR)             # ║
                                                                                            # ║
# ════════════════════════════════════════════════════════════════════════════════════════════╝


# ══ Force Vectors ═══════════════════════════════════════════════════════════════════════════╗
                                                                                            # ║
def draw_force_vectors(bodies, queue_label, camera):                                        # ║
    for body in bodies:                                                                     # ║
        total = Vector3D(0, 0, 0)                                                           # ║
                                                                                            # ║
        # ── Per-source forces ────────────────────────────────────────────                 # ║
        for force, source in body.forces:                                                   # ║
            force_dir     = force.normalize()                                               # ║
            offset_origin = body.position + force_dir * body.radius                         # ║
            scaled        = force_dir * min(3.0, math.sqrt(force.length()) * 4)             # ║
            draw_arrow(offset_origin, scaled, source.color)                                 # ║
            total += force                                                                  # ║
                                                                                            # ║
        # ── Resultant force ──────────────────────────────────────────────                 # ║
        total_dir     = total.normalize()                                                   # ║
        offset_origin = body.position + total_dir * body.radius                             # ║
        scaled_total  = total_dir * (math.log1p(total.length()) * 3)                        # ║
        draw_arrow(offset_origin, scaled_total, RESULTANT_COL)                              # ║
        queue_label(to_rl(body.position), "F", camera)                                      # ║
                                                                                            # ║
def draw_arrow(origin, vec, color, shaft_r=0.085, head_r=0.23, head_ratio=0.22):            # ║
    direction = vec.normalize()                                                             # ║
    length    = vec.length()                                                                # ║
    if length < 1e-6:                                                                       # ║
        return                                                                              # ║
    shaft_end = origin + direction * (length * (1 - head_ratio))                            # ║
    tip       = origin + vec                                                                # ║
    rl.draw_cylinder_ex(to_rl(origin),     to_rl(shaft_end), shaft_r, shaft_r, 12, color)   # ║
    rl.draw_cylinder_ex(to_rl(shaft_end),  to_rl(tip),       head_r,  0.0,     12, color)   # ║
                                                                                            # ║
# ════════════════════════════════════════════════════════════════════════════════════════════╝
