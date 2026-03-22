# Main code to run a Solar System simulation (eventually)
# currently runs a simple orbital camera demo


import pyray as rl
from utils.raywindow import Window
from scripts.camera import OrbitCam
from scripts.body import Body


def main():
    # --- Initialize window ---
    win = Window(title="Orbit Camera Demo")
    win.init()

    # --- Create bodies ---
    sphere1 = Body(x=0, y=0, z=0, radius=8, color=rl.BLUE, density=1000.0, fixed=True)
    sphere1_moon1 = Body(25, 0, 0, 3, rl.GRAY, 2000.0)
    sphere1_moon1.vy = 20  # initial velocity
    sphere1_moon2 = Body(-40, 0, 0, 2, rl.DARKGRAY, 150.0)

    # --- Initialize camera ---
    camera = OrbitCam(target_body=sphere1, radius=50.0)

    # Main game loop
    while not rl.window_should_close():
        dt = rl.get_frame_time()

        Body.update_all_bodies(dt)

        camera.update(bodies=Body.get_all_bodies())

        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)

        rl.begin_mode_3d(camera.get_camera())

        Body.draw_all_bodies()

        rl.end_mode_3d()
        rl.end_drawing()

    win.close_window()


if __name__ == "__main__":
    main()
