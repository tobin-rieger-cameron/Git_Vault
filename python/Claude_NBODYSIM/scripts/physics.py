"""
╔══════════════════════════════════════════════════════════════╗
║  physics.py                                                  ║
║  Force computation, Euler integration, collision response    ║
╚══════════════════════════════════════════════════════════════╝
"""

from utils.vector3D import Vector3D


# ══ Vector Relationships ════════════════════════════════════════════════════════════╗
                                                                                    # ║
def displacement(b1, b2):                                                           # ║
    # vector pointing from b1 to b2                                                 # ║
    return b2.position - b1.position                                                # ║
                                                                                    # ║
def distance(b1, b2):                                                               # ║
    return displacement(b1, b2).length()                                            # ║
                                                                                    # ║
def normal(b1, b2):                                                                 # ║
    # unit vector pointing from b1 to b2                                            # ║
    return displacement(b1, b2).normalize()                                         # ║
                                                                                    # ║
def acceleration(force, mass):                                                      # ║
    # Newton's 2nd law: a = F / m                                                   # ║
    return force / mass                                                             # ║
                                                                                    # ║
# ════════════════════════════════════════════════════════════════════════════════════╝


# ══ Force Accumulation ══════════════════════════════════════════════════════════════╗
                                                                                    # ║
def compute_forces(bodies: tuple, G: float):                                        # ║
    """                                                                             # ║
    Calculate the gravitational forces bodies exert on one another.                 # ║
    Appends (force_vec, source_body) tuples directly to each body's                 # ║
    forces list — consumed later by apply_forces().                                 # ║
    """                                                                             # ║
    # clear forces from previous frame                                              # ║
    for body in bodies:                                                             # ║
        body.forces = []                                                            # ║
                                                                                    # ║
    # compute forces for each unique pair — inner loop starts at i+1                # ║
    # so each pair (b1, b2) is addressed exactly once                               # ║
    for i, b1 in enumerate(bodies):                                                 # ║
        for b2 in bodies[i+1:]:                                                     # ║
            disp = displacement(b1, b2)                                             # ║
            dist = distance(b1, b2)                                                 # ║
                                                                                    # ║
            # Newton's law of gravitation: F = G * m1 * m2 / r²                     # ║
            # + 0.01 softening term prevents singularity at r ≈ 0                   # ║
            force_magnitude  = G * (b1.mass * b2.mass) / (dist**2 + 0.01)           # ║
            force_direction  = disp.normalize()                                     # ║
            force_vec        = force_direction * force_magnitude                    # ║
                                                                                    # ║
            # equal and opposite forces — Newton's 3rd law                          # ║
            b1.forces.append(( force_vec, b2))                                      # ║
            b2.forces.append((-force_vec, b1))                                      # ║
                                                                                    # ║
# ════════════════════════════════════════════════════════════════════════════════════╝


# ══ Integration ═════════════════════════════════════════════════════════════════════╗
                                                                                    # ║
def apply_forces(bodies, dt):                                                       # ║
    for body in bodies:                                                             # ║
        total_force = Vector3D(0, 0, 0)                                             # ║
        for f, _ in body.forces:                                                    # ║
            total_force += f                                                        # ║
                                                                                    # ║
        a = acceleration(total_force, body.mass)                                    # ║
                                                                                    # ║
        # symplectic Euler: velocity updated before position                        # ║
        # this conserves energy better than standard Euler                          # ║
        body.velocity += a * dt                                                     # ║
        body.position += body.velocity * dt                                         # ║
                                                                                    # ║
# ════════════════════════════════════════════════════════════════════════════════════╝


# ══ Collision Detection & Response ══════════════════════════════════════════════════════════╗
                                                                                            # ║
def collision_detection(bodies):                                                            # ║
    # check every unique pair for radius overlap                                            # ║
    for i, b1 in enumerate(bodies):                                                         # ║
        for b2 in bodies[i+1:]:                                                             # ║
            if distance(b1, b2) < b1.radius + b2.radius:                                    # ║
                resolve_collision(b1, b2)                                                   # ║
                                                                                            # ║
def resolve_collision(b1, b2):                                                              # ║
    restitution = 0.8   # 1.0 = perfectly elastic, 0.0 = perfectly inelastic                # ║
                                                                                            # ║
    # unit vector along the line connecting both centers                                    # ║
    contact_axis = normal(b1, b2)                                                           # ║
                                                                                            # ║
    # relative velocity along the contact axis                                              # ║
    relative_vel = (b2.velocity - b1.velocity).dot(contact_axis)                            # ║
                                                                                            # ║
    # ── Positional Correction ────────────────────────────────────────────                 # ║
    # push bodies apart proportional to mass ratio to resolve overlap                       # ║
    overlap     = (b1.radius + b2.radius) - distance(b1, b2)                                # ║
    total_mass  = b1.mass + b2.mass                                                         # ║
    b1.position -= contact_axis * overlap * (b2.mass / total_mass)                          # ║
    b2.position += contact_axis * overlap * (b1.mass / total_mass)                          # ║
                                                                                            # ║
    # ── Impulse Response ─────────────────────────────────────────────────                 # ║
    if relative_vel > 0:                                                                    # ║
        # impulse scalar derived from conservation of momentum                              # ║
        # j = -(1 + e) * vRel / (1/m1 + 1/m2)                                               # ║
        impulse_scalar = (-(1 + restitution) * relative_vel) / (1 / b1.mass + 1 / b2.mass)  # ║
        b1.velocity += (impulse_scalar / b1.mass) * contact_axis                            # ║
        b2.velocity -= (impulse_scalar / b2.mass) * contact_axis                            # ║
                                                                                            # ║
# ════════════════════════════════════════════════════════════════════════════════════════════╝


# ── sim_step ──────────────────────────────────────────────────────
""" single simulation tick: forces → integration → collisions """
def sim_step(bodies, dt, G):
    compute_forces(bodies, G)
    apply_forces(bodies, dt)
    collision_detection(bodies)
