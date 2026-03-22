# pip install pyray
# pip install raylib

# python/main.py
"""
working demo created by claude to test function utility

ties together utils and scrips to be
visually represented on the screen
"""

import pyray as rl
from utils.definitions import Point, StraightLine, Angle
import threading
import queue
import math

# screen dimensions set as constants for now
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800


class ConsoleCommand:
    """Handles console command parsing and execution"""
    
    def __init__(self, window):
        self.window = window
        self.objects = {}  # Store created objects by name
        self.command_queue = queue.Queue()
        self.running = True
        
    def parse_command(self, command):
        """Parse and execute console commands"""
        parts = command.strip().split()
        if not parts:
            return
            
        cmd = parts[0].lower()
        
        try:
            if cmd == "point":
                self.create_point(parts[1:])
            elif cmd == "line":
                self.create_line(parts[1:])
            elif cmd == "angle":
                self.create_angle(parts[1:])
            elif cmd == "move":
                self.move_object(parts[1:])
            elif cmd == "list":
                self.list_objects()
            elif cmd == "delete":
                self.delete_object(parts[1:])
            elif cmd == "clear":
                self.clear_objects()
            elif cmd == "help":
                self.show_help()
            else:
                print(f"Unknown command: {cmd}. Type 'help' for available commands.")
        except Exception as e:
            print(f"Error executing command: {e}")
    
    def create_point(self, args):
        """Create a point: point <name> <x> <y> [radius] [color]"""
        if len(args) < 3:
            print("Usage: point <name> <x> <y> [radius] [color]")
            return
            
        name = args[0]
        x, y = float(args[1]), float(args[2])
        radius = float(args[3]) if len(args) > 3 else 5
        
        # Color parsing (simplified)
        color = rl.RED
        if len(args) > 4:
            color_name = args[4].upper()
            color_map = {
                'RED': rl.RED, 'GREEN': rl.GREEN, 'BLUE': rl.BLUE,
                'BLACK': rl.BLACK, 'WHITE': rl.WHITE, 'YELLOW': rl.YELLOW,
                'PURPLE': rl.PURPLE, 'ORANGE': rl.ORANGE
            }
            color = color_map.get(color_name, rl.RED)
        
        self.objects[name] = Point(x, y, radius, color)
        print(f"Created point '{name}' at ({x}, {y})")
    
    def create_line(self, args):
        """Create a line: line <name> <point1> <point2>"""
        if len(args) < 3:
            print("Usage: line <name> <point1> <point2>")
            return
            
        name = args[0]
        p1_name, p2_name = args[1], args[2]
        
        if p1_name not in self.objects or p2_name not in self.objects:
            print(f"Points '{p1_name}' and/or '{p2_name}' not found")
            return
            
        p1, p2 = self.objects[p1_name], self.objects[p2_name]
        if not isinstance(p1, Point) or not isinstance(p2, Point):
            print("Both arguments must be points")
            return
            
        self.objects[name] = StraightLine(p1, p2)
        print(f"Created line '{name}' from {p1_name} to {p2_name}")
    
    def create_angle(self, args):
        """Create an angle: angle <name> <line1> <line2>"""
        if len(args) < 3:
            print("Usage: angle <name> <line1> <line2>")
            return
            
        name = args[0]
        l1_name, l2_name = args[1], args[2]
        
        if l1_name not in self.objects or l2_name not in self.objects:
            print(f"Lines '{l1_name}' and/or '{l2_name}' not found")
            return
            
        l1, l2 = self.objects[l1_name], self.objects[l2_name]
        if not isinstance(l1, StraightLine) or not isinstance(l2, StraightLine):
            print("Both arguments must be lines")
            return
            
        try:
            self.objects[name] = Angle(l1, l2)
            angle_measure = self.objects[name].measure()
            print(f"Created angle '{name}' measuring {angle_measure:.2f} degrees")
        except ValueError as e:
            print(f"Cannot create angle: {e}")
    
    def move_object(self, args):
        """Move a point: move <point_name> <new_x> <new_y>"""
        if len(args) < 3:
            print("Usage: move <point_name> <new_x> <new_y>")
            return
            
        name = args[0]
        if name not in self.objects:
            print(f"Object '{name}' not found")
            return
            
        obj = self.objects[name]
        if not isinstance(obj, Point):
            print("Can only move points")
            return
            
        obj.x, obj.y = float(args[1]), float(args[2])
        print(f"Moved '{name}' to ({obj.x}, {obj.y})")
    
    def list_objects(self):
        """List all created objects"""
        if not self.objects:
            print("No objects created")
            return
            
        print("\nCreated objects:")
        for name, obj in self.objects.items():
            if isinstance(obj, Point):
                print(f"  {name}: Point at ({obj.x}, {obj.y})")
            elif isinstance(obj, StraightLine):
                print(f"  {name}: Line (length: {obj.length():.2f})")
            elif isinstance(obj, Angle):
                print(f"  {name}: Angle ({obj.measure():.2f} degrees)")
    
    def delete_object(self, args):
        """Delete an object: delete <name>"""
        if len(args) < 1:
            print("Usage: delete <name>")
            return
            
        name = args[0]
        if name in self.objects:
            del self.objects[name]
            print(f"Deleted '{name}'")
        else:
            print(f"Object '{name}' not found")
    
    def clear_objects(self):
        """Clear all objects"""
        self.objects.clear()
        print("All objects cleared")
    
    def show_help(self):
        """Show available commands"""
        print("\nAvailable commands:")
        print("  point <name> <x> <y> [radius] [color] - Create a point")
        print("  line <name> <point1> <point2> - Create a line between two points")
        print("  angle <name> <line1> <line2> - Create an angle from two lines")
        print("  move <point_name> <x> <y> - Move a point to new coordinates")
        print("  list - List all created objects")
        print("  delete <name> - Delete an object")
        print("  clear - Clear all objects")
        print("  help - Show this help")
        print("\nColors: RED, GREEN, BLUE, BLACK, WHITE, YELLOW, PURPLE, ORANGE")
        print("Note: Coordinates are relative to screen center (0,0)")


