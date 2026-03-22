import pyray as rl
import math

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
G = 50  # Gravitational constant (scaled for simulation)


class Body:
    def __init__(self, x, y, z, vx, vy, vz, mass, radius, color, fixed=False):
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx  # velocity x
        self.vy = vy  # velocity y
        self.vz = vz  # velocity z
        self.mass = mass
        self.radius = radius
        self.color = color
        self.fixed = fixed  # If True, body cannot move

        # For trail effect
        self.trail = []
        self.max_trail_length = 150

    def apply_force(self, fx, fy, fz):
        # Don't apply forces to fixed bodies
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
        # Don't update position of fixed bodies
        if self.fixed:
            return

        # Update position based on velocity
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt

        # Add current position to trail
        self.trail.append((self.x, self.y, self.z))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

    def get_position(self):
        return rl.Vector3(self.x, self.y, self.z)

    def get_velocity(self):
        return rl.Vector3(self.vx, self.vy, self.vz)

    def draw(self):
        position = self.get_position()

        # Draw trail as connected line segments
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
                    self.trail[i][0], self.trail[i][1], self.trail[i][2]
                )
                end_pos = rl.Vector3(
                    self.trail[i + 1][0], self.trail[i + 1][1], self.trail[i + 1][2]
                )
                rl.draw_line_3d(start_pos, end_pos, trail_color)

        rl.draw_sphere(position, self.radius, self.color)
        rl.draw_sphere_wires(position, self.radius, 8, 8, rl.WHITE)


def calculate_gravitational_force(body1, body2):
    # Calculate distance vector
    dx = body2.x - body1.x
    dy = body2.y - body1.y
    dz = body2.z - body1.z
    distance = math.sqrt(dx * dx + dy * dy + dz * dz)

    # Avoid division by zero and extreme forces
    if distance < 0.01:
        distance = 0.01

    # Calculate force magnitude: F = G * m1 * m2 / r^2
    force_magnitude = G * body1.mass * body2.mass / (distance * distance)

    # Calculate force components (normalized direction * magnitude)
    fx = force_magnitude * dx / distance
    fy = force_magnitude * dy / distance
    fz = force_magnitude * dz / distance

    return fx, fy, fz


