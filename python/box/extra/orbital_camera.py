import pyray as rl
import math


def vector3_to_list(v):
    """Convert Vector3 to list for matrix operations"""
    return [v.x, v.y, v.z]


def list_to_vector3(l):
    """Convert list to Vector3"""
    return rl.Vector3(l[0], l[1], l[2])


def matrix_vector3_multiply(matrix, vector):
    """Multiply a 4x4 matrix with a Vector3 (treating vector as homogeneous with w=1)"""
    result = rl.vector3_transform(vector, matrix)
    return result


class OrbitalCamera:
    def __init__(self, radius=10.0, target_x=0.0, target_y=0.0, target_z=0.0):
        self.target = rl.Vector3(target_x, target_y, target_z)
        self.radius = radius
        self.min_radius = 2.0
        self.max_radius = 50.0

        # Movement speeds
        self.rotation_speed = 2.0  # radians per second
        self.zoom_speed = 2.0

        # Cumulative rotation matrix - starts as identity
        self.rotation_matrix = rl.matrix_identity()

        # Initial camera direction (looking at target from negative Z)
        self.initial_offset = rl.Vector3(0.0, 0.0, self.radius)

        # Camera object
        self.camera = rl.Camera3D()
        self.camera.target = self.target
        self.camera.up = rl.Vector3(0.0, 1.0, 0.0)
        self.camera.fovy = 60.0
        self.camera.projection = rl.CAMERA_PERSPECTIVE

        self.update_camera_position()

    def update_camera_position(self):
        """Update camera position and orientation based on rotation matrix"""
        # Apply cumulative rotation to the initial offset
        rotated_offset = matrix_vector3_multiply(
            self.rotation_matrix, self.initial_offset
        )

        # Set camera position
        self.camera.position = rl.Vector3(
            self.target.x + rotated_offset.x,
            self.target.y + rotated_offset.y,
            self.target.z + rotated_offset.z,
        )

        # Calculate the up vector by rotating the world up vector
        world_up = rl.Vector3(0.0, 1.0, 0.0)
        rotated_up = matrix_vector3_multiply(self.rotation_matrix, world_up)
        self.camera.up = rotated_up

    def apply_rotation(self, rotation_matrix):
        """Apply a rotation to the cumulative rotation matrix"""
        # Multiply the new rotation with the existing cumulative rotation
        self.rotation_matrix = rl.matrix_multiply(rotation_matrix, self.rotation_matrix)

    def get_camera_right_vector(self):
        """Get the camera's right vector (screen-relative right direction)"""
        # Calculate the right vector as cross product of view direction and up
        view_direction = rl.vector3_subtract(self.target, self.camera.position)
        view_direction = rl.vector3_normalize(view_direction)
        right = rl.vector3_cross_product(view_direction, self.camera.up)
        return rl.vector3_normalize(right)

    def get_camera_local_up_vector(self):
        """Get the camera's local up vector (screen-relative up direction)"""
        # This is perpendicular to both the view direction and right vector
        view_direction = rl.vector3_subtract(self.target, self.camera.position)
        view_direction = rl.vector3_normalize(view_direction)
        right = self.get_camera_right_vector()
        local_up = rl.vector3_cross_product(right, view_direction)
        return rl.vector3_normalize(local_up)

    def update(self, dt):
        """Update camera based on input using rotation matrices"""
        rotation_amount = self.rotation_speed * dt

        # Handle W/S movement (elevation - rotate around camera's right axis)
        if rl.is_key_down(rl.KEY_W):  # Move north (toward world up)
            # Create rotation matrix around the camera's right axis
            right_vector = self.get_camera_right_vector()
            rotation = rl.matrix_rotate(
                right_vector, -rotation_amount
            )  # Negative for correct direction
            self.apply_rotation(rotation)

        if rl.is_key_down(rl.KEY_S):  # Move south (away from world up)
            right_vector = self.get_camera_right_vector()
            rotation = rl.matrix_rotate(right_vector, rotation_amount)
            self.apply_rotation(rotation)

        # Handle A/D movement (azimuth - rotate around world Y axis for consistent behavior)
        if rl.is_key_down(rl.KEY_A):  # Move screen-left
            # Rotate around world up axis (Y) for consistent left movement
            world_up = rl.Vector3(0.0, 1.0, 0.0)
            rotation = rl.matrix_rotate(world_up, rotation_amount)
            self.apply_rotation(rotation)

        if rl.is_key_down(rl.KEY_D):  # Move screen-right
            world_up = rl.Vector3(0.0, 1.0, 0.0)
            rotation = rl.matrix_rotate(world_up, -rotation_amount)
            self.apply_rotation(rotation)

        # Handle mouse wheel zoom
        wheel = rl.get_mouse_wheel_move()
        if wheel != 0:
            self.radius -= wheel * self.zoom_speed
            self.radius = max(self.min_radius, min(self.max_radius, self.radius))

            # Update the initial offset with new radius
            self.initial_offset = rl.Vector3(0.0, 0.0, self.radius)

        self.update_camera_position()

    def get_azimuth_degrees(self):
        """Calculate current azimuth in degrees for display"""
        # Extract azimuth from the current camera position
        offset = rl.vector3_subtract(self.camera.position, self.target)
        azimuth = math.atan2(offset.x, offset.z)
        return math.degrees(azimuth)

    def get_elevation_degrees(self):
        """Calculate current elevation in degrees for display"""
        # Extract elevation from the current camera position
        offset = rl.vector3_subtract(self.camera.position, self.target)
        distance_xz = math.sqrt(offset.x * offset.x + offset.z * offset.z)
        elevation = math.atan2(offset.y, distance_xz)
        return math.degrees(elevation)


