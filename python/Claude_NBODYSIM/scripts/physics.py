# scripts/physics.py
from utils.vector3D import Vector3D

GRAVITATIONAL_CONSTANT = 0.01

def compute_forces(bodies, G):
    for body in bodies:
        body.forces = []
    for i, b1 in enumerate(bodies):
        for b2 in bodies[i+1:]:
            displacement = b2.position - b1.position
            distance = displacement.length()

            force_magnitude = G * (b1.mass * b2.mass) / (distance**2 + 0.01)

            direction = displacement.normalize()
            force_vec = direction * force_magnitude

            b1.forces.append(force_vec)
            b2.forces.append(-force_vec)

def apply_forces(bodies, dt):
    for body in bodies:
        total_force = Vector3D(0, 0, 0)
        for f in body.forces:
            total_force += f
        acceleration = total_force / body.mass
        body.velocity += acceleration * dt
        body.position += body.velocity * dt

def sim_step(bodies, dt, G):
    compute_forces(bodies, G)
    apply_forces(bodies, dt)
