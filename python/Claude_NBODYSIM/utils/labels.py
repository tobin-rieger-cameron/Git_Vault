# utils/labels.py
import pyray as rl


pending_labels = []

def queue_label(position, text, camera):
    screen_pos = rl.get_world_to_screen(position, camera)
    pending_labels.append((screen_pos, text))

def flush_labels(font):
    for screen_pos, text in pending_labels:
        rl.draw_text_ex(font, text, rl.Vector2(int(screen_pos.x), int(screen_pos.y)), 16, 1, rl.WHITE)
    pending_labels.clear()
