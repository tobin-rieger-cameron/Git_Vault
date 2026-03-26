# scripts/state.py

import pyray as rl
from dataclasses import dataclass
from scripts.camera  import Camera
from scripts.body    import Body
from scripts.physics import GRAVITATIONAL_CONSTANT


@dataclass
class DisplayState:
    """Controls what is visible in the scene."""
    show_trails     : bool = True
    show_vectors    : bool = True
    show_components : bool = False


@dataclass
class SimulationState:
    """Controls how the simulation runs."""
    is_paused        : bool  = False
    time_scale       : float = 1.0
    gravity_constant : float = GRAVITATIONAL_CONSTANT
    simulation_time  : float = 0.0


@dataclass
class InputState:
    """Tracks raw input between frames."""
    is_dragging    : bool = False
    previous_mouse : any  = None

    def __post_init__(self):
        # previous_mouse needs a live pyray call so we can't set it
        # as a default value above — pyray must be initialized first
        self.previous_mouse = rl.get_mouse_position()


class SimState:
    """
    Single source of truth for the entire simulation.
    All mutable runtime values live here, grouped by concern.

    Access pattern:
        state.display.show_trails
        state.sim.time_scale
        state.input.is_dragging
        state.camera
        state.bodies
    """

    def __init__(self):
        self.camera  = Camera()
        self.bodies  = Body.create_all()
        self.display = DisplayState()
        self.sim     = SimulationState()
        self.input   = InputState()

    def reset(self):
        """Reset simulation back to initial conditions."""
        self.bodies               = Body.create_all()
        self.sim.simulation_time  = 0.0
        self.sim.time_scale       = 1.0
        self.sim.gravity_constant = GRAVITATIONAL_CONSTANT
