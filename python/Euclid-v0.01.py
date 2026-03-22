import numpy as np
import math
from vpython import *

class Point:
    """Definition 1: A point is that which has no part."""
    def __init__(self, x, y, z=0, label=None):
        self.x = x
        self.y = y
        self.z = z
        self.label = label
        self.visual = None
    
    def distance_to(self, other_point):
        return math.sqrt((self.x - other_point.x)**2 + 
                         (self.y - other_point.y)**2 + 
                         (self.z - other_point.z)**2)
    
    def equals(self, other_point, epsilon=1e-9):
        return (abs(self.x - other_point.x) < epsilon and 
                abs(self.y - other_point.y) < epsilon and 
                abs(self.z - other_point.z) < epsilon)
    
    def __str__(self):
        if self.label:
            return f"Point {self.label}({self.x}, {self.y}, {self.z})"
        return f"Point({self.x}, {self.y}, {self.z})"
    
    def draw(self, color=color.blue, radius=0.1, show_label=True):
        self.visual = sphere(pos=vector(self.x, self.y, self.z), radius=radius, color=color)
        if self.label and show_label:
            text(text=self.label, pos=vector(self.x + 0.2, self.y + 0.2, self.z),
                 height=0.2, color=color)
        return self.visual


class Line:
    """Definition 2: A line is breadthless length."""
    def __init__(self, point1, point2, label=None):
        self.point1 = point1
        self.point2 = point2
        self.label = label
        self.visual = None
    
    def length(self):
        return self.point1.distance_to(self.point2)
    
    def contains_point(self, point, epsilon=1e-9):
        # Check if point is on the line segment
        d1 = point.distance_to(self.point1)
        d2 = point.distance_to(self.point2)
        line_length = self.length()
        return abs(d1 + d2 - line_length) < epsilon
    
    def __str__(self):
        if self.label:
            return f"Line {self.label} from {self.point1} to {self.point2}"
        return f"Line from {self.point1} to {self.point2}"
    
    def draw(self, color=color.black, radius=0.03, show_label=True):
        self.visual = cylinder(pos=vector(self.point1.x, self.point1.y, self.point1.z),
                             axis=vector(self.point2.x - self.point1.x, 
                                       self.point2.y - self.point1.y,
                                       self.point2.z - self.point1.z),
                             radius=radius, color=color)
        
        # Draw label at the midpoint of the line
        if self.label and show_label:
            mid_x = (self.point1.x + self.point2.x) / 2
            mid_y = (self.point1.y + self.point2.y) / 2
            mid_z = (self.point1.z + self.point2.z) / 2
            text(text=self.label, pos=vector(mid_x, mid_y, mid_z), 
                 height=0.2, color=color)
        
        return self.visual


