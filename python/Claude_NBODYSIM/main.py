# main.py
import pyray as rl
from utils.labels     import queue_label, flush_labels
from utils.colors     import BACKGROUND
from utils.hud        import draw_hud
from scripts.state    import SimState
from scripts.input    import handle_input
from scripts.physics  import sim_step
from scripts.render   import (draw_grid, draw_axes, draw_trails,
                              draw_gravity_lines, draw_bodies,
                              draw_force_vectors)

WINDOW_WIDTH      = 1280
WINDOW_HEIGHT     = 720
SUBSTEPS_PER_FRAME = 8

rl.init_window(WINDOW_WIDTH, WINDOW_HEIGHT, "N-Body Gravity Simulator")
rl.set_target_fps(60)

state = SimState()

while not rl.window_should_close():
    state = handle_input(state)

    if not state.sim.is_paused:
        real_dt    = rl.get_frame_time()
        substep_dt = real_dt * state.sim.time_scale / SUBSTEPS_PER_FRAME
        for _ in range(SUBSTEPS_PER_FRAME):
            sim_step(state.bodies, substep_dt, state.sim.gravity_constant)
        state.sim.simulation_time += real_dt * state.sim.time_scale

    rl.begin_drawing()
    rl.clear_background(BACKGROUND)
    rl.begin_mode_3d(state.camera.get())

    draw_grid()
    draw_axes(queue_label, state.camera.get())
    draw_gravity_lines(state.bodies)
    draw_bodies(state.bodies, queue_label, state.camera.get())

    if state.display.show_trails:
        draw_trails(state.bodies)
    if state.display.show_vectors:
        draw_force_vectors(state.bodies, queue_label, state.camera.get())

    rl.end_mode_3d()

    flush_labels()
    draw_hud(state, WINDOW_WIDTH, WINDOW_HEIGHT)

    rl.end_drawing()

rl.close_window()
"""
Two things to notice:

**1. `sim_step` signature changed** — your original `main.py` was passing `state.display.show_trails` into `sim_step`, but we removed that — trail appending needs to be added to `apply_forces` in `physics.py` instead. That's one of the remaining TODOs.

**2. `rl.close_window()`** at the end — cleans up pyray properly when the loop exits.

---

Here's the full TODO list before first run:
```
1. physics.py  — append body.position to body.trail in apply_forces when trails enabled
2. body.py     — create_all() needs realistic starting positions/velocities for interesting orbits
4. input.py    — add import pyray as rl at the top
"""
