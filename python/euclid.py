import math
import pyray as rl


# ---- Definitions ----

## -----------
## -- Point --
## -----------

class Point():
    """
    a point is that which has no parts,
    it has position
    """
    def __init__(self, x: float, y: float):
        # initialization
        self.x = x
        self.y = y

    def __repr__(self):
        # string representation
        return f"Point({self.x}, {self.y})" # debug print

    def draw(self, rl.RED: color):
        # draw with raylib
        rl.draw_circle(int(self.x), int(self.y), 5, color)

## ----------
## -- Line --
## ----------

class Line():
    """
    any type of line
    a line is breadthless length
    """

    # so far, this object is simply here for difinition
    # TODO: line type implementation

    pass

class StraightLine(Line):
    """
    A straight line lies evenly with
    the points on itself.
    It is breathless length.
    Its extremities are points
    """
    def __init__( self, A: Point, B: Point):
        # initialization
        self.A = A
        self.B = B

    def __repr__(self):
        # string representation
        return f"Straight Line: {self.A}, {self.B}" # debug print

    def length(self) -> float:
        # Pythagorean theorum used to find length
        return ((self.B.x - self.A.x) ** 2 + (self.B.y - self.A.y) ** 2) ** 0.5 # √((Bx - Ax)² + (By - Ay)²)

    def draw(self, rl.BLACK: color):
        # draw with raylib
        rl.draw_line(int(self.A.x), int(self.A.y), int(self.B.x), int(self.B.y), color)


## -------------
## -- Surface --
## -------------

class Surface():
    """
    A surface is that which has length and breadth only
    Its extremities are lines
    """

    def __init__(self, boundaries: list[Line]):
        self.boundaries = boundaries

    def __repr__(self):
        return f"Surface(boundaries={self.boundaries}"

class PlaneSurface(Surface):
    """
    a flat surface
    """
    def __init__(self, boundaries: list[StraightLine]):
        super().__init__(boundaries)

## -----------
## -- Angle --
## -----------

class Angle:
    """
    the inclination of two lines which
    meet each other but do not have the same direction
    """
    def __init__(self, AB: StraightLine, AC: StraightLine):
        if AB.A != AC.A:
            raise ValueError("Lines must share a common point to create an angle")
        self.vertex = AB.A
        self.AB = AB
        self.AC = AC

    def measure(self) -> float:
        """return angle in degrees"""
        v1 = (self.AB.B.x - self.AB.A.x, self.AB.B.y - self.AB.A.y) # TODO: function to calc vectors
        v2 = (self.AC.B.x - self.AC.A.x, self.AC.B.y - self.AC.A.y)
        dot_product = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = (v1[0]**2 + v1[1]**2) ** 0.5 # TODO: function to calculate magnitude
        mag2 = (v2[0]**2 + v2[1]**2) ** 0.5
        cos_theta = dot_product / (mag1 * mag2)
        return math.degrees(math.acos(cos_theta))

    def __repr___(self):
        return f"Angle({self.AB}, {self.AC}"
