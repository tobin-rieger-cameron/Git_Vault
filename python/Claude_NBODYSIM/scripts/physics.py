# scripts/physics.py
from utils.vector3D import Vector3D


# Vector relationships between two bodies

def displacement(b1, b2):
    return b2.position - b1.position

def distance(b1, b2):
    return displacement(b1, b2).length()

def normal(b1, b2):
    return displacement(b1, b2).normalize()

def acceleration(force, mass):
    return force / mass


def compute_forces(bodies: tuple, G: float):
    """ Calculate the forces that a group of bodies
        apply to one another.

        Args:
            bodies: list of bodies (and their qualities) 
                    held in statefile.

                 G: Gravitational Constant

        Returns: N/a
            appends calculated forces directly to body state
    """
    # clear forces from previous frame
    for body in bodies:
        body.forces = []

    # compute forces for each unique set of bodies
    for i, b1 in enumerate(bodies):
        for b2 in bodies[i+1:]: # address each pair once

            disp = displacement(b1, b2)
            dist = distance(b1, b2)

            # Newton's law: F = G * m1 * m2 / r^2
            force_magnitude = G * (b1.mass * b2.mass) / (dist**2 + 0.01)

            force_direction = disp.normalize()
            force_vec = force_direction * force_magnitude

            # add computed forces to state list
            b1.forces.append((force_vec, b2))
            b2.forces.append((-force_vec, b1))

def apply_forces(bodies, dt):

    # apply force to each body
    for body in bodies:
        total_force = Vector3D(0, 0, 0)

        for f, _ in body.forces:
            total_force += f

        #a = F/m
        a = acceleration(total_force, body.mass)

        # symplectic Euler integration:
        # update velocity, then position
        body.velocity += a * dt
        body.position += body.velocity * dt

def collision_detection(bodies):
    
    # bodies cannot move within each others radii
    for i, b1 in enumerate(bodies):
        for b2 in bodies[i+1:]:
            if distance(b1, b2) < b1.radius + b2.radius:
                # bodies are colliding
                # prevent bodies from moving further inside one another
                resolve_collision(b1, b2)

# applies necessary forces to avoid boundary overlap
def resolve_collision(b1, b2):

    restitution = 0.8

    # normalized vector pointing from one bodies center to the other
    contact_axis = normal(b1, b2)
    relative_vel = (b2.velocity - b1.velocity).dot(contact_axis)

    # move overlapping bodies away from each other
    overlap = ((b1.radius + b2.radius) - distance(b1, b2)) * restitution
    total_mass = b1.mass + b2.mass
    b1.position -= contact_axis * overlap * (b2.mass / total_mass)
    b2.position += contact_axis * overlap * (b1.mass / total_mass)

    if relative_vel > 0:
        # impulse_scalar = (2 * relative_vel) / (1 / b1.mass + 1 / b2.mass)
        impulse_scalar = (-(1 + restitution) * relative_vel) / (1 / b1.mass + 1 / b2.mass)

        # apply equal and opposite velocities
        b1.velocity += (impulse_scalar / b1.mass) * contact_axis
        b2.velocity -= (impulse_scalar / b2.mass) * contact_axis

    



def sim_step(bodies, dt, G):
    compute_forces(bodies, G)
    apply_forces(bodies, dt)
    collision_detection(bodies)
