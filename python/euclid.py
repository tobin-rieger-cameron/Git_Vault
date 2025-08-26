# ---- Definitions ----

class Point():
    """
    a point is that which has no parts,
    it has position
    """
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point({self.x}, {self.y})" # debug print

class Line():
    """
    A straight line lies evenly with
    the points on itself.
    It is breathless length.
    """
    def __init__( self, A: Point, B: Point):
        if A == B:
            raise ValueError("A straight line requires two distinct points")
        self.A = A
        self.B = B

    def __repr__(self):
        return f"Straight Line: {self.A}, {self.B}" # debug print

    def length(self) -> float:
        # Pythagorean theorum used to find length
        return ((self.B.x - self.A.x)^2 + (self.B.y - self.A.y)^2) ** 0.5 # √((Bx - Ax)² + (By - Ay)²)

