import pyray as rl
import math


class Body:
    # --- Class-level Constants
    all_bodies = []
    G = 6.67430e-11
    G2 = .01

    def __init__(
            self, 
            x, y, z, 
            radius, 
            color, 
            density, 
            fixed=False
    ):
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius
        self.color = color
        self.density = density
        self.fixed = fixed
        self.volume = (4/3) * math.pi * self.radius**3
        self.mass = self.volume * self.density

        # Velocity components
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0

        # Acceleration components
        self.ax = 0.0
        self.ay = 0.0
        self.az = 0.0

        # Set initial mass
        

        # register this body in the class-level list
        Body.all_bodies.append(self)

    def calculate_gravitational_force(self, other):
        # Calculate distance components
        dx = other.x - self.x
        dy = other.y - self.y
        dz = other.z - self.z

        # Calculate distance
        distance = math.sqrt(dx**2 + dy**2 + dz**2)

        min_distance = self.radius + other.radius
        if distance < min_distance:
            distance = min_distance
        
        if distance == 0:
            return 0.0, 0.0, 0.0

        # F = G * (m1 * m2) / r^2
        force_magnitude = Body.G2 * (self.mass * other.mass) / (distance ** 2)

        # Calculate force components
        fx = (dx / distance) * force_magnitude
        fy = (dy / distance) * force_magnitude
        fz = (dz / distance) * force_magnitude

        return fx, fy, fz

    def update(self, dt):
        """Update position and velocity based on acceleration"""

        if self.fixed:
            return

        # Velocity: v = v + a * dt
        self.vx += self.ax * dt
        self.vy += self.ay * dt
        self.vz += self.az * dt

        # Position: p = p + v * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt

        # Reset acceleration for the next frame
        self.ax = 0.0
        self.ay = 0.0
        self.az = 0.0        

    def apply_force(self, fx, fy, fz):
        if self.fixed:
            return # Keep fixed bodies stable
        else:
            # F = ma, so a = F/m
            self.ax += fx / self.mass
            self.ay += fy / self.mass
            self.az += fz / self.mass

    def get_position(self):
        return rl.Vector3(self.x, self.y, self.z)

    def draw(self):
        position = self.get_position()
        rl.draw_sphere(position, self.radius, self.color)
        rl.draw_sphere_wires(position, self.radius, 8, 8, rl.BLACK)


    @classmethod
    def get_all_bodies(cls):
        """Return the list of all bodies"""
        return cls.all_bodies
    
    @classmethod
    def update_all_bodies(cls, dt):
        """Apply physics for all bodies at once"""
        for i, body1 in enumerate(cls.all_bodies):
            for body2 in cls.all_bodies[i+1:]:
                fx, fy, fz = body1.calculate_gravitational_force(body2)
                body1.apply_force(fx, fy, fz)
                body2.apply_force(-fx, -fy, -fz)

        for body in cls.all_bodies:
            body.update(dt)

    @classmethod
    def draw_all_bodies(cls):
        """Draw all bodies"""
        for body in cls.all_bodies:
            body.draw()
    
    @classmethod
    def clear_bodies(cls):
        """Clear all bodies"""
        cls.all_bodies = []
