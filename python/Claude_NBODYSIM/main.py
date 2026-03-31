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


state = SimState()

while not rl.window_should_close():
    state = handle_input(state)

    if not state.sim.is_paused:
        real_dt    = rl.get_frame_time()
        substep_dt = real_dt * state.sim.time_scale / state.substeps
        for _ in range(state.substeps):
            sim_step(state.bodies, substep_dt, state.sim.gravity_constant)
        state.sim.simulation_time += real_dt * state.sim.time_scale

        if state.render.show_trails:
            for body in state.bodies:
                body.trail.append(body.position.copy())

    rl.begin_drawing()
    rl.clear_background(BACKGROUND)
    state.camera.set_target_body(state.bodies[2])
    rl.begin_mode_3d(state.camera.get())

    #draw_grid()
    #draw_axes(queue_label, state.camera.get())
    draw_gravity_lines(state.bodies)
    draw_bodies(state.bodies, queue_label, state.camera.get())

    if state.render.show_trails:
        draw_trails(state.bodies)
    if state.render.show_vectors:
        draw_force_vectors(state.bodies, queue_label, state.camera.get())

    rl.end_mode_3d()

    flush_labels(state.font)
    draw_hud(state, state.window.width, state.window.height)

    rl.end_drawing()

rl.close_window()
print(f"font: {state.font}")
