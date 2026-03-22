import pyray as rl
import math
import random

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800


class CelestialBody:
    def __init__(
        self,
        x,
        y,
        z,
        radius,
        color,
        orbital_radius=0,
        orbital_speed=0,
        orbital_inclination=0,
        parent=None,
    ):
        self.position = rl.Vector3(x, y, z)
        self.radius = radius
        self.color = color
        self.orbital_radius = orbital_radius
        self.orbital_speed = orbital_speed
        self.orbital_inclination = orbital_inclination  # Tilt of orbit in radians
        self.angle = random.uniform(0, 2 * math.pi)  # Random starting position
        self.rotation_angle = 0.0  # For body rotation
        self.rotation_speed = random.uniform(0.5, 2.0)
        self.parent = parent
        self.trail = []
        self.max_trail_length = 200

    def update(self, dt):
        # Update rotation
        self.rotation_angle += self.rotation_speed * dt

        if self.parent and self.orbital_radius > 0:
            # Update orbital position
            self.angle += self.orbital_speed * dt

            # Calculate 3D orbital position with inclination
            base_x = math.cos(self.angle) * self.orbital_radius
            base_z = math.sin(self.angle) * self.orbital_radius

            # Apply orbital inclination
            y_offset = base_z * math.sin(self.orbital_inclination)
            z_offset = base_z * math.cos(self.orbital_inclination)

            # Position relative to parent
            self.position.x = self.parent.position.x + base_x
            self.position.y = self.parent.position.y + y_offset
            self.position.z = self.parent.position.z + z_offset

        # Add current position to trail
        self.trail.append((self.position.x, self.position.y, self.position.z))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

    def draw(self):
        # Draw orbital path (only show orbit when parent exists)
        if self.orbital_radius > 0 and self.parent:
            # Draw orbit as a series of points
            orbit_points = []
            for i in range(64):  # 64 points for smooth circle
                angle = (i / 64) * 2 * math.pi
                base_x = math.cos(angle) * self.orbital_radius
                base_z = math.sin(angle) * self.orbital_radius

                # Apply inclination
                y_offset = base_z * math.sin(self.orbital_inclination)
                z_offset = base_z * math.cos(self.orbital_inclination)

                orbit_points.append(
                    rl.Vector3(
                        self.parent.position.x + base_x,
                        self.parent.position.y + y_offset,
                        self.parent.position.z + z_offset,
                    )
                )

            # Draw orbit lines
            orbit_color = rl.Color(60, 60, 60, 80)
            for i in range(len(orbit_points)):
                next_i = (i + 1) % len(orbit_points)
                rl.draw_line_3d(orbit_points[i], orbit_points[next_i], orbit_color)

        # Draw trail
        if len(self.trail) > 2:
            for i in range(1, len(self.trail)):
                alpha = int((i / len(self.trail)) * 120)
                # Handle color properly
                if hasattr(self.color, "r"):
                    trail_color = rl.Color(
                        self.color.r, self.color.g, self.color.b, alpha
                    )
                else:
                    r, g, b = self.color[:3]
                    trail_color = rl.Color(r, g, b, alpha)

                start_pos = rl.Vector3(
                    self.trail[i - 1][0], self.trail[i - 1][1], self.trail[i - 1][2]
                )
                end_pos = rl.Vector3(
                    self.trail[i][0], self.trail[i][1], self.trail[i][2]
                )
                rl.draw_line_3d(start_pos, end_pos, trail_color)

        # Draw the celestial body as a sphere
        rl.draw_sphere(self.position, self.radius, self.color)

        # Add wireframe for better 3D perception
        wireframe_color = rl.Color(255, 255, 255, 50)
        rl.draw_sphere_wires(self.position, self.radius, 8, 8, wireframe_color)

        # Special effects for the sun
        is_sun = self.radius > 15
        if is_sun:
            # Draw multiple glowing spheres for sun effect
            for i in range(3):
                glow_radius = self.radius + i * 2
                glow_alpha = max(10, 40 - i * 12)
                glow_color = rl.Color(255, 255, 0, glow_alpha)
                rl.draw_sphere(self.position, glow_radius, glow_color)


class Camera3D:
    def __init__(self):
        self.camera = rl.Camera3D()
        self.camera.position = rl.Vector3(400.0, 300.0, 400.0)
        self.camera.target = rl.Vector3(0.0, 0.0, 0.0)
        self.camera.up = rl.Vector3(0.0, 1.0, 0.0)
        self.camera.fovy = 45.0
        self.camera.projection = rl.CAMERA_PERSPECTIVE

        self.distance = 500.0
        self.angle_horizontal = 0.0
        self.angle_vertical = math.pi / 6  # 30 degrees up

    def update(self):
        # Handle camera controls
        if rl.is_key_down(rl.KEY_A):
            self.angle_horizontal -= 2.0 * rl.get_frame_time()
        if rl.is_key_down(rl.KEY_D):
            self.angle_horizontal += 2.0 * rl.get_frame_time()
        if rl.is_key_down(rl.KEY_W):
            self.angle_vertical = min(
                math.pi / 2 - 0.1, self.angle_vertical + 1.0 * rl.get_frame_time()
            )
        if rl.is_key_down(rl.KEY_S):
            self.angle_vertical = max(
                -math.pi / 2 + 0.1, self.angle_vertical - 1.0 * rl.get_frame_time()
            )

        # Zoom with mouse wheel
        wheel_move = rl.get_mouse_wheel_move()
        if wheel_move != 0:
            self.distance = max(100, min(1000, self.distance - wheel_move * 50))

        # Update camera position based on spherical coordinates
        self.camera.position.x = (
            math.cos(self.angle_vertical)
            * math.cos(self.angle_horizontal)
            * self.distance
        )
        self.camera.position.y = math.sin(self.angle_vertical) * self.distance
        self.camera.position.z = (
            math.cos(self.angle_vertical)
            * math.sin(self.angle_horizontal)
            * self.distance
        )


