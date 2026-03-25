# main.py

from scripts.state import SimState

state = SimState()

while not rl.window_should_close():

    state = handle_input(state)

    # sim-state per step
    if not state.sim.is_paused:
        real_delta_time    = rl.get_frame_time()
        substep_delta_time = real_delta_time * state.sim.time_scale / SUBSTEPS_PER_FRAME
        for _ in range(SUBSTEPS_PER_FRAME):
            simulation_step(
                state.bodies,
                substep_delta_time,
                state.sim.gravity_constant,
                state.display.show_trails,
            )
        state.sim.simulation_time += real_delta_time * state.sim.time_scale

    rl.begin_drawing()
    rl.clear_background(BACKGROUND_COLOR)
    rl.begin_mode_3d(state.camera.get())

    draw_grid()
    draw_axes(queue_label)
    draw_gravity_lines(state.bodies)
    draw_bodies(state.bodies, queue_label)

    if state.display.show_trails:
        draw_trails(state.bodies)
    if state.display.show_vectors:
        draw_force_vectors(state.bodies, queue_label)

    rl.end_mode_3d()

    flush_labels()
    draw_hud(state, WINDOW_WIDTH, WINDOW_HEIGHT)

    rl.end_drawing()