class StraightLine(Line):
    """Definition 4: A straight line is a line which lies evenly with the points on itself."""
    def __init__(self, point1, point2, label=None, extend_factor=10):
        super().__init__(point1, point2, label)
        self.extend_factor = extend_factor
        
        # Calculate line equation: ax + by + cz + d = 0
        self.direction = vector(self.point2.x - self.point1.x,
                              self.point2.y - self.point1.y,
                              self.point2.z - self.point1.z)
        
        # Normalize direction
        self.direction_length = math.sqrt(self.direction.x**2 + self.direction.y**2 + self.direction.z**2)
        self.unit_direction = vector(self.direction.x / self.direction_length,
                                   self.direction.y / self.direction_length,
                                   self.direction.z / self.direction_length)
    
    def contains_point(self, point, epsilon=1e-9):
        # Vector from point1 to the check point
        v = vector(point.x - self.point1.x, point.y - self.point1.y, point.z - self.point1.z)
        
        # Cross product should be zero if points are collinear
        cross = vector(
            v.y * self.unit_direction.z - v.z * self.unit_direction.y,
            v.z * self.unit_direction.x - v.x * self.unit_direction.z,
            v.x * self.unit_direction.y - v.y * self.unit_direction.x
        )
        
        # Magnitude of cross product
        cross_magnitude = math.sqrt(cross.x**2 + cross.y**2 + cross.z**2)
        return cross_magnitude < epsilon
    
    def intersection_with(self, other_line):
        # This is a simplified 2D intersection for now
        # Would need more complex 3D line intersection for full implementation
        
        # For 2D lines assuming z=0
        # Line 1: p1 + t1 * dir1
        # Line 2: p2 + t2 * dir2
        
        # Cross product of directions
        cross_z = self.unit_direction.x * other_line.unit_direction.y - self.unit_direction.y * other_line.unit_direction.x
        
        # If parallel (cross product near zero)
        if abs(cross_z) < 1e-9:
            return None
        
        # Vector between starting points
        dp = vector(other_line.point1.x - self.point1.x,
                  other_line.point1.y - self.point1.y,
                  other_line.point1.z - self.point1.z)
        
        # Calculate parameters
        t1 = (dp.x * other_line.unit_direction.y - dp.y * other_line.unit_direction.x) / cross_z
        
        # Intersection point
        x = self.point1.x + t1 * self.unit_direction.x
        y = self.point1.y + t1 * self.unit_direction.y
        z = self.point1.z + t1 * self.unit_direction.z
        
        return Point(x, y, z)
    
    def draw(self, color=color.black, radius=0.02, show_label=True):
        # Extend the line in both directions
        ext1 = vector(self.point1.x - self.extend_factor * self.unit_direction.x,
                    self.point1.y - self.extend_factor * self.unit_direction.y,
                    self.point1.z - self.extend_factor * self.unit_direction.z)
        
        ext2 = vector(self.point2.x + self.extend_factor * self.unit_direction.x,
                    self.point2.y + self.extend_factor * self.unit_direction.y,
                    self.point2.z + self.extend_factor * self.unit_direction.z)
        
        self.visual = cylinder(pos=ext1, axis=vector(ext2.x - ext1.x, ext2.y - ext1.y, ext2.z - ext1.z),
                             radius=radius, color=color)
        
        # Draw label at the original point1
        if self.label and show_label:
            text(text=self.label, pos=vector(self.point1.x, self.point1.y, self.point1.z), 
                 height=0.2, color=color)
        
        return self.visual


