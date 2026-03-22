import pyray as rl
from pyray import Vector3, Matrix
import math

# Screen dimensions
SCREEN_WIDTH = 1524
SCREEN_HEIGHT = 768

# --- Camera mode
camera_mode = 0  # 0 = spherical orbit, 1 = clamped orbit, 2 = free 6DOF

# --- Spherical coordinates for orbit mode ---
theta = 0.0
phi = math.radians(30)

# --- Rotation matrix for 6DOF mode
camera_rotation = Matrix(
    1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0
)


def draw_coordinate_axes(length=10):
    origin = Vector3(0, 0, 0)

    # X-axis (red)
    rl.draw_line_3d(origin, Vector3(length + 1000, 0, 0), rl.RED)
    rl.draw_line_3d(origin, Vector3(-length - 1000, 0, 0), rl.RED)

    # Y-axis (green)
    rl.draw_line_3d(origin, Vector3(0, length + 1000, 0), rl.GREEN)
    rl.draw_line_3d(origin, Vector3(0, -length - 1000, 0), rl.GREEN)

    # Z-axis (blue)
    rl.draw_line_3d(origin, Vector3(0, 0, length + 1000), rl.BLUE)
    rl.draw_line_3d(origin, Vector3(0, 0, -length - 1000), rl.BLUE)


def draw_rotation_guides(radius=8):
    # rl.draw_circle_lines(0, 0, radius, rl.RED)

    # Horizontal circle (on ground)
    rl.draw_circle_3d(rl.Vector3(0, 0, 0), 5, rl.Vector3(1, 0, 0), 90.0, rl.BLUE)

    # Vertical circle facing forward
    rl.draw_circle_3d(rl.Vector3(0, 0, 0), 5, rl.Vector3(0, 0, 1), 0.0, rl.RED)

    # Vertical circle facing sideways
    rl.draw_circle_3d(rl.Vector3(0, 0, 0), 5, rl.Vector3(0, 1, 0), 90.0, rl.GREEN)


def update_camera_orbit_spherical(camera, target, radius, sensitivity=0.005):
    global theta, phi

    if rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT):
        delta = rl.get_mouse_delta()
        theta -= delta.x * sensitivity
        phi -= delta.y * sensitivity

    # --- Orbit logic ---
    camera.position.x = target.x + radius * math.cos(phi) * math.sin(theta)
    camera.position.y = target.y + radius * math.sin(phi)
    camera.position.z = target.z + radius * math.cos(phi) * math.cos(theta)

    camera.target = target
    camera.up = Vector3(0, 1, 0)


def update_camera_orbit_clamped(camera, target, radius, sensitivity=0.005):
    global theta, phi

    if rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT):
        delta = rl.get_mouse_delta()
        theta -= delta.x * sensitivity
        phi -= delta.y * sensitivity

        # Clamp phi to prevent gimbal lock and flipping
        # Leave a small margin from the exact poles
        phi = max(-math.pi / 2 + 0.1, min(math.pi / 2 - 0.1, phi))

    # --- Orbit logic ---
    camera.position.x = target.x + radius * math.cos(phi) * math.sin(theta)
    camera.position.y = target.y + radius * math.sin(phi)
    camera.position.z = target.z + radius * math.cos(phi) * math.cos(theta)

    camera.target = target
    camera.up = Vector3(0, 1, 0)


