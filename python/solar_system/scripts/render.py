
# scripts/render.py
import pyray as rl
import math
from utils.colors import FORCE_COLS, RESULTANT_COL
from utils.vector3d import Vector3D

def to_rl(v):
    """Convert Vector3D to rl.Vector3 for pyray calls."""
    return rl.Vector3(v.x, v.y, v.z)


def draw_arrow(origin, vec, color, shaft_r=0.045, head_r=0.13, head_ratio=0.22):
    # convert to Vector3D for math
    origin = Vector3D(origin.x, origin.y, origin.z)
    vec = Vector3D(vec.x, vec.y, vec.z)

    length = vec.length()
    if length < 1e-6:
        return

    direction = vec.normalize()
    shaft_end = origin + direction.scale(length * (1 - head_ratio))
    tip       = origin + vec

    # convert back to rl.Vector3 for pyray
    rl.draw_cylinder_ex(to_rl(origin), to_rl(shaft_end), shaft_r, shaft_r, 12, color)
    rl.draw_cylinder_ex(to_rl(shaft_end), to_rl(tip), head_r, 0.0, 12, color)

def draw_force_vectors(bodies):
    for i, b in enumerate(bodies):

        # per-pair force arrows
        for j, (fx, fy, fz) in enumerate(b.forces):
            fvec = Vector3D(fx, fy, fz)
            flen = fvec.length()
            if flen < 1e-6:
                continue

            display_len = min(3.0, 0.8 * math.log1p(flen))
            fdisplay    = fvec.normalize() * display_len

            other_idx = [k for k in range(len(bodies)) if k != i][j]
            fc = rl.Color(
                FORCE_COLS[other_idx].r,
                FORCE_COLS[other_idx].g,
                FORCE_COLS[other_idx].b,
                200,
            )

            origin = b.get_position()
            tip    = to_rl(Vector3D(origin.x, origin.y, origin.z) + fdisplay)

            draw_arrow(origin, to_rl(fdisplay), fc,
                       shaft_r=0.035, head_r=0.10, head_ratio=0.22)

            # component projections
            cc = rl.Color(fc.r, fc.g, fc.b, 70)
            rl.draw_line_3d(tip, rl.Vector3(tip.x, origin.y, tip.z), cc)
            rl.draw_line_3d(tip, rl.Vector3(tip.x, tip.y,   origin.z), cc)
            rl.draw_line_3d(tip, rl.Vector3(origin.x, tip.y, tip.z), cc)

        # resultant force arrow
        if b.forces:
            net = sum(
                (Vector3D(fx, fy, fz) for fx, fy, fz in b.forces),
                Vector3D()
            )
            net_len = net.length()

            if net_len > 1e-6:
                display_len = min(3.5, 0.9 * math.log1p(net_len))
                net_display = net.normalize() * display_len

                origin  = b.get_position()
                tip_w   = to_rl(Vector3D(origin.x, origin.y, origin.z) + net_display * 1.1)

                draw_arrow(origin, to_rl(net_display), RESULTANT_COL,
                           shaft_r=0.055, head_r=0.14, head_ratio=0.22)
                #queue_label(tip_w, "R", RESULTANT_COL, font_size=13)
