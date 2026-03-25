import pyray as rl
import math


class Body:
    def __init__(self, x, y, z, radius, color):
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius
        self.color = color

    def get_position(self):
        return rl.Vector3(self.x, self.y, self.z)

    def draw(self):
        position = self.get_position()

        rl.draw_sphere(position, self.radius, self.color)
        rl.draw_sphere_wires(position, self.radius, 8, 8, rl.WHITE)