def main():
    # Initialize window
    rl.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "3D Gravity Simulation")
    rl.set_target_fps(60)

    # Define the camera
    camera = rl.Camera3D()
    camera.position = rl.Vector3(300.0, 200.0, 300.0)  # Camera position
    camera.target = rl.Vector3(0.0, 0.0, 0.0)  # Camera looking at point
    camera.up = rl.Vector3(0.0, 1.0, 0.0)  # Camera up vector
    camera.fovy = 45.0  # Camera field-of-view Y
    camera.projection = rl.CAMERA_PERSPECTIVE  # Camera projection type

    # Create bodies
    bodies = []

    # Central massive body (sun-like) at origin - FIXED POSITION
    central_body = Body(
        0,
        0,
        0,  # position at origin
        0,
        0,
        0,  # velocity (stationary)
        1000,  # mass
        25,  # radius
        rl.YELLOW,  # color
        fixed=True,  # This body cannot move from origin
    )
    bodies.append(central_body)

    # Orbiting body 1 (planet-like) - XY plane orbit
    planet1 = Body(
        120,
        0,
        0,  # position
        0,
        0,
        140,  # initial velocity (tangential in XZ plane)
        50,  # mass
        8,  # radius
        rl.BLUE,  # color
    )
    bodies.append(planet1)

    # Orbiting body 2 (planet-like) - tilted orbit
    planet2 = Body(
        0,
        0,
        -150,  # position
        120,
        0,
        0,  # initial velocity (tangential in XY plane)
        40,  # mass
        6,  # radius
        rl.RED,  # color
    )
    bodies.append(planet2)

    # Orbiting body 3 (moon-like) - inclined orbit
    moon = Body(
        80,
        60,
        40,  # position (offset in all axes)
        -80,
        100,
        -60,  # initial velocity (complex 3D orbit)
        15,  # mass
        4,  # radius
        rl.GREEN,  # color
    )
    bodies.append(moon)

    # Simulation variables
    dt = 0.016  # Delta time (roughly 60 FPS)
    paused = False
    show_vectors = False
    camera_mode = 1  # 0: free camera, 1: orbital camera

    # Disable cursor for free camera mode initially
    rl.disable_cursor()

    # Main game loop
    while not rl.window_should_close():
        # Handle input
        if rl.is_key_pressed(rl.KEY_SPACE):
            paused = not paused
        if rl.is_key_pressed(rl.KEY_V):
            show_vectors = not show_vectors
        if rl.is_key_pressed(rl.KEY_R):
            # Reset simulation
            main()
            return
        if rl.is_key_pressed(rl.KEY_C):
            camera_mode = (camera_mode + 1) % 2
            # Toggle cursor based on camera mode
            if camera_mode == 0:  # Free camera
                rl.disable_cursor()
            else:  # Orbital camera
                rl.enable_cursor()

        # Update camera
        if camera_mode == 0:
            # Free camera mode
            rl.update_camera(camera, rl.CAMERA_FREE)
        else:
            # Orbital camera mode - rotate around center
            angle = rl.get_time() * 0.3
            radius = 400
            camera.position.x = math.cos(angle) * radius
            camera.position.z = math.sin(angle) * radius
            camera.position.y = 150 + math.sin(angle * 0.5) * 50
            camera.target = rl.Vector3(0.0, 0.0, 0.0)

        # Update physics (if not paused)
        if not paused:
            # Calculate forces between all bodies
            for i, body1 in enumerate(bodies):
                total_fx = 0
                total_fy = 0
                total_fz = 0

                for j, body2 in enumerate(bodies):
                    if i != j:  # Don't calculate force on itself
                        fx, fy, fz = calculate_gravitational_force(body1, body2)
                        total_fx += fx
                        total_fy += fy
                        total_fz += fz

                # Apply total force to body
                body1.apply_force(total_fx, total_fy, total_fz)

            # Update all bodies
            for body in bodies:
                body.update(dt)

        # Draw everything
        rl.begin_drawing()
        rl.clear_background(rl.Color(10, 10, 30, 255))  # Dark space-like background

        rl.begin_mode_3d(camera)

        # Draw a subtle grid for reference
        rl.draw_grid(20, 50.0)

        # Draw coordinate axes
        rl.draw_line_3d(rl.Vector3(-100, 0, 0), rl.Vector3(100, 0, 0), rl.RED)  # X axis
        rl.draw_line_3d(
            rl.Vector3(0, -100, 0), rl.Vector3(0, 100, 0), rl.GREEN
        )  # Y axis
        rl.draw_line_3d(
            rl.Vector3(0, 0, -100), rl.Vector3(0, 0, 100), rl.BLUE
        )  # Z axis

        # Draw bodies
        for body in bodies:
            body.draw()

        # Draw velocity vectors (if enabled)
        if show_vectors:
            for body in bodies:
                start_pos = body.get_position()
                velocity = body.get_velocity()
                # Scale down velocity for visibility
                end_pos = rl.Vector3(
                    start_pos.x + velocity.x * 0.3,
                    start_pos.y + velocity.y * 0.3,
                    start_pos.z + velocity.z * 0.3,
                )
                rl.draw_line_3d(start_pos, end_pos, rl.WHITE)
                # Draw arrowhead
                rl.draw_sphere(end_pos, 2, rl.WHITE)

        rl.end_mode_3d()

        # Draw UI
        rl.draw_text("SPACE: Pause/Resume", 10, 10, 20, rl.WHITE)
        rl.draw_text("V: Toggle velocity vectors", 10, 35, 20, rl.WHITE)
        rl.draw_text("C: Toggle camera mode", 10, 60, 20, rl.WHITE)
        rl.draw_text("R: Reset simulation", 10, 85, 20, rl.WHITE)
        rl.draw_text("Mouse + WASD: Free camera", 10, 110, 20, rl.WHITE)
        rl.draw_text("ESC: Exit", 10, 135, 20, rl.WHITE)

        camera_text = "Orbital Camera" if camera_mode == 1 else "Free Camera"
        rl.draw_text(f"Camera: {camera_text}", 10, 160, 20, rl.YELLOW)

        if paused:
            rl.draw_text(
                "PAUSED", SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT // 2 - 100, 30, rl.RED
            )

        # Show FPS
        rl.draw_fps(SCREEN_WIDTH - 80, 10)

        rl.end_drawing()

    # Cleanup
    rl.enable_cursor()  # Re-enable cursor before closing
    rl.close_window()


if __name__ == "__main__":
    main()
