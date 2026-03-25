import pyray as rl
import math
import random

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
CENTER_X = SCREEN_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2


class CelestialBody:
    def __init__(
        self, x, y, radius, color, orbital_radius=0, orbital_speed=0, parent=None
    ):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.orbital_radius = orbital_radius
        self.orbital_speed = orbital_speed
        self.angle = random.uniform(0, 2 * math.pi)  # Random starting position
        self.parent = parent
        self.trail = []
        self.max_trail_length = 100

    def update(self, dt):
        if self.parent and self.orbital_radius > 0:
            # Update orbital position
            self.angle += self.orbital_speed * dt

            # Calculate position relative to parent
            if self.parent:
                self.x = self.parent.x + math.cos(self.angle) * self.orbital_radius
                self.y = self.parent.y + math.sin(self.angle) * self.orbital_radius
            else:
                self.x = CENTER_X + math.cos(self.angle) * self.orbital_radius
                self.y = CENTER_Y + math.sin(self.angle) * self.orbital_radius

        # Add current position to trail
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

    def draw(self):
        # Draw orbital path
        if self.orbital_radius > 0 and self.parent:
            center_pos = rl.Vector2(self.parent.x, self.parent.y)
            orbit_color = rl.Color(40, 40, 40, 100)
            rl.draw_circle_lines_v(center_pos, self.orbital_radius, orbit_color)

        # Draw trail
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                alpha = int((i / len(self.trail)) * 80)  # Fade effect
                # Handle both Color objects and tuples
                if hasattr(self.color, "r"):
                    trail_color = rl.Color(
                        self.color.r, self.color.g, self.color.b, alpha
                    )
                else:
                    # Assume it's a tuple (r, g, b) or (r, g, b, a)
                    r, g, b = self.color[:3]
                    trail_color = rl.Color(r, g, b, alpha)

                start_pos = rl.Vector2(self.trail[i - 1][0], self.trail[i - 1][1])
                end_pos = rl.Vector2(self.trail[i][0], self.trail[i][1])
                rl.draw_line_v(start_pos, end_pos, trail_color)

        # Draw the body
        position = rl.Vector2(self.x, self.y)
        rl.draw_circle_v(position, self.radius, self.color)

        # Add a subtle glow effect for the sun (yellow bodies)
        # Check if this is the sun by comparing with yellow color and large radius
        is_sun = self.radius > 15 and (
            (
                hasattr(self.color, "r")
                and self.color.r == 255
                and self.color.g == 255
                and self.color.b == 0
            )
            or self.color == rl.YELLOW
        )
        if is_sun:
            for i in range(3):
                glow_radius = self.radius + i * 3
                glow_alpha = max(5, 30 - i * 8)
                glow_color = rl.Color(255, 255, 0, glow_alpha)
                rl.draw_circle_v(position, glow_radius, glow_color)


class SolarSystem:
    def __init__(self):
        self.bodies = []
        self.create_solar_system()
        self.paused = False
        self.time_scale = 1.0

    def create_solar_system(self):
        # Sun
        sun = CelestialBody(CENTER_X, CENTER_Y, 20, rl.YELLOW)
        self.bodies.append(sun)

        # Planets with realistic-ish relative sizes and distances
        planets_data = [
            # (orbital_radius, radius, color, orbital_speed, name)
            (80, 3, rl.GRAY, 0.02, "Mercury"),
            (110, 4, rl.ORANGE, 0.015, "Venus"),
            (150, 5, rl.BLUE, 0.012, "Earth"),
            (190, 4, rl.RED, 0.010, "Mars"),
            (280, 12, rl.BROWN, 0.005, "Jupiter"),
            (340, 10, rl.Color(255, 255, 150, 255), 0.004, "Saturn"),  # Light yellow
            (400, 7, rl.SKYBLUE, 0.003, "Uranus"),
            (450, 7, rl.DARKBLUE, 0.002, "Neptune"),
        ]

        for orbital_radius, radius, color, speed, name in planets_data:
            planet = CelestialBody(
                CENTER_X + orbital_radius,
                CENTER_Y,
                radius,
                color,
                orbital_radius,
                speed,
                sun,
            )
            self.bodies.append(planet)

        # Add Earth's moon
        earth = self.bodies[3]  # Earth is the 4th body (index 3)
        moon = CelestialBody(earth.x + 25, earth.y, 2, rl.WHITE, 25, 0.05, earth)
        self.bodies.append(moon)

        # Add some asteroids
        for _ in range(15):
            asteroid_distance = random.uniform(220, 260)  # Asteroid belt
            asteroid = CelestialBody(
                CENTER_X + asteroid_distance,
                CENTER_Y,
                1,
                rl.LIGHTGRAY,
                asteroid_distance,
                random.uniform(0.006, 0.008),
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
        SCREEN_WIDTH, SCREEN_HEIGHT, "Solar System Simulation - Sebastian Lague Style"
    )
    rl.set_target_fps(60)

    solar_system = SolarSystem()

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

        # Update
        solar_system.update(dt)

        # Draw
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        # Draw solar system
        solar_system.draw()

        # Draw UI
        pause_text = "PAUSED" if solar_system.paused else "RUNNING"
        status_text = f"Status: {pause_text} | Speed: {solar_system.time_scale:.1f}x"
        rl.draw_text(status_text, 10, 10, 20, rl.WHITE)

        controls_text = "SPACE: Pause | UP/DOWN: Speed | R: Reset"
        rl.draw_text(controls_text, 10, SCREEN_HEIGHT - 30, 20, rl.WHITE)

        rl.end_drawing()

    rl.close_window()


if __name__ == "__main__":
    main()