class SolarSystem:
    def __init__(self):
        self.bodies = []
        self.create_solar_system()
        self.paused = False
        self.time_scale = 1.0

    def create_solar_system(self):
        # Sun at origin
        sun = CelestialBody(0, 0, 0, 20, rl.YELLOW)
        self.bodies.append(sun)

        # Planets with realistic-ish relative sizes, distances, and orbital inclinations
        planets_data = [
            # (orbital_radius, radius, color, orbital_speed, inclination, name)
            (80, 3, rl.GRAY, 0.02, math.radians(7), "Mercury"),
            (110, 4, rl.ORANGE, 0.015, math.radians(3.4), "Venus"),
            (150, 5, rl.BLUE, 0.012, math.radians(0), "Earth"),
            (190, 4, rl.RED, 0.010, math.radians(1.9), "Mars"),
            (280, 12, rl.BROWN, 0.005, math.radians(1.3), "Jupiter"),
            (340, 10, rl.Color(255, 255, 150, 255), 0.004, math.radians(2.5), "Saturn"),
            (400, 7, rl.SKYBLUE, 0.003, math.radians(0.8), "Uranus"),
            (450, 7, rl.DARKBLUE, 0.002, math.radians(1.8), "Neptune"),
        ]

        for orbital_radius, radius, color, speed, inclination, name in planets_data:
            planet = CelestialBody(
                orbital_radius,
                0,
                0,
                radius,
                color,
                orbital_radius,
                speed,
                inclination,
                sun,
            )
            self.bodies.append(planet)

        # Add Earth's moon
        earth = self.bodies[3]  # Earth is the 4th body (index 3)
        moon = CelestialBody(
            earth.position.x + 25,
            earth.position.y,
            earth.position.z,
            2,
            rl.WHITE,
            25,
            0.05,
            math.radians(5.1),
            earth,
        )
        self.bodies.append(moon)

        # Add Saturn's rings effect with small particles
        saturn = self.bodies[6]  # Saturn
        for i in range(30):
            ring_distance = random.uniform(12, 18)  # Ring particles around Saturn
            ring_particle = CelestialBody(
                saturn.position.x + ring_distance,
                saturn.position.y,
                saturn.position.z,
                0.5,
                rl.LIGHTGRAY,
                ring_distance,
                0.02,
                math.radians(0),
                saturn,
            )
            self.bodies.append(ring_particle)

        # Add asteroid belt
        for _ in range(25):
            asteroid_distance = random.uniform(220, 260)  # Asteroid belt
            asteroid_inclination = random.uniform(-math.radians(10), math.radians(10))
            asteroid = CelestialBody(
                asteroid_distance,
                0,
                0,
                random.uniform(0.5, 1.5),
                rl.LIGHTGRAY,
                asteroid_distance,
                random.uniform(0.006, 0.008),
                asteroid_inclination,
                sun,
            )
            self.bodies.append(asteroid)

    def update(self, dt):
        if not self.paused:
            scaled_dt = dt * self.time_scale
            for body in self.bodies:
                body.update(scaled_dt)

    def draw(self):
        for body in self.bodies:
            body.draw()

    def toggle_pause(self):
        self.paused = not self.paused

    def change_time_scale(self, delta):
        self.time_scale = max(0.1, min(5.0, self.time_scale + delta))


def main():
    # Initialize Raylib
    rl.init_window(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "3D Solar System Simulation - Sebastian Lague Style",
    )
    rl.set_target_fps(60)

    solar_system = SolarSystem()
    camera = Camera3D()

    while not rl.window_should_close():
        dt = rl.get_frame_time() * 60  # Convert to 60 FPS equivalent

        # Handle input
        if rl.is_key_pressed(rl.KEY_SPACE):
            solar_system.toggle_pause()
        elif rl.is_key_pressed(rl.KEY_UP):
            solar_system.change_time_scale(0.2)
        elif rl.is_key_pressed(rl.KEY_DOWN):
            solar_system.change_time_scale(-0.2)
        elif rl.is_key_pressed(rl.KEY_R):
            solar_system = SolarSystem()  # Reset

        # Update camera
        camera.update()

        # Update solar system
        solar_system.update(dt)

        # Draw
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        # Begin 3D mode
        rl.begin_mode_3d(camera.camera)

        # Draw 3D grid for reference
        rl.draw_grid(20, 50.0)

        # Draw solar system
        solar_system.draw()

        # End 3D mode
        rl.end_mode_3d()

        # Draw 2D UI overlay
        pause_text = "PAUSED" if solar_system.paused else "RUNNING"
        status_text = f"Status: {pause_text} | Speed: {solar_system.time_scale:.1f}x"
        rl.draw_text(status_text, 10, 10, 20, rl.WHITE)

        controls_text = "WASD: Rotate Camera | Mouse Wheel: Zoom | SPACE: Pause | UP/DOWN: Speed | R: Reset"
        rl.draw_text(controls_text, 10, SCREEN_HEIGHT - 30, 16, rl.WHITE)

        rl.end_drawing()

    rl.close_window()


if __name__ == "__main__":
    main()