class Angle:
    """Definition 8: A plane angle is the inclination to one another of two lines which meet..."""
    def __init__(self, point1, vertex, point2, label=None):
        self.point1 = point1
        self.vertex = vertex
        self.point2 = point2
        self.label = label
        self.visual = None
    
    def measure(self):
        """Calculate the angle in radians"""
        vector1 = vector(self.point1.x - self.vertex.x, 
                       self.point1.y - self.vertex.y,
                       self.point1.z - self.vertex.z)
        
        vector2 = vector(self.point2.x - self.vertex.x, 
                       self.point2.y - self.vertex.y,
                       self.point2.z - self.vertex.z)
        
        # Calculate magnitudes
        mag1 = math.sqrt(vector1.x**2 + vector1.y**2 + vector1.z**2)
        mag2 = math.sqrt(vector2.x**2 + vector2.y**2 + vector2.z**2)
        
        # Calculate dot product
        dot_product = vector1.x * vector2.x + vector1.y * vector2.y + vector1.z * vector2.z
        
        # Calculate angle using dot product formula (clamping to avoid domain errors)
        cos_angle = max(min(dot_product / (mag1 * mag2), 1.0), -1.0)
        return math.acos(cos_angle)
    
    def measure_degrees(self):
        """Convert angle to degrees"""
        return math.degrees(self.measure())
    
    def __str__(self):
        if self.label:
            return f"Angle {self.label} at {self.vertex} between {self.point1} and {self.point2}: {self.measure_degrees():.2f}°"
        return f"Angle at {self.vertex} between {self.point1} and {self.point2}: {self.measure_degrees():.2f}°"
    
    def draw(self, radius=0.5, color=color.green, show_label=True):
        # Create a curve for the angle arc
        angle_rad = self.measure()
        
        # Vectors from vertex to points
        v1 = vector(self.point1.x - self.vertex.x, 
                  self.point1.y - self.vertex.y,
                  self.point1.z - self.vertex.z)
        
        v2 = vector(self.point2.x - self.vertex.x, 
                  self.point2.y - self.vertex.y,
                  self.point2.z - self.vertex.z)
        
        # Normalize vectors
        v1_length = math.sqrt(v1.x**2 + v1.y**2 + v1.z**2)
        v2_length = math.sqrt(v2.x**2 + v2.y**2 + v2.z**2)
        
        v1_unit = vector(v1.x / v1_length, v1.y / v1_length, v1.z / v1_length)
        v2_unit = vector(v2.x / v2_length, v2.y / v2_length, v2.z / v2_length)
        
        # Normal to the plane containing the angle
        normal = cross(v1_unit, v2_unit)
        normal_length = math.sqrt(normal.x**2 + normal.y**2 + normal.z**2)
        
        # If vectors are nearly parallel, we need a different approach
        if normal_length < 1e-6:
            # Choose an arbitrary perpendicular direction
            if abs(v1_unit.x) > 0.1:
                normal = vector(0, 1, 0)
            else:
                normal = vector(1, 0, 0)
        else:
            normal = vector(normal.x / normal_length, 
                          normal.y / normal_length, 
                          normal.z / normal_length)
        
        # Create points for the angle arc
        num_segments = 20
        arc_points = []
        
        # Calculate rotation matrix around normal
        for i in range(num_segments + 1):
            t = i / num_segments
            angle_t = t * angle_rad
            
            # Rodrigues' rotation formula
            # v_rot = v * cos(θ) + (k × v) * sin(θ) + k * (k · v) * (1 - cos(θ))
            # where k is the unit axis of rotation, v is the vector to rotate
            
            cos_angle_t = math.cos(angle_t)
            sin_angle_t = math.sin(angle_t)
            
            # k × v1_unit
            cross_prod = cross(normal, v1_unit)
            
            # k · v1_unit
            dot_prod = dot(normal, v1_unit)
            
            # Rotated vector
            rotated = vector(
                v1_unit.x * cos_angle_t + cross_prod.x * sin_angle_t + normal.x * dot_prod * (1 - cos_angle_t),
                v1_unit.y * cos_angle_t + cross_prod.y * sin_angle_t + normal.y * dot_prod * (1 - cos_angle_t),
                v1_unit.z * cos_angle_t + cross_prod.z * sin_angle_t + normal.z * dot_prod * (1 - cos_angle_t)
            )
            
            # Scale by radius and add to vertex position
            point_pos = vector(
                self.vertex.x + radius * rotated.x,
                self.vertex.y + radius * rotated.y,
                self.vertex.z + radius * rotated.z
            )
            
            arc_points.append(point_pos)
        
        # Create the visual curve
        self.visual = curve(pos=arc_points, color=color, radius=0.02)
        
        # Add label
        if self.label and show_label:
            # Calculate the midpoint angle
            mid_idx = len(arc_points) // 2
            mid_pos = arc_points[mid_idx]
            
            text(text=f"{self.label}: {self.measure_degrees():.1f}°", 
                 pos=vector(mid_pos.x, mid_pos.y, mid_pos.z),
                 height=0.15, color=color)
        
        return self.visual


