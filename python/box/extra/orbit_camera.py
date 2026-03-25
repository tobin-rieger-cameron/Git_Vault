import pyray as rl
import math

Vector3 = rl.Vector3

# Initial camera parameters
target = Vector3(0, 0, 0)
radius = 10.0
theta = 0.0  # yaw
phi = math.radians(30)  # pitch


def update_camera_orbit(camera, target, radius, sensitivity=0.005):
    global theta, phi

    # If left mouse button is pressed
    if rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT):
        delta = rl.get_mouse_delta()
        theta -= delta.x * sensitivity
        phi -= delta.y * sensitivity

    # Convert spherical to Cartesian
    camera.position.x = target.x + radius * math.cos(phi) * math.sin(theta)
    camera.position.y = target.y + radius * math.sin(phi)
    camera.position.z = target.z + radius * math.cos(phi) * math.cos(theta)

    camera.target = target
    camera.up = Vector3(0, 1, 0)


# --- Main ---
rl.init_window(800, 600, "Orbit Camera Example")
rl.set_target_fps(60)

camera = rl.Camera3D(Vector3(0, 10, 10), target, Vector3(0, 1, 0), 45.0, 0)

while not rl.window_should_close():
    update_camera_orbit(camera, target, radius)

    rl.begin_drawing()
    rl.clear_background(rl.RAYWHITE)

    rl.begin_mode_3d(camera)
    rl.draw_grid(20, 1.0)
    rl.draw_cube(target, 0.5, 0.5, 0.5, rl.RED)  # centerpoint
    rl.end_mode_3d()

    rl.end_drawing()

rl.close_window()
