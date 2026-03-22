
import pygame
import math

# Initialize pygame
pygame.init()

# Set up the display
WIDTH = 800
HEIGHT = 600
screen = pygame.display.set_mode(WIDTH, HEIGHT)
pygame.display.set_caption("Geometry")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
LIGHT_BLUE = (173, 216, 230)
DARK_GRAY = (100, 100, 100)


ORIGIN = (WIDTH // 2, HEIGHT // 2)

# Define a Point Class
class Point:
    # a point has position, it has no dimention
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def draw(self, screen):
        pygame.draw.circle(screen, RED, (self.x, self.y), 10)

# Define a Line Class
class Line:
    def __init__(self, point1, point2):
        self.point1 = point1
        self.point2 = point2

        self.slope = slope
        self.y_intercept = y_intercept




    def draw(self, screen):
        pygame.draw.line(screen, BLACK, (self.point1.x, self.point1.y), (self.point2.x, self.point2.y), 2)

# Create some points and lines
p1 = Point(100, 100)
p2 = Point(400, 300)
line = Line(p1, p2)

# Main loop
running = True
while running:
    screen.fill(WHITE)

    # Event handling
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYUP:



    # Draw objects
    p1.draw(screen)
    p2.draw(screen)
    line.draw(screen)

    pygame.display.flip()

pygame.quit()
