import pyray as rl
from utils.raywindow import Window


class Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def draw(self, win, color=rl.BLACK, size=3, show_pos=True):
        sx, sy = win.to_screen(self.x, self.y)
        rl.draw_circle(sx, sy, size, color)

        # TODO: add this code to its own class/function
        # text = ""
        # if self.label:
        #    text += self.label
        # if show_pos:
        #    pos_str = f"{self.x}, {self.y}"
        #    text = f"{text} {pos_str}" if text else pos_str

        # if text:
        #    rl.draw_text(text, sx + 8, sy - 8, 10, rl.GRAY)


class Line:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    def draw(self, win, color=rl.BLACK, thickness=2):
        x1, y1 = win.to_screen(self.p1.x, self.p1.x)
        x2, y2 = win.to_screen(self.p2.x, self.p2.x)

        rl.draw_line_ex((x1, y1), (x2, y2), thickness, color)


def main():
    A = Point(0, 0)
    B = Point(15, 15)

    AB = Line(A, B)

    # ---- Initialize Window ----
    win = Window(title="Window")
    win.init()
    rl.disable_cursor()

    while not rl.window_should_close():
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)

        A.draw(win)
        B.draw(win)
        AB.draw(win)

        rl.end_drawing()

    rl.enable_cursor()
    win.close_window()


if __name__ == "__main__":
    main()