class Window:
    """
    raylib window
    """

    def __init__(
        self,
        w=SCREEN_WIDTH,
        h=SCREEN_HEIGHT,
        title="Window",
        fps=60,
    ):
        self.width = w
        self.height = h
        self.title = title
        self.fps = fps
        self._initialized = False

    def init(self):
        rl.init_window(self.width, self.height, self.title)
        rl.set_target_fps(self.fps)
        # rl.disable_cursor()
        self._initialized = True

    def close_window(self):
        if self._initialized:
            rl.close_window()
            self._initialized = False

    def to_screen(self, x: float, y: float):
        # normalize position around screen center
        sx = self.width // 2 + int(x)
        sy = self.height // 2 - int(y)
        return sx, sy


def console_input_thread(console_cmd):
    """Thread function for handling console input"""
    print("\n=== Geometry Console ===")
    print("Type 'help' for available commands")
    print("Press Ctrl+C or close window to exit\n")
    
    while console_cmd.running:
        try:
            command = input(">> ")
            if command.strip().lower() == 'quit':
                console_cmd.running = False
                break
            console_cmd.command_queue.put(command)
        except (KeyboardInterrupt, EOFError):
            console_cmd.running = False
            break


def main():
    # --- Initialize Window ---
    win = Window(title="Geometry Visualizer")
    win.init()
    
    # --- Initialize Console Command System ---
    console_cmd = ConsoleCommand(win)
    
    # Start console input thread
    input_thread = threading.Thread(target=console_input_thread, args=(console_cmd,), daemon=True)
    input_thread.start()

    # --- Main Loop ---
    while not rl.window_should_close() and console_cmd.running:
        # Process console commands
        while not console_cmd.command_queue.empty():
            try:
                command = console_cmd.command_queue.get_nowait()
                console_cmd.parse_command(command)
            except queue.Empty:
                break
        
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)
        
        # Draw coordinate system
        center_x, center_y = win.width // 2, win.height // 2
        rl.draw_line(0, center_y, win.width, center_y, rl.LIGHTGRAY)  # X-axis
        rl.draw_line(center_x, 0, center_x, win.height, rl.LIGHTGRAY)  # Y-axis
        
        # Draw all objects
        for name, obj in console_cmd.objects.items():
            if isinstance(obj, Point):
                screen_x, screen_y = win.to_screen(obj.x, obj.y)
                rl.draw_circle(screen_x, screen_y, obj.radius, obj.color)
                # Draw label
                rl.draw_text(name, screen_x + 10, screen_y - 10, 12, rl.BLACK)
                
            elif isinstance(obj, StraightLine):
                ax, ay = win.to_screen(obj.A.x, obj.A.y)
                bx, by = win.to_screen(obj.B.x, obj.B.y)
                rl.draw_line_ex(rl.Vector2(ax, ay), rl.Vector2(bx, by), 2, rl.BLACK)
                # Draw label at midpoint
                mid_x, mid_y = (ax + bx) // 2, (ay + by) // 2
                rl.draw_text(name, mid_x + 5, mid_y - 15, 12, rl.BLUE)
        
        # Draw instructions
        rl.draw_text("Use console commands to create and manipulate geometric objects", 10, 10, 16, rl.DARKGRAY)
        rl.draw_text("Coordinate system: (0,0) is at screen center", 10, 30, 14, rl.DARKGRAY)

        rl.end_drawing()
    
    # Cleanup
    console_cmd.running = False
    rl.enable_cursor()
    win.close_window()


if __name__ == "__main__":
    main()
