import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle as MplCircle
from matplotlib.patches import Polygon
import matplotlib.colors as mcolors
import math

# blueprint to create geometric points
class Point:
    """
    Definition 1: A point is that which has no part.
    
    It has Position
    """
    def __init__(self, x, y, label=None):
        self.x = x
        self.y = y
        self.label = label
    
    def distance_to(self, other_point):
        # d = sqrt((x2 - x1)^2 + (y2 - y1)^2)
        return math.sqrt((self.x - other_point.x)**2 + (self.y - other_point.y)**2)
    
    def equals(self, other_point, epsilon=1e-9):
        return abs(self.x - other_point.x) < epsilon and abs(self.y - other_point.y) < epsilon
    
    def __str__(self):
        if self.label:
            return f"Point {self.label}({self.x}, {self.y})"
        return f"Point({self.x}, {self.y})"
    
    def plot(self, ax, color='blue', marker='o', size=50, show_label=True):
        ax.scatter(self.x, self.y, color=color, s=size, zorder=10)
        if self.label and show_label:
            ax.annotate(self.label, (self.x + 0.1, self.y + 0.1), fontsize=12)


class Line:
    """Definition 2: A line is breadthless length."""
    def __init__(self, point1, point2, label=None):
        self.point1 = point1
        self.point2 = point2
        self.label = label
    
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
    
    def plot(self, ax, color='black', linewidth=1.5, linestyle='-', show_label=True):
        ax.plot([self.point1.x, self.point2.x], [self.point1.y, self.point2.y], 
                color=color, linewidth=linewidth, linestyle=linestyle)
        
        # Plot label at the midpoint of the line
        if self.label and show_label:
            mid_x = (self.point1.x + self.point2.x) / 2
            mid_y = (self.point1.y + self.point2.y) / 2
            ax.annotate(self.label, (mid_x, mid_y), fontsize=10, 
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7))


class StraightLine(Line):
    """Definition 4: A straight line is a line which lies evenly with the points on itself."""
    def __init__(self, point1, point2, label=None):
        super().__init__(point1, point2, label)
        
        # Calculate line equation: ax + by + c = 0
        self.a = self.point2.y - self.point1.y
        self.b = self.point1.x - self.point2.x
        self.c = (self.point2.x * self.point1.y) - (self.point1.x * self.point2.y)
    
    def contains_point(self, point, epsilon=1e-9):
        # Check if point is on the infinite line
        return abs(self.a * point.x + self.b * point.y + self.c) < epsilon
    
    def intersection_with(self, other_line):
        det = self.a * other_line.b - other_line.a * self.b
        
        # Check if lines are parallel
        if abs(det) < 1e-9:
            return None
        
        x = (other_line.b * (-self.c) - self.b * (-other_line.c)) / det
        y = (self.a * (-other_line.c) - other_line.a * (-self.c)) / det
        
        return Point(x, y)
    
    def plot(self, ax, xlim=None, ylim=None, color='black', linewidth=1.5, linestyle='-', show_label=True):
        if xlim is None:
            xlim = ax.get_xlim()
        if ylim is None:
            ylim = ax.get_ylim()
        
        # Calculate points at the boundaries of the plot
        if abs(self.b) < 1e-9:  # Vertical line
            x = -self.c / self.a
            ax.plot([x, x], ylim, color=color, linewidth=linewidth, linestyle=linestyle)
        elif abs(self.a) < 1e-9:  # Horizontal line
            y = -self.c / self.b
            ax.plot(xlim, [y, y], color=color, linewidth=linewidth, linestyle=linestyle)
        else:
            # Calculate y for the left and right boundaries
            x_left, x_right = xlim
            y_left = (-self.a * x_left - self.c) / self.b
            y_right = (-self.a * x_right - self.c) / self.b
            
            # Check if these points are within the y limits
            in_bounds = []
            points = []
            
            if ylim[0] <= y_left <= ylim[1]:
                in_bounds.append(True)
                points.append((x_left, y_left))
            else:
                in_bounds.append(False)
            
            if ylim[0] <= y_right <= ylim[1]:
                in_bounds.append(True)
                points.append((x_right, y_right))
            else:
                in_bounds.append(False)
            
            # If we don't have 2 points, calculate x for top and bottom boundaries
            if in_bounds.count(True) < 2:
                y_bottom, y_top = ylim
                x_bottom = (-self.b * y_bottom - self.c) / self.a
                x_top = (-self.b * y_top - self.c) / self.a
                
                if xlim[0] <= x_bottom <= xlim[1] and not (x_bottom, y_bottom) in points:
                    points.append((x_bottom, y_bottom))
                
                if xlim[0] <= x_top <= xlim[1] and not (x_top, y_top) in points:
                    points.append((x_top, y_top))
            
            # Plot the line using the calculated points
            if len(points) >= 2:
                ax.plot([points[0][0], points[1][0]], [points[0][1], points[1][1]], 
                       color=color, linewidth=linewidth, linestyle=linestyle)
        
        # Plot label at a point on the line
        if self.label and show_label:
            mid_x = (self.point1.x + self.point2.x) / 2
            mid_y = (self.point1.y + self.point2.y) / 2
            ax.annotate(self.label, (mid_x, mid_y), fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7))


