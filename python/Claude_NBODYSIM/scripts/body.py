# scripts/body.py

from utils.colors import *
from utils.vector3D import Vector3D

DEFAULT_BODIES = [
    dict(
        position = Vector3D(25, 30, 100),
        velocity = Vector3D(0, 0, 0),
        mass = 1000, radius = 10,
        color = BODY_COLS[0],
        trail_color = TRAIL_COLS[0],
    ),

    dict(
        position = Vector3D(80, -70, 60),
        velocity = Vector3D(0, 0, 0),
        mass = 2000, radius = 8,
        color = BODY_COLS[1],
        trail_color = TRAIL_COLS[1],
    ),

    dict(
        position = Vector3D(0, 0, 0),
        velocity = Vector3D(0, 0, 0),
        mass = 3000, radius = 20,
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
    # create_all needs to build Body objects, so it can't be a regular instance method
    def create_all(cls, system=DEFAULT_BODIES):
        return [cls(name=f"b{i+1}", **body_data) for i, body_data in enumerate(system)]
