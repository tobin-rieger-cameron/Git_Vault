# utils/vector3D.py
import math


class Vector3D:
    """
    A Vector3D is a container for x, y, z
    represents a point or direction in 3D space.
    used for things like:

    a body's position (where it is in the world)
    a body's velocity (how fast and which direction it's moving)
    a force acting on a body (magnitude + direction)

    should to be able to write natural expressions like:
    (a + b) or (a * 2.5) instead of calling helper functions every time.
    Python lets you do that with dunder methods
    (double-underscore methods)
    """

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    # print(v1)
    def __repr__(self):
        return f"Vector3D({self.x}, {self.y}, {self.z})"

    # v1 + v2
    def __add__(self, other):
        return Vector3D(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z
        )

    # v1 += v2
    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        self.z += other.z
        return self

    # v1 - v2
    def __sub__(self, other):
        return Vector3D(
            self.x - other.x,
            self.y - other.y,
            self.z - other.z
        )

    #TODO: ADD INCREMENTAL SUBTRACTION, MULTIPLICATION

    # v1 * x
    def __mul__(self, scalar):
        return Vector3D(
            self.x * scalar,
            self.y * scalar,
            self.z * scalar
        )

    # x * v1
    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    # v1 / x
    def __truediv__(self, scalar):
        return Vector3D(
            self.x / scalar,
            self.y / scalar,
            self.z / scalar
        )

    # -v1
    def __neg__(self):
        return Vector3D(
            -self.x,
            -self.y,
            -self.z
        )

    # v1.dot(v2)
    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    # v1.cross(v2)
    def cross(self, other):
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    # v1.length()
    def length(self):
        return math.hypot(self.x, self.y, self.z)

    # v1.length_squared()
    def length_squared(self):
        return self.x**2 + self.y**2 + self.z**2

    # v1.normalize()
    def normalize(self):
        ln = self.length()
        if ln == 0:
            return Vector3D(0, 0, 0)
        # unit vector (length = 1)
        return Vector3D(self.x / ln, self.y / ln, self.z / ln)

    # v1.distance_to(v2)
    def distance_to(self, other):
        return (other - self).length()

    # v1.scale(x)
    def scale(self, scalar):
        return self.__mul__(scalar)

    # v1.copy()
    def copy(self):
        return Vector3D(self.x, self.y, self.z)