class Angle:
    """Definition 8: A plane angle is the inclination to one another of two lines which meet..."""
    def __init__(self, point1, vertex, point2, label=None):
        self.point1 = point1
        self.vertex = vertex
        self.point2 = point2
        self.label = label
    
    def measure(self):
        """Calculate the angle in radians"""
        vector1 = (self.point1.x - self.vertex.x, self.point1.y - self.vertex.y)
        vector2 = (self.point2.x - self.vertex.x, self.point2.y - self.vertex.y)
        
        # Calculate dot product
        dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]
        
        # Calculate magnitudes
        mag1 = math.sqrt(vector1[0]**2 + vector1[1]**2)
        mag2 = math.sqrt(vector2[0]**2 + vector2[1]**2)
        
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
    
    def plot(self, ax, radius=0.5, color='green', show_label=True):
        # Get angle in radians
        angle_rad = self.measure()
        
        # Calculate vectors from vertex to points
        v1 = (self.point1.x - self.vertex.x, self.point1.y - self.vertex.y)
        v2 = (self.point2.x - self.vertex.x, self.point2.y - self.vertex.y)
        
        # Normalize vectors
        def normalize(v):
            mag = math.sqrt(v[0]**2 + v[1]**2)
            return (v[0]/mag, v[1]/mag)
        
        v1_norm = normalize(v1)
        v2_norm = normalize(v2)
        
        # Determine the angle direction (clockwise or counterclockwise)
        cross_product = v1_norm[0] * v2_norm[1] - v1_norm[1] * v2_norm[0]
        
        # Calculate the starting angle
        start_angle = math.atan2(v1[1], v1[0])
        
        # Determine the end angle based on the cross product
        if cross_product < 0:  # clockwise
            end_angle = start_angle - angle_rad
        else:  # counterclockwise
            end_angle = start_angle + angle_rad
        
        # Convert to degrees for matplotlib
        start_angle_deg = math.degrees(start_angle)
        end_angle_deg = math.degrees(end_angle)
        
        # Create the angle arc
        arc = plt.matplotlib.patches.Arc((self.vertex.x, self.vertex.y),
                                       2*radius, 2*radius,
                                       theta1=min(start_angle_deg, end_angle_deg),
                                       theta2=max(start_angle_deg, end_angle_deg),
                                       color=color)
        ax.add_patch(arc)
        
        # Add label
        if self.label and show_label:
            # Calculate the midpoint angle
            mid_angle = (start_angle + end_angle) / 2
            label_x = self.vertex.x + 1.2 * radius * math.cos(mid_angle)
            label_y = self.vertex.y + 1.2 * radius * math.sin(mid_angle)
            
            ax.text(label_x, label_y, f"{self.label}: {self.measure_degrees():.1f}°", 
                    fontsize=9, ha='center', va='center',
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="gray", alpha=0.7))


