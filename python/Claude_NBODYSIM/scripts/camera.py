"""
╔══════════════════════════════════════════════════════════════╗
║  camera.py                                                   ║
║  Matrix-rotation orbit camera — avoids gimbal lock           ║
╚══════════════════════════════════════════════════════════════╝
"""

import pyray as rl
from pyray import Vector3, Matrix


# ══ Camera ══════════════════════════════════════════════════════════════════════════╗
                                                                                    # ║
class Camera:                                                                       # ║
                                                                                    # ║
    # ── Init ─────────────────────────────────────────────────────────────         # ║
    def __init__(self):                                                             # ║
        self.zoom             = 50.0                                                # ║
        self.sensitivity      = 0.03                                                # ║
        self.target_position  = rl.Vector3(0, 0, 0)                                 # ║
        self.target_body      = None                                                # ║
        self.rot_matrix       = rl.matrix_identity()                                # ║
                                                                                    # ║
        self.rl_cam = rl.Camera3D(                                                  # ║
            rl.Vector3(0, 0, self.zoom),    # position                              # ║
            rl.Vector3(0, 0, 0),            # target                                # ║
            rl.Vector3(0, 1, 0),            # up                                    # ║
            45,                             # fovy                                  # ║
            rl.CAMERA_PERSPECTIVE,                                                  # ║
        )                                                                           # ║
                                                                                    # ║
    # ── Update ───────────────────────────────────────────────────────────         # ║
    def update(self):                                                               # ║
        if self.target_body is not None:                                            # ║
            self.target_position = Vector3(self.target_body.position.x,             # ║
                                           self.target_body.position.y,             # ║
                                           self.target_body.position.z)             # ║
                                                                                    # ║
        # extract forward and up vectors from rotation matrix columns               # ║
        forward = Vector3(                                                          # ║
            -self.rot_matrix.m8,                                                    # ║
            -self.rot_matrix.m9,                                                    # ║
            -self.rot_matrix.m10,                                                   # ║
        )                                                                           # ║
        self.rl_cam.up = Vector3(                                                   # ║
            self.rot_matrix.m4,                                                     # ║
            self.rot_matrix.m5,                                                     # ║
            self.rot_matrix.m6,                                                     # ║
        )                                                                           # ║
                                                                                    # ║
        # place camera behind target along the forward vector                       # ║
        self.rl_cam.position.x = self.target_position.x - forward.x * self.zoom     # ║
        self.rl_cam.position.y = self.target_position.y - forward.y * self.zoom     # ║
        self.rl_cam.position.z = self.target_position.z - forward.z * self.zoom     # ║
        self.rl_cam.target = self.target_position                                   # ║
                                                                                    # ║
    # ── Orbit ────────────────────────────────────────────────────────────         # ║
    def orbit(self, delta_x, delta_y):                                              # ║
        # accumulate rotations into rot_matrix to avoid gimbal lock                 # ║
        # Y rotation applied globally, X rotation applied locally                   # ║
        y_rotation  = rl.matrix_rotate_y(-delta_x * self.sensitivity)               # ║
        x_rotation  = rl.matrix_rotate_x(-delta_y * self.sensitivity)               # ║
        self.rot_matrix = rl.matrix_multiply(y_rotation, self.rot_matrix)           # ║
        self.rot_matrix = rl.matrix_multiply(x_rotation, self.rot_matrix)           # ║
                                                                                    # ║
    # ── Zoom & Target ────────────────────────────────────────────────────         # ║
    def set_zoom(self, scroll):                                                     # ║
        self.zoom -= scroll * 2.0                                                   # ║
                                                                                    # ║
    def get(self):                                                                  # ║
        return self.rl_cam                                                          # ║
                                                                                    # ║
    def set_target_pos(self, target_position):                                      # ║
        # clears body tracking and locks to a fixed point                           # ║
        self.target_body     = None                                                 # ║
        self.target_position = target_position                                      # ║
                                                                                    # ║
    def set_target_body(self, body):                                                # ║
        self.target_body = body                                                     # ║
                                                                                    # ║
# ════════════════════════════════════════════════════════════════════════════════════╝
