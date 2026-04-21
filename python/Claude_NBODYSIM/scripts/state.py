"""
 ╔══════════════════════════════════════════════════════════════╗
 ║  scripts/state.py                                            ║
 ║  All mutable runtime values live here.                       ║
 ║  Single source for the entire simulation.                    ║
 ╚══════════════════════════════════════════════════════════════╝
"""

import pyray as rl
from dataclasses import dataclass, field
from scripts.camera  import Camera
from scripts.body    import Body
from utils.hud       import ScreenPanel, BodyPanel

# ══ Data Classes ════════════════════════════════════════════════════════════╗
                                                                            # ║
@dataclass                                                                  # ║
class WindowState:                                                          # ║
    """Tracks raylib window"""                                              # ║
    def update_window(self):
        if rl.get_current_monitor != self.current_monitor:
            self.current_monitor = rl.get_current_monitor
            self.width = rl.get_monitor_width(current_monitor)
            self.height = rl.get_monitor_height(current_monitor)

    def __post_init__(self):                                                # ║
        rl.init_window(0, 0, "N-Body Gravity Simulator")                    # ║
        rl.set_target_fps(60)                                               # ║
        current_monitor = rl.get_current_monitor()
        self.width = rl.get_monitor_width(current_monitor)                  # ║ #TODO: currently grabs the first monitors resolution, needs to grab the active monitors resolution, and maybe change resolution depending on the active monitor
        self.height = rl.get_monitor_height(current_monitor)                # ║
        rl.set_window_size(self.width, self.height)                         # ║
        rl.toggle_fullscreen()                                              # ║
                                                                            # ║
@dataclass                                                                  # ║
class HudState:                                                             # ║
    """Holds hud information"""                                             # ║
    screen_panels   : list = field(default_factory=list)                    # ║
    body_panels     : dict = field(default_factory=dict)                    # ║
    edit_mode       : bool = False
                                                                            # ║
def init_hud(bodies):                                                       # ║
    top_left   = ScreenPanel(x=0.01, y=0.01, w=0.20, h=0.40, elements=[])   # ║
    top_right  = ScreenPanel(x=0.79, y=0.01, w=0.20, h=0.40, elements=[])   # ║
    bottom_bar = ScreenPanel(x=0.00, y=0.95, w=1.00, h=0.05, elements=[])   # ║
                                                                            # ║
    body_panels = {}                                                        # ║
    for body in bodies:                                                     # ║
        body_panels[body.id] = BodyPanel(                                   # ║
            w=0.15,                                                         # ║
            h=0.20,                                                         # ║
            offset_x=10,                                                    # ║
            offset_y=-20,                                                   # ║
            elements=[]                                                     # ║
        )                                                                   # ║
                                                                            # ║
        return HudState(                                                    # ║
            screen_panels=[top_left, top_right, bottom_bar],                # ║
            body_panels=body_panels,                                        # ║
        )                                                                   # ║
                                                                            # ║
class RenderState:                                                          # ║
    """Controls what is visible in the scene."""                            # ║
    show_trails     : bool = True                                           # ║
    show_vectors    : bool = True                                           # ║
    show_components : bool = False                                          # ║
                                                                            # ║
@dataclass                                                                  # ║
class SimulationState:                                                      # ║
    """Controls how the simulation runs."""                                 # ║
    is_paused        : bool  = False                                        # ║
    time_scale       : float = 1.0                                          # ║
    gravity_constant : float = 0.01                                         # ║
    simulation_time  : float = 0.0                                          # ║
                                                                            # ║
@dataclass                                                                  # ║
class InputState:                                                           # ║
    """Tracks raw input between frames."""                                  # ║
    is_dragging    : bool = False                                           # ║
    previous_mouse : Any = None                                             # ║
                                                                            # ║
 # ═══════════════════════════════════════════════════════════════════════════╝

class SimState:
    """
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
        self.hud      = init_hud(self.bodies)
        self.render   = RenderState()
        self.sim      = SimulationState()
        self.input    = InputState()
        self.substeps = 32

        self.font     = rl.load_font("assets/fonts/CaskaydiaCoveNerdFontMono-Regular.ttf")

    def reset(self):
        """Reset simulation back to initial conditions."""
        self.bodies  = Body.create_all()
        self.hud     = init_hud(self.bodies)
        self.sim     = SimulationState()

