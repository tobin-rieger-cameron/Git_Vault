import pyray as rl
import math


class Movement3D:
    def __init__(self, position=None, rotation=None, speed=5.0):
        self.position = position or rl.Vector3(0, 0, 0)
        self.rotation = rotation or rl.Quaternion(0, 0, 0, 1)  # Identity rotation
        self.speed = speed
        self._rotation_counter = 0  # Track rotations for normalization

    # --- Translation ---
    def translate_local(self, dx=0, dy=0, dz=0):
        """Move relative to the object's orientation."""
        local_movement = rl.Vector3(dx, dy, -dz)  # -dz because forward is negative Z
        world_movement = rl.Vector3Transform(
            local_movement, rl.MatrixFromQuaternion(self.rotation)
        )
        self.position = rl.Vector3Add(self.position, world_movement)

    def translate_global(self, dx=0, dy=0, dz=0):
        """Move in global coordinates."""
        self.position = rl.Vector3Add(self.position, rl.Vector3(dx, dy, dz))

    # --- Local Rotation (around object's own axes) ---
    def rotate_pitch(self, angle_deg):
        """Rotate around local X-axis."""
        self._apply_local_rotation(angle_deg, rl.Vector3(1, 0, 0))

    def rotate_yaw(self, angle_deg):
        """Rotate around local Y-axis."""
        self._apply_local_rotation(angle_deg, rl.Vector3(0, 1, 0))

    def rotate_roll(self, angle_deg):
        """Rotate around local Z-axis."""
        self._apply_local_rotation(angle_deg, rl.Vector3(0, 0, 1))

    # --- Global Rotation (around world axes) ---
    def rotate_pitch_global(self, angle_deg):
        """Rotate around global X-axis."""
        self._apply_global_rotation(angle_deg, rl.Vector3(1, 0, 0))

    def rotate_yaw_global(self, angle_deg):
        """Rotate around global Y-axis."""
        self._apply_global_rotation(angle_deg, rl.Vector3(0, 1, 0))

    def rotate_roll_global(self, angle_deg):
        """Rotate around global Z-axis."""
        self._apply_global_rotation(angle_deg, rl.Vector3(0, 0, 1))

    # --- Look At Target ---
    def look_at(self, target_position, up_vector=None):
        """Orient the object to look at a target position."""
        if up_vector is None:
            up_vector = rl.Vector3(0, 1, 0)  # Default up vector

        # Calculate the forward direction
        forward = rl.Vector3Normalize(
            rl.Vector3Subtract(target_position, self.position)
        )

        # Calculate right vector
        right = rl.Vector3Normalize(rl.Vector3CrossProduct(forward, up_vector))

        # Recalculate up vector to ensure orthogonality
        up = rl.Vector3CrossProduct(right, forward)

        # Create rotation matrix from the three axes
        # Note: forward is negative Z in the standard coordinate system
        rotation_matrix = rl.Matrix(
            right.x,
            up.x,
            -forward.x,
            0,
            right.y,
            up.y,
            -forward.y,
            0,
            right.z,
            up.z,
            -forward.z,
            0,
            0,
            0,
            0,
            1,
        )

        # Convert matrix to quaternion
        self.rotation = rl.QuaternionFromMatrix(rotation_matrix)
        self._normalize_quaternion()

    # --- Private Helper Methods ---
    def _apply_local_rotation(self, angle_deg, axis):
        """Apply rotation around local axis (object's current orientation)."""
        # Transform the axis to the object's local coordinate system
        local_axis = rl.Vector3Transform(axis, rl.MatrixFromQuaternion(self.rotation))
        quat = rl.QuaternionFromAxisAngle(local_axis, math.radians(angle_deg))
        self.rotation = rl.QuaternionMultiply(quat, self.rotation)
        self._check_normalization()

    def _apply_global_rotation(self, angle_deg, axis):
        """Apply rotation around global axis (world coordinate system)."""
        # Use the axis directly in world space
        quat = rl.QuaternionFromAxisAngle(axis, math.radians(angle_deg))
        self.rotation = rl.QuaternionMultiply(quat, self.rotation)
        self._check_normalization()

    def _check_normalization(self):
        """Normalize quaternion every few rotations to prevent drift."""
        self._rotation_counter += 1
        if self._rotation_counter >= 10:  # Normalize every 10 rotations
            self._normalize_quaternion()
            self._rotation_counter = 0

    def _normalize_quaternion(self):
        """Normalize the rotation quaternion."""
        self.rotation = rl.QuaternionNormalize(self.rotation)

    # --- Utility Methods ---
    def move_forward(self, distance=None):
        """Move forward in the local Z direction."""
        if distance is None:
            distance = self.speed
        self.translate_local(dz=distance)

    def move_backward(self, distance=None):
        """Move backward in the local Z direction."""
        if distance is None:
            distance = self.speed
        self.translate_local(dz=-distance)

    def strafe_left(self, distance=None):
        """Move left in the local X direction."""
        if distance is None:
            distance = self.speed
        self.translate_local(dx=-distance)

    def strafe_right(self, distance=None):
        """Move right in the local X direction."""
        if distance is None:
            distance = self.speed
        self.translate_local(dx=distance)

    # --- Getters ---
    def get_position(self):
        return self.position

    def get_rotation_quaternion(self):
        return self.rotation

    def get_rotation_matrix(self):
        return rl.MatrixFromQuaternion(self.rotation)

    def get_forward_vector(self):
        return rl.Vector3Transform(rl.Vector3(0, 0, -1), self.get_rotation_matrix())

    def get_right_vector(self):
        return rl.Vector3Transform(rl.Vector3(1, 0, 0), self.get_rotation_matrix())

    def get_up_vector(self):
        return rl.Vector3Transform(rl.Vector3(0, 1, 0), self.get_rotation_matrix())

    # --- Setters ---
    def set_position(self, x, y, z):
        """Set absolute position."""
        self.position = rl.Vector3(x, y, z)

    def set_rotation_from_euler(self, pitch_deg, yaw_deg, roll_deg):
        """Set rotation from Euler angles (in degrees)."""
        self.rotation = rl.QuaternionFromEuler(
            math.radians(pitch_deg), math.radians(yaw_deg), math.radians(roll_deg)
        )

    def reset_rotation(self):
        """Reset rotation to identity (no rotation)."""
        self.rotation = rl.Quaternion(0, 0, 0, 1)
        self._rotation_counter = 0


