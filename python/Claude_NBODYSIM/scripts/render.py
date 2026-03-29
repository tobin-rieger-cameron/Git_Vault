# scripts/render.py
import pyray as rl
import math
from utils.colors import *
from utils.vector3D import Vector3D

# convert to raylib vector for drawing
def to_rl(v):
    return rl.Vector3(v.x, v.y, v.z)

def draw_grid():
    rl.draw_grid(100, 10)

def draw_axes(queue_label, camera):
    rl.draw_line_3d(rl.Vector3(0, 0, 0), rl.Vector3(100, 0, 0), X_AXIS_COLOR); queue_label(rl.Vector3(100, 0, 0), "X", camera)
    rl.draw_line_3d(rl.Vector3(0, 0, 0), rl.Vector3(0, 100, 0), Y_AXIS_COLOR); queue_label(rl.Vector3(0, 100, 0), "Y", camera)
    rl.draw_line_3d(rl.Vector3(0, 0, 0), rl.Vector3(0, 0, 100), Z_AXIS_COLOR); queue_label(rl.Vector3(0, 0, 100), "Z", camera)

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
        queue_label(to_rl(body.position), body.name, camera)

def draw_force_vectors(bodies, queue_label, camera):
    for i, body in enumerate(bodies):
        total = Vector3D(0, 0, 0)
        
        for force, ref in body.forces:
            force_direction = force.normalize()
            offset_origin = body.position + force_direction * body.radius
            scaled = force_direction * min(3.0, math.sqrt(force.length()) * 4)

            draw_arrow(offset_origin, scaled, ref.color)
            total += force
        
        total_direction = total.normalize()
        scaled_total = total_direction * (math.log1p(total.length()) * 3)
        offset_origin = body.position + total_direction * body.radius
        draw_arrow(offset_origin, scaled_total, RESULTANT_COL)
        queue_label(to_rl(body.position), "F", camera)

def draw_arrow(origin, vec, color, shaft_r=0.085, head_r=0.23, head_ratio=0.22):

    direction = vec.normalize()
    length = vec.length()
    if length < 1e-6:
        return

    shaft_end = origin + direction * (length * (1 - head_ratio))
    tip       = origin + vec

    rl.draw_cylinder_ex(to_rl(origin), to_rl(shaft_end), shaft_r, shaft_r, 12, color)
    rl.draw_cylinder_ex(to_rl(shaft_end), to_rl(tip), head_r, 0.0, 12, color)







    
