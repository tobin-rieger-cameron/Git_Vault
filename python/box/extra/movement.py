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
