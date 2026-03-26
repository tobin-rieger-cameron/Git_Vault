# scripts/render.py
import pyray as rl
import math
from utils.colors import *
from utils.vector3D import Vector3D

V3 = rl.Vector3

def to_rl(v):
    return rl.Vector3(v.x, v.y, v.z)

def draw_grid():
    rl.draw_grid(100, 10)

def draw_axes(queue_label, camera):
    rl.draw_line_3d(V3(0, 0, 0), V3(100, 0, 0), X_AXIS_COLOR)
    queue_label(V3(100, 0, 0), "X", camera)
    rl.draw_line_3d(V3(0, 0, 0), V3(0, 100, 0), Y_AXIS_COLOR)
    queue_label(V3(0, 100, 0), "Y", camera)
    rl.draw_line_3d(V3(0, 0, 0), V3(0, 0, 100), Z_AXIS_COLOR)
    queue_label(V3(0, 0, 100), "Z", camera)

def draw_trails(bodies):
    for body in bodies:
        for i in range(len(body.trail) - 1):
            start = body.trail[i]
            end   = body.trail[i + 1]
            rl.draw_line_3d(to_rl(start), to_rl(end), body.trail_color)

def draw_gravity_lines(bodies):
    for i, b1 in enumerate(bodies):
        for b2 in bodies[i+1:]:
            rl.draw_line_3d(to_rl(b1.position), to_rl(b2.position), GRID_COLOR)

def draw_bodies(bodies, queue_label, camera):
    for i, body in enumerate(bodies):
        rl.draw_sphere(to_rl(body.position), body.radius, body.color)
        queue_label(to_rl(body.position), f"body {i}", camera)

def draw_force_vectors(bodies, queue_label, camera):
    for i, body in enumerate(bodies):
        for force in body.forces:
            scaled = force.normalize() * math.log1p(force.length()) * 3
            draw_arrow(to_rl(body.position), scaled, FORCE_COLS[i])
        total = Vector3D(0, 0, 0)
        for force in body.forces:
            total += force
        scaled_total = total.normalize() * math.log1p(total.length()) * 3
        draw_arrow(to_rl(body.position), scaled_total, RESULTANT_COL)
        queue_label(to_rl(body.position), "F", camera)

def draw_arrow(start, force, color):
    end = V3(start.x + force.x, start.y + force.y, start.z + force.z)
    rl.draw_line_3d(start, end, color)
    rl.draw_sphere(end, 0.3, color)
