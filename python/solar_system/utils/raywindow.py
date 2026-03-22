# utils/raywindow.py
import pyray as rl

# Constants (can be overridden)
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800

"""
Creates a default raylib window
"""


class Window:
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
        self._initialized = True

    def should_close(self):
        return rl.window_should_close()

    def close_window(self):
        if self._initialized:
            rl.close_window()
            self._initialized = False
