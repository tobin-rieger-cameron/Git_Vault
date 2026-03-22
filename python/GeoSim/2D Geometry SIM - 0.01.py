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

# Define a Point Class
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def draw(self, screen):
        pygame.draw.circle(screen, RED, (self.x, self.y), 5)

# Define a Line Class
class Line:
    def __init__(self, point1, point2):
        self.point1 = point1
        self.point2 = point2

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

    # Draw objects
    p1.draw(screen)
    p2.draw(screen)
    line.draw(screen)

    pygame.display.flip()

pygame.quit()