def draw_coordinate_axes(size=5.0):
    """Draw coordinate axes (X=red, Y=green, Z=blue)"""
    # X axis - Red
    rl.draw_line_3d(rl.Vector3(0, 0, 0), rl.Vector3(size, 0, 0), rl.RED)
    rl.draw_cube(rl.Vector3(size + 0.5, 0, 0), 0.3, 0.3, 0.3, rl.RED)

    # Y axis - Green
    rl.draw_line_3d(rl.Vector3(0, 0, 0), rl.Vector3(0, size, 0), rl.GREEN)
    rl.draw_cube(rl.Vector3(0, size + 0.5, 0), 0.3, 0.3, 0.3, rl.GREEN)

    # Z axis - Blue
    rl.draw_line_3d(rl.Vector3(0, 0, 0), rl.Vector3(0, 0, size), rl.BLUE)
    rl.draw_cube(rl.Vector3(0, 0, size + 0.5), 0.3, 0.3, 0.3, rl.BLUE)


def draw_reference_cubes():
    """Draw reference cubes at cardinal directions"""
    distance = 8.0
    size = 0.8

    # North (positive Z)
    rl.draw_cube(rl.Vector3(0, 0, distance), size, size, size, rl.WHITE)
    rl.draw_cube_wires(rl.Vector3(0, 0, distance), size, size, size, rl.BLACK)

    # South (negative Z)
    rl.draw_cube(rl.Vector3(0, 0, -distance), size, size, size, rl.GRAY)
    rl.draw_cube_wires(rl.Vector3(0, 0, -distance), size, size, size, rl.BLACK)

    # East (positive X)
    rl.draw_cube(rl.Vector3(distance, 0, 0), size, size, size, rl.YELLOW)
    rl.draw_cube_wires(rl.Vector3(distance, 0, 0), size, size, size, rl.BLACK)

    # West (negative X)
    rl.draw_cube(rl.Vector3(-distance, 0, 0), size, size, size, rl.ORANGE)
    rl.draw_cube_wires(rl.Vector3(-distance, 0, 0), size, size, size, rl.BLACK)

    # Top (positive Y)
    rl.draw_cube(rl.Vector3(0, distance, 0), size, size, size, rl.LIME)
    rl.draw_cube_wires(rl.Vector3(0, distance, 0), size, size, size, rl.BLACK)

    # Bottom (negative Y)
    rl.draw_cube(rl.Vector3(0, -distance, 0), size, size, size, rl.PURPLE)
    rl.draw_cube_wires(rl.Vector3(0, -distance, 0), size, size, size, rl.BLACK)


def draw_grid(size=20, spacing=2):
    """Draw a grid on the XZ plane"""
    half_size = size // 2
    for i in range(-half_size, half_size + 1):
        x = i * spacing
        z = i * spacing

        color = rl.LIGHTGRAY if i % 5 != 0 else rl.GRAY

        # Lines parallel to X axis
        rl.draw_line_3d(
            rl.Vector3(-half_size * spacing, 0, z),
            rl.Vector3(half_size * spacing, 0, z),
            color,
        )

        # Lines parallel to Z axis
        rl.draw_line_3d(
            rl.Vector3(x, 0, -half_size * spacing),
            rl.Vector3(x, 0, half_size * spacing),
            color,
        )


def draw_compass(camera, x=80, y=80, radius=60):
    """Draw a compass showing current camera direction"""
    # Calculate compass direction based on camera position
    offset = rl.vector3_subtract(camera.camera.position, camera.target)
    compass_angle = -math.atan2(
        offset.x, offset.z
    )  # Negative for correct compass orientation

    # Draw compass circle
    rl.draw_circle(x, y, radius, rl.Color(50, 50, 50, 100))
    rl.draw_circle_lines(x, y, radius, rl.WHITE)

    # Draw cardinal directions
    rl.draw_text("N", x - 5, y - radius - 20, 16, rl.WHITE)
    rl.draw_text("S", x - 5, y + radius + 5, 16, rl.WHITE)
    rl.draw_text("E", x + radius + 5, y - 8, 16, rl.WHITE)
    rl.draw_text("W", x - radius - 20, y - 8, 16, rl.WHITE)

    # Draw direction needle
    needle_length = radius - 10
    needle_x = x + math.cos(compass_angle) * needle_length
    needle_y = y + math.sin(compass_angle) * needle_length

    rl.draw_line_ex(rl.Vector2(x, y), rl.Vector2(needle_x, needle_y), 4, rl.RED)

    # Draw center dot
    rl.draw_circle(x, y, 4, rl.WHITE)


