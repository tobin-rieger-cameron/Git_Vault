import pyray as pr
from pyray import Vector3, Ray, Camera3D

# Initialize window
pr.init_window(1000, 800, "3D Axis Lines with Rays")

# Set up camera
camera = Camera3D(
    Vector3(5, 5, 5),  # position
    Vector3(0, 0, 0),  # target (looking at origin)
    Vector3(0, 1, 0),  # up vector
    45.0,  # field of view
    pr.CAMERA_PERSPECTIVE,
)


def draw_ray(
    ray, color, length=5.0, show_origin=True, show_endpoint=True, show_ticks=False
):
    """General purpose ray drawing function"""

    # Calculate end point
    end_point = Vector3(
        ray.position.x + ray.direction.x * length,
        ray.position.y + ray.direction.y * length,
        ray.position.z + ray.direction.z * length,
    )

    # Draw the main ray line
    pr.draw_line_3d(ray.position, end_point, color)

    # Optional: Draw origin marker
    if show_origin:
        pr.draw_sphere(ray.position, 0.05, color)

    # Optional: Draw end point marker
    if show_endpoint:
        pr.draw_sphere(end_point, 0.08, color)

    # Optional: Draw tick marks along the ray
    if show_ticks:
        for i in range(1, int(length) + 1):
            tick_point = Vector3(
                ray.position.x + ray.direction.x * i,
                ray.position.y + ray.direction.y * i,
                ray.position.z + ray.direction.z * i,
            )
            pr.draw_sphere(tick_point, 0.03, color)


def draw_axis(origin=Vector3(0, 0, 0), length=5.0):
    """Draw X, Y, Z axes using the ray drawing function"""

    # Create axis rays
    x_ray = Ray(origin, Vector3(1, 0, 0))  # X-axis (red)
    y_ray = Ray(origin, Vector3(0, 1, 0))  # Y-axis (green)
    z_ray = Ray(origin, Vector3(0, 0, 1))  # Z-axis (blue)

    # Draw positive axes
    draw_ray(
        x_ray, pr.RED, length, show_origin=True, show_endpoint=True, show_ticks=True
    )
    draw_ray(
        y_ray, pr.GREEN, length, show_origin=False, show_endpoint=True, show_ticks=True
    )  # Don't duplicate origin
    draw_ray(
        z_ray, pr.BLUE, length, show_origin=False, show_endpoint=True, show_ticks=True
    )  # Don't duplicate origin

    # Create and draw negative axes (dashed effect)
    neg_x_ray = Ray(origin, Vector3(-1, 0, 0))
    neg_y_ray = Ray(origin, Vector3(0, -1, 0))
    neg_z_ray = Ray(origin, Vector3(0, 0, -1))

    # Draw negative axes with dashed effect
    for i in range(0, int(length * 2)):
        if i % 4 < 2:  # Create dashed effect
            dash_start = i * 0.5
            dash_end = min((i + 1) * 0.5, length)

            if dash_end <= length:
                # Create short ray segments for dashed effect
                dash_x_ray = Ray(Vector3(-dash_start, 0, 0), Vector3(-1, 0, 0))
                dash_y_ray = Ray(Vector3(0, -dash_start, 0), Vector3(0, -1, 0))
                dash_z_ray = Ray(Vector3(0, 0, -dash_start), Vector3(0, 0, -1))

                dash_length = dash_end - dash_start
                draw_ray(
                    dash_x_ray,
                    pr.Color(150, 0, 0, 150),
                    dash_length,
                    False,
                    False,
                    False,
                )
                draw_ray(
                    dash_y_ray,
                    pr.Color(0, 150, 0, 150),
                    dash_length,
                    False,
                    False,
                    False,
                )
                draw_ray(
                    dash_z_ray,
                    pr.Color(0, 0, 150, 150),
                    dash_length,
                    False,
                    False,
                    False,
                )

    # Draw a larger origin marker
    pr.draw_sphere(origin, 0.1, pr.WHITE)


def draw_axis_labels_2d():
    """Draw 2D axis labels on screen"""
    pr.draw_text("Red = X-axis", 10, 10, 20, pr.RED)
    pr.draw_text("Green = Y-axis", 10, 35, 20, pr.GREEN)
    pr.draw_text("Blue = Z-axis", 10, 60, 20, pr.BLUE)
    pr.draw_text("Use mouse to rotate camera", 10, 90, 16, pr.DARKGRAY)


# Create the axis system
axis_length = 5.0

# Main loop
while not pr.window_should_close():
    # Update camera (allow free movement)
    pr.update_camera(camera, pr.CAMERA_FREE)

    pr.begin_drawing()
    pr.clear_background(pr.BLACK)

    # 3D drawing
    pr.begin_mode_3d(camera)

    # Draw a grid plane for reference
    pr.draw_plane(Vector3(0, 0, 0), Vector3(10, 10), pr.Color(50, 50, 50, 100))

    # Draw the complete axis system using our draw_axis function
    draw_axis(Vector3(0, 0, 0), axis_length)

    # Add some reference objects to show the coordinate system in action
    pr.draw_cube(
        Vector3(2, 0, 0), 0.5, 0.5, 0.5, pr.Color(255, 100, 100, 200)
    )  # On X-axis
    pr.draw_cube(
        Vector3(0, 2, 0), 0.5, 0.5, 0.5, pr.Color(100, 255, 100, 200)
    )  # On Y-axis
    pr.draw_cube(
        Vector3(0, 0, 2), 0.5, 0.5, 0.5, pr.Color(100, 100, 255, 200)
    )  # On Z-axis

    # Example: Draw additional rays using the draw_ray function
    # A diagonal ray from origin
    diagonal_ray = Ray(
        Vector3(0, 0, 0), Vector3(0.577, 0.577, 0.577)
    )  # Normalized diagonal
    draw_ray(diagonal_ray, pr.YELLOW, 3.0, show_ticks=False)

    pr.end_mode_3d()

    # 2D UI overlay
    draw_axis_labels_2d()

    # Show camera position
    cam_text = f"Camera: ({camera.position.x:.1f}, {camera.position.y:.1f}, {camera.position.z:.1f})"
    pr.draw_text(cam_text, 10, pr.get_screen_height() - 30, 16, pr.WHITE)

    pr.end_drawing()

# Cleanup
pr.close_window()
