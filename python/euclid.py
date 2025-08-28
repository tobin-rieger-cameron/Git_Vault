"""
!important
this script needs raylib and pyray pip packages to run

I have created a virtual environment with the required
packages for my own needs. ./python-venv/

run: source ./python-venv/bin/activate(.csh, .fish,)
"""
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

    def is_hovered(self, mx, my):
        return (self.x - mx) ** 2 + (self.y - my) ** 2 <= 5 ** 2

    def draw(self, color=rl.RED):
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

    def draw(self, color=rl.BLACK):
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

    def __repr__(self):
        return f"Angle({self.AB}, {self.AC}"

    def measure(self) -> float:
        """return angle in degrees"""
        v1 = (self.AB.B.x - self.AB.A.x, self.AB.B.y - self.AB.A.y) # TODO: function to calc vectors
        v2 = (self.AC.B.x - self.AC.A.x, self.AC.B.y - self.AC.A.y)
        dot_product = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = (v1[0]**2 + v1[1]**2) ** 0.5 # TODO: function to calculate magnitude
        mag2 = (v2[0]**2 + v2[1]**2) ** 0.5
        cos_theta = dot_product / (mag1 * mag2)
        return math.degrees(math.acos(cos_theta))



# ---- Application Framework ----

class GeometryApp:
    def __init__(self, width = 1280, height = 720, title = "Euclidean Geometry"):
        self.width = width
        self.height = height
        self.title = title

        self.points: list[Point] = []
        self.lines: list[StraightLine] = []

    def run(self):
        rl.init_window(self.width, self.height, self.title)
        rl.set_target_fps(60)
        
        print("Window initialized, starting main loop...")
        while not rl.window_should_close():
            self.update()
            self.draw()

        rl.close_window()
        print("Window closed")

    def update(self):
        # left click to add a point
        if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
            mx, my = rl.get_mouse_x(), rl.get_mouse_y()
            self.points.append(Point(mx, my))
            print(f"point created at:({Point(mx, my)})")

            # for now, automatically create a line between two points
            #if len(self.points) >= 2:
            #    self.lines.append(StraightLine(self.points[-2], self.points[-1]))

        if rl.is_mouse_button_pressed(rl.MOUSE_RIGHT_BUTTON):
            mx, my = rl.get_mouse_x(), rl.get_mouse_y()
            mouse_point = Point(mx, my)
            self.lines.append(StraightLine(mouse_point, self.points[-1]))
            print(f"line created from {mouse_point} to {self.points[-1]}")

    def draw(self):
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)

        for line in self.lines:
            line.draw()


        for p in self.points:
            p.draw()

        rl.end_drawing()

if __name__ == "__main__":
    print("Starting application...")
    app = GeometryApp()
    app.run()
