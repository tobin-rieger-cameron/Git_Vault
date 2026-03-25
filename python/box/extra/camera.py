# scripts/camera.py
import pyray as rl
import math


class Camera:
    def __init__(self, x, y, z, target, radius, sensitivity=0.01):
        self.x = x
        self.y = y
        self.z = z
        self.target = target
        self.radius = radius
        self.sensitivity = sensitivity

        # Spherical coordinates for camera position
        self.theta = math.atan2(z, x)  # Horizontal angle
        self.phi = math.acos(y / radius)  # Vertical angle

        # Raylib camera object
        self.camera = rl.Camera3D()
        self.camera.target = rl.Vector3(target.x, target.y, target.z)
        self.camera.up = rl.Vector3(0.0, 1.0, 0.0)
        self.camera.fovy = 45.0
        self.camera.projection = rl.CAMERA_PERSPECTIVE

        self.update_position()

    def update_position(self):
        """Update camera position based on spherical coordinates"""
        # Convert spherical to cartesian coordinates
        x = self.radius * math.sin(self.phi) * math.cos(self.theta)
        z = self.radius * math.sin(self.phi) * math.sin(self.theta)
        y = self.radius * math.cos(self.phi)

        # Add target offset
        x += self.target.x
        y += self.target.y
        z += self.target.z

        self.camera.position = rl.Vector3(x, y, z)

    def update(self):
        """Update camera based on mouse movement"""
        mouse_delta = rl.get_mouse_delta()

        # Update angles based on mouse movement
        self.theta -= mouse_delta.x * self.sensitivity
        self.phi += mouse_delta.y * self.sensitivity

        # Clamp phi to prevent camera from flipping
        self.phi = max(0.1, min(math.pi - 0.1, self.phi))

        # Handle mouse wheel for zooming
        wheel = rl.get_mouse_wheel_move()
        self.radius = max(2.0, self.radius - wheel)

        self.update_position()

    def get_camera(self):
        """Return the raylib Camera3D object"""
        return self.camera

    def set_target(self, target):
        """Update the camera target"""
        self.target = target
        self.camera.target = rl.Vector3(target.x, target.y, target.z)
        self.update_position()
