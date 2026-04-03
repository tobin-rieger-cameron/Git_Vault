# scripts/state.py

import pyray as rl
from dataclasses import dataclass
from scripts.camera  import Camera
from scripts.body    import Body


@dataclass
class WindowState:
    """Tracks raylib window"""
    w          : int = 1280
    h          : int = 720
    fullscreen : bool = True

    @property
    def width(self) -> int:
        return rl.get_screen_width()

    @property
    def height(self) -> int:
        return rl.get_screen_height()

@dataclass
class RenderState:
    """Controls what is visible in the scene."""
    show_trails     : bool = True
    show_vectors    : bool = True
    show_components : bool = False

@dataclass
class SimulationState:
    """Controls how the simulation runs."""
    is_paused        : bool  = False
    time_scale       : float = 1.0
    gravity_constant : float = 0.01
    simulation_time  : float = 0.0

@dataclass
class InputState:
    """Tracks raw input between frames."""
    is_dragging    : bool = False
    previous_mouse : Any = None


class SimState:
    """
    Single source for the entire simulation.
    All mutable runtime values live here.

    Access pattern:
        state.render.show_trails
        state.sim.time_scale
        state.input.is_dragging
        state.camera
        state.bodies
    """

    def __init__(self):
        """init simulation based on starting variables"""
        self.window   = WindowState()
        self.camera   = Camera()
        self.bodies   = Body.create_all()
        self.render   = RenderState()
        self.sim      = SimulationState()
        self.input    = InputState()
        self.substeps = 32

        if self.window.fullscreen:
            rl.toggle_fullscreen()
        rl.init_window(self.window.w, self.window.h, "N-Body Gravity Simulator")
        rl.set_target_fps(60)

        self.font     = rl.load_font("assets/fonts/CaskaydiaCoveNerdFontMono-Regular.ttf")

    def reset(self):
        """Reset simulation back to initial conditions."""
        self.bodies  = Body.create_all()
        self.sim     = SimulationState()
