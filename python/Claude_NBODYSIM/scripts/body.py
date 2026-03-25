# scripts/body.py

from utils.colors import *
from utils.vector3D import Vector3D

class Body:
    def __init__(
        self,
        position,
        velocity,
        mass,
        radius,
        color,
        trail_color,
    ):
        self.position = position
        self.velocity = velocity
        self.mass = mass
        self.radius = radius
        self.color = color
        self.trail_color = trail_color
        self.trail = []
        self.forces = []

    @classmethod
    # create_all needs to build Body objects, so it can't be a regular instance method
    def create_all(cls, initial_states):
        return [
            cls(
                position = Vector3D(10, 10, 10),
                velocity = Vector3D(10, 10, 10),
                mass = 10, radius = 10,
                color = BODY_COLS[0],
                trail_color = TRAIL_COLS[0],
            ),

            cls(
                position = Vector3D(20, 20, 20),
                velocity = Vector3D(20, 20, 20),
                mass = 20, radius = 20,
                color = BODY_COLS[1],
                trail_color = TRAIL_COLS[1],
            ),

            cls(
                position = Vector3D(30, 30, 30),
                velocity = Vector3D(30, 30, 30),
                mass = 30, radius = 30,
                color = BODY_COLS[2],
                trail_color = TRAIL_COLS[2],
            ),
        ]