def update_camera_free_6dof(camera, target, radius, sensitivity=0.01):
    """Free 6DOF rotation using rotation matrices"""
    global camera_rotation

    if rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT):
        delta = rl.get_mouse_delta()

        # Y-axis rotation (horizontal mouse movement)
        y_rotation = rl.matrix_rotate_y(-delta.x * sensitivity)

        # X-axis rotation (vertical mouse movement)
        x_rotation = rl.matrix_rotate_x(-delta.y * sensitivity)

        # Apply mouse rotations: 
        camera_rotation = rl.matrix_multiply(y_rotation, camera_rotation)
        camera_rotation = rl.matrix_multiply(x_rotation, camera_rotation)

    
    # Handle Y-axis rotation (Yaw) with A/D keys - camera-relative
    if rl.is_key_down(rl.KEY_A):
        y_rotation = rl.matrix_rotate_y(-0.02)
        camera_rotation = rl.matrix_multiply(y_rotation, camera_rotation)  # Post-multiply for local
    if rl.is_key_down(rl.KEY_D):
        y_rotation = rl.matrix_rotate_y(0.02) 
        camera_rotation = rl.matrix_multiply(y_rotation, camera_rotation)  # Post-multiply for local

    # Handle X-axis rotation (Pitch) with W/S keys - camera-relative
    if rl.is_key_down(rl.KEY_W):
        x_rotation = rl.matrix_rotate_x(-0.02)
        camera_rotation = rl.matrix_multiply(x_rotation, camera_rotation)
    if rl.is_key_down(rl.KEY_S):
        x_rotation = rl.matrix_rotate_x(0.02)
        camera_rotation = rl.matrix_multiply(x_rotation, camera_rotation)

    # Handle Z-axis rotation (Roll) with Q/E keys - camera-relative
    if rl.is_key_down(rl.KEY_Q):
        z_rotation = rl.matrix_rotate_z(-0.02)
        camera_rotation = rl.matrix_multiply(z_rotation, camera_rotation)
    if rl.is_key_down(rl.KEY_E):
        z_rotation = rl.matrix_rotate_z(0.02)
        camera_rotation = rl.matrix_multiply(z_rotation, camera_rotation)

    # Extract forward vector from rotation matrix (negative Z direction)
    forward = Vector3(-camera_rotation.m8, -camera_rotation.m9, -camera_rotation.m10)

    # Calculate camera position
    camera.position.x = target.x - forward.x * radius
    camera.position.y = target.y - forward.y * radius
    camera.position.z = target.z - forward.z * radius

    camera.target = target

    # Extract up vector from rotation matrix
    camera.up = Vector3(camera_rotation.m4, camera_rotation.m5, camera_rotation.m6)


def get_camera_mode_name():
    """Get the name of the current camera mode"""
    if camera_mode == 0:
        return "Spherical Orbit (Original)"
    elif camera_mode == 1:
        return "Spherical Orbit (Clamped)"
    elif camera_mode == 2:
        return "Free 6DOF Rotation"
    return "Unknown"


def main():
    global camera_mode

    # --- Initialize raylib window ---
    rl.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "3D Grid Scene")
    rl.set_target_fps(60)

    camera = rl.Camera3D()
    camera.position = Vector3(15.0, 15.0, 15.0)
    camera.target = Vector3(0.0, 0.0, 0.0)
    camera.up = Vector3(0.0, 1.0, 0.0)
    camera.fovy = 60.0
    camera.projection = rl.CAMERA_PERSPECTIVE

    # --- Main loop ---
    while not rl.window_should_close():
        # Handle camera mode switching
        if rl.is_key_pressed(rl.KEY_ONE):
            camera_mode = 0
        elif rl.is_key_pressed(rl.KEY_TWO):
            camera_mode = 1
        elif rl.is_key_pressed(rl.KEY_THREE):
            camera_mode = 2

        # Update camera based on current mode
        if camera_mode == 0:
            update_camera_orbit_spherical(camera, Vector3(0, 0, 0), 15.0)
        elif camera_mode == 1:
            update_camera_orbit_clamped(camera, Vector3(0, 0, 0), 15.0)
        elif camera_mode == 2:
            update_camera_free_6dof(camera, Vector3(0, 0, 0), 15.0)

        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        rl.begin_mode_3d(camera)
        draw_coordinate_axes(length=1200)  # axis lines
        draw_rotation_guides()
        rl.draw_sphere(Vector3(0, 0, 0), 0.3, rl.WHITE)
        rl.draw_sphere(Vector3(5, 3, -2), 0.5, rl.YELLOW)
        rl.draw_cube(Vector3(-3, -4, 6), 1.0, 1.0, 1.0, rl.PURPLE)
        rl.end_mode_3d()

        # UI
        rl.draw_text(b"Camera Controls:", 10, 10, 20, rl.WHITE)
        rl.draw_text(
            f"Current Mode: {get_camera_mode_name()}".encode(), 10, 35, 16, rl.YELLOW
        )
        rl.draw_text(b"1 - Spherical Orbit (unclamped)", 10, 60, 14, rl.WHITE)
        rl.draw_text(b"2 - Spherical Orbit (clamped)", 10, 80, 14, rl.WHITE)
        rl.draw_text(b"3 - Free 6DOF (Q/E for roll)", 10, 199, 14, rl.WHITE)

        rl.draw_fps(SCREEN_WIDTH - 95, 10)

        rl.end_drawing()

    # Clean up
    rl.close_window()


if __name__ == "__main__":
    main()
