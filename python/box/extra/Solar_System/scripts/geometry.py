import math
from typing import Optional, Tuple, Union
import pyray as rl
from utils.vector3d import Vector3D
from typing import Optional, Tuple


class Point:
    """Represents a 2D point."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point({self.x}, {self.y})"

    def distance_to(self, other: "Point") -> float:
        """Calculate distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class Vector2D:
    """Represents a 2D vector for direction."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Vector2D({self.x}, {self.y})"

    def normalize(self) -> "Vector2D":
        """Return normalized vector."""
        length = math.sqrt(self.x**2 + self.y**2)
        if length == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / length, self.y / length)

    def length(self) -> float:
        """Return vector length."""
        return math.sqrt(self.x**2 + self.y**2)


class Ray2D:
    """Represents a ray with a starting point and direction."""

    def __init__(self, start_point: Point, direction: Vector2D):
        self.start_point = start_point
        self.direction = direction.normalize()

    def __repr__(self):
        return f"Ray(start={self.start_point}, direction={self.direction})"

    def get_point_at_distance(self, distance: float) -> Point:
        """Get point at specified distance along the ray."""
        return Point(
            self.start_point.x + self.direction.x * distance,
            self.start_point.y + self.direction.y * distance,
        )

    def is_point_on_ray(self, point: Point, tolerance: float = 1e-10) -> bool:
        """Check if a point lies on the ray."""
        # Vector from start to point
        to_point = Vector2D(point.x - self.start_point.x, point.y - self.start_point.y)

        # Check if vectors are parallel (cross product near zero)
        cross = self.direction.x * to_point.y - self.direction.y * to_point.x
        if abs(cross) > tolerance:
            return False

        # Check if point is in the same direction (dot product positive)
        dot = self.direction.x * to_point.x + self.direction.y * to_point.y
        return dot >= -tolerance

    def draw(
        self,
        length: float = 1000,
        color: rl.Color = rl.BLUE,
        thickness: float = 2.0,
    ):
        """Draw ray with specified length."""
        end_point = self.get_point_at_distance(length)
        rl.draw_line_ex(
            rl.Vector2(self.start_point.x, self.start_point.y),
            rl.Vector2(end_point.x, end_point.y),
            thickness,
            color,
        )

        # Draw arrow head to show direction
        arrow_length = 20
        arrow_angle = math.pi / 6  # 30 degrees

        # Calculate arrow head points
        angle = math.atan2(self.direction.y, self.direction.x)

        arrow_point1 = Point(
            end_point.x - arrow_length * math.cos(angle - arrow_angle),
            end_point.y - arrow_length * math.sin(angle - arrow_angle),
        )
        arrow_point2 = Point(
            end_point.x - arrow_length * math.cos(angle + arrow_angle),
            end_point.y - arrow_length * math.sin(angle + arrow_angle),
        )

        rl.draw_line_ex(
            rl.Vector2(end_point.x, end_point.y),
            rl.Vector2(arrow_point1.x, arrow_point1.y),
            thickness,
            color,
        )
        rl.draw_line_ex(
            rl.Vector2(end_point.x, end_point.y),
            rl.Vector2(arrow_point2.x, arrow_point2.y),
            thickness,
            color,
        )


class FiniteLine2D:
    """Represents a line segment with two endpoints."""

    def __init__(self, start_point: Point, end_point: Point):
        self.start_point = start_point
        self.end_point = end_point
        self.length = start_point.distance_to(end_point)

    def __repr__(self):
        return f"FiniteLine(start={self.start_point}, end={self.end_point})"

    def get_midpoint(self) -> Point:
        """Get the midpoint of the line segment."""
        return Point(
            (self.start_point.x + self.end_point.x) / 2,
            (self.start_point.y + self.end_point.y) / 2,
        )

    def get_point_at_parameter(self, t: float) -> Point:
        """Get point along line segment where t=0 is start, t=1 is end."""
        return Point(
            self.start_point.x + t * (self.end_point.x - self.start_point.x),
            self.start_point.y + t * (self.end_point.y - self.start_point.y),
        )

    def is_point_on_segment(self, point: Point, tolerance: float = 1e-10) -> bool:
        """Check if a point lies on the line segment."""
        # Check if point is collinear with segment endpoints
        cross_product = (point.y - self.start_point.y) * (
            self.end_point.x - self.start_point.x
        ) - (point.x - self.start_point.x) * (self.end_point.y - self.start_point.y)

        if abs(cross_product) > tolerance:
            return False

        # Check if point is within the segment bounds
        dot_product = (point.x - self.start_point.x) * (
            self.end_point.x - self.start_point.x
        ) + (point.y - self.start_point.y) * (self.end_point.y - self.start_point.y)

        if dot_product < 0:
            return False

        squared_distance = (self.end_point.x - self.start_point.x) ** 2 + (
            self.end_point.y - self.start_point.y
        ) ** 2

        return dot_product <= squared_distance

    def get_direction_vector(self) -> Vector2D:
        """Get normalized direction vector from start to end."""
        dx = self.end_point.x - self.start_point.x
        dy = self.end_point.y - self.start_point.y
        return Vector2D(dx, dy).normalize()

    def draw(self, color: rl.Color = rl.GREEN, thickness: float = 2.0):
        """Draw the finite line segment."""
        rl.draw_line_ex(
            rl.Vector2(self.start_point.x, self.start_point.y),
            rl.Vector2(self.end_point.x, self.end_point.y),
            thickness,
            color,
        )

        # Draw endpoint circles to show it's finite
        rl.draw_circle(int(self.start_point.x), int(self.start_point.y), 4, color)
        rl.draw_circle(int(self.end_point.x), int(self.end_point.y), 4, color)


def create_ray_from_points(start_point: Point, through_point: Point) -> Ray2D:
    """Create a ray starting at start_point and passing through through_point."""
    direction = Vector2D(
        through_point.x - start_point.x, through_point.y - start_point.y
    )
    return Ray2D(start_point, direction)


def create_finite_line_from_points(point1: Point, point2: Point) -> FiniteLine2D:
    """Create a finite line segment between two points."""
    return FiniteLine2D(point1, point2)


class Ray3D:
    """3D Ray for your solar system - useful for physics, collision detection, etc."""

    def __init__(self, origin: Vector3D, direction: Vector3D):
        self.origin = origin
        self.direction = (
            direction.normalized()
        )  # Assuming Vector3D has normalized() method

    def __repr__(self):
        return f"Ray3D(origin={self.origin}, direction={self.direction})"

    def get_point_at_distance(self, distance: float) -> Vector3D:
        """Get point at specified distance along the ray."""
        return Vector3D(
            self.origin.x + self.direction.x * distance,
            self.origin.y + self.direction.y * distance,
            self.origin.z + self.direction.z * distance,
        )

    def draw(
        self, length: float = 10.0, color: rl.Color = rl.BLUE, thickness: float = 0.1
    ):
        """Draw the 3D ray."""
        end_point = self.get_point_at_distance(length)

        # Draw the main ray line
        rl.draw_line_3d(
            rl.Vector3(self.origin.x, self.origin.y, self.origin.z),
            rl.Vector3(end_point.x, end_point.y, end_point.z),
            color,
        )

        # Draw arrow head (simplified as a small sphere)
        rl.draw_sphere(
            rl.Vector3(end_point.x, end_point.y, end_point.z), thickness * 3, color
        )

    def intersect_sphere(
        self, sphere_center: Vector3D, sphere_radius: float
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if ray intersects with a sphere (useful for planet collision detection).
        Returns (hit, distance_to_intersection)
        """
        # Vector from ray origin to sphere center
        oc = Vector3D(
            self.origin.x - sphere_center.x,
            self.origin.y - sphere_center.y,
            self.origin.z - sphere_center.z,
        )

        # Quadratic equation coefficients
        a = self.direction.dot(self.direction)  # Should be 1 for normalized direction
        b = 2.0 * oc.dot(self.direction)
        c = oc.dot(oc) - sphere_radius * sphere_radius

        discriminant = b * b - 4 * a * c

        if discriminant < 0:
            return False, None  # No intersection

        # Calculate the nearest intersection point
        sqrt_discriminant = math.sqrt(discriminant)
        t1 = (-b - sqrt_discriminant) / (2.0 * a)
        t2 = (-b + sqrt_discriminant) / (2.0 * a)

        # Return the nearest positive intersection
        if t1 > 0:
            return True, t1
        elif t2 > 0:
            return True, t2
        else:
            return False, None  # Intersections are behind the ray origin