class Circle:
    """Definition 15: A circle is a plane figure contained by one line such that..."""
    def __init__(self, center, radius, label=None):
        self.center = center
        self.radius = radius
        self.label = label
    
    def contains_point(self, point, epsilon=1e-9):
        distance = self.center.distance_to(point)
        return abs(distance - self.radius) < epsilon
    
    def intersection_with_line(self, line):
        if not isinstance(line, StraightLine):
            line = StraightLine(line.point1, line.point2)
        
        # Calculate distance from center to line
        distance = abs(line.a * self.center.x + line.b * self.center.y + line.c) / math.sqrt(line.a**2 + line.b**2)
        
        # No intersection if distance > radius
        if distance > self.radius:
            return []
        
        # Tangent case
        if abs(distance - self.radius) < 1e-9:
            # Find tangent point
            factor = -line.c - line.a * self.center.x - line.b * self.center.y
            norm = line.a**2 + line.b**2
            x = self.center.x + line.a * factor / norm
            y = self.center.y + line.b * factor / norm
            return [Point(x, y)]
        
        # Two intersection points
        # First find the closest point on the line to the center
        factor = -line.c - line.a * self.center.x - line.b * self.center.y
        norm = line.a**2 + line.b**2
        x0 = self.center.x + line.a * factor / norm
        y0 = self.center.y + line.b * factor / norm
        closest_point = Point(x0, y0)
        
        # Find the distance along the line to the intersection
        along_line = math.sqrt(self.radius**2 - distance**2)
        
        # Calculate unit vector along the line
        dx = line.point2.x - line.point1.x
        dy = line.point2.y - line.point1.y
        line_length = math.sqrt(dx**2 + dy**2)
        ux = dx / line_length
        uy = dy / line_length
        
        # Calculate the two intersection points
        point1 = Point(x0 + along_line * ux, y0 + along_line * uy)
        point2 = Point(x0 - along_line * ux, y0 - along_line * uy)
        
        return [point1, point2]
    
    def __str__(self):
        if self.label:
            return f"Circle {self.label} with center {self.center} and radius {self.radius}"
        return f"Circle with center {self.center} and radius {self.radius}"
    
    def plot(self, ax, color='red', fill=False, alpha=0.3, linewidth=1.5, show_label=True):
        circle = MplCircle((self.center.x, self.center.y), self.radius,
                         fill=fill, alpha=alpha, edgecolor=color, facecolor=color, linewidth=linewidth)
        ax.add_patch(circle)
        
        if self.label and show_label:
            ax.text(self.center.x, self.center.y + self.radius + 0.2, 
                    self.label, fontsize=10, ha='center',
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.7))


class Triangle:
    """A triangle is a figure contained by three straight lines."""
    def __init__(self, point1, point2, point3, label=None):
        self.point1 = point1
        self.point2 = point2
        self.point3 = point3
        self.label = label
        
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
    
    def plot(self, ax, color='blue', fill=True, alpha=0.2, linewidth=1.5, show_label=True):
        # Plot vertices
        self.point1.plot(ax)
        self.point2.plot(ax)
        self.point3.plot(ax)
        
        # Plot sides
        self.side1.plot(ax, linewidth=linewidth)
        self.side2.plot(ax, linewidth=linewidth)
        self.side3.plot(ax, linewidth=linewidth)
        
        # Fill the triangle
        if fill:
            polygon = Polygon([(self.point1.x, self.point1.y), 
                             (self.point2.x, self.point2.y), 
                             (self.point3.x, self.point3.y)], 
                            closed=True, fill=True, color=color, alpha=alpha)
            ax.add_patch(polygon)
        
        # Plot label
        if self.label and show_label:
            # Calculate centroid
            centroid_x = (self.point1.x + self.point2.x + self.point3.x) / 3
            centroid_y = (self.point1.y + self.point2.y + self.point3.y) / 3
            
            ax.text(centroid_x, centroid_y, self.label, fontsize=10, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.7))
        
        # Plot angles
        self.angle1.plot(ax, radius=min(0.3, self.side2.length()/3, self.side3.length()/3))
        self.angle2.plot(ax, radius=min(0.3, self.side1.length()/3, self.side3.length()/3))
        self.angle3.plot(ax, radius=min(0.3, self.side1.length()/3, self.side2.length()/3))


