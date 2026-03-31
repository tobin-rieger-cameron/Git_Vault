# utils/hud.py
import pyray as rl
from utils.colors import DARK_OVERLAY, WHITE, BODY_COLS


class Panel:
    """A positioned, padded HUD region. All values pre-scaled at construction."""

    def __init__(self, font, x, y, w, h, padding):
        self.font    = font
        self.x       = x
        self.y       = y
        self.w       = w
        self.h       = h
        self.padding = padding

    def draw_background(self):
        rl.draw_rectangle(self.x, self.y, self.w, self.h, DARK_OVERLAY)

    def text(self, label, ox, oy, size, color=WHITE):
        rl.draw_text_ex(self.font, label,
                        rl.Vector2(self.x + ox, self.y + oy),
                        size, 1, color)


def make_bodies_panel(state, s):
    return Panel(
        font    = state.font,
        x       = s(10),
        y       = s(10),
        w       = s(220),
        h       = s(20) + len(state.bodies) * s(80),
        padding = s(5)
    )

def make_sim_panel(state, s, window_width):
    return Panel(
        font    = state.font,
        x       = window_width - s(210),
        y       = s(10),
        w       = s(200),
        h       = s(100),
        padding = s(5)
    )

def make_footer_panel(state, s, window_width, window_height):
    return Panel(
        font    = state.font,
        x       = 0,
        y       = window_height - s(30),
        w       = window_width,
        h       = s(30),
        padding = s(5)
    )


def draw_hud(state, window_width, window_height):
    scale = window_height / 720
    def s(v): return int(v * scale)

    # --- bodies panel
    bp = make_bodies_panel(state, s)
    bp.draw_background()
    bp.text("BODIES", bp.padding, bp.padding, s(16))
    for i, body in enumerate(state.bodies):
        row_y = s(35) + i * s(80)
        bp.text(body.name,                                                           bp.padding, row_y,        s(14), BODY_COLS[i])
        bp.text(f"pos  x:{body.position.x:.1f} y:{body.position.y:.1f} z:{body.position.z:.1f}", bp.padding, row_y + s(18), s(12))
        bp.text(f"vel  x:{body.velocity.x:.1f} y:{body.velocity.y:.1f} z:{body.velocity.z:.1f}", bp.padding, row_y + s(34), s(12))
        bp.text(f"mass {body.mass:.2f}  radius {body.radius:.1f}",                  bp.padding, row_y + s(50), s(12))

    # --- sim panel
    sp = make_sim_panel(state, s, window_width)
    sp.draw_background()
    sp.text("SIMULATION",                                sp.padding, sp.padding,        s(16))
    sp.text(f"time       {state.sim.simulation_time:.1f}", sp.padding, sp.padding+s(25), s(12))
    sp.text(f"timescale  {state.sim.time_scale:.2f}",      sp.padding, sp.padding+s(41), s(12))
    sp.text(f"G          {state.sim.gravity_constant:.2f}", sp.padding, sp.padding+s(57), s(12))
    sp.text("PAUSED" if state.sim.is_paused else "RUNNING", sp.padding, sp.padding+s(73), s(12))

    # --- footer
    fp = make_footer_panel(state, s, window_width, window_height)
    fp.draw_background()
    fp.text(
        "SPACE pause   R reset   T trails   V vectors   C components   +/- timescale   G/shift+G gravity",
        fp.padding, fp.padding, s(12)
    )
