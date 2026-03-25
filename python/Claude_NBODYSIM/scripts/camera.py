# scripts/camera.py
import pyray as rl
from pyray import Vector3, Matrix


class Camera:
    def __init__(
        self,
        target_position=None,
        target_body=None,
        orbit_dist=50.0,
        sensitivity=0.03,
    ):
        self.target = target_position if target_position else Vector3(0, 0, 0)
        self.target_body = target_body
        self.orbit_dist = orbit_dist
        self.sensitivity = sensitivity

        # Initialize the camera
        self.camera = rl.Camera3D(
            Vector3(0, 0, orbit_dist),  # position
            Vector3(0, 0, 0),  # target
            Vector3(0, 1, 0),  # up
            45,  # fovy
            rl.CAMERA_PERSPECTIVE,  # projection
        )

        # ----------------------------- Rotation matrix ---
        self.camera_rotation = Matrix( 1.0, 0.0, 0.0, 0.0,
                                       0.0, 1.0, 0.0, 0.0,
                                       0.0, 0.0, 1.0, 0.0,
                                       0.0, 0.0, 0.0, 1.0, )

    def update(self, bodies=None):
        if self.target_body is not None:
            self.target = self.target_body.get_position()

        self.update_camera_free_6dof()

    def update_camera_free_6dof(self):
        """Free 6DOF rotation using rotation matrices"""

        # Forward vector from rotation matrix
        forward = Vector3(
            -self.camera_rotation.m8,
            -self.camera_rotation.m9,
            -self.camera_rotation.m10,
        )

        # Up vector from rotation matrix
        self.camera.up = Vector3(
            self.camera_rotation.m4,
            self.camera_rotation.m5,
            self.camera_rotation.m6,
        )

        # Camera position
        self.camera.position.x = self.target.x - forward.x * self.orbit_dist
        self.camera.position.y = self.target.y - forward.y * self.orbit_dist
        self.camera.position.z = self.target.z - forward.z * self.orbit_dist

        self.camera.target = self.target

    def orbit(self, delta_x, delta_y):
        y_rotation = rl.matrix_rotate_y(-delta_x * self.sensitivity)
        x_rotaion  = rl.matrix_rotate_x(-delta_y * self.sensitivity)
        self.camera_rotation = rl.matrix_multiply(y_rotation, self.camera_rotation)
        self.camera_rotation = rl.matrix_multiply(x_rotation, self.camera_rotation)

    def zoom(self, scroll):
        """Control distance from body"""
        self.orbit_dist = self.orbit_dist - scroll * 2.0

    def get(self):
        """Return camera object for rendering"""
        return self.camera

    def set_target(self, target_position):
        """Update target position"""
        self.target_body = None
        self.target = target_position

    def set_target_body(self, body):
        """Update target to follow a body"""
        self.target_body = body

    def set_orbit_dist(self, x):
        """Update orbit radius"""
        self.orbit_dist = x
