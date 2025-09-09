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
    def __init__(self, x: float, y: float, radius=5, color=rl.RED):
        # initialization
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color

    def __repr__(self):
        # debug string representation
        return f"Point({self.x}, {self.y})"

    def is_hovered(self, mx, my):
        # distance check
        return (self.x - mx) ** 2 + (self.y - my) ** 2 <= self.radius ** 3

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

    def add_line():

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

    def draw(self, color=rl.BLACK, thickness=2):
        # draw with raylib
        # rl.draw_line(int(self.A.x), int(self.A.y), int(self.B.x), int(self.B.y), color)
        rl.draw_line_ex(rl.Vector2(self.A.x, self.A.y), rl.Vector2(self.B.x, self.B.y), thickness, color)


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
        v1 = (self.AB.B.x - self.AB.A.x, self.AB.B.y - self.AB.A.y)
        v2 = (self.AC.B.x - self.AC.A.x, self.AC.B.y - self.AC.A.y)
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
        


# ---- Application Framework ----

class GeometryApp:
    def __init__(self, width = 1280, height = 720, title = "Euclidean Geometry"):
        self.width = width
        self.height = height
        self.title = title

        # Object lists
        self.points: list[Point] = []
        self.lines: list[StraightLine] = []

        self.mode = None # POINT, LINE, SURFACE,
        self.preview_line = None
        self.hovered_point = None
        self.line_start_point = None

    ## -----------------------
    ## -- Get hovered point --
    ## -----------------------
    def get_hovered_point(self, mx, my):
        """find point under ouse cursor"""
        for point in self.points:
            if point.is_hovered(mx, my):
                return point
    
    ## ---------
    ## -- Run --
    ## ---------
    def run(self):
        rl.init_window(self.width, self.height, self.title)
        rl.set_target_fps(60)
        
        print("Window initialized, starting main loop...")
        while not rl.window_should_close():
            self.update()
            self.draw()

        rl.close_window()
        print("Window closed")


    ## ------------
    ## -- Update --
    ## ------------
    def update(self):

        mx, my = rl.get_mouse_x(), rl.get_mouse_y()
        hovered_point = self.get_hovered_point(mx, my)


        if self.line_start_point and not hovered_point:
            self.preview_line = StraightLine(self.line_start_point, Point(mx, my))

        if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
            # if hovering a point
            if hovered_point:
                if not self.line_start_point:
                    # Clicked on hovered point, start new line
                    self.line_start_point = hovered_point
                    print(f"Line started from: {hovered_point}")
                elif self.line_start_point != hovered_point:
                    # Complete the line
                    new_line = StraightLine(self.line_start_point, hovered_point)
                    self.lines.append(new_line)
                    print(f"Line created: {new_line}")
                    self.line_start_point = None
                    self.preview_line = None
                else:
                    # Clicked the same point, cancel
                    self.line_start_point = None
                    print("Line creation cancelled")
            else:
                # clicked empty space, create new point
                new_point = Point(mx, my)
                self.points.append(new_point)
                print(f"Point created at: {new_point}")

    ## ----------
    ## -- Draw --
    ## ----------

    def draw(self):
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)

        mx, my = rl.get_mouse_x(), rl.get_mouse_y()
        hovered_point = self.get_hovered_point(mx, my)

        # draw lines
        for line in self.lines:
            line.draw()

        # draw preview line
        if self.preview_line:
            self.preview_line.draw(rl.BLUE, 1)

        # Draw points
        for p in self.points:

            # Highlight hovered point
            if p == self.hovered_point:
                color = rl.ORANGE
                radus = 8

            # Highlihgt line start point
            if p == self.line_start_point:
                color = rl.BLUE
                radius = 8

            p.draw()

        rl.end_drawing()

if __name__ == "__main__":
    print("Starting application...")
    app = GeometryApp()
    app.run()
