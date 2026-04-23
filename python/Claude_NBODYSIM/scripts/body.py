"""
╔══════════════════════════════════════════════════════════════╗
║  body.py                                                     ║
║  Body class, presets, factory — the simulatable unit         ║
╚══════════════════════════════════════════════════════════════╝
"""

import uuid
from utils.colors  import *
from utils.vector3D import Vector3D


# ══ Presets ═════════════════════════════════════════════════════════════════════════════════╗  TODO: move this block to systemgen.py
                                                                                            # ║
def figure_8():                                                                             # ║
    # Choreographic figure-8 solution (Chenciner & Montgomery, 2000)                        # ║
    # positions and velocities are scaled for screen-space                                  # ║
    scale_pos = 90                                                                          # ║
    scale_vel = 0.35                                                                        # ║
    return [                                                                                # ║
        dict(                                                                               # ║
            position    = Vector3D(-0.97000436 * scale_pos,  0.24308753 * scale_pos, 0),    # ║
            velocity    = Vector3D( 0.46620368 * scale_vel,  0.43236573 * scale_vel, 0),    # ║
            radius      = 8,                                                                # ║
            mass        = 1000,                                                             # ║
            color       = BODY_COLS[0],                                                     # ║
            trail_color = TRAIL_COLS[0],                                                    # ║
        ),                                                                                  # ║
        dict(                                                                               # ║
            position    = Vector3D( 0.97000436 * scale_pos, -0.24308753 * scale_pos, 0),    # ║
            velocity    = Vector3D( 0.46620368 * scale_vel,  0.43236573 * scale_vel, 0),    # ║
            radius      = 8,                                                                # ║
            mass        = 1000,                                                             # ║
            color       = BODY_COLS[1],                                                     # ║
            trail_color = TRAIL_COLS[1],                                                    # ║
        ),                                                                                  # ║
        dict(                                                                               # ║
            position    = Vector3D(0, 0, 0),                                                # ║
            velocity    = Vector3D(-0.93240737 * scale_vel, -0.86473146 * scale_vel, 0),    # ║
            radius      = 8,                                                                # ║
            mass        = 1000,                                                             # ║
            color       = BODY_COLS[2],                                                     # ║
            trail_color = TRAIL_COLS[2],                                                    # ║
        ),                                                                                  # ║
    ]                                                                                       # ║
                                                                                            # ║
def default_bodies():                                                                       # ║
    return [                                                                                # ║
        dict(                                                                               # ║
            position    = Vector3D(25, 30, 100),                                            # ║
            velocity    = Vector3D(0, 0, 0),                                                # ║
            radius      = 10,                                                               # ║
            mass        = 1000,                                                             # ║
            color       = BODY_COLS[0],                                                     # ║
            trail_color = TRAIL_COLS[0],                                                    # ║
        ),                                                                                  # ║
        dict(                                                                               # ║
            position    = Vector3D(80, -70, 60),                                            # ║
            velocity    = Vector3D(0, 0, 0),                                                # ║
            radius      = 8,                                                                # ║
            mass        = 2000,                                                             # ║
            color       = BODY_COLS[1],                                                     # ║
            trail_color = TRAIL_COLS[1],                                                    # ║
        ),                                                                                  # ║
        dict(                                                                               # ║
            position    = Vector3D(0, 0, 0),                                                # ║
            velocity    = Vector3D(0, 0, 0),                                                # ║
            radius      = 20,                                                               # ║
            mass        = 3000,                                                             # ║
            color       = BODY_COLS[2],                                                     # ║
            trail_color = TRAIL_COLS[2],                                                    # ║
        ),                                                                                  # ║
    ]                                                                                       # ║
                                                                                            # ║
# ════════════════════════════════════════════════════════════════════════════════════════════╝


# ══ Body ════════════════════════════════════════════════════════════════════════════════╗
                                                                                        # ║
class Body:                                                                             # ║
                                                                                        # ║
    def __init__(self, name, position, velocity, mass, radius, color, trail_color):     # ║
        self.name        = name                                                         # ║
        self.id          = str(uuid.uuid4())                                            # ║
        self.position    = position                                                     # ║
        self.velocity    = velocity                                                     # ║
        self.mass        = mass                                                         # ║
        self.radius      = radius                                                       # ║
        self.color       = color                                                        # ║
        self.trail_color = trail_color                                                  # ║
        self.forces      = []                                                           # ║
        self.trail       = []                                                           # ║
                                                                                        # ║
    # ── Properties ───────────────────────────────────────────────────────             # ║
    @property                                                                           # ║
    def direction(self):                                                                # ║
        return self.velocity.normalize()                                                # ║
                                                                                        # ║
    # ── Factory ──────────────────────────────────────────────────────────             # ║
    @classmethod                                                                        # ║
    def create_all(cls, system=None):                                                   # ║
        # defaults to default_bodies() if no system preset is passed                    # ║
        if system is None:                                                              # ║
            system = default_bodies()                                                   # ║
        return [cls(name=f"b{i+1}", **body_data) for i, body_data in enumerate(system)] # ║
                                                                                        # ║
# ════════════════════════════════════════════════════════════════════════════════════════╝
