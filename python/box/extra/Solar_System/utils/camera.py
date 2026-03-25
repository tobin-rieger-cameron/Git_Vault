# utils/camera.py
import pyray as rl
import math
from utils.vector3d import Vector3D


class Camera:
    """
    A standardized camera class for PyRay applications.
    Supports multiple camera modes: FPS, Orbital, Free, and Fixed.
    """

    # Camera mode constants
    MODE_FPS = "fps"
    MODE_ORBITAL = "orbital"
    MODE_FREE = "free"
    MODE_FIXED = "fixed"

    def __init__(
        self, mode=MODE_ORBITAL, position=None, target=None, up=None, fovy=60.0
    ):
        self.mode = mode

        # Default positions
        self.position = position or Vector3D(10.0, 10.0, 10.0)
        self.target = target or Vector3D(0.0, 0.0, 0.0)
        self.up = up or Vector3D(0.0, 1.0, 0.0)
        self.fovy = fovy

        # Orbital camera specific parameters
        self.distance = self._calculate_distance()
        self.angle_horizontal = 0.0
        self.angle_vertical = 0.0
        self.min_distance = 1.0
        self.max_distance = 100.0

        # Movement sensitivity
        self.mouse_sensitivity = 0.005
        self.zoom_sensitivity = 1.0
        self.move_speed = 5.0

        # Create PyRay camera
        self._update_pyray_camera()

    def _calculate_distance(self):
        """Calculate distance from camera to target."""
        dx = self.position.x - self.target.x
        dy = self.position.y - self.target.y
        dz = self.position.z - self.target.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _update_pyray_camera(self):
        """Update the internal PyRay camera object."""
        self.pyray_camera = rl.Camera3D(
            [self.position.x, self.position.y, self.position.z],
            [self.target.x, self.target.y, self.target.z],
            [self.up.x, self.up.y, self.up.z],
            self.fovy,
            rl.CAMERA_PERSPECTIVE,
        )

    def begin_mode_3d(self):
        """Begin 3D camera mode. Call before drawing 3D objects."""
        self._update_pyray_camera()
        rl.begin_mode_3d(self.pyray_camera)

    def end_mode_3d(self):
        """End 3D camera mode. Call after drawing 3D objects."""
        rl.end_mode_3d()

    def update(self, delta_time=None):
        """
        Update camera based on input and current mode.

        Args:
            delta_time (float): Time since last frame (optional)
        """
        if delta_time is None:
            delta_time = rl.get_frame_time()

        if self.mode == self.MODE_ORBITAL:
            self._update_orbital(delta_time)
        elif self.mode == self.MODE_FPS:
            self._update_fps(delta_time)
        elif self.mode == self.MODE_FREE:
            self._update_free(delta_time)
        # Fixed mode doesn't update automatically

    def _update_orbital(self, delta_time):
        """Update orbital camera mode."""
        # Mouse input for rotation
        mouse_delta = rl.get_mouse_delta()
        if rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT):
            self.angle_horizontal -= mouse_delta.x * self.mouse_sensitivity
            self.angle_vertical -= mouse_delta.y * self.mouse_sensitivity

            # Clamp vertical angle to avoid flipping
            self.angle_vertical = max(
                -math.pi / 2 + 0.1, min(math.pi / 2 - 0.1, self.angle_vertical)
            )

        # Scroll wheel for zoom
        wheel_move = rl.get_mouse_wheel_move()
        if wheel_move != 0:
            self.distance -= wheel_move * self.zoom_sensitivity
            self.distance = max(
                self.min_distance, min(self.max_distance, self.distance)
            )

        # Calculate new position based on angles and distance
        self.position.x = self.target.x + self.distance * math.cos(
            self.angle_vertical
        ) * math.cos(self.angle_horizontal)
        self.position.y = self.target.y + self.distance * math.sin(self.angle_vertical)
        self.position.z = self.target.z + self.distance * math.cos(
            self.angle_vertical
        ) * math.sin(self.angle_horizontal)

    def _update_fps(self, delta_time):
        """Update FPS camera mode."""
        # Use PyRay's built-in FPS camera update
        rl.update_camera(self.pyray_camera, rl.CAMERA_FIRST_PERSON)

        # Sync our vectors with PyRay camera
        self.position.x = self.pyray_camera.position.x
        self.position.y = self.pyray_camera.position.y
        self.position.z = self.pyray_camera.position.z
        self.target.x = self.pyray_camera.target.x
        self.target.y = self.pyray_camera.target.y
        self.target.z = self.pyray_camera.target.z

    def _update_free(self, delta_time):
        """Update free camera mode."""
        # Use PyRay's built-in free camera update
        rl.update_camera(self.pyray_camera, rl.CAMERA_FREE)

        # Sync our vectors with PyRay camera
        self.position.x = self.pyray_camera.position.x
        self.position.y = self.pyray_camera.position.y
        self.position.z = self.pyray_camera.position.z
        self.target.x = self.pyray_camera.target.x
        self.target.y = self.pyray_camera.target.y
        self.target.z = self.pyray_camera.target.z

    def set_position(self, x, y, z):
        """Set camera position."""
        self.position.x, self.position.y, self.position.z = x, y, z
        if self.mode == self.MODE_ORBITAL:
            self.distance = self._calculate_distance()

    def set_target(self, x, y, z):
        """Set camera target."""
        self.target.x, self.target.y, self.target.z = x, y, z
        if self.mode == self.MODE_ORBITAL:
            self.distance = self._calculate_distance()

    def set_mode(self, mode):
        """Change camera mode."""
        if mode in [self.MODE_FPS, self.MODE_ORBITAL, self.MODE_FREE, self.MODE_FIXED]:
            self.mode = mode
            if mode == self.MODE_ORBITAL:
                self.distance = self._calculate_distance()
        else:
            print(f"Warning: Unknown camera mode '{mode}'")

    def get_position(self):
        """Get current camera position as Vector3D."""
        return Vector3D(self.position.x, self.position.y, self.position.z)

    def get_target(self):
        """Get current camera target as Vector3D."""
        return Vector3D(self.target.x, self.target.y, self.target.z)

    def get_forward_vector(self):
        """Get the forward direction vector of the camera."""
        forward = Vector3D(
            self.target.x - self.position.x,
            self.target.y - self.position.y,
            self.target.z - self.position.z,
        )
        # Normalize the vector
        length = math.sqrt(forward.x**2 + forward.y**2 + forward.z**2)
        if length > 0:
            forward.x /= length
            forward.y /= length
            forward.z /= length
        return forward

    def look_at(self, target_pos, smooth=False, speed=2.0):
        """
        Make camera look at a specific position.

        Args:
            target_pos (Vector3D): Position to look at
            smooth (bool): Whether to smoothly transition
            speed (float): Speed of smooth transition
        """
        if smooth:
            # Smooth interpolation toward target
            dt = rl.get_frame_time() * speed
            self.target.x += (target_pos.x - self.target.x) * dt
            self.target.y += (target_pos.y - self.target.y) * dt
            self.target.z += (target_pos.z - self.target.z) * dt
        else:
            # Immediate snap to target
            self.target.x = target_pos.x
            self.target.y = target_pos.y
            self.target.z = target_pos.z

        if self.mode == self.MODE_ORBITAL:
            self.distance = self._calculate_distance()

    def reset(self):
        """Reset camera to initial position and target."""
        self.position = Vector3D(10.0, 10.0, 10.0)
        self.target = Vector3D(0.0, 0.0, 0.0)
        self.up = Vector3D(0.0, 1.0, 0.0)
        self.angle_horizontal = 0.0
        self.angle_vertical = 0.0
        self.distance = self._calculate_distance()

    def set_orbital_constraints(self, min_dist=1.0, max_dist=100.0):
        """Set distance constraints for orbital mode."""
        self.min_distance = min_dist
        self.max_distance = max_dist
        self.distance = max(min_dist, min(max_dist, self.distance))

    def set_sensitivity(self, mouse_sens=0.005, zoom_sens=1.0, move_speed=5.0):
        """Set input sensitivity values."""
        self.mouse_sensitivity = mouse_sens
        self.zoom_sensitivity = zoom_sens
        self.move_speed = move_speed

    def get_info(self):
        """Get camera information as a dictionary."""
        return {
            "mode": self.mode,
            "position": (self.position.x, self.position.y, self.position.z),
            "target": (self.target.x, self.target.y, self.target.z),
            "distance": self.distance if self.mode == self.MODE_ORBITAL else None,
            "fovy": self.fovy,
        }
