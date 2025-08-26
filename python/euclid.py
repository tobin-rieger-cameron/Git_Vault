
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
    def __init__( self, A: Point, B: Point):
        if A == B:
            raise ValueError("A straight line requires two distinct points")
        self.A = A
        self.B = B

    def __repr__

