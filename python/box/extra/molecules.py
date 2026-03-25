import pyray as rl
import random
import math

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WATER_MOLECULE_COUNT = 30
OXYGEN_RADIUS = 16
HYDROGEN_RADIUS = 8
BOND_LENGTH = 25
BOND_ANGLE = 104.5  # degrees (actual H-O-H bond angle in water)
SPEED_FACTOR = 0.15

# Physical constants (scaled for simulation)
HYDROGEN_BOND_STRENGTH = 0.8  # Attractive force between H and O of different molecules
HYDROGEN_BOND_DISTANCE = 40  # Optimal distance for hydrogen bonding
VDW_STRENGTH = 0.2  # Van der Waals attraction
VDW_REPULSION = 15.0  # Van der Waals repulsion (Pauli exclusion)
VDW_EQUILIBRIUM = 30  # Van der Waals equilibrium distance
ELECTROSTATIC_STRENGTH = 0.1  # Partial charge interactions

# Partial charges (scaled for simulation)
OXYGEN_CHARGE = -0.82  # Oxygen is electronegative
HYDROGEN_CHARGE = 0.41  # Hydrogen is electropositive


class WaterMolecule:
    def __init__(self):
        self.x = random.uniform(150, SCREEN_WIDTH - 150)
        self.y = random.uniform(150, SCREEN_HEIGHT - 150)
        self.vx = random.uniform(-1, 1) * SPEED_FACTOR
        self.vy = random.uniform(-1, 1) * SPEED_FACTOR
        self.rotation = random.uniform(0, 2 * math.pi)
        self.angular_velocity = random.uniform(-0.01, 0.01)

        # Colors
        self.oxygen_color = rl.Color(0, 0, 0, 255)
        self.hydrogen_color = rl.Color(255, 255, 255, 255)
        self.hydrogen_outline = rl.Color(0, 0, 0, 255)

        # Force tracking for visualization
        self.total_force_x = 0
        self.total_force_y = 0

    def get_atom_positions(self):
        """Calculate positions of oxygen and hydrogen atoms"""
        ox = self.x
        oy = self.y

        angle1 = self.rotation - math.radians(BOND_ANGLE / 2)
        angle2 = self.rotation + math.radians(BOND_ANGLE / 2)

        h1x = ox + BOND_LENGTH * math.cos(angle1)
        h1y = oy + BOND_LENGTH * math.sin(angle1)

        h2x = ox + BOND_LENGTH * math.cos(angle2)
        h2y = oy + BOND_LENGTH * math.sin(angle2)

        return (ox, oy), (h1x, h1y), (h2x, h2y)

    def calculate_forces(self, other_molecule):
        """Calculate all intermolecular forces between this molecule and another"""
        (ox1, oy1), (h1x1, h1y1), (h2x1, h2y1) = self.get_atom_positions()
        (ox2, oy2), (h1x2, h1y2), (h2x2, h2y2) = other_molecule.get_atom_positions()

        total_fx, total_fy = 0, 0
        total_torque = 0

        # All atom pairs with their types and charges
        atoms1 = [
            (ox1, oy1, OXYGEN_CHARGE, "O"),
            (h1x1, h1y1, HYDROGEN_CHARGE, "H"),
            (h2x1, h2y1, HYDROGEN_CHARGE, "H"),
        ]
        atoms2 = [
            (ox2, oy2, OXYGEN_CHARGE, "O"),
            (h1x2, h1y2, HYDROGEN_CHARGE, "H"),
            (h2x2, h2y2, HYDROGEN_CHARGE, "H"),
        ]

        for i, (x1, y1, charge1, type1) in enumerate(atoms1):
            for j, (x2, y2, charge2, type2) in enumerate(atoms2):
                dx = x2 - x1
                dy = y2 - y1
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < 1.0:  # Avoid division by zero
                    continue

                # Normalized direction vector (force points from atom1 to atom2)
                nx = dx / distance
                ny = dy / distance

                fx, fy = 0, 0

                # 1. HYDROGEN BONDING (H of one molecule attracted to O of another)
                # Only occurs between H and O of different molecules
                if (type1 == "H" and type2 == "O") or (type1 == "O" and type2 == "H"):
                    if distance < HYDROGEN_BOND_DISTANCE * 1.8:
                        # Attraction with optimal distance
                        if distance > HYDROGEN_BOND_DISTANCE:
                            # Too far - attractive force
                            force_magnitude = HYDROGEN_BOND_STRENGTH / (
                                distance / HYDROGEN_BOND_DISTANCE
                            )
                            fx += nx * force_magnitude
                            fy += ny * force_magnitude
                        else:
                            # Too close - weaker attraction (not repulsion!)
                            force_magnitude = HYDROGEN_BOND_STRENGTH * 0.3
                            fx += nx * force_magnitude
                            fy += ny * force_magnitude

                # 2. VAN DER WAALS FORCES (all atom pairs)
                # Lennard-Jones potential: attractive at medium range, repulsive at close range
                if distance < VDW_EQUILIBRIUM * 2.5:
                    # Simplified Lennard-Jones: F = A/r^7 - B/r^13 (attractive - repulsive)
                    r_ratio = VDW_EQUILIBRIUM / distance

                    if distance < VDW_EQUILIBRIUM:
                        # Repulsive regime (very close)
                        force_magnitude = -VDW_REPULSION * (r_ratio**12) / distance
                    else:
                        # Attractive regime (medium distance)
                        force_magnitude = VDW_STRENGTH * (r_ratio**6) / distance

                    fx += nx * force_magnitude
                    fy += ny * force_magnitude

                # 3. ELECTROSTATIC INTERACTIONS (partial charges)
                # Coulomb's law: F = k * q1 * q2 / r^2
                if distance < 80:  # Electrostatic cutoff
                    force_magnitude = (
                        ELECTROSTATIC_STRENGTH
                        * charge1
                        * charge2
                        / (distance * distance)
                    )
                    # Negative force = attraction, positive force = repulsion
                    fx += nx * force_magnitude
                    fy += ny * force_magnitude

                total_fx += fx
                total_fy += fy

                # Calculate torque for molecular rotation
                # Torque = r × F (position relative to center of mass)
                rx = x1 - self.x
                ry = y1 - self.y
                torque = rx * fy - ry * fx
                total_torque += torque * 0.01  # Scale down torque

        return total_fx, total_fy, total_torque

    def update(self, molecules):
        fx_total, fy_total = 0, 0
        torque_total = 0

        # Calculate forces from all other molecules
        for other in molecules:
            if other != self:
                fx, fy, torque = self.calculate_forces(other)
                fx_total += fx
                fy_total += fy
                torque_total += torque

        # Store for visualization
        self.total_force_x = fx_total
        self.total_force_y = fy_total

        # Add thermal motion (Brownian motion)
        thermal_strength = 0.03
        fx_total += random.uniform(-thermal_strength, thermal_strength)
        fy_total += random.uniform(-thermal_strength, thermal_strength)
        torque_total += random.uniform(-0.002, 0.002)

        # Update velocities (F = ma, assuming m = 1)
        self.vx += fx_total * 0.1  # Scale down acceleration
        self.vy += fy_total * 0.1
        self.angular_velocity += torque_total

        # Velocity limits to prevent runaway motion
        max_velocity = 2.0
        if abs(self.vx) > max_velocity:
            self.vx = max_velocity * (1 if self.vx > 0 else -1)
        if abs(self.vy) > max_velocity:
            self.vy = max_velocity * (1 if self.vy > 0 else -1)
        if abs(self.angular_velocity) > 0.05:
            self.angular_velocity = 0.05 * (1 if self.angular_velocity > 0 else -1)

        # Damping (friction/viscosity)
        damping = 0.98
        self.vx *= damping
        self.vy *= damping
        self.angular_velocity *= 0.95

        # Update positions
        self.x += self.vx
        self.y += self.vy
        self.rotation += self.angular_velocity

        # Normalize rotation
        self.rotation = self.rotation % (2 * math.pi)

        # Wall collisions with proper bouncing
        margin = BOND_LENGTH + HYDROGEN_RADIUS + 10

        if self.x <= margin:
            self.x = margin
            self.vx = abs(self.vx) * 0.7  # Bounce with energy loss
        elif self.x >= SCREEN_WIDTH - margin:
            self.x = SCREEN_WIDTH - margin
            self.vx = -abs(self.vx) * 0.7

        if self.y <= margin:
            self.y = margin
            self.vy = abs(self.vy) * 0.7
        elif self.y >= SCREEN_HEIGHT - margin:
            self.y = SCREEN_HEIGHT - margin
            self.vy = -abs(self.vy) * 0.7

    def draw(self, show_forces=False):
        """Draw H₂O molecule with optional force vectors"""
        (ox, oy), (h1x, h1y), (h2x, h2y) = self.get_atom_positions()

        # Draw bonds first (behind atoms)
        bond_color = rl.Color(100, 100, 100, 160)
        rl.draw_line_ex(rl.Vector2(ox, oy), rl.Vector2(h1x, h1y), 2, bond_color)
        rl.draw_line_ex(rl.Vector2(ox, oy), rl.Vector2(h2x, h2y), 2, bond_color)

        # Draw hydrogen atoms (white with black outline)
        rl.draw_circle(int(h1x), int(h1y), HYDROGEN_RADIUS, self.hydrogen_color)
        rl.draw_circle_lines(int(h1x), int(h1y), HYDROGEN_RADIUS, self.hydrogen_outline)

        rl.draw_circle(int(h2x), int(h2y), HYDROGEN_RADIUS, self.hydrogen_color)
        rl.draw_circle_lines(int(h2x), int(h2y), HYDROGEN_RADIUS, self.hydrogen_outline)

        # Draw oxygen atom (black, larger)
        rl.draw_circle(int(ox), int(oy), OXYGEN_RADIUS, self.oxygen_color)

        # Draw force vector if enabled
        if show_forces and (
            abs(self.total_force_x) > 0.01 or abs(self.total_force_y) > 0.01
        ):
            force_scale = 100  # Reduced scale for better visualization
            end_x = self.x + self.total_force_x * force_scale
            end_y = self.y + self.total_force_y * force_scale

            # Force vector line
            rl.draw_line_ex(
                rl.Vector2(self.x, self.y),
                rl.Vector2(end_x, end_y),
                2,
                rl.Color(255, 100, 100, 180),
            )

            # Arrow head
            if (
                abs(end_x - self.x) > 5 or abs(end_y - self.y) > 5
            ):  # Only draw arrow if vector is long enough
                arrow_size = 4
                angle = math.atan2(end_y - self.y, end_x - self.x)
                rl.draw_triangle(
                    rl.Vector2(end_x, end_y),
                    rl.Vector2(
                        end_x - arrow_size * math.cos(angle - 0.5),
                        end_y - arrow_size * math.sin(angle - 0.5),
                    ),
                    rl.Vector2(
                        end_x - arrow_size * math.cos(angle + 0.5),
                        end_y - arrow_size * math.sin(angle + 0.5),
                    ),
                    rl.Color(255, 100, 100, 180),
                )


