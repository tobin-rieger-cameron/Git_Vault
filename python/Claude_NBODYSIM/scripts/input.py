"""
╔══════════════════════════════════════════════════════════════╗
║  input.py                                                    ║
║  Keyboard and mouse input — camera, sim controls, toggles    ║
╚══════════════════════════════════════════════════════════════╝
"""

import pyray as rl


# ── handle_input ─────────────────────────────────────────────────────────────────────────────
def handle_input(state):

    # ══ Mouse ═══════════════════════════════════════════════════════════════════════════════╗
                                                                                            # ║
    if state.input.previous_mouse is None:                                                  # ║
        state.input.previous_mouse = rl.get_mouse_position()                                # ║
                                                                                            # ║
    current_mouse   = rl.get_mouse_position()                                               # ║
    left_mouse_held = rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT)                         # ║
    scroll_amount   = rl.get_mouse_wheel_move()                                             # ║
                                                                                            # ║
    # ── Camera Orbit: (left-click drag) ────────────────────────────                       # ║
    if left_mouse_held:                                                                     # ║
        if state.input.is_dragging:                                                         # ║
            delta_x = current_mouse.x - state.input.previous_mouse.x                        # ║
            delta_y = current_mouse.y - state.input.previous_mouse.y                        # ║
            state.camera.orbit(delta_x, delta_y)                                            # ║
        state.input.is_dragging = True                                                      # ║
    else:                                                                                   # ║
        state.input.is_dragging = False                                                     # ║
                                                                                            # ║
    state.camera.set_zoom(scroll_amount)                                                    # ║
    state.camera.update()                                                                   # ║
    state.input.previous_mouse = current_mouse                                              # ║
                                                                                            # ║
    # ════════════════════════════════════════════════════════════════════════════════════════╝

    # ══ Keyboard ════════════════════════════════════════════════════════════════════════════╗
                                                                                            # ║
    # ── Sim Controls ───────────────────────────────────────────────────────────────       # ║
    if rl.is_key_pressed(rl.KEY_SPACE):                                                     # ║
        state.sim.is_paused = not state.sim.is_paused                                       # ║
                                                                                            # ║
    if rl.is_key_pressed(rl.KEY_R):                                                         # ║
        state.reset()                                                                       # ║
                                                                                            # ║
    # ── Toggles ────────────────────────────────────────────────────────────────────       # ║
    if rl.is_key_pressed(rl.KEY_T):                                                         # ║
        state.render.show_trails = not state.render.show_trails                             # ║
        if not state.render.show_trails:                                                    # ║
            for body in state.bodies:                                                       # ║
                body.trail.clear()                                                          # ║
                                                                                            # ║
    if rl.is_key_pressed(rl.KEY_V):                                                         # ║
        state.render.show_vectors = not state.render.show_vectors                           # ║
                                                                                            # ║
    # ── Time Scale (+/-) ───────────────────────────────────────────────────────────       # ║
    if rl.is_key_pressed(rl.KEY_EQUAL):                                                     # ║
        state.sim.time_scale = min(100.0, state.sim.time_scale * 1.25)                      # ║
    if rl.is_key_pressed(rl.KEY_MINUS):                                                     # ║
        state.sim.time_scale = max(0.05, state.sim.time_scale / 1.25)                       # ║
                                                                                            # ║
    # ── Gravity Constant (G / Shift+G) ─────────────────────────────────────────────       # ║
    if rl.is_key_pressed(rl.KEY_G):                                                         # ║
        shift_held = (                                                                      # ║
            rl.is_key_down(rl.KEY_LEFT_SHIFT) or                                            # ║
            rl.is_key_down(rl.KEY_RIGHT_SHIFT)                                              # ║
        )                                                                                   # ║
        if shift_held:                                                                      # ║
            state.sim.gravity_constant = max(0.1,  state.sim.gravity_constant - 0.25)       # ║
        else:                                                                               # ║
            state.sim.gravity_constant = min(20.0, state.sim.gravity_constant + 0.25)       # ║
                                                                                            # ║
                                                                                            # ║
    # ════════════════════════════════════════════════════════════════════════════════════════╝

    return state