class Square:
    """Definition 22: Of quadrilateral figures, a square is that which is both equilateral and right-angled."""
    def __init__(self, point1, point2, label=None):
        self.point1 = point1
        self.point2 = point2
        self.label = label
        
        # Calculate the side length
        dx = point2.x - point1.x
        dy = point2.y - point1.y
        self.side_length = math.sqrt(dx**2 + dy**2)
        
        # Calculate unit vector perpendicular to the first side
        ux = -dy / self.side_length
        uy = dx / self.side_length
        
        # Calculate the other corners
        self.point3 = Point(point2.x + ux * self.side_length, point2.y + uy * self.side_length)
        self.point4 = Point(point1.x + ux * self.side_length, point1.y + uy * self.side_length)
        
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
    
    def plot(self, ax, color='purple', fill=True, alpha=0.2, linewidth=1.5, show_label=True):
        # Plot vertices
        self.point1.plot(ax)
        self.point2.plot(ax)
        self.point3.plot(ax)
        self.point4.plot(ax)
        
        # Plot sides
        self.side1.plot(ax, linewidth=linewidth)
        self.side2.plot(ax, linewidth=linewidth)
        self.side3.plot(ax, linewidth=linewidth)
        self.side4.plot(ax, linewidth=linewidth)
        
        # Fill the square
        if fill:
            polygon = Polygon([(self.point1.x, self.point1.y), 
                             (self.point2.x, self.point2.y), 
                             (self.point3.x, self.point3.y),
                             (self.point4.x, self.point4.y)], 
                            closed=True, fill=True, color=color, alpha=alpha)
            ax.add_patch(polygon)
        
        # Plot label
        if self.label and show_label:
            # Calculate centroid
            centroid_x = (self.point1.x + self.point2.x + self.point3.x + self.point4.x) / 4
            centroid_y = (self.point1.y + self.point2.y + self.point3.y + self.point4.y) / 4
            
            ax.text(centroid_x, centroid_y, self.label, fontsize=10, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.7))


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
        
        new_point = Point(point.x + dx, point.y + dy)
        return StraightLine(point, new_point)
    
    @staticmethod
    def bisect_angle(angle):
        """Proposition 9: To bisect a given rectilineal angle."""
        # Construct equal distance points on the two rays of the angle
        distance = 2  # arbitrary distance
        
        # Calculate unit vectors for both rays
        ray1_length = math.sqrt((angle.point1.x - angle.vertex.x)**2 + (angle.point1.y - angle.vertex.y)**2)
        ray2_length = math.sqrt((angle.point2.x - angle.vertex.x)**2 + (angle.point2.y - angle.vertex.y)**2)
        
        ray1_unit_x = (angle.point1.x - angle.vertex.x) / ray1_length
        ray1_unit_y = (angle.point1.y - angle.vertex.y) / ray1_length
        
        ray2_unit_x = (angle.point2.x - angle.vertex.x) / ray2_length
        ray2_unit_y = (angle.point2.y - angle.vertex.y) / ray2_length
        
        # Points at equal distances along the rays
        point_on_ray1 = Point(angle.vertex.x + ray1_unit_x * distance, 
                             angle.vertex.y + ray1_unit_y * distance)
        
        point_on_ray2 = Point(angle.vertex.x + ray2_unit_x * distance, 
                             angle.vertex.y + ray2_unit_y * distance)
        
        # Draw circles centered at these points with the same radius
        radius = distance * 0.8  # Arbitrary but smaller than distance
        circle1 = Circle(point_on_ray1, radius)
        circle2 = Circle(point_on_ray2, radius)
        
        # Find the intersection of the two circles
        # This is an approximation since we don't have a direct circle-circle intersection method
        # We'll create a line between the circle centers and find the point that's equidistant
        center_line = Line(point_on_ray1, point_on_ray2)
        center_line_length = center_line.length()
        
        # The point between the centers that forms the angle bisector
        midpoint_x = (point_on_ray1.x + point_on_ray2.x) / 2
        midpoint_y = (point_on_ray1.y + point_on_ray2.y) / 2
        
        # Calculate the perpendicular direction to get the intersection point inside the angle
        perp_x = -(point_on_ray2.y - point_on_ray1.y) / center_line_length
        perp_y = (point_on_ray2.x - point_on_ray1.x) / center_line_length
        
        # Calculate the distance from midpoint to intersection
        height = math.sqrt(radius**2 - (center_line_length/2)**2)
        
        # The intersection point (we choose the one inside the angle)
        # We need to determine which direction is "inside" the angle
        # by checking the cross product with the angle's rays
        cross_product = (ray1_unit_x * ray2_unit_y - ray1_unit_y * ray2_unit_x)
        
        if cross_product > 0:
            intersection = Point(midpoint_x + perp_x * height, midpoint_y + perp_y * height)
        else:
            intersection = Point(midpoint_x - perp_x * height, midpoint_y - perp_y * height)
        
        # The angle bisector is the line from the vertex through this intersection
        return Line(angle.vertex, intersection)
    
    @staticmethod
    def construct_equilateral_triangle(point1, point2):
        """Proposition 1: On a given finite straight line to construct an equilateral triangle."""
        side_length = point1.distance_to(point2)
        
        # Draw circles centered at the endpoints with radius equal to the side length
        circle1 = Circle(point1, side_length)
        circle2 = Circle(point2, side_length)
        
        # The circles intersect at two points - we'll pick the one with positive y
        # (assuming original points are on the x-axis for simplicity)
        # In a general case, we'd need to determine which intersection is on the
        # desired side of the line
        
        # Calculate the midpoint of the line
        midpoint_x = (point1.x + point2.x) / 2
        midpoint_y = (point1.y + point2.y) / 2
        
        # Calculate the perpendicular direction
        dx = point2.x - point1.x
        dy = point2.y - point1.y
        line_length = math.sqrt(dx**2 + dy**2)
        
        # Unit perpendicular vector
        perp_x = -dy / line_length
        perp_y = dx / line_length
        
        # Distance from midpoint to intersection
        height = math.sqrt(side_length**2 - (side_length/2)**2)
        
        # The third point of the equilateral triangle
        third_point = Point(midpoint_x + perp_x * height, midpoint_y + perp_y * height)
        
        return Triangle(point1, point2, third_point)


