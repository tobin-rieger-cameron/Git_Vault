import numpy as np
import pyray as rl

# --- Simulation constants ---
G = 1.0        # normalized gravitational constant (for figure-eight solution)
DT = 0.01      # time step
SCALE = 200    # for converting simulation units to screen pixels

# --- Figure-eight initial conditions ---
bodies = [
    {"mass": 1.0, "pos": np.array([-0.97000436, 0.24308753]), "vel": np.array([0.4662036850, 0.4323657300]), "color": rl.RED},
    {"mass": 1.0, "pos": np.array([0.97000436, -0.24308753]), "vel": np.array([0.4662036850, 0.4323657300]), "color": rl.GREEN},
    {"mass": 1.0, "pos": np.array([0.0, 0.0]), "vel": np.array([-0.93240737, -0.86473146]), "color": rl.BLUE},
]

def gravitational_force(m1, m2, r1, r2):
    diff = r2 - r1
    dist = np.linalg.norm(diff)
    if dist < 1e-5:
        return np.zeros(2)
    return G * m1 * m2 * diff / dist**3

# --- Derivatives for RK4 ---
def compute_accelerations(bodies):
    accelerations = []
    for i, bi in enumerate(bodies):
        force = np.zeros(2)
        for j, bj in enumerate(bodies):
            if i != j:
                force += gravitational_force(bi["mass"], bj["mass"], bi["pos"], bj["pos"])
        accelerations.append(force / bi["mass"])
    return accelerations

def rk4_step(bodies, dt):
    # Convert to state vectors
    pos = [np.copy(b["pos"]) for b in bodies]
    vel = [np.copy(b["vel"]) for b in bodies]

    # k1
    a1 = compute_accelerations(bodies)

    # k2
    temp_bodies = [{"mass": b["mass"], "pos": pos[i] + 0.5 * vel[i] * dt, "vel": vel[i] + 0.5 * a1[i] * dt, "color": b["color"]} for i, b in enumerate(bodies)]
    a2 = compute_accelerations(temp_bodies)

    # k3
    temp_bodies = [{"mass": b["mass"], "pos": pos[i] + 0.5 * (vel[i] + 0.5 * a1[i] * dt) * dt, "vel": vel[i] + 0.5 * a2[i] * dt, "color": b["color"]} for i, b in enumerate(bodies)]
    a3 = compute_accelerations(temp_bodies)

    # k4
    temp_bodies = [{"mass": b["mass"], "pos": pos[i] + (vel[i] + 0.5 * a2[i] * dt) * dt, "vel": vel[i] + a3[i] * dt, "color": b["color"]} for i, b in enumerate(bodies)]
    a4 = compute_accelerations(temp_bodies)

    # Update
    for i, b in enumerate(bodies):
        b["pos"] += vel[i] * dt + (dt**2 / 6.0) * (a1[i] + a2[i] + a3[i])
        b["vel"] += (dt / 6.0) * (a1[i] + 2*a2[i] + 2*a3[i] + a4[i])

def to_screen(pos):
    return int(pos[0] * SCALE + 400), int(pos[1] * SCALE + 300)

# --- Raylib setup ---
rl.init_window(800, 600, "3 Body Figure-Eight Simulation")
rl.set_target_fps(60)

trail_len = 300
trails = [[] for _ in bodies]

while not rl.window_should_close():
    # Update physics
    rk4_step(bodies, DT)

    # Update trails
    for t, body in zip(trails, bodies):
        t.append(tuple(body["pos"]))
        if len(t) > trail_len:
            t.pop(0)

    # Draw
    rl.begin_drawing()
    rl.clear_background(rl.BLACK)

    # Trails
    for t, body in zip(trails, bodies):
        for p in t:
            x, y = to_screen(p)
            rl.draw_pixel(x, y, body["color"])

    # Bodies
    for body in bodies:
        x, y = to_screen(body["pos"])
        rl.draw_circle(x, y, 5, body["color"])

    rl.end_drawing()

rl.close_window()
