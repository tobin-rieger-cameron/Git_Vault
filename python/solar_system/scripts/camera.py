# import pyray as rl
import pyray as rl
from pyray import Vector3, Matrix


class OrbitCam:
    def __init__(
        self, target_position=None, target_body=None, orbit_dist=50.0, sensitivity=0.01
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

        # --- Rotation matrix
        self.camera_rotation = Matrix( 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0,)

    def update(self, bodies=None):
        if self.target_body is not None:
            self.target = self.target_body.get_position()

        self.update_camera_free_6dof()
        self.change_target(bodies)
        self.set_orbit_dist(self.orbit_dist - rl.get_mouse_wheel_move())

    def update_camera_free_6dof(self):
        """Free 6DOF rotation using rotation matrices"""

        # --- Camera-relative mouse rotation
        if rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT):
            delta = rl.get_mouse_delta()

            # Y-axis (yaw)
            y_rotation = rl.matrix_rotate_y(-delta.x * self.sensitivity)

            # X-axis (pitch)
            x_rotation = rl.matrix_rotate_x(-delta.y * self.sensitivity)

            self.camera_rotation = rl.matrix_multiply(y_rotation, self.camera_rotation)
            self.camera_rotation = rl.matrix_multiply(x_rotation, self.camera_rotation)

        # --- Camera-relative keyboard rotation
        rotation_keys = [
            (rl.KEY_A, rl.matrix_rotate_y, -0.02),
            (rl.KEY_D, rl.matrix_rotate_y, 0.02),
            (rl.KEY_W, rl.matrix_rotate_x, -0.02),
            (rl.KEY_S, rl.matrix_rotate_x, 0.02),
            (rl.KEY_Q, rl.matrix_rotate_z, -0.02),
            (rl.KEY_E, rl.matrix_rotate_z, 0.02),
        ]

        for key, rot_func, angle in rotation_keys:
            if rl.is_key_down(key):
                rotation = rot_func(angle)
                self.camera_rotation = rl.matrix_multiply(
                    rotation, self.camera_rotation
                )

        # Forward vector from rotation matrix
        forward = Vector3(
            -self.camera_rotation.m8,
            -self.camera_rotation.m9,
            -self.camera_rotation.m10,
        )

        # Up vector from rotation matrix
        self.camera.up = Vector3(
            self.camera_rotation.m4, self.camera_rotation.m5, self.camera_rotation.m6
        )

        # Camera position
        self.camera.position.x = self.target.x - forward.x * self.orbit_dist
        self.camera.position.y = self.target.y - forward.y * self.orbit_dist
        self.camera.position.z = self.target.z - forward.z * self.orbit_dist

        self.camera.target = self.target

    def change_target(self, bodies):
        """Change target position"""
        if bodies is None:
            return

        if rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT):
            mouse_pos = rl.get_mouse_position()
            ray = rl.get_screen_to_world_ray(mouse_pos, self.camera)

            closest_distance = float("inf")
            clicked_body = None

            for body in bodies:
                collision = rl.get_ray_collision_sphere(
                    ray, body.get_position(), body.radius
                )

                if collision.hit and collision.distance < closest_distance:
                    closest_distance = collision.distance
                    clicked_body = body

            if clicked_body is not None:
                self.target_body = clicked_body
                self.target = clicked_body.get_position()

    def get_camera(self):
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
