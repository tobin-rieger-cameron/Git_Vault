from vpython import sphere, vector, color, scene

class Point:
    """
    Definition 1: A point is that which has no part.
    
    It has Position (x, y, z) in 3D space.
    """
    def __init__(self, x, y, z=0, label=None, radius=0.1, point_color=color.blue):
        self.x = x
        self.y = y
        self.z = z
        self.label = label
        self.radius = radius  # Size of the point
        self.color = point_color  # VPython color
        
        # Create a visual representation in VPython
        self.visual = sphere(pos=vector(self.x, self.y, self.z), 
                             radius=self.radius, 
                             color=self.color)

    def distance_to(self, other_point):
        # d = sqrt((x2 - x1)^2 + (y2 - y1)^2 + (z2 - z1)^2)
        return ((self.x - other_point.x) ** 2 + 
                (self.y - other_point.y) ** 2 + 
                (self.z - other_point.z) ** 2) ** 0.5

    def equals(self, other_point, epsilon=1e-9):
        """Check if two points are approximately equal (floating-point precision)."""
        return (abs(self.x - other_point.x) < epsilon and 
                abs(self.y - other_point.y) < epsilon and 
                abs(self.z - other_point.z) < epsilon)

    def __str__(self):
        """String representation for easy debugging."""
        if self.label:
            return f"Point {self.label}({self.x}, {self.y}, {self.z})"
        return f"Point({self.x}, {self.y}, {self.z})"



    
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






















# Set up VPython scene
scene.title = "VPython Point Example"

# Create two points
A = Point(1, 2, 3, "A", point_color=color.red)
B = Point(4, 5, 6, "B", point_color=color.green)

# Print details
print(A)  # Output: Point A(1, 2, 3)
print(B)  # Output: Point B(4, 5, 6)
print(A.distance_to(B))  # Output: ~5.196 (3D distance)

# Keep the window open
while True:
    pass