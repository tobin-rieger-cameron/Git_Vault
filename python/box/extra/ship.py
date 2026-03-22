# ship.py
import pyray as rl
from utils.vector3d import Vector3D
import math

class Ship:
    def __init__(self, position=None):
        self.position = position if position else Vector3D(0, 0, -100)
        self.velocity = Vector3D(0, 0, 0)
        self.mass = 1000.0

        # --- Orientation ---
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0

        # --- Movement ---
        self.thrust_input = Vector3D(0, 0, 0)
        self.thrust_strength = 50000.0
        self.mouse_sensitivity = 0.003

        # --- Gravity Toggle ---
        self.use_gravity = True
        self.gravity_force = Vector3D(0, -9.81, 0)

        # --- Camera ---
        self.camera = rl.Camera3D(
            rl.Vector3(0, 0, 0),
            rl.Vector3(0, 0, 1),
            rl.Vector3(0, 1, 0),
            70.0,
            rl.CAMERA_PERSPECTIVE
        )

    def handle_input(self, dt):
        # --- Mouse look ---
        if rl.is_cursor_hidden():
            mouse_delta = rl.get_mouse_delta()
            self.yaw += mouse_delta.x * self.mouse_sensitivity
            self.pitch -= mouse_delta.y * self.mouse_sensitivity
            self.pitch = max(-math.pi/2, min(math.pi/2, self.pitch))

        # --- Keyboard movement input ---
        thrust_x = thrust_y = thrust_z = 0
        if rl.is_key_down(rl.KEY_D):          thrust_x += 1
        if rl.is_key_down(rl.KEY_A):          thrust_x -= 1
        if rl.is_key_down(rl.KEY_SPACE):      thrust_y += 1
        if rl.is_key_down(rl.KEY_LEFT_SHIFT): thrust_y -= 1
        if rl.is_key_down(rl.KEY_W):          thrust_z += 1
        if rl.is_key_down(rl.KEY_S):          thrust_z -= 1

        self.thrust_input = Vector3D(thrust_x, thrust_y, thrust_z)

        # --- Gravity toggle (G) ---
        if rl.is_key_pressed(rl.KEY_G):
            self.use_gravity = not self.use_gravity
        
        # --- Reset Velocity (R) ---
        if rl.is_key_pressed(rl.KEY_R):
            self.reset_velocity()

        # --- Simple Teleport (T) ---
        if rl.is_key_pressed(rl.KEY_T):
            self.teleport_to(0, 100, 0)

    def reset_velocity(self):
        self.velocity = Vector3D(0, 0, 0)

    def teleport_to(self, x, y, z):
        self.position = Vector3D(x, y, z)
        self.reset_velocity()

    def get_forward_vector(self):
        cos_pitch = math.cos(self.pitch)
        sin_pitch = math.sin(self.pitch)
        cos_yaw = math.cos(self.yaw)
        sin_yaw = math.sin(self.yaw)
        return Vector3D(cos_pitch * sin_yaw, sin_pitch, cos_pitch * cos_yaw)

    def get_right_vector(self):
        return Vector3D(math.cos(self.yaw), 0, -math.sin(self.yaw))

    def get_up_vector(self):
        forward = self.get_forward_vector()
        right = self.get_right_vector()
        return Vector3D(
            right.y * forward.z - right.z * forward.y,
            right.z * forward.x - right.x * forward.z,
            right.x * forward.y - right.y * forward.x
        )

    def update_physics(self, dt):
        # Simplified thrust (no gravity yet)
        forward = self.get_forward_vector()
        right = self.get_right_vector()
        up = self.get_up_vector()

        thrust_world = (
            right * self.thrust_input.x +
            up * self.thrust_input.y +
            forward * self.thrust_input.z
        ) * (self.thrust_strength / self.mass)

        acceleration = thrust_world
        if self.use_gravity:
            acceleration = acceleration + self.gravity_force

        self.velocity = self.velocity + acceleration * dt
        self.position = self.position + self.velocity * dt

    def update_camera(self):
        self.camera.position = self.position.to_raylib()
        target = self.position + self.get_forward_vector()
        self.camera.target = target.to_raylib()
        self.camera.up = self.get_up_vector().to_raylib()

    def draw_debug(self):
        # Draw position axis at ship location
        rl.draw_line_3d(self.position.to_raylib(),
                        (self.position + Vector3D(5, 0, 0)).to_raylib(),
                        rl.RED)
        rl.draw_line_3d(self.position.to_raylib(),
                        (self.position + Vector3D(0, 5, 0)).to_raylib(),
                        rl.GREEN)
        rl.draw_line_3d(self.position.to_raylib(),
                        (self.position + Vector3D(0, 0, 5)).to_raylib(),
                        rl.BLUE)