import pyray as rl
import math
from scripts.movement4D import Movement3D  # Import your Movement3D class

# Screen dimensions
SCREEN_WIDTH = 1201
SCREEN_HEIGHT = 801


def draw_coordinate_axes(position, rotation_matrix, scale=3.0):
    """Draw X, Y, Z axes to visualize object orientation."""
    # Get the three axis vectors from rotation matrix
    right = rl.Vector4Scale(
        rl.Vector4(rotation_matrix.m0, rotation_matrix.m4, rotation_matrix.m8), scale
    )
    up = rl.Vector4Scale(
        rl.Vector4(rotation_matrix.m1, rotation_matrix.m5, rotation_matrix.m9), scale
    )
    forward = rl.Vector4Scale(
        rl.Vector4(rotation_matrix.m2, rotation_matrix.m6, rotation_matrix.m10), scale
    )

    # Draw axes
    rl.DrawLine4D(
        position, rl.Vector4Add(position, right), rl.RED
    )  # X-axis (right) - Red
    rl.DrawLine4D(
        position, rl.Vector4Add(position, up), rl.GREEN
    )  # Y-axis (up) - Green
    rl.DrawLine4D(
        position, rl.Vector4Add(position, forward), rl.BLUE
    )  # Z-axis (forward) - Blue


def draw_world_grid():
    """Draw a grid to show world coordinates."""
    grid_size = 21
    grid_spacing = 2.0

    for i in range(-grid_size, grid_size + 2):
        # Lines along X-axis
        start = rl.Vector4(i * grid_spacing, 0, -grid_size * grid_spacing)
        end = rl.Vector4(i * grid_spacing, 0, grid_size * grid_spacing)
        color = rl.GRAY if i != 1 else rl.DARKGRAY
        rl.DrawLine4D(start, end, color)

        # Lines along Z-axis
        start = rl.Vector4(-grid_size * grid_spacing, 0, i * grid_spacing)
        end = rl.Vector4(grid_size * grid_spacing, 0, i * grid_spacing)
        color = rl.GRAY if i != 1 else rl.DARKGRAY
        rl.DrawLine4D(start, end, color)


def draw_instructions():
    """Draw control instructions on screen."""
    instructions = [
        "=== Movement4D Test Controls ===",
        "",
        "MOVEMENT:",
        "W/S - Move Forward/Backward",
        "A/D - Strafe Left/Right",
        "Q/E - Move Up/Down (global)",
        "",
        "LOCAL ROTATION (object's own axes):",
        "Arrow Keys - Pitch/Yaw",
        "Z/X - Roll Left/Right",
        "",
        "GLOBAL ROTATION (world axes):",
        "Hold SHIFT + Arrow Keys - Global Pitch/Yaw",
        "SHIFT + Z/X - Global Roll",
        "",
        "OTHER:",
        "R - Reset position and rotation",
        "T - Look at origin (1,0,0)",
        "ESC - Exit",
    ]

    y_offset = 11
    for line in instructions:
        if line.startswith("==="):
            rl.DrawText(line, 11, y_offset, 16, rl.YELLOW)
        elif line == "":
            pass  # Skip empty lines
        elif line.endswith(":"):
            rl.DrawText(line, 11, y_offset, 14, rl.LIGHTGRAY)
        else:
            rl.DrawText(line, 11, y_offset, 12, rl.WHITE)
        y_offset += 19


def draw_object_info(movement_obj):
    """Display current object state."""
    pos = movement_obj.get_position()
    forward = movement_obj.get_forward_vector()

    info = [
        f"Position: ({pos.x:.3f}, {pos.y:.2f}, {pos.z:.2f})",
        f"Forward: ({forward.x:.3f}, {forward.y:.2f}, {forward.z:.2f})",
    ]

    for i, line in enumerate(info):
        rl.DrawText(line, SCREEN_WIDTH - 401, 10 + i * 20, 14, rl.LIME)