class Line3D:
    """3D Line segment for your solar system."""

    def __init__(self, start_point: Vector3D, end_point: Vector3D):
        self.start_point = start_point
        self.end_point = end_point
        self.length = start_point.distance_to(
            end_point
        )  # Assuming Vector3D has distance_to method

    def __repr__(self):
        return f"Line3D(start={self.start_point}, end={self.end_point})"

    def get_midpoint(self) -> Vector3D:
        """Get the midpoint of the line segment."""
        return Vector3D(
            (self.start_point.x + self.end_point.x) / 2,
            (self.start_point.y + self.end_point.y) / 2,
            (self.start_point.z + self.end_point.z) / 2,
        )

    def get_direction_vector(self) -> Vector3D:
        """Get direction vector from start to end."""
        return Vector3D(
            self.end_point.x - self.start_point.x,
            self.end_point.y - self.start_point.y,
            self.end_point.z - self.start_point.z,
        ).normalized()

    def draw(self, color: rl.Color = rl.GREEN, thickness: float = 0.1):
        """Draw the 3D line segment."""
        rl.draw_line_3d(
            rl.Vector3(self.start_point.x, self.start_point.y, self.start_point.z),
            rl.Vector3(self.end_point.x, self.end_point.y, self.end_point.z),
            color,
        )

        # Draw endpoints as small spheres
        rl.draw_sphere(
            rl.Vector3(self.start_point.x, self.start_point.y, self.start_point.z),
            thickness * 2,
            color,
        )
        rl.draw_sphere(
            rl.Vector3(self.end_point.x, self.end_point.y, self.end_point.z),
            thickness * 2,
            color,
        )