def draw_elevation_indicator(camera, x=200, y=80, width=20, height=120):
    """Draw an elevation indicator"""
    # Calculate elevation from current camera position
    elevation_degrees = camera.get_elevation_degrees()
    normalized_elevation = elevation_degrees / 90.0  # Normalize to -1 to 1 range
    normalized_elevation = max(-1, min(1, normalized_elevation))  # Clamp for display

    # Draw background
    rl.draw_rectangle(x, y, width, height, rl.Color(50, 50, 50, 100))
    rl.draw_rectangle_lines(x, y, width, height, rl.WHITE)

    # Draw center line (horizon)
    center_y = y + height // 2
    rl.draw_line(x, center_y, x + width, center_y, rl.GRAY)

    # Draw elevation indicator
    indicator_y = center_y - (normalized_elevation * (height // 2))
    rl.draw_rectangle(x, int(indicator_y - 2), width, 4, rl.YELLOW)

    # Draw labels
    rl.draw_text("90°", x + width + 5, y - 5, 12, rl.WHITE)
    rl.draw_text("0°", x + width + 5, center_y - 6, 12, rl.WHITE)
    rl.draw_text("-90°", x + width + 5, y + height - 10, 12, rl.WHITE)


def main():
    # Initialize raylib
    screen_width = 1200
    screen_height = 800
    rl.init_window(
        screen_width, screen_height, "Orbital Camera Controller - Matrix Rotation"
    )
    rl.set_target_fps(60)

    # Create orbital camera
    orbital_cam = OrbitalCamera(radius=15.0)

    while not rl.window_should_close():
        dt = rl.get_frame_time()

        # Update camera
        orbital_cam.update(dt)

        # Rendering
        rl.begin_drawing()
        rl.clear_background(rl.Color(20, 20, 30, 255))

        # 3D rendering
        rl.begin_mode_3d(orbital_cam.camera)

        # Draw main sphere with wireframe
        rl.draw_sphere(rl.Vector3(0, 0, 0), 2.0, rl.BLUE)
        rl.draw_sphere_wires(rl.Vector3(0, 0, 0), 2.0, 16, 16, rl.WHITE)

        # Draw coordinate axes
        draw_coordinate_axes()

        # Draw reference cubes
        draw_reference_cubes()

        # Draw grid
        draw_grid()

        rl.end_mode_3d()

        # UI Elements
        # Camera info
        info_text = [
            f"Camera Position: ({orbital_cam.camera.position.x:.1f}, {orbital_cam.camera.position.y:.1f}, {orbital_cam.camera.position.z:.1f})",
            f"Azimuth: {orbital_cam.get_azimuth_degrees():.1f}°",
            f"Elevation: {orbital_cam.get_elevation_degrees():.1f}°",
            f"Radius: {orbital_cam.radius:.1f}",
            f"Up Vector: ({orbital_cam.camera.up.x:.2f}, {orbital_cam.camera.up.y:.2f}, {orbital_cam.camera.up.z:.2f})",
            "",
            "Controls (Matrix Rotation):",
            "W/S - Move North/South (Elevation)",
            "A/D - Move Screen Left/Right (Azimuth)",
            "Mouse Wheel - Zoom In/Out",
            "ESC - Exit",
        ]

        y_offset = 10
        for line in info_text:
            rl.draw_text(line, 10, y_offset, 16, rl.WHITE)
            y_offset += 20

        # Draw compass
        draw_compass(orbital_cam)

        # Draw elevation indicator
        draw_elevation_indicator(orbital_cam)

        # Reference cube legend
        legend_x = screen_width - 200
        legend_y = 10
        legend_items = [
            ("North (Z+)", rl.WHITE),
            ("South (Z-)", rl.GRAY),
            ("East (X+)", rl.YELLOW),
            ("West (X-)", rl.ORANGE),
            ("Top (Y+)", rl.LIME),
            ("Bottom (Y-)", rl.PURPLE),
        ]

        rl.draw_text("Reference Cubes:", legend_x, legend_y, 16, rl.WHITE)
        for i, (label, color) in enumerate(legend_items):
            y = legend_y + 25 + i * 20
            rl.draw_rectangle(legend_x, y, 15, 15, color)
            rl.draw_text(label, legend_x + 20, y + 2, 14, rl.WHITE)

        rl.end_drawing()

    rl.close_window()


if __name__ == "__main__":
    main()
