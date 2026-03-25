# Main code to run a Solar System simulation with camera
import pyray as rl
from utils.vector3d import Vector3D
from utils.raywindow import Window
from utils.camera import Camera
from scripts.body import Body
from scripts.geometry import InfiniteLine, Ray, FiniteLine, Point, Vector2D


def main():
    # --- Initialize window ---
    win = Window(title="Orbit Camera Demo")
    win.init()
    rl.disable_cursor()

    # --- Initialize camera ---
    # Start with orbital camera mode
    camera = Camera(
        mode=Camera.MODE_ORBITAL,
        position=Vector3D(15.0, 10.0, 15.0),
        target=Vector3D(0.0, 0.0, 0.0),
        fovy=45.0,
    )

    # Configure camera settings
    camera.set_orbital_constraints(min_dist=5.0, max_dist=50.0)
    camera.set_sensitivity(mouse_sens=0.003, zoom_sens=2.0)

    # Create some bodies for testing
    sphere1 = Body(0, 0, 0, 8, rl.BLACK)
    sphere2 = Body(20, 0, 0, 3, rl.RED)
    sphere3 = Body(-15, 5, 10, 2, rl.BLUE)

    # --- Initialize 2D geometry objects for testing ---
    # These will be drawn as a 2D overlay
    show_geometry = False  # Toggle with 'G' key

    # Create some geometry objects
    # Infinite line from slope-intercept
    infinite_line1 = InfiniteLine(m=0.5, b=100)

    # Infinite line from two points
    infinite_line2 = InfiniteLine(point1=Point(100, 400), point2=Point(700, 200))

    # Ray starting from center, going right-up
    center_point = Point(400, 300)
    ray1 = Ray(center_point, Vector2D(1, -0.5))
    ray2 = Ray(center_point, Vector2D(-1, 0.8))

    # Finite line segments
    finite_line1 = FiniteLine(Point(50, 50), Point(200, 150))
    finite_line2 = FiniteLine(Point(600, 100), Point(750, 300))

    # Store all geometry objects for easy iteration
    geometry_objects = [
        ("Infinite Lines", [infinite_line1, infinite_line2]),
        ("Rays", [ray1, ray2]),
        ("Finite Lines", [finite_line1, finite_line2]),
    ]

    # Main game loop
    while not rl.window_should_close():
        # Update camera
        camera.update()

        # Handle camera mode switching (for testing)
        if rl.is_key_pressed(rl.KEY_ONE):
            camera.set_mode(Camera.MODE_ORBITAL)
            print("Switched to Orbital Camera")
        elif rl.is_key_pressed(rl.KEY_TWO):
            camera.set_mode(Camera.MODE_FPS)
            print("Switched to FPS Camera")
        elif rl.is_key_pressed(rl.KEY_THREE):
            camera.set_mode(Camera.MODE_FREE)
            print("Switched to Free Camera")
        elif rl.is_key_pressed(rl.KEY_FOUR):
            camera.set_mode(Camera.MODE_FIXED)
            print("Switched to Fixed Camera")

        # Toggle geometry overlay
        if rl.is_key_pressed(rl.KEY_G):
            show_geometry = not show_geometry
            print(f"Geometry overlay: {'ON' if show_geometry else 'OFF'}")

        # Reset camera position
        if rl.is_key_pressed(rl.KEY_R):
            camera.reset()
            print("Camera reset")

        # Interactive geometry creation with mouse (when geometry is visible)
        if show_geometry:
            if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
                mouse_pos = rl.get_mouse_position()
                # Create a new ray from center to mouse position
                direction = Vector2D(
                    mouse_pos.x - center_point.x, mouse_pos.y - center_point.y
                )
                # Replace ray2 with new ray pointing to mouse
                ray2 = Ray(center_point, direction)
                # Update geometry objects list
                geometry_objects[1] = ("Rays", [ray1, ray2])

        # Begin drawing
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)

        # Begin 3D mode
        camera.begin_mode_3d()

        # Draw 3D objects
        sphere1.draw()
        sphere2.draw()
        sphere3.draw()

        # Draw a grid for reference
        rl.draw_grid(50, 1.0)

        # End 3D mode
        camera.end_mode_3d()

        # --- 2D Overlay Section ---
        # Draw geometry objects as 2D overlay
        if show_geometry:
            # Semi-transparent background for geometry overlay
            rl.draw_rectangle(
                0,
                0,
                rl.get_screen_width(),
                rl.get_screen_height(),
                rl.Color(0, 0, 0, 50),
            )

            # Draw all geometry objects
            for category_name, objects in geometry_objects:
                for obj in objects:
                    obj.draw()

            # Draw center point for reference
            rl.draw_circle(int(center_point.x), int(center_point.y), 6, rl.YELLOW)
            rl.draw_text(
                "CENTER",
                int(center_point.x - 25),
                int(center_point.y - 20),
                12,
                rl.YELLOW,
            )

            # Draw geometry info
            rl.draw_text("2D GEOMETRY OVERLAY", 10, 120, 20, rl.WHITE)
            rl.draw_text("Red: Infinite Lines", 10, 145, 16, rl.RED)
            rl.draw_text("Blue: Rays (with arrows)", 10, 165, 16, rl.BLUE)
            rl.draw_text("Green: Finite Lines (with endpoints)", 10, 185, 16, rl.GREEN)
            rl.draw_text("Left click to redirect ray to mouse", 10, 205, 16, rl.WHITE)

        # Draw UI info
        rl.draw_text(f"Camera Mode: {camera.mode.upper()}", 10, 10, 20, rl.BLACK)
        rl.draw_text(
            f"Position: ({camera.position.x:.1f}, {camera.position.y:.1f}, {camera.position.z:.1f})",
            10,
            35,
            16,
            rl.BLACK,
        )

        if camera.mode == Camera.MODE_ORBITAL:
            rl.draw_text(
                "Left click + drag to rotate, scroll to zoom", 10, 60, 16, rl.BLACK
            )
        elif camera.mode == Camera.MODE_FPS:
            rl.draw_text("WASD to move, mouse to look around", 10, 60, 16, rl.BLACK)
        elif camera.mode == Camera.MODE_FREE:
            rl.draw_text("WASD + mouse to fly around freely", 10, 60, 16, rl.BLACK)

        # Add geometry toggle instruction
        rl.draw_text(
            "Press 'G' to toggle 2D geometry overlay",
            10,
            rl.get_screen_height() - 40,
            16,
            rl.DARKGRAY,
        )

        rl.end_drawing()

    rl.enable_cursor()
    win.close_window()


if __name__ == "__main__":
    main()