class Circle:
    """Definition 15: A circle is a plane figure contained by one line such that..."""
    def __init__(self, center, radius, label=None):
        self.center = center
        self.radius = radius
        self.label = label
        self.visual = None
    
    def contains_point(self, point, epsilon=1e-9):
        distance = self.center.distance_to(point)
        return abs(distance - self.radius) < epsilon
    
    def intersection_with_line(self, line):
        if not isinstance(line, StraightLine):
            line = StraightLine(line.point1, line.point2)
        
        # Line in parametric form: point1 + t * direction
        # Circle equation: |p - center|^2 = radius^2
        
        # Vector from line point to circle center
        oc = vector(self.center.x - line.point1.x,
                  self.center.y - line.point1.y,
                  self.center.z - line.point1.z)
        
        # Quadratic equation coefficients
        a = dot(line.unit_direction, line.unit_direction)  # Should be 1
        b = 2 * dot(oc, line.unit_direction)
        c = dot(oc, oc) - self.radius * self.radius
        
        discriminant = b * b - 4 * a * c
        
        # No intersection
        if discriminant < 0:
            return []
        
        # Calculate intersection parameters
        t1 = (-b + math.sqrt(discriminant)) / (2 * a)
        t2 = (-b - math.sqrt(discriminant)) / (2 * a)
        
        # Create intersection points
        intersections = []
        
        # First intersection
        x1 = line.point1.x + t1 * line.unit_direction.x
        y1 = line.point1.y + t1 * line.unit_direction.y
        z1 = line.point1.z + t1 * line.unit_direction.z
        intersections.append(Point(x1, y1, z1))
        
        # Second intersection (if not tangent)
        if discriminant > 1e-9:
            x2 = line.point1.x + t2 * line.unit_direction.x
            y2 = line.point1.y + t2 * line.unit_direction.y
            z2 = line.point1.z + t2 * line.unit_direction.z
            intersections.append(Point(x2, y2, z2))
        
        return intersections
    
    def __str__(self):
        if self.label:
            return f"Circle {self.label} with center {self.center} and radius {self.radius}"
        return f"Circle with center {self.center} and radius {self.radius}"
    
    def draw(self, color=color.red, opacity=0.3, show_label=True):
        # Create a ring to represent the circle
        self.visual = ring(pos=vector(self.center.x, self.center.y, self.center.z),
                         axis=vector(0, 0, 1),  # Default to xy plane
                         radius=self.radius,
                         thickness=self.radius*0.05,
                         color=color,
                         opacity=1)
        
        # Add a transparent disk inside
        self.disk = cylinder(pos=vector(self.center.x, self.center.y, self.center.z - 0.01),
                           axis=vector(0, 0, 0.02),
                           radius=self.radius,
                           color=color,
                           opacity=opacity)
        
        if self.label and show_label:
            text(text=self.label, 
                 pos=vector(self.center.x, self.center.y + self.radius + 0.2, self.center.z),
                 height=0.2, color=color)
        
        return self.visual


class Triangle:
    """A triangle is a figure contained by three straight lines."""
    def __init__(self, point1, point2, point3, label=None):
        self.point1 = point1
        self.point2 = point2
        self.point3 = point3
        self.label = label
        self.visual = None
        
        # Create the sides
        self.side1 = Line(point2, point3)  # Opposite to point1
        self.side2 = Line(point1, point3)  # Opposite to point2
        self.side3 = Line(point1, point2)  # Opposite to point3
        
        # Create the angles
        self.angle1 = Angle(point3, point1, point2)  # At point1
        self.angle2 = Angle(point1, point2, point3)  # At point2
        self.angle3 = Angle(point2, point3, point1)  # At point3
    
    def perimeter(self):
        return self.side1.length() + self.side2.length() + self.side3.length()
    
    def area(self):
        # Calculate area using Heron's formula
        s = self.perimeter() / 2
        return math.sqrt(s * (s - self.side1.length()) * (s - self.side2.length()) * (s - self.side3.length()))
    
    def __str__(self):
        if self.label:
            return f"Triangle {self.label} with vertices {self.point1}, {self.point2}, {self.point3}"
        return f"Triangle with vertices {self.point1}, {self.point2}, {self.point3}"
    
    def draw(self, color=color.blue, opacity=0.3, show_label=True):
        # Draw vertices
        self.point1.draw()
        self.point2.draw()
        self.point3.draw()
        
        # Draw sides
        self.side1.draw()
        self.side2.draw()
        self.side3.draw()
        
        # Create a triangle face
        self.visual = triangle(
            v0=vertex(pos=vector(self.point1.x, self.point1.y, self.point1.z), color=color),
            v1=vertex(pos=vector(self.point2.x, self.point2.y, self.point2.z), color=color),
            v2=vertex(pos=vector(self.point3.x, self.point3.y, self.point3.z), color=color),
            opacity=opacity
        )
        
        # Draw angles
        angle_radius = min(0.3, self.side1.length()/3, self.side2.length()/3, self.side3.length()/3)
        self.angle1.draw(radius=angle_radius)
        self.angle2.draw(radius=angle_radius)
        self.angle3.draw(radius=angle_radius)
        
        # Plot label at centroid
        if self.label and show_label:
            centroid_x = (self.point1.x + self.point2.x + self.point3.x) / 3
            centroid_y = (self.point1.y + self.point2.y + self.point3.y) / 3
            centroid_z = (self.point1.z + self.point2.z + self.point3.z) / 3
            
            text(text=self.label, 
                 pos=vector(centroid_x, centroid_y, centroid_z),
                 height=0.2, color=color)
        
        return self.visual


