import pygame
import math

# Initialize pygame
pygame.init()

# Set up the display
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Euclid's Geometry Simulator")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# Define a Point Class
class Point:
    """
    Definition 1: A point is that which has no part.
    It has position
    """
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

# Define a Line Class
class Line:
    def __init__(self, point1, point2):
        self.point1 = point1
        self.point2 = point2
        self.color = BLACK
        self.width = 2
    
    def draw(self, screen):
        pygame.draw.line(screen, self.color, (self.point1.x, self.point1.y), 
                         (self.point2.x, self.point2.y), self.width)
    
    def involves_point(self, point):
        return self.point1 == point or self.point2 == point

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
                                # Create new line
                                new_line = Line(line_start_point, point)
                                lines.append(new_line)
                            
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
    
    # Update selected point position if dragging
    if dragging and selected_point:
        selected_point.update_position(mouse_x, mouse_y)
    
    # Draw all lines
    for line in lines:
        line.draw(screen)
    
    # Draw all points
    for point in points:
        point.draw(screen)
    
    # Draw temporary line when in drawing mode
    if drawing_line and line_start_point:
        pygame.draw.line(screen, GREEN, (line_start_point.x, line_start_point.y), 
                         (mouse_x, mouse_y), 1)
    
    # Display instructions
    instructions = [
        "Left-click: Create new point or drag existing point",
        "Right-click on point: Start/finish drawing a line",
        "Right-click same points: Toggle line existence"
    ]
    
    y_offset = 10
    for instruction in instructions:
        text_surface = font.render(instruction, True, BLACK)
        screen.blit(text_surface, (10, y_offset))
        y_offset += 25
    
    pygame.display.flip()

pygame.quit()