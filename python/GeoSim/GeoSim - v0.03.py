import pygame
import math

# Initialize pygame
pygame.init()

# Set up the display
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Euclid's Geometry Simulator v0.03")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
PURPLE = (128, 0, 128)

# Define a Point Class
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 8
        self.color = RED
        self.selected = False
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)
    
    def is_clicked(self, mouse_x, mouse_y):
        # Check if mouse position is within the point
        distance = math.sqrt((mouse_x - self.x)**2 + (mouse_y - self.y)**2)
        return distance <= self.radius
    
    def update_position(self, x, y):
        self.x = x
        self.y = y

# Define a StraightLine Class following Euclid's Definition 4
class StraightLine:
    def __init__(self, point1, point2):
        # Two points define a straight line
        self.point1 = point1
        self.point2 = point2
        # Store the line in slope-intercept form (y = mx + b) when possible
        self.calculate_equation()
        self.color = BLACK
        self.width = 2
    
    def calculate_equation(self):
        """Calculate the equation of the line in the form y = mx + b, or x = c"""
        # Handle vertical lines as a special case
        if self.point1.x == self.point2.x:
            self.vertical = True
            self.constant = self.point1.x  # x = constant
            self.slope = None
            self.y_intercept = None
        else:
            self.vertical = False
            # Calculate slope (m)
            self.slope = (self.point2.y - self.point1.y) / (self.point2.x - self.point1.x)
            # Calculate y-intercept (b) using point-slope form: y - y1 = m(x - x1)
            self.y_intercept = self.point1.y - self.slope * self.point1.x
    
    def get_y(self, x):
        """Get the y-coordinate for a given x-coordinate on the line"""
        if self.vertical:
            return None  # Undefined for vertical lines
        return self.slope * x + self.y_intercept
    
    def get_x(self, y):
        """Get the x-coordinate for a given y-coordinate on the line"""
        if self.vertical:
            return self.constant
        if self.slope == 0:
            return None  # Undefined for horizontal lines (y = constant)
        return (y - self.y_intercept) / self.slope
    
    def contains_point(self, point, tolerance=2):
        """Check if a point lies on the line within a small tolerance"""
        if self.vertical:
            return abs(point.x - self.constant) <= tolerance
        
        # Calculate expected y for the given x
        expected_y = self.get_y(point.x)
        # Compare with actual y
        return abs(point.y - expected_y) <= tolerance
    
    def distance_to_point(self, point):
        """Calculate the perpendicular distance from a point to the line"""
        if self.vertical:
            return abs(point.x - self.constant)
        
        # For non-vertical lines, use the formula d = |ax + by + c|/√(a² + b²)
        # Where ax + by + c = 0 is the general form of the line
        a = self.slope
        b = -1
        c = self.y_intercept
        
        return abs(a * point.x + b * point.y + c) / math.sqrt(a**2 + b**2)
    
    def intersection_with(self, other_line):
        """Find the intersection point with another line"""
        # If both lines are vertical, they are either the same line or parallel
        if self.vertical and other_line.vertical:
            if self.constant == other_line.constant:
                return "Coincident lines"  # Same line
            return None  # Parallel lines
        
        # If one line is vertical
        if self.vertical:
            x = self.constant
            y = other_line.get_y(x)
            return Point(x, y)
        
        if other_line.vertical:
            x = other_line.constant
            y = self.get_y(x)
            return Point(x, y)
        
        # If lines have the same slope, they are either the same line or parallel
        if self.slope == other_line.slope:
            if self.y_intercept == other_line.y_intercept:
                return "Coincident lines"  # Same line
            return None  # Parallel lines
        
        # Find intersection of two non-vertical, non-parallel lines
        # Solve: m1x + b1 = m2x + b2
        # x = (b2 - b1) / (m1 - m2)
        x = (other_line.y_intercept - self.y_intercept) / (self.slope - other_line.slope)
        y = self.get_y(x)
        
        return Point(x, y)
    
    def draw(self, screen):
        """Draw the line on the screen, extending to the edges of the screen"""
        # Calculate endpoints at the screen boundaries
        start_point = None
        end_point = None
        
        if self.vertical:
            # Line is vertical (x = constant)
            start_point = (self.constant, 0)
            end_point = (self.constant, HEIGHT)
        elif self.slope == 0:
            # Line is horizontal (y = constant)
            start_point = (0, self.y_intercept)
            end_point = (WIDTH, self.y_intercept)
        else:
            # Calculate intersections with screen edges
            # Left edge (x = 0)
            left_y = self.get_y(0)
            # Right edge (x = WIDTH)
            right_y = self.get_y(WIDTH)
            # Top edge (y = 0)
            top_x = self.get_x(0)
            # Bottom edge (y = HEIGHT)
            bottom_x = self.get_x(HEIGHT)
            
            # Find which edges the line intersects
            points = []
            
            if 0 <= left_y <= HEIGHT:
                points.append((0, left_y))
            
            if 0 <= right_y <= HEIGHT:
                points.append((WIDTH, right_y))
            
            if 0 <= top_x <= WIDTH:
                points.append((top_x, 0))
            
            if 0 <= bottom_x <= WIDTH:
                points.append((bottom_x, HEIGHT))
            
            # We need exactly two intersection points
            if len(points) >= 2:
                start_point, end_point = points[0], points[1]
        
        # Draw the line if both endpoints are defined
        if start_point and end_point:
            pygame.draw.line(screen, self.color, start_point, end_point, self.width)
    
    def involves_point(self, point):
        """Check if the line is defined using the given point"""
        return self.point1 == point or self.point2 == point
    
    def is_parallel_to(self, other_line):
        """Check if this line is parallel to another line"""
        if self.vertical and other_line.vertical:
            return True
        if self.vertical or other_line.vertical:
            return False
        return self.slope == other_line.slope
    
    def is_perpendicular_to(self, other_line):
        """Check if this line is perpendicular to another line"""
        if self.vertical and other_line.slope == 0:
            return True
        if other_line.vertical and self.slope == 0:
            return True
        if self.vertical or other_line.vertical:
            return False
        # Perpendicular lines have slopes that are negative reciprocals of each other
        return abs(self.slope * other_line.slope + 1) < 0.0001  # Account for floating point errors

# Create some initial points
points = [
    Point(100, 100),
    Point(400, 300),
    Point(200, 450),
    Point(600, 200)
]

# Start with no lines
lines = []

# Variables for handling interaction
selected_point = None
line_start_point = None
dragging = False
drawing_line = False
font = pygame.font.SysFont('Arial', 18)

# For detecting line intersections
intersection_points = []

# Main loop
running = True
while running:
    screen.fill(WHITE)
    
    # Get mouse position
    mouse_x, mouse_y = pygame.mouse.get_pos()
    
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                for point in points:
                    if point.is_clicked(mouse_x, mouse_y):
                        selected_point = point
                        point.selected = True
                        point.color = BLUE
                        dragging = True
                        break
                        
                if not dragging:  # If not dragging an existing point, create a new one
                    new_point = Point(mouse_x, mouse_y)
                    points.append(new_point)
                    
            elif event.button == 3:  # Right mouse button
                # First, check if we clicked on a point
                clicked_on_point = False
                for point in points:
                    if point.is_clicked(mouse_x, mouse_y):
                        clicked_on_point = True
                        # If we haven't selected a start point for a line
                        if line_start_point is None:
                            line_start_point = point
                            point.color = GREEN
                            drawing_line = True
                        # If we have a start point and clicked a different point
                        elif line_start_point != point:
                            # Check if line already exists
                            line_exists = False
                            line_to_remove = None
                            for line in lines:
                                if ((line.point1 == line_start_point and line.point2 == point) or
                                    (line.point2 == line_start_point and line.point1 == point)):
                                    line_exists = True
                                    line_to_remove = line
                                    break
                            
                            if line_exists:
                                # Remove existing line
                                lines.remove(line_to_remove)
                            else:
                                # Create new line using Euclid's definition
                                new_line = StraightLine(line_start_point, point)
                                lines.append(new_line)
                            
                            # Recalculate all intersections
                            intersection_points = []
                            # Check for intersections between all lines
                            for i, line1 in enumerate(lines):
                                for j, line2 in enumerate(lines):
                                    if i < j:  # Avoid checking the same pair twice
                                        intersection = line1.intersection_with(line2)
                                        if intersection and intersection != "Coincident lines":
                                            # Add intersection point if it's within the screen
                                            if 0 <= intersection.x <= WIDTH and 0 <= intersection.y <= HEIGHT:
                                                intersection_points.append(intersection)
                            
                            # Reset line drawing state
                            line_start_point.color = RED
                            line_start_point = None
                            drawing_line = False
                        # If we clicked the same point twice, cancel line drawing
                        else:
                            line_start_point.color = RED
                            line_start_point = None
                            drawing_line = False
                
                # If clicking in empty space and in drawing mode, cancel line drawing
                if not clicked_on_point and drawing_line:
                    line_start_point.color = RED
                    line_start_point = None
                    drawing_line = False
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and selected_point:  # Left mouse button release
                selected_point.color = RED
                selected_point.selected = False
                selected_point = None
                dragging = False
                
                # Recalculate all intersections after moving a point
                intersection_points = []
                # Update equations for all lines involving this point
                for line in lines:
                    if line.involves_point(selected_point):
                        line.calculate_equation()
                
                # Check for intersections between all lines
                for i, line1 in enumerate(lines):
                    for j, line2 in enumerate(lines):
                        if i < j:  # Avoid checking the same pair twice
                            intersection = line1.intersection_with(line2)
                            if intersection and intersection != "Coincident lines":
                                # Add intersection point if it's within the screen
                                if 0 <= intersection.x <= WIDTH and 0 <= intersection.y <= HEIGHT:
                                    intersection_points.append(intersection)
    
    # Update selected point position if dragging
    if dragging and selected_point:
        selected_point.update_position(mouse_x, mouse_y)
        
        # Update equations for all lines involving the selected point in real-time
        for line in lines:
            if line.involves_point(selected_point):
                line.calculate_equation()
        
        # Calculate intersection points in real-time while dragging
        intersection_points = []
        for i, line1 in enumerate(lines):
            for j, line2 in enumerate(lines):
                if i < j:  # Avoid checking the same pair twice
                    intersection = line1.intersection_with(line2)
                    if intersection and intersection != "Coincident lines":
                        # Add intersection point if it's within the screen
                        if 0 <= intersection.x <= WIDTH and 0 <= intersection.y <= HEIGHT:
                            intersection_points.append(intersection)
    
    # Draw all lines (extending to screen edges as per Euclid's definition)
    for line in lines:
        line.draw(screen)
    
    # Draw all points
    for point in points:
        point.draw(screen)
    
    # Draw intersection points
    for point in intersection_points:
        pygame.draw.circle(screen, PURPLE, (point.x, point.y), 5)
    
    # Draw temporary line when in drawing mode
    if drawing_line and line_start_point:
        pygame.draw.line(screen, GREEN, (line_start_point.x, line_start_point.y), 
                         (mouse_x, mouse_y), 1)
    
    # Display instructions
    instructions = [
        "Left-click: Create new point or drag existing point",
        "Right-click on point: Start/finish drawing a line",
        "Right-click same points: Toggle line existence",
        "Purple dots: Intersection points of lines"
    ]
    
    y_offset = 10
    for instruction in instructions:
        text_surface = font.render(instruction, True, BLACK)
        screen.blit(text_surface, (10, y_offset))
        y_offset += 25
    
    pygame.display.flip()

pygame.quit()