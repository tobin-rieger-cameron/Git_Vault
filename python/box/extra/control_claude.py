import pygame
import sys

# Initialize pygame
pygame.init()

# Set up the display
WIDTH, HEIGHT = 800, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Interactive Keyboard")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_BLUE = (173, 216, 230)
DARK_GRAY = (100, 100, 100)

# Font
font = pygame.font.SysFont('Arial', 18)

# Define a Key class
class Key:
    def __init__(self, x, y, width, height, key_code, label):
        self.rect = pygame.Rect(x, y, width, height)
        self.key_code = key_code
        self.label = label
        self.active = False
        self.color = GRAY
        
    def draw(self, screen):
        # Draw key background
        pygame.draw.rect(screen, self.color if not self.active else LIGHT_BLUE, self.rect)
        # Draw key border
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        # Draw key label
        text = font.render(self.label, True, BLACK)
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)
        
    def toggle(self):
        self.active = not self.active

# Create a keyboard layout
def create_keyboard():
    keys = []
    
    # Define key layouts
    # Row 1: numbers
    number_keys = [
        ('1', pygame.K_1), ('2', pygame.K_2), ('3', pygame.K_3), ('4', pygame.K_4),
        ('5', pygame.K_5), ('6', pygame.K_6), ('7', pygame.K_7), ('8', pygame.K_8),
        ('9', pygame.K_9), ('0', pygame.K_0)
    ]
    
    # Row 2: QWERTY
    qwerty_keys = [
        ('Q', pygame.K_q), ('W', pygame.K_w), ('E', pygame.K_e), ('R', pygame.K_r),
        ('T', pygame.K_t), ('Y', pygame.K_y), ('U', pygame.K_u), ('I', pygame.K_i),
        ('O', pygame.K_o), ('P', pygame.K_p)
    ]
    
    # Row 3: ASDF
    asdf_keys = [
        ('A', pygame.K_a), ('S', pygame.K_s), ('D', pygame.K_d), ('F', pygame.K_f),
        ('G', pygame.K_g), ('H', pygame.K_h), ('J', pygame.K_j), ('K', pygame.K_k),
        ('L', pygame.K_l)
    ]
    
    # Row 4: ZXCV
    zxcv_keys = [
        ('Shift', pygame.K_LSHIFT), ('Z', pygame.K_z), ('X', pygame.K_x), ('C', pygame.K_c), ('V', pygame.K_v),
        ('B', pygame.K_b), ('N', pygame.K_n), ('M', pygame.K_m)
    ]
    
    # Position parameters
    key_width = 50
    key_height = 50
    start_x = 100
    start_y = 50
    row_gap = 10
    
    # Row 1
    x = start_x
    for label, key_code in number_keys:
        keys.append(Key(x, start_y, key_width, key_height, key_code, label))
        x += key_width + 5
    
    # Row 2
    x = start_x + 25
    y = start_y + key_height + row_gap
    for label, key_code in qwerty_keys:
        keys.append(Key(x, y, key_width, key_height, key_code, label))
        x += key_width + 5
    
    # Row 3
    x = start_x + 40
    y = y + key_height + row_gap
    for label, key_code in asdf_keys:
        keys.append(Key(x, y, key_width, key_height, key_code, label))
        x += key_width + 5
    
    # Row 4
    x = start_x + 20
    y = y + key_height + row_gap
    for label, key_code in zxcv_keys:
        keys.append(Key(x, y, key_width, key_height, key_code, label))
        x += key_width + 5
    
    # Space bar
    space_width = 250
    space_x = (WIDTH - space_width) // 2
    space_y = y + key_height + row_gap
    keys.append(Key(space_x, space_y, space_width, key_height, pygame.K_SPACE, "SPACE"))
    
    return keys

# Create keyboard
keys = create_keyboard()

# Create a dictionary for key lookup by key_code
key_dict = {key.key_code: key for key in keys}

# Main loop
clock = pygame.time.Clock()
running = True

# Instructions text
instructions1 = font.render("Press keys on your keyboard to toggle the on-screen keys", True, BLACK)
instructions2 = font.render("Press ESC to quit", True, BLACK)

while running:
    screen.fill(WHITE)
    
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key in key_dict:
                key_dict[event.key].toggle()
        elif event.type == pygame.KEYUP:
            pass  # We're toggling, so we don't need to handle key up events
    
    # Draw all keys
    for key in keys:
        key.draw(screen)
    
    # Draw instructions
    screen.blit(instructions1, (20, HEIGHT - 60))
    screen.blit(instructions2, (20, HEIGHT - 30))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
