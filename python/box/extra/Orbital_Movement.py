import pyray as rl
import math

from gravity import SCREEN_HEIGHT, SCREEN_WIDTH


# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
G = 6.674 * 10e-11
G2 = 1 * 10e-3

# G = G2


def init_window(width=SCREEN_WIDTH, height=SCREEN_HEIGHT, title="Raylib Window"):
    """Basic Raylaib window"""
    rl.init_window(width, height, title)


class Body:
    def __init__(self, x, y, z, vx, vy, vz, mass, radius, color, fixed=False):
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx  # Velocity x
        self.vy = vy  # velocity y
        self.vz = vz  # velocity z
        self.mass = mass
        self.radius = radius
        self.color = color
        self.fixed = fixed  # if true, locks body

        # trail effect
        self.trail = []
        self.max_trail_length = 150

    def apply_force(self, fx, fy, fz):
        if self.fixed:
            return

        # F = ma, so a = F/m
        ax = fx / self.mass
        ay = fy / self.mass
        az = fz / self.mass
        self.vx += ax
        self.vy += ay
        self.vz += az

    def update(self, dt):
        if self.fixed:
            return

        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt

        # add current pos to trail
        self.trail.append((self.x, self.y, self.z))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

    def get_position(self):
        return rl.Vector3(self.x, self.y, self.z)

    def get_velocity(self):
        return rl.Vector3(self.vx, self.vy, self.vz)

    def draw(self):
        position = self.get_position()

        # trail
        if len(self.trail) > 1:
            for i in range(len(self.trail) - 1):
                alpha = i / len(self.trail)
                trail_color = (
                    int(self.color[0] * alpha),
                    int(self.color[1] * alpha),
                    int(self.color[2] * alpha),
                    int(255 * alpha),
                )

                start_pos = rl.Vector3(
                    self.trail[i + 1][0], self.trail[i][1], self.trail[i][2]
                )
                end_pos = rl.Vector3(
                    self.trail[i + 1][0], self.trail[i + 1][1], self.trail[i + 1][2]
                )
                rl.draw_line_3d(start_pos, end_pos, trail_color)

        # Draw body as sphere
        rl.draw_sphere(position, self.radius, self.color)

        # Draw wireframe
        rl.draw_sphere_wires(position, self.radius, 8, 8, rl.WHITE)


# consider more general name for camera class
# allow multiple camera modes
class OrbitCamera:
    def __init__(self, target=(0, 0, 0), distance=10, yaw=0, pitch=20, fovy=60):
        self.target = rl.Vector3(*target)
        self.distance = distance
        self.yaw = math.radians(yaw)
        self.pitch = math.radians(pitch)

        self.camera = rl.Camera3D()
        self.camera.target = self.target
        self.camera.fovy = fovy
        self.camera.up = rl.Vector3(0, 1, 0)

        self.update_position()


def main():
    init_window()

    while not rl.window_should_close():
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)

        """
        set up scene with a camera looking at a sphere(body)
        the body is fixed on point 0,0,0

        the camera, using w a s d keys, can "orbit" around the planet
        movement should be relative to camera north, not the bodies north
        """

        cam.begin()
        rl.draw_grid(20, 1.0)
        cam.end()

        rl.end_drawing()
    rl.close_window()


if __name__ == "__main__":
    main()
