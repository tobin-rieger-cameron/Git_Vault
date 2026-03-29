# utils/hud.py
import pyray as rl
from utils.colors import DARK_OVERLAY, WHITE, BODY_COLS

#TODO: placeholder hud, needs to be customized

def draw_hud(state, window_width, window_height):
    # --- Body stats panel (top left)
    panel_width = 220
    panel_height = 20 + len(state.bodies) * 80
    rl.draw_rectangle(10, 10, panel_width, panel_height, DARK_OVERLAY)
    rl.draw_text_ex(state.font, "BODIES", rl.Vector2(15, 15), 16, 1, WHITE)
    for i, body in enumerate(state.bodies):
        y = 35 + i * 80
        rl.draw_text_ex(state.font, body.name, rl.Vector2(15, y), 14, 1, BODY_COLS[i])
        rl.draw_text_ex(state.font, f"pos  x:{body.position.x:.1f} y:{body.position.y:.1f} z:{body.position.z:.1f}", rl.Vector2(15, y+18), 12, 1, WHITE)
        rl.draw_text_ex(state.font, f"vel  x:{body.velocity.x:.1f} y:{body.velocity.y:.1f} z:{body.velocity.z:.1f}", rl.Vector2(15, y+34), 12, 1, WHITE)
        rl.draw_text_ex(state.font, f"mass {body.mass:.2f}  radius {body.radius:.1f}", rl.Vector2(15, y+50), 12, 1, WHITE)

    # --- Sim info panel (top right)
    sx = window_width - 210
    rl.draw_rectangle(sx, 10, 200, 90, DARK_OVERLAY)
    rl.draw_text_ex(state.font, "SIMULATION", rl.Vector2(sx+5, 15), 16, 1, WHITE)
    rl.draw_text_ex(state.font, f"time       {state.sim.simulation_time:.1f}", rl.Vector2(sx+5, 35), 12, 1, WHITE)
    rl.draw_text_ex(state.font, f"timescale  {state.sim.time_scale:.2f}", rl.Vector2(sx+5, 51), 12, 1, WHITE)
    rl.draw_text_ex(state.font, f"G          {state.sim.gravity_constant:.2f}", rl.Vector2(sx+5, 67), 12, 1, WHITE)
    paused = "PAUSED" if state.sim.is_paused else "RUNNING"
    rl.draw_text_ex(state.font, paused, rl.Vector2(sx+5, 83), 12, 1, WHITE)

    # --- Controls footer (bottom)
    rl.draw_rectangle(0, window_height - 30, window_width, 30, DARK_OVERLAY)
    rl.draw_text_ex(state.font,
        "SPACE pause   R reset   T trails   V vectors   C components   +/- timescale   G/shift+G gravity",
        rl.Vector2(10, window_height - 20), 12, 1, WHITE
    )
