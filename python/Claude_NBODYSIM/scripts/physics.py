# scripts/physics.py
from utils.vector3D import Vector3D


def compute_forces(bodies, G):

    # clear forces from previous frame
    for body in bodies:
        body.forces = []

    # compute forces for each unique set of bodies
    for i, b1 in enumerate(bodies):
        for b2 in bodies[i+1:]: # address each pair once
            
            displacement = b2.position - b1.position
            distance = displacement.length()

            # Newton's law: F = G * m1 * m2 / r^2
            force_magnitude = G * (b1.mass * b2.mass) / (distance**2 + 0.01)

            force_direction = displacement.normalize()
            force_vec = force_direction * force_magnitude

            # add computed forces to state list
            b1.forces.append((force_vec, b2))
            b2.forces.append((-force_vec, b1))

def apply_forces(bodies, dt):

    for body in bodies:
        total_force = Vector3D(0, 0, 0)

        for f, _ in body.forces:
            total_force += f

        #a = F/m
        acceleration = total_force / body.mass

        # symplectic Euler integraation:
        # update velocity, then position
        body.velocity += acceleration * dt
        body.position += body.velocity * dt

def sim_step(bodies, dt, G):
    compute_forces(bodies, G)
    apply_forces(bodies, dt)
