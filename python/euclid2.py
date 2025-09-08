"""
Enhanced control schemes for the Euclidean Geometry application

!important
this script needs raylib and pyray pip packages to run

I have created a virtual environment with the required
packages for my own needs. ./python-venv/

run: source ./python-venv/bin/activate(.csh, .fish,)
"""
import math
import pyray as rl

# ---- Definitions ----

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

    def is_hovered(self, mx, my, radius=8):
        return (self.x - mx) ** 2 + (self.y - my) ** 2 <= radius ** 2

    def draw(self, color=rl.RED, radius=5):
        # draw with raylib
        rl.draw_circle(int(self.x), int(self.y), radius, color)

class Line():
    """
    any type of line
    a line is breadthless length
    """
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

    def draw(self, color=rl.BLACK, thickness=2):
        # draw with raylib
        rl.draw_line_ex(rl.Vector2(self.A.x, self.A.y), rl.Vector2(self.B.x, self.B.y), thickness, color)

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

# ---- Application Framework ----

class GeometryApp:
    def __init__(self, width = 1280, height = 720, title = "Euclidean Geometry"):
        self.width = width
        self.height = height
        self.title = title

        self.points: list[Point] = []
        self.lines: list[StraightLine] = []
        
        # Control state
        self.mode = "POINT"  # POINT, LINE, SELECT
        self.selected_point = None
        self.line_start_point = None
        self.preview_line = None
        
        # UI colors
        self.hover_color = rl.ORANGE
        self.selected_color = rl.GREEN
        self.preview_color = rl.GRAY

    def run(self):
        rl.init_window(self.width, self.height, self.title)
        rl.set_target_fps(60)
        
        print("Window initialized, starting main loop...")
        print("Controls:")
        print("  TAB - Switch between POINT, LINE, and SELECT modes")
        print("  POINT mode: Left click to add points")
        print("  LINE mode: Click two points to create a line")
        print("  SELECT mode: Click to select/deselect points")
        print("  ESC - Cancel current operation")
        print("  DELETE/BACKSPACE - Delete selected point")
        
        while not rl.window_should_close():
            self.update()
            self.draw()

        rl.close_window()
        print("Window closed")

    def get_hovered_point(self, mx, my):
        """Find the point under the mouse cursor"""
        for point in self.points:
            if point.is_hovered(mx, my):
                return point
        return None

    def update(self):
        mx, my = rl.get_mouse_x(), rl.get_mouse_y()
        
        # Mode switching with TAB
        if rl.is_key_pressed(rl.KEY_TAB):
            modes = ["POINT", "LINE", "SELECT"]
            current_index = modes.index(self.mode)
            self.mode = modes[(current_index + 1) % len(modes)]
            self.selected_point = None
            self.line_start_point = None
            self.preview_line = None
            print(f"Switched to {self.mode} mode")

        # Cancel operation with ESC
        if rl.is_key_pressed(rl.KEY_ESCAPE):
            self.selected_point = None
            self.line_start_point = None
            self.preview_line = None
            print("Operation cancelled")

        # Delete selected point
        if (rl.is_key_pressed(rl.KEY_DELETE) or rl.is_key_pressed(rl.KEY_BACKSPACE)) and self.selected_point:
            # Remove lines connected to this point
            self.lines = [line for line in self.lines if line.A != self.selected_point and line.B != self.selected_point]
            # Remove the point
            self.points.remove(self.selected_point)
            self.selected_point = None
            print("Point deleted")

        # Handle different modes
        if self.mode == "POINT":
            self.handle_point_mode(mx, my)
        elif self.mode == "LINE":
            self.handle_line_mode(mx, my)
        elif self.mode == "SELECT":
            self.handle_select_mode(mx, my)

    def handle_point_mode(self, mx, my):
        """Handle point creation mode"""
        if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
            # Don't create a point if clicking on an existing one
            if not self.get_hovered_point(mx, my):
                new_point = Point(mx, my)
                self.points.append(new_point)
                print(f"Point created at: {new_point}")

    def handle_line_mode(self, mx, my):
        """Handle line creation mode"""
        hovered_point = self.get_hovered_point(mx, my)
        
        # Update preview line
        if self.line_start_point and not hovered_point:
            self.preview_line = StraightLine(self.line_start_point, Point(mx, my))
        else:
            self.preview_line = None

        if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
            if hovered_point:
                if not self.line_start_point:
                    # Start a new line
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
                # Clicked empty space, cancel line creation
                self.line_start_point = None
                print("Line creation cancelled")

    def handle_select_mode(self, mx, my):
        """Handle selection mode"""
        if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
            hovered_point = self.get_hovered_point(mx, my)
            if hovered_point:
                if self.selected_point == hovered_point:
                    # Deselect if clicking the same point
                    self.selected_point = None
                    print("Point deselected")
                else:
                    # Select the new point
                    self.selected_point = hovered_point
                    print(f"Point selected: {hovered_point}")
            else:
                # Clicked empty space, deselect
                self.selected_point = None
                print("Selection cleared")

    def draw(self):
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)
        
        mx, my = rl.get_mouse_x(), rl.get_mouse_y()
        hovered_point = self.get_hovered_point(mx, my)

        # Draw lines
        for line in self.lines:
            line.draw()

        # Draw preview line
        if self.preview_line:
            self.preview_line.draw(self.preview_color, 1)

        # Draw points
        for point in self.points:
            color = rl.RED
            radius = 5
            
            # Highlight hovered points
            if point == hovered_point:
                color = self.hover_color
                radius = 7
            
            # Highlight selected point
            if point == self.selected_point:
                color = self.selected_color
                radius = 8
            
            # Highlight line start point
            if point == self.line_start_point:
                color = rl.BLUE
                radius = 8
            
            point.draw(color, radius)

        # Draw UI
        self.draw_ui()

        rl.end_drawing()

    def draw_ui(self):
        """Draw user interface elements"""
        # Mode indicator
        mode_text = f"Mode: {self.mode}"
        rl.draw_text(mode_text, 10, 10, 20, rl.BLACK)
        
        # Instructions based on mode
        instruction_y = 35
        if self.mode == "POINT":
            rl.draw_text("Left click: Add point", 10, instruction_y, 16, rl.DARKGRAY)
        elif self.mode == "LINE":
            if self.line_start_point:
                rl.draw_text("Click another point to complete line", 10, instruction_y, 16, rl.DARKGRAY)
            else:
                rl.draw_text("Click a point to start line", 10, instruction_y, 16, rl.DARKGRAY)
        elif self.mode == "SELECT":
            rl.draw_text("Click point to select/deselect", 10, instruction_y, 16, rl.DARKGRAY)
        
        # Controls
        controls_y = self.height - 80
        rl.draw_text("TAB: Switch mode | ESC: Cancel | DEL: Delete selected", 10, controls_y, 14, rl.DARKGRAY)

if __name__ == "__main__":
    print("Starting enhanced geometry application...")
    app = GeometryApp()
    app.run()
