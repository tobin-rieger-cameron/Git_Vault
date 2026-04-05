# scripts/body.py

from utils.colors import *
from utils.vector3D import Vector3D

def figure_8():
    scale_pos = 90
    scale_vel = 0.35  # sqrt(0.01)

    return [
        dict(
            position = Vector3D(-0.97000436 * scale_pos,  0.24308753 * scale_pos, 0),
            velocity = Vector3D( 0.4662036850 * scale_vel,  0.4323657300 * scale_vel, 0),
            radius = 8,
            mass = 1000,
            color = BODY_COLS[0],
            trail_color = TRAIL_COLS[0],
        ),

        dict(
            position = Vector3D( 0.97000436 * scale_pos, -0.24308753 * scale_pos, 0),
            velocity = Vector3D( 0.4662036850 * scale_vel,  0.4323657300 * scale_vel, 0),
            radius = 8,
            mass = 1000,
            color = BODY_COLS[1],
            trail_color = TRAIL_COLS[1],
        ),

        dict(
            position = Vector3D(0, 0, 0),
            velocity = Vector3D(-0.93240737 * scale_vel, -0.86473146 * scale_vel, 0),
            radius = 8,
            mass = 1000,
            color = BODY_COLS[2],
            trail_color = TRAIL_COLS[2],
        ),
    ]


def default_bodies():
    return [
        dict(
            position = Vector3D(25, 30, 100),
            velocity = Vector3D(0, 0, 0),
            radius = 10,
            mass = 1000,
            color = BODY_COLS[0],
            trail_color = TRAIL_COLS[0],
        ),

        dict(
            position = Vector3D(80, -70, 60),
            velocity = Vector3D(0, 0, 0),
            radius = 8,
            mass = 2000,
            color = BODY_COLS[1],
            trail_color = TRAIL_COLS[1],
        ),

        dict(
            position = Vector3D(0, 0, 0),
            velocity = Vector3D(0, 0, 0),
            radius = 20,
            mass = 3000,
            color = BODY_COLS[2],
            trail_color = TRAIL_COLS[2],
        ),
    ]

class Body:
    def __init__(
        self,
        name,
        position,
        velocity,
        mass,
        radius,
        color,
        trail_color,
    ):
        self.name = name
        self.position = position
        self.velocity = velocity
        self.mass = mass
        self.radius = radius
        self.forces = []

        self.color = color
        self.trail_color = trail_color
        self.trail = []

    @property
    def direction(self):
        return self.velocity.normalize()

    @classmethod
    def create_all(cls, system=None):
        if system is None:
            system = default_bodies()
        return [cls(name=f"b{i+1}", **body_data) for i, body_data in enumerate(system)]