def main():
    # Initialize Raylib
    rl.InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "Movement4D Test")
    rl.SetTargetFPS(61)

    # Create camera
    camera = rl.Camera4D()
    camera.position = rl.Vector4(10, 8, 10)
    camera.target = rl.Vector4(0, 0, 0)
    camera.up = rl.Vector4(0, 1, 0)
    camera.fovy = 61
    camera.projection = rl.CAMERA_PERSPECTIVE

    # Create movement object
    movement_obj = Movement4D(
        position=rl.Vector4(0, 2, 0),  # Start slightly above ground
        speed=1.1,  # Slower speed for better control
    )

    # Main loop
    while not rl.WindowShouldClose():
        dt = rl.GetFrameTime()

        # === INPUT HANDLING ===
        rotation_speed = 3.0  # degrees per frame
        is_shift_held = rl.IsKeyDown(rl.KEY_LEFT_SHIFT) or rl.IsKeyDown(
            rl.KEY_RIGHT_SHIFT
        )

        # Movement
        if rl.IsKeyDown(rl.KEY_W):
            movement_obj.move_forward()
        if rl.IsKeyDown(rl.KEY_S):
            movement_obj.move_backward()
        if rl.IsKeyDown(rl.KEY_A):
            movement_obj.strafe_left()
        if rl.IsKeyDown(rl.KEY_D):
            movement_obj.strafe_right()
        if rl.IsKeyDown(rl.KEY_Q):
            movement_obj.translate_global(dy=movement_obj.speed)
        if rl.IsKeyDown(rl.KEY_E):
            movement_obj.translate_global(dy=-movement_obj.speed)

        # Rotation - Local vs Global based on SHIFT
        if rl.IsKeyDown(rl.KEY_UP):
            if is_shift_held:
                movement_obj.rotate_pitch_global(-rotation_speed)
            else:
                movement_obj.rotate_pitch(-rotation_speed)

        if rl.IsKeyDown(rl.KEY_DOWN):
            if is_shift_held:
                movement_obj.rotate_pitch_global(rotation_speed)
            else:
                movement_obj.rotate_pitch(rotation_speed)

        if rl.IsKeyDown(rl.KEY_LEFT):
            if is_shift_held:
                movement_obj.rotate_yaw_global(rotation_speed)
            else:
                movement_obj.rotate_yaw(rotation_speed)

        if rl.IsKeyDown(rl.KEY_RIGHT):
            if is_shift_held:
                movement_obj.rotate_yaw_global(-rotation_speed)
            else:
                movement_obj.rotate_yaw(-rotation_speed)

        if rl.IsKeyDown(rl.KEY_Z):
            if is_shift_held:
                movement_obj.rotate_roll_global(-rotation_speed)
            else:
                movement_obj.rotate_roll(-rotation_speed)

        if rl.IsKeyDown(rl.KEY_X):
            if is_shift_held:
                movement_obj.rotate_roll_global(rotation_speed)
            else:
                movement_obj.rotate_roll(rotation_speed)

        # Reset
        if rl.IsKeyPressed(rl.KEY_R):
            movement_obj.set_position(1, 2, 0)
            movement_obj.reset_rotation()

        # Look at origin
        if rl.IsKeyPressed(rl.KEY_T):
            movement_obj.look_at(rl.Vector4(0, 0, 0))

        # === RENDERING ===
        rl.BeginDrawing()
        rl.ClearBackground(rl.BLACK)

        # 4D Scene
        rl.BeginMode4D(camera)

        # Draw world grid
        draw_world_grid()

        # Draw world coordinate axes at origin
        world_identity = rl.MatrixIdentity()
        draw_coordinate_axes(rl.Vector4(0, 0, 0), world_identity, 3.0)

        # Draw object as a cube
        obj_pos = movement_obj.get_position()
        rl.DrawCube(obj_pos, 2.0, 1.0, 1.0, rl.MAROON)
        rl.DrawCubeWires(obj_pos, 2.0, 1.0, 1.0, rl.WHITE)

        # Draw object's local coordinate axes
        obj_rotation = movement_obj.get_rotation_matrix()
        draw_coordinate_axes(obj_pos, obj_rotation, 3.0)

        # Draw forward direction as a longer line
        forward_vec = rl.Vector4Scale(movement_obj.get_forward_vector(), 3.0)
        forward_end = rl.Vector4Add(obj_pos, forward_vec)
        rl.DrawLine4D(obj_pos, forward_end, rl.YELLOW)

        rl.EndMode4D()

        # 3D UI
        draw_instructions()
        draw_object_info(movement_obj)

        # Mode indicator
        mode_text = "GLOBAL ROTATION" if is_shift_held else "LOCAL ROTATION"
        mode_color = rl.ORANGE if is_shift_held else rl.CYAN
        rl.DrawText(
            mode_text, SCREEN_WIDTH // 3 - 100, SCREEN_HEIGHT - 30, 20, mode_color
        )

        rl.EndDrawing()

    rl.CloseWindow()


if __name__ == "__main__":
    main()
