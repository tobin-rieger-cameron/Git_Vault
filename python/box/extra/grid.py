import pygame
import sys

# Initialize pygame
pygame.init()

# Screen settings
WIDTH = 800
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mathematical Grid")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Grid configuration
GRID_SIZE = 40  # Pixels between grid lines
ORIGIN = (WIDTH // 2, HEIGHT // 2)  # Center of screen
AXIS_WIDTH = 2  # Width of x and y axes
GRID_WIDTH = 1  # Width of regular grid lines



# Define a Point Class
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    #def is_hovered(self, mouse_x, mouse_y):
        # Check if mouse position is within the point

    def update_position(self, x, y):
        self.x = x
        self.y = y

class Line:
    def __init__(self, slope=1, y_intercept=0):
        """
        Initialize a line with the equation y = mx + b.
        """
        self.slope = slope
        self.y_intercept = y_intercept
    
    def __str__(self):
        if self.y_intercept == 0:
            return f"y = {self.slope}x"

        elif self.y_intercept < 0:
            return f"y = {self.slope}x - {abs(self.y_intercept)}"

        else:
            return f"y = {self.slope}x + {self.y_intercept}"
    
    def evaluate(self, x):
        """
        Compute y for a given x value.
        """
        return self.slope * x + self.y_intercept
    
    def screen_coordinates(self, x_range, origin):
        """
        Args:
            x_range (tuple): (min_x, max_x) range to calculate points for
            origin (tuple): (x, y) screen coordinates of the mathematical origin
            
        Returns:
            list: List of (x, y) screen coordinate tuples representing the line
        """
        points = []
        
        # Handle special case of vertical line (infinite slope)
        if self.slope == float('inf'):
            # For a vertical line at x = c, we return a vertical segment
            x_screen = origin[0] + self.y_intercept  # In this case, y_intercept is actually x_intercept
            return [(x_screen, 0), (x_screen, HEIGHT)]
        
        # Generate points for the line across the x_range
        for x_screen in range(x_range[0], x_range[1]):
            # Convert from screen x to mathematical x
            x_math = (x_screen - origin[0]) / GRID_SIZE
            
            # Calculate mathematical y using the line equation
            y_math = self.evaluate(x_math)
            
            # Convert from mathematical y to screen y (inverted)
            y_screen = origin[1] - (y_math * GRID_SIZE)
            
            # Add point if it's within the screen bounds
            if 0 <= y_screen <= HEIGHT:
                points.append((x_screen, int(y_screen)))
        
        return points
    
    def draw(self, surface, color, width, origin, x_range=(0, WIDTH)):
        """
            surface: Pygame surface to draw on
            color: RGB tuple for line color
            width: Line width in pixels
            origin: (x, y) screen coordinates of the mathematical origin
            x_range: (min_x, max_x) range of screen x-coordinates to draw
        """
        points = self.screen_coordinates(x_range, origin)
        
        # Need at least 2 points to draw a line
        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, points, width)
        

def draw_grid():
    """Draw the mathematical grid with highlighted axes."""
    # Fill background
    screen.fill(WHITE)
    
    # Calculate starting positions for grid lines
    x_start = ORIGIN[0] % GRID_SIZE
    y_start = ORIGIN[1] % GRID_SIZE
    
    # Draw vertical grid lines
    for x in range(x_start, WIDTH, GRID_SIZE):
        # Use red for x-axis, gray for other grid lines
        color = RED if x == ORIGIN[0] else GRAY
        thickness = AXIS_WIDTH if x == ORIGIN[0] else GRID_WIDTH
        pygame.draw.line(screen, color, (x, 0), (x, HEIGHT), thickness)
    
    # Draw horizontal grid lines
    for y in range(y_start, HEIGHT, GRID_SIZE):
        # Use blue for y-axis, gray for other grid lines
        color = BLUE if y == ORIGIN[1] else GRAY
        thickness = AXIS_WIDTH if y == ORIGIN[1] else GRID_WIDTH
        pygame.draw.line(screen, color, (0, y), (WIDTH, y), thickness)
    
    # Mark the origin point
    pygame.draw.circle(screen, BLACK, ORIGIN, 5)


def main():
    """Main program loop."""
    clock = pygame.time.Clock()
    
    # Create some example lines to draw
    lines = [
        # y = x (identity line)
        (Line(1, 0), (255, 0, 255), 2),  # Purple
        
        # y = -0.5x + 2
        (Line(-0.5, 2), (0, 128, 0), 2),  # Green
        
        # y = 0.5x - 1
        (Line(0.5, -1), (255, 165, 0), 2),  # Orange
    ]
    
    # Game loop
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Draw the grid
        draw_grid()
        
        # Draw the example lines
        for line, color, width in lines:
            line.draw(screen, color, width, ORIGIN)
        
        # Update the display
        pygame.display.flip()
        clock.tick(60)  # Limit to 60 frames per second

    # Clean up
    pygame.quit()
    sys.exit()


# Run the program
if __name__ == "__main__":
    main()