class Square:
    """Definition 22: Of quadrilateral figures, a square is that which is both equilateral and right-angled."""
    def __init__(self, point1, point2, label=None):
        self.point1 = point1
        self.point2 = point2
        self.label = label
        self.visual = None
        
        # Calculate the side length
        dx = point2.x - point1.x
        dy = point2.y - point1.y
        dz = point2.z - point1.z
        self.side_length = math.sqrt(dx**2 + dy**2 + dz**2)
        
        # For simplicity, we'll assume the square is in the xy plane if z coordinates are equal
        if abs(dz) < 1e-9:
            # Calculate unit vector perpendicular to the first side
            ux = -dy / self.side_length
            uy = dx / self.side_length
            uz = 0
            
            # Calculate the other corners
            self.point3 = Point(point2.x + ux * self.side_length, 
                               point2.y + uy * self.side_length, 
                               point2.z + uz * self.side_length)
                               
            self.point4 = Point(point1.x + ux * self.side_length, 
                               point1.y + uy * self.side_length, 
                               point1.z + uz * self.side_length)
        else:
            # 3D case - find a perpendicular vector to create a square
            # We need two perpendicular vectors to the edge vector
            edge = vector(dx, dy, dz)
            
            # Find a perpendicular vector - we can use cross product with any non-parallel vector
            # Using z-axis as a common reference, unless edge is parallel to z-axis
            if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                ref_vector = vector(1, 0, 0)  # use x-axis
            else:
                ref_vector = vector(0, 0, 1)  # use z-axis
            
            # First perpendicular vector
            perp1 = cross(edge, ref_vector)
            perp1_length = math.sqrt(perp1.x**2 + perp1.y**2 + perp1.z**2)
            perp1 = vector(perp1.x / perp1_length, perp1.y / perp1_length, perp1.z / perp1_length)
            
            # Second perpendicular vector (perpendicular to both edge and perp1)
            perp2 = cross(edge, perp1)
            perp2_length = math.sqrt(perp2.x**2 + perp2.y**2 + perp2.z**2)
            perp2 = vector(perp2.x / perp2_length, perp2.y / perp2_length, perp2.z / perp2_length)
            
            # Scale to side length
            scaled_perp = vector(perp1.x * self.side_length, 
                               perp1.y * self.side_length, 
                               perp1.z * self.side_length)
            
            # Calculate the other corners
            self.point3 = Point(point2.x + scaled_perp.x, 
                               point2.y + scaled_perp.y, 
                               point2.z + scaled_perp.z)
                               
            self.point4 = Point(point1.x + scaled_perp.x, 
                               point1.y + scaled_perp.y, 
                               point1.z + scaled_perp.z)
        
        # Create the sides
        self.side1 = Line(self.point1, self.point2)
        self.side2 = Line(self.point2, self.point3)
        self.side3 = Line(self.point3, self.point4)
        self.side4 = Line(self.point4, self.point1)
    
    def perimeter(self):
        return 4 * self.side_length
    
    def area(self):
        return self.side_length**2
    
    def __str__(self):
        if self.label:
            return f"Square {self.label} with vertices {self.point1}, {self.point2}, {self.point3}, {self.point4}"
        return f"Square with vertices {self.point1}, {self.point2}, {self.point3}, {self.point4}"
    
    def draw(self, color=color.purple, opacity=0.3, show_label=True):
        # Draw vertices
        self.point1.draw()
        self.point2.draw()
        self.point3.draw()
        self.point4.draw()
        
        # Draw sides
        self.side1.draw()
        self.side2.draw()
        self.side3.draw()
        self.side4.draw()
        
        # Create square faces
        self.visual = quad(
            v0=vertex(pos=vector(self.point1.x, self.point1.y, self.point1.z), color=color),
            v1=vertex(pos=vector(self.point2.x, self.point2.y, self.point2.z), color=color),
            v2=vertex(pos=vector(self.point3.x, self.point3.y, self.point3.z), color=color),
            v3=vertex(pos=vector(self.point4.x, self.point4.y, self.point4.z), color=color),
            opacity=opacity
        )
        
        # Plot label at center
        if self.label and show_label:
            center_x = (self.point1.x + self.point2.x + self.point3.x + self.point4.x) / 4
            center_y = (self.point1.y + self.point2.y + self.point3.y + self.point4.y) / 4
            center_z = (self.point1.z + self.point2.z + self.point3.z + self.point4.z) / 4
            
            text(text=self.label, 
                 pos=vector(center_x, center_y, center_z),
                 height=0.2, color=color)
        
        return self.visual


