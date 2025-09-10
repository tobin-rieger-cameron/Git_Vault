
# ../utils/definitions.py
"""
this script is for object definitions only
"""


## -----------
## -- Point --
## -----------
class Point():
    """
    a point is that which has no parts,
    it has position
    """
    def __init__(self, x: float, y: float, radius=5, color=rl.RED):
        # initialization
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color

    def __repr__(self):
        # string representation
        return f"Point({self.x}, {self.y})" # debug print

    def draw(self):
        # draw with raylib
        rl.draw_circle(int(self.x), int(self.y), self.radius, self.color)

## ----------
## -- Line --
## ----------
class Line():
    """
    a line is breadthless length
    """
    # so far, this object is simply here for difinition
    # TODO: line type implementation: curved, infinite, cissoid


class StraightLine(Line):
    """
    A straight line lies evenly with the points on itself.
    It is breathless length.
    Its extremities are points.
    """
    def __init__( self, A: Point, B: Point):
        # initialization
        self.A = A
        self.B = B

    def __repr__(self):
        # string representation
        return f"Straight Line: {self.A}, {self.B}" # debug print

    def length(self) -> float:
        # distance between two points, with pythagorean theorum
        return math.sqrt((self.B.x - self.A.x) ** 2 + (self.B.y - self.A.y) ** 2) # √((Bx - Ax)² + (By - Ay)²)
 g
    def connects(self, point: Point) ->  bool:
        # checks for connections
        return self.A == point or self.B == point

    def other_point(self, point: Point) -> Point:
        """Return other endpoint if point is part of a line"""
        if point == self.A:
            return self.B
        elif point == self.B:
            return self.A
        else:
            raise ValueError(f"{point} not on this line")

    def draw(self, color=rl.BLACK, thickness=2):
        # draw with raylib
        # rl.draw_line(int(self.A.x), int(self.A.y), int(self.B.x), int(self.B.y), color)
        rl.draw_line_ex(rl.Vector2(self.A.x, self.A.y), 
                        rl.Vector2(self.B.x, self.B.y), 
                        thickness, color)


## -------------
## -- Surface --
## -------------
class Surface():
    """
    A surface is that which has length and breadth only
    Its extremities are lines
    """
    def __init__(self, length, width, area, position: Point(), perimeter: list[Line]):
        self.length = length
        self.width = width
        self.area = length * width
        self.position = position # center point
        self.perimeter = length * 2 + width * 2

    def __repr__(self):
        return f"Surface(perimeter={self.perimeter}" #TODO:

class PlaneSurface(Surface): #TODO:
    """
    a flat surface lies evenly with all the points in itself
    """
    def __init__(self):




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

    def __repr__(self):
        return f"Angle({self.AB}, {self.AC}"

    def measure(self) -> float:
        """return angle in degrees"""
        v1 = (self.AB.B.x - self.AB.A.x, self.AB.B.y - self.AB.A.y) # vector 1
        v2 = (self.AC.B.x - self.AC.A.x, self.AC.B.y - self.AC.A.y) # vector 2
        dot_product = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = (v1[0]**2 + v1[1]**2) ** 0.5
        mag2 = (v2[0]**2 + v2[1]**2) ** 0.5
        cos_theta = dot_product / (mag1 * mag2)
        return math.degrees(math.acos(cos_theta))

    def get_type(self):
        """check if angle is acute or obtuse"""
        pass

    def draw(self, color=rl.RED, thickness=2):
        """draw a curved line to represent the angle"""
        pass
