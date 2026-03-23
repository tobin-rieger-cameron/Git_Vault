# utils/vector3d.py
import math


class Vector3D:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z
    
    # ── arithmetic operators ──────────────────────────────────────────────────
    def __add__(self, other):
        return Vector3D( self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3D( self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vector3D( self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    def __neg__(self):
        return Vector3D(-self.x, -self.y, -self.z)


    # ── vector operations ─---─────────────────────────────────────────────────
    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def scale(self, scalar):
        return self.__mul__(scalar)

    def length(self):
        return math.hypot(self.x, self.y, self.z)

    def length_squared(self):
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalize(self):
        magnitude = self.length()
        if magnitude < 1e-12:
            return Vector3D(0.0, 0.0, 0.0)
        return self.__mul__(1.0 / magnitude)

    def distance_to(self, other):
        return (self - other).length()


    # ── display ─────────────────────────────────────────────────────-───────
    def __str__(self):
        return f"Vector3D({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    def __repr__(self):
        return self.__str__()
