# pyray must be installed to run
import pyray as rl

# screen dimensions set as constants for now
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800


class Window:
    """
    raylib window
    """

    def __init__(
        self,
        w=SCREEN_WIDTH,
        h=SCREEN_HEIGHT,
        title="Window",
        fps=60,
    ):
        self.width = w
        self.height = h
        self.title = title
        self.fps = fps
        self._initialized = False

    def init(self):
        rl.init_window(self.width, self.height, self.title)
        rl.set_target_fps(self.fps)
        # rl.disable_cursor()
        self._initialized = True

    def close_window(self):
        if self._initialized:
            rl.close_window()
            self._initialized = False

    def to_screen(self, x: float, y: float):
        # normalize position around screen center
        sx = self.width // 2 + int(x)
        sy = self.height // 2 - int(y)
        return sx, sy


def main():
    # --- Initialize Window ---
    win = Window(title="Window")
    win.init()

    # --- Main Loop ---
    while not rl.window_should_close():
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)

        # draw objects here

        rl.end_drawing()
    rl.enable_curson()
    win.close_window


if __name__ == "__main__":
    main()