def demonstrate_euclidean_geometry():
    """Demonstrate Euclid's Elements with visualizations"""
    
    # Create a figure with subplots for different demonstrations
    fig = plt.figure(figsize=(15, 12))
    fig.suptitle("Euclid's Elements - Visualization", fontsize=16)
    
    # Define a helper function to setup the axes
    def setup_axes(ax, title, xlim=(-2, 8), ylim=(-2, 8)):
        ax.set_title(title)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect('equal')
        ax.grid(True, linestyle='--', alpha=0.7)
        return ax
    
    # 1. Triangle and its properties
    ax1 = fig.add_subplot(2, 2, 1)
    setup_axes(ax1, "Triangle with Angles and Measurements")
    
    # Create labeled points for triangle
    pointA = Point(1, 1, "A")
    pointB = Point(5, 1, "B")
    pointC = Point(3, 4, "C")
    
    # Create and plot triangle
    triangle = Triangle(pointA, pointB, pointC, "ABC")
    triangle.plot(ax1)
    
    # Add information text
    angle_sum = triangle.angle1.measure_degrees() + triangle.angle2.measure_degrees() + triangle.angle3.measure_degrees()
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    info_text = (f"Area: {triangle.area():.2f}\n"
                f"Perimeter: {triangle.perimeter():.2f}\n"
                f"Angle sum: {angle_sum:.2f}° (≈