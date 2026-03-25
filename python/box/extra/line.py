"""
geometry.py - Euclidean Geometry Classes
Based on Euclid's Elements definitions
"""

import math
from typing import Tuple, Optional, Union


class Point:
    """
    Euclid's Definition 1: A point is that which has no part.
    Represented as coordinates in 2D space.
    """

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point({self.x}, {self.y})"

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return math.isclose(self.x, other.x) and math.isclose(self.y, other.y)


class Line:
    """
    Euclidean Line Class based on Euclid's Elements

    Euclid's Definition 2: A line is breadthless length.
    Definition 4: A straight line is a line which lies evenly with the points on itself.

    This class represents different types of lines according to Euclid:
    1. Infinite line (extends infinitely in both directions)
    2. Ray (extends infinitely in one direction from a point)
    3. Line segment (finite line between two points)
    """

    def __init__(
        self,
        point1: Point,
        point2: Optional[Point] = None,
        line_type: str = "infinite",
        direction: Optional[Tuple[float, float]] = None,
    ):
        """
        Initialize a line according to Euclidean definitions.

        Args:
            point1: First point defining the line
            point2: Second point (for segments and infinite lines)
            line_type: "infinite", "ray", or "segment"
            direction: Direction vector for rays (if point2 not provided)
        """
        self.point1 = point1
        self.point2 = point2
        self.line_type = line_type.lower()

        if self.line_type not in ["infinite", "ray", "segment"]:
            raise ValueError("line_type must be 'infinite', 'ray', or 'segment'")

        if self.line_type == "segment" and point2 is None:
            raise ValueError("Line segments require two points")

        if self.line_type == "ray" and point2 is None and direction is None:
            raise ValueError("Rays require either a second point or direction vector")

        # Calculate direction vector and slope
        if point2:
            self.direction = (point2.x - point1.x, point2.y - point1.y)
        elif direction:
            self.direction = direction
        else:
            self.direction = (1, 0)  # Default horizontal direction

        # Calculate slope (undefined for vertical lines)
        if abs(self.direction[0]) < 1e-10:  # Vertical line
            self.slope = float("inf")
            self.y_intercept = None
        else:
            self.slope = self.direction[1] / self.direction[0]
            # y = mx + b, so b = y - mx
            self.y_intercept = point1.y - self.slope * point1.x

    def __repr__(self):
        type_str = self.line_type.capitalize()
        if self.point2:
            return f"{type_str}({self.point1}, {self.point2})"
        else:
            return f"{type_str}({self.point1}, direction={self.direction})"

    def length(self) -> Optional[float]:
        """
        Return the length of the line.
        - Infinite lines and rays return None (infinite length)
        - Segments return the distance between endpoints
        """
        if self.line_type in ["infinite", "ray"]:
            return None  # Infinite length
        else:
            # Euclidean distance between two points
            dx = self.point2.x - self.point1.x
            dy = self.point2.y - self.point1.y
            return math.sqrt(dx * dx + dy * dy)

    def contains_point(self, point: Point) -> bool:
        """
        Check if a point lies on this line (Euclid's concept of collinearity).
        """
        # Check if point is collinear with the line's direction
        if self.point2:
            # Use cross product to check collinearity
            dx1 = point.x - self.point1.x
            dy1 = point.y - self.point1.y
            dx2 = self.point2.x - self.point1.x
            dy2 = self.point2.y - self.point1.y

            # Cross product should be zero for collinear points
            cross_product = dx1 * dy2 - dy1 * dx2
            is_collinear = abs(cross_product) < 1e-10
        else:
            # Use direction vector
            dx = point.x - self.point1.x
            dy = point.y - self.point1.y

            if abs(self.direction[0]) < 1e-10 and abs(self.direction[1]) < 1e-10:
                return point == self.point1
            elif abs(self.direction[0]) < 1e-10:
                is_collinear = abs(dx) < 1e-10
            elif abs(self.direction[1]) < 1e-10:
                is_collinear = abs(dy) < 1e-10
            else:
                # Check if ratios are equal
                ratio_x = (
                    dx / self.direction[0] if abs(self.direction[0]) > 1e-10 else 0
                )
                ratio_y = (
                    dy / self.direction[1] if abs(self.direction[1]) > 1e-10 else 0
                )
                is_collinear = abs(ratio_x - ratio_y) < 1e-10

        if not is_collinear:
            return False

        # For segments, check if point is between endpoints
        if self.line_type == "segment":
            # Point must be between point1 and point2
            min_x, max_x = (
                min(self.point1.x, self.point2.x),
                max(self.point1.x, self.point2.x),
            )
            min_y, max_y = (
                min(self.point1.y, self.point2.y),
                max(self.point1.y, self.point2.y),
            )
            return min_x <= point.x <= max_x and min_y <= point.y <= max_y

        # For rays, check if point is in the correct direction
        elif self.line_type == "ray":
            if self.point2:
                # Check if point is on the same side as point2 relative to point1
                t1 = self._parameter_for_point(point)
                return t1 >= -1e-10  # Allow for small floating point errors
            else:
                # Use direction vector
                dx = point.x - self.point1.x
                dy = point.y - self.point1.y
                dot_product = dx * self.direction[0] + dy * self.direction[1]
                return dot_product >= -1e-10

        # For infinite lines, any collinear point is on the line
        return True

    def _parameter_for_point(self, point: Point) -> float:
        """
        Calculate the parameter t such that point = point1 + t * (point2 - point1)
        """
        if not self.point2:
            return 0

        dx = self.point2.x - self.point1.x
        dy = self.point2.y - self.point1.y

        if abs(dx) > abs(dy):
            return (point.x - self.point1.x) / dx
        else:
            return (point.y - self.point1.y) / dy if abs(dy) > 1e-10 else 0

    def is_parallel(self, other: "Line") -> bool:
        """
        Check if two lines are parallel (Euclid's Postulate 5 related).
        Parallel lines have the same slope (or both are vertical).
        """
        if not isinstance(other, Line):
            raise TypeError("Can only compare with another Line")

        # Both vertical
        if self.slope == float("inf") and other.slope == float("inf"):
            return True

        # One vertical, one not
        if self.slope == float("inf") or other.slope == float("inf"):
            return False

        # Compare slopes
        return abs(self.slope - other.slope) < 1e-10

    def is_perpendicular(self, other: "Line") -> bool:
        """
        Check if two lines are perpendicular (meet at right angles).
        """
        if not isinstance(other, Line):
            raise TypeError("Can only compare with another Line")

        # One vertical, one horizontal
        if (self.slope == float("inf") and abs(other.slope) < 1e-10) or (
            other.slope == float("inf") and abs(self.slope) < 1e-10
        ):
            return True

        # Both have finite slopes
        if self.slope != float("inf") and other.slope != float("inf"):
            return abs(self.slope * other.slope + 1) < 1e-10

        return False

    @classmethod
    def from_points(cls, point1: Point, point2: Point, line_type: str = "infinite"):
        """
        Create a line from two points (Euclid's Postulate 1:
        "It is possible to draw a straight line from any point to any other point").
        """
        return cls(point1, point2, line_type)

    @classmethod
    def segment(cls, point1: Point, point2: Point):
        """Create a line segment between two points."""
        return cls(point1, point2, "segment")

    @classmethod
    def ray(cls, start_point: Point, through_point: Point):
        """Create a ray starting at start_point and passing through through_point."""
        return cls(start_point, through_point, "ray")


# Example usage and tests
if __name__ == "__main__":
    # Create some points
    p1 = Point(0, 0)
    p2 = Point(3, 4)
    p3 = Point(1.5, 2)  # Midpoint of p1 and p2

    # Create different types of lines
    infinite_line = Line.from_points(p1, p2, "infinite")
    segment = Line.segment(p1, p2)
    ray = Line.ray(p1, p2)

    print(f"Infinite line: {infinite_line}")
    print(f"Segment: {segment}")
    print(f"Ray: {ray}")

    print(f"\nSegment length: {segment.length()}")
    print(f"Infinite line length: {infinite_line.length()}")

    print(f"\nMidpoint on segment: {segment.contains_point(p3)}")
    print(f"Midpoint on infinite line: {infinite_line.contains_point(p3)}")

    # Test parallel lines
    p4 = Point(1, 1)
    p5 = Point(4, 5)
    parallel_line = Line.from_points(p4, p5)

    print(f"\nLines are parallel: {infinite_line.is_parallel(parallel_line)}")
