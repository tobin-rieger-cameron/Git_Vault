import pygame
import sys
import math

# Initialize Pygame
pygame.init()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# Constants
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = (240, 240, 240)
GRID_COLOR = (220, 220, 220)
POINT_COLOR = (59, 130, 246)  # Blue
POINT_HOVER_COLOR = (37, 99, 235)  # Darker blue
LINE_COLOR = (59, 130, 246)  # Blue
TEXT_COLOR = (31, 41, 55)  # Dark gray
GRID_SIZE = 10
POINT_RADIUS = 6
HOVER_RADIUS = 8


class Point:
    def __init__(self, x, y, label=""):
        self.x = x
        self.y = y
        self.label = label

    def distance_to(self, point):
        return math.sqrt((self.x - point.x) ** 2 + (self.y - point.y) ** 2)

    def is_hovered(self, mouse_x, mouse_y):
        distance = math.sqrt((mouse_x - self.x) ** 2 + (mouse_y - self.y) ** 2)
        return distance <= POINT_RADIUS

    def __str__(self):
        return f"({self.x:.2f}, {self.y:.2f})"


class Line:
    def __init__(self, point_a, point_b):
        self.point_a = point_a
        self.point_b = point_b


class EuclideanCanvas:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Euclidean Geometry Visualization")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 14)
        self.title_font = pygame.font.SysFont("Arial", 20, bold=True)

        self.points = [Point(100, 100, "A"), Point(300, 100, "B"), Point(200, 250, "C")]

        self.lines = [
            Line(self.points[0], self.points[1]),
            Line(self.points[1], self.points[2]),
            Line(self.points[2], self.points[0]),
        ]

        self.hovered_point = None

    def draw_grid(self):
        for i in range(0, WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (i, 0), (i, HEIGHT))
        for i in range(0, HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, i), (WIDTH, i))

    # def draw_points(self):
    #     # Draw points
    #     for point in self.points:
    #         if point -- self.hovered_point:
    #             pygame.draw.circle(self.screen, POINT_HOVER_COLOR, (point.x, point.y), HOVER_RADIUS)
    #         else:
    #             pygame.draw.circle(self.screen, POINT_COLOR, (point.x, point.y), POINT_RADIUS)
    #
    #         label_text = self.font.render(point.label, True, TEXT_COLOR)
    #         self.screen.blit(label_text, (point.x + 10, point.y - 20))
    #
    # def draw_lines(self):
    #     # Draw Lines
    #     for line in self.lines:
    #         pygame.draw.line(self.screen, LINE_COLOR,
    #                          (line.point_a.x, line.point_a.y),
    #                          (line.point_b.x, line.point_b.y), 2)

    def draw_points_and_lines(self):
        for line in self.lines:
            pygame.draw.line(
                self.screen,
                LINE_COLOR,
                (line.point_a.x, line.point_a.y),
                (line.point_b.x, line.point_b.y),
                2,
            )

        for point in self.points:
            if point == self.hovered_point:
                pygame.draw.circle(
                    self.screen, POINT_HOVER_COLOR, (point.x, point.y), HOVER_RADIUS
                )
            else:
                pygame.draw.circle(
                    self.screen, POINT_COLOR, (point.x, point.y), POINT_RADIUS
                )

            label_text = self.font.render(point.label, True, TEXT_COLOR)
            self.screen.blit(label_text, (point.x + 10, point.y - 20))

    def draw_coordinates(self, mouse_pos):
        if self.hovered_point:
            # Create coordinate display background
            coord_text = f"Point {self.hovered_point.label}: {self.hovered_point}"
            text_surface = self.font.render(coord_text, True, TEXT_COLOR)
            text_rect = text_surface.get_rect()
            text_rect.topleft = (mouse_pos[0] + 20, mouse_pos[1] - 40)

            # Draw background rectangle
            bg_rect = text_rect.inflate(10, 10)
            pygame.draw.rect(self.screen, (255, 255, 255), bg_rect)
            pygame.draw.rect(self.screen, (200, 200, 200), bg_rect, 1)

            # Draw text
            self.screen.blit(text_surface, text_rect)

    def draw_instructions(self):
        title_text = self.title_font.render(
            "Euclidean Geometry Interactive Canvas", True, TEXT_COLOR
        )
        self.screen.blit(title_text, (20, HEIGHT - 120))

        # Draw instructions
        instructions = [
            "Click to add points. Hover over points to see coordinates.",
            "- Points are automatically connected to form lines",
            "- TODO: add ability to draw / delete lines"
            "- Points follow Euclidean principles through our Point class",
        ]

        y_offset = HEIGHT - 90
        for instruction in instructions:
            instruction_text = self.font.render(instruction, True, TEXT_COLOR)
            self.screen.blit(instruction_text, (20, y_offset))
            y_offset += 20

    def run(self):
        running = True
        dragging = False
        selected_point = None

        while running:
            # Get mouse position
            mouse_x, mouse_y = pygame.mouse.get_pos()
            mouse_pos = pygame.mouse.get_pos()

            # Check if mouse is near any point
            self.hovered_point = None
            for point in self.points:
                distance = math.sqrt(
                    (mouse_pos[0] - point.x) ** 2 + (mouse_pos[1] - point.y) ** 2
                )
                if distance < 10:
                    self.hovered_point = point
                    break

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # Add new point on click
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.hovered_point is not None:
                            selected_point = self.hovered_point
                            selected_point.color = BLUE
                            dragging = True
                        else:
                            x, y = event.pos
                            next_label = chr(65 + len(self.points) % 26)
                            new_point = Point(x, y, next_label)

                            # Create a line to the most recently added point if there are points
                            # if self.points:
                            #     last_point = self.points[-1]
                            #     self.lines.append(Line(last_point, new_point))
                            #
                            self.points.append(new_point)

                    if event.button == 3:
                        if self.hovered_point is not None:
                            last_point = self.points[-1]
                            self.lines.append(Line(last_point, self.hovered_point))

                # Handle mouse movement for dragging
                elif event.type == pygame.MOUSEMOTION:
                    if dragging and selected_point is not None:
                        selected_point.x, selected_point.y = event.pos

                # Handle mouse release to stop dragging
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and dragging:
                        dragging = False
                        if selected_point:
                            selected_point.color = POINT_COLOR  # Reset color
                            selected_point = None

            # Draw everything
            self.screen.fill(BACKGROUND_COLOR)
            self.draw_grid()
            self.draw_points_and_lines()
            self.draw_instructions()

            # Draw coordinates popup if hovering over a point
            if self.hovered_point:
                self.draw_coordinates(mouse_pos)

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    canvas = EuclideanCanvas()
    canvas.run()
