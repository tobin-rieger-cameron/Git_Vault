import pyray as rl


def hex_to_color(hex_str, alpha=255):
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    return rl.Color(r, g, b, alpha)




BACKGROUND    = hex_to_color("#f2e5bc")
GRID_COLOR    = rl.Color(180, 170, 150, 80)
X_AXIS_COLOR  = rl.Color(255, 0, 0, 120)
Y_AXIS_COLOR  = rl.Color(0, 255, 0, 120)
Z_AXIS_COLOR  = rl.Color(0, 0, 255, 120)
RESULTANT_COL = rl.Color(255, 220,  50, 255)
WHITE         = rl.Color(255, 255, 255, 255)
DARK_OVERLAY  = rl.Color(  0,   0,   0, 140)

BODY_COLS = [
    rl.Color( 70, 140, 230, 255),   # blue
    rl.Color(220,  80,  80, 255),   # red
    rl.Color( 55, 200, 120, 255),   # green
]
FORCE_COLS = [
    rl.Color(120, 190, 255, 220),
    rl.Color(255, 140, 140, 220),
    rl.Color(120, 240, 170, 220),
]
TRAIL_COLS = [
    rl.Color( 70, 140, 230, 120),
    rl.Color(220,  80,  80, 120),
    rl.Color( 55, 200, 120, 120),
]