class OrbitPath:
    """Represents an elliptical orbit path for planets."""

    def __init__(
        self,
        center: Vector3D,
        semi_major_axis: float,
        semi_minor_axis: float,
        rotation: Vector3D = Vector3D(0, 0, 0),
    ):
        self.center = center
        self.semi_major_axis = semi_major_axis
        self.semi_minor_axis = semi_minor_axis
        self.rotation = rotation  # Rotation angles around x, y, z axes

    def get_position_at_angle(self, angle_radians: float) -> Vector3D:
        """Get position on orbit at given angle (0 to 2π)."""
        # Basic ellipse calculation
        x = self.semi_major_axis * math.cos(angle_radians)
        y = 0  # Orbit in XZ plane initially
        z = self.semi_minor_axis * math.sin(angle_radians)

        # Apply rotation (simplified - you might want proper rotation matrices)
        # This is a basic rotation around Y axis
        if self.rotation.y != 0:
            cos_rot = math.cos(self.rotation.y)
            sin_rot = math.sin(self.rotation.y)
            new_x = x * cos_rot - z * sin_rot
            new_z = x * sin_rot + z * cos_rot
            x, z = new_x, new_z

        return Vector3D(self.center.x + x, self.center.y + y, self.center.z + z)

    def draw(self, segments: int = 64, color: rl.Color = rl.YELLOW):
        """Draw the orbit path as a series of connected lines."""
        points = []
        for i in range(segments + 1):
            angle = (2 * math.pi * i) / segments
            point = self.get_position_at_angle(angle)
            points.append(point)

        # Draw lines connecting the points
        for i in range(len(points) - 1):
            rl.draw_line_3d(
                rl.Vector3(points[i].x, points[i].y, points[i].z),
                rl.Vector3(points[i + 1].x, points[i + 1].y, points[i + 1].z),
                color,
            )


# Utility functions for 3D geometry
def create_ray_from_camera_to_mouse(
    camera_pos: Vector3D, mouse_screen_pos: rl.Vector2, camera: rl.Camera3D
) -> Ray3D:
    """Create a 3D ray from camera through mouse position (for object picking)."""
    # Get ray from camera through screen point
    ray = rl.get_mouse_ray(mouse_screen_pos, camera)

    origin = Vector3D(ray.position.x, ray.position.y, ray.position.z)
    direction = Vector3D(ray.direction.x, ray.direction.y, ray.direction.z)

    return Ray3D(origin, direction)


def create_connection_line(body1_pos: Vector3D, body2_pos: Vector3D) -> Line3D:
    """Create a line connecting two celestial bodies."""
    return Line3D(body1_pos, body2_pos)


# Example usage for your solar system
def create_planetary_system():
    """Example of how to use 3D geometry in your solar system."""
    # Sun at center
    sun_pos = Vector3D(0, 0, 0)

    # Create orbit paths for planets
    earth_orbit = OrbitPath(
        sun_pos, 20.0, 19.5, Vector3D(0, 0.1, 0)
    )  # Slightly elliptical
    mars_orbit = OrbitPath(sun_pos, 30.0, 28.0, Vector3D(0, 0.2, 0))

    # Create some rays (maybe for light rays from sun)
    sun_ray1 = Ray3D(sun_pos, Vector3D(1, 0, 0))
    sun_ray2 = Ray3D(sun_pos, Vector3D(0, 1, 0))
    sun_ray3 = Ray3D(sun_pos, Vector3D(0, 0, 1))

    return {"orbits": [earth_orbit, mars_orbit], "rays": [sun_ray1, sun_ray2, sun_ray3]}