class EuclideanGeometry:
    """Implementation of Euclid's postulates and constructions"""
    
    @staticmethod
    def draw_line(point1, point2):
        """Postulate 1: To draw a straight line from any point to any point."""
        return Line(point1, point2)
    
    @staticmethod
    def extend_line(line):
        """Postulate 2: To extend a finite straight line continuously in a straight line."""
        return StraightLine(line.point1, line.point2)
    
    @staticmethod
    def draw_circle(center, radius):
        """Postulate 3: To describe a circle with any center and radius."""
        return Circle(center, radius)
    
    @staticmethod
    def is_right_angle(angle, epsilon=1e-9):
        """Postulate 4: All right angles are equal to one another."""
        return abs(angle.measure() - math.pi/2) < epsilon
    
    @staticmethod
    def draw_parallel_line(line, point):
        """Postulate 5: The parallel postulate."""
        # Create a parallel line through the given point
        dx = line.point2.x - line.point1.x
        dy = line.point2.y - line.point1.y
        dz = line.point2.z - line.point1.z
        
        new_point = Point(point.x + dx, point.y + dy, point.z + dz)
        return StraightLine(point, new_point)
    
    @staticmethod
    def bisect_angle(angle):
        """Proposition 9: To bisect a given rectilineal angle."""
        # Similar to original implementation but with VPython visualization
        # Construct equal distance points on the two rays of the angle
        distance = 2  # arbitrary distance
        
        # Calculate unit vectors for both rays
        ray1 = vector(angle.point1.x - angle.vertex.x, 
                    angle.point1.y - angle.vertex.y,
                    angle.point1.z - angle.vertex.z)
        
        ray2 = vector(angle.point2.x - angle.vertex.x, 
                    angle.point2.y - angle.vertex.y,
                    angle.point2.z - angle.vertex.z)
        
        ray1_length = math.sqrt(ray1.x**2 + ray1.y**2 + ray1.z**2)
        ray2_length = math.sqrt(ray2.x**2 + ray2.y**2 + ray2.z**2)
        
        ray1_unit = vector(ray1.x / ray1_length, ray1.y / ray1_length, ray1.z / ray1_length)
        ray2_unit = vector(ray2.x / ray2