"""
!important
this script needs raylib and pyray pip packages to run

I have created a virtual environment with the required
packages for my own needs. ./python-venv/

run: source ./python-venv/bin/activate(.csh, .fish,)
currently untested on windows
"""
import math
import pyray as rl
import utils.definitions as def
        


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
    ## -- Helper Functions --
    ## -----------------------
    
    def add_line(self, A: Point, B: Point):
        """Add line and check for polygon closure"""
        new_line = StraightLine(A, B)
        self.lines.append(new_line)
        print(f"Line Created at: {new_line}")

        polygon = self.detect_polygon()
        if polygon:
            surface = PlaneSurface(polygon)
            print(f"Surface created at: {surface}")
        return new_line

    def detect_polygon(self):
        # each line should only have 2 points connected to it
        if len(self.lines) < 3:
            return None
        
        # adjacency map:
        adjacency = {}
        for line in self.lines:
            adjacency.setdefault(line.A, []).append(line.B)
            adjacency.setdefault(line.B, []).append(line.A)

        for start in adjacency:
            path = [start]
            if self._walk_cycle(start, start, adjacency, path):
                return [StraightLine(path[i], path[i+1]) for i in range(len(path)-1)]
        return None

        def _walk_cycle(self, current, target, adjacency, path):
            """DFS walk to find cycle."""
            for neighbor in adjacency[current]:
                if neighbor == target and len(path) >= 3:
                    path.append(neighbor)
                    return True
                if neighbor not in path:
                    path.append(neighbor)
                    if self._walk_cycle(neighbor, target, adjacency, path):
                        return True
                    path.pop()
            return False 

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
    # def update(self):
    #
    #     mx, my = rl.get_mouse_x(), rl.get_mouse_y()
    #
    #
    #     if self.line_start_point and not hovered_point:
    #         self.preview_line = StraightLine(self.line_start_point, Point(mx, my))
    #
    #     if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
    #         # if hovering a point
    #         if hovered_point:
    #             if not self.line_start_point:
    #                 # Clicked on hovered point, start new line
    #                 self.line_start_point = hovered_point
    #                 print(f"Line started from: {hovered_point}")
    #             elif self.line_start_point != hovered_point:
    #                 # Complete the line
    #                 new_line = StraightLine(self.line_start_point, hovered_point)
    #                 self.lines.append(new_line)
    #                 print(f"Line created: {new_line}")
    #                 self.line_start_point = None
    #                 self.preview_line = None
    #             else:
    #                 # Clicked the same point, cancel
    #                 self.line_start_point = None
    #                 print("Line creation cancelled")
    #         else:
    #             # clicked empty space, create new point
    #             new_point = Point(mx, my)
    #             self.points.append(new_point)
    #             print(f"Point created at: {new_point}")

    def update(self):
        # Draw all points
        for p in self.points:
            # highlight if hovered
            if p.is_hovered(self.hovered_point):
                p.draw(color=rl.ORANGE, radis=8)
            else:
                p.draw()

        # Draw all lines
        for line in self.lines:
            ine.draw()

        # Mouse input
        if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
            mx, my = rl.get_mouse_x(), rl.get_mouse_y()
            clicked_point = None

            # did we click on an existing point?
            for p in self.points:
                if p.is_hovered(rl.get_mouse_position):
                    clicked_point = p
                    break

            if clicked_point:
                # select/deselect points for line creation
                if self.selected_point is None:
                    self.selected_point = clicked_point
                    print("Selected {clicked_point}")
                else:
                    if self.selected_point != clicked_point:
                        # create a line between two selected points
                        self.add_line(self.selected_point, clicked_point)
                    self.selected_point = None # reset after use
            else:
                # no point clicked -> create a new point
                new_point = Point(mx, my)
                self.points.append(new_point)
                print(r"Point created: {new_point}")

    ## ----------
    ## -- Draw --
    ## ----------

    def draw(self):
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)

        mx, my = rl.get_mouse_x(), rl.get_mouse_y()

        # draw lines
        for line in self.lines:
            line.draw()

        # draw preview line
        if self.preview_line:
            self.preview_line.draw(rl.BLUE, 1)

        # Draw points
        for p in self.points:

            # Highlight hovered point
            if p.is_hovered:
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