def main():
    rl.init_window(
        SCREEN_WIDTH, SCREEN_HEIGHT, "H₂O Molecular Forces - Physics Corrected"
    )
    rl.set_target_fps(60)

    molecules = [WaterMolecule() for _ in range(WATER_MOLECULE_COUNT)]
    show_forces = False
    paused = False

    while not rl.window_should_close():
        # Controls
        if rl.is_key_pressed(rl.KEY_F):
            show_forces = not show_forces
        if rl.is_key_pressed(rl.KEY_SPACE):
            paused = not paused

        # Update physics (only if not paused)
        if not paused:
            for molecule in molecules:
                molecule.update(molecules)

        # Draw
        rl.begin_drawing()
        rl.clear_background(rl.Color(240, 240, 240, 255))

        # Title
        rl.draw_text(
            "WATER MOLECULES - CORRECTED INTERMOLECULAR FORCES", 110, 20, 18, rl.BLACK
        )
        status = "PAUSED" if paused else "RUNNING"
        rl.draw_text(f"Status: {status}", 350, 45, 14, rl.GRAY)

        # Draw molecules
        for molecule in molecules:
            molecule.draw(show_forces)

        # Legend
        legend_x, legend_y = 20, 80
        rl.draw_text("Physics:", legend_x, legend_y, 16, rl.BLACK)
        rl.draw_text(
            "✓ Hydrogen Bonding (H→O attraction)",
            legend_x,
            legend_y + 25,
            12,
            rl.GRAY,
        )
        rl.draw_text(
            "✓ Van der Waals (Lennard-Jones)", legend_x, legend_y + 40, 12, rl.GRAY
        )
        rl.draw_text(
            "✓ Electrostatic (δ+ H, δ- O)", legend_x, legend_y + 55, 12, rl.GRAY
        )
        rl.draw_text("✓ Brownian Motion", legend_x, legend_y + 70, 12, rl.GRAY)

        # Controls
        force_text = "ON" if show_forces else "OFF"
        rl.draw_text("SPACE - Pause/Resume", 10, SCREEN_HEIGHT - 70, 14, rl.GRAY)
        rl.draw_text(
            f"F - Force Vectors: {force_text}", 10, SCREEN_HEIGHT - 50, 14, rl.GRAY
        )
        rl.draw_text("ESC - Exit", 10, SCREEN_HEIGHT - 30, 14, rl.GRAY)

        # Physics parameters
        rl.draw_text(
            f"Molecules: {WATER_MOLECULE_COUNT}", legend_x, legend_y + 100, 12, rl.GRAY
        )
        rl.draw_text("H₂O Bond Angle: 104.5°", legend_x, legend_y + 115, 12, rl.GRAY)

        rl.end_drawing()

    rl.close_window()


if __name__ == "__main__":
    main()
