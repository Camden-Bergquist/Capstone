import pygame
import numpy as np
import random
import time

# Constants
DEFAULT_WIDTH, DEFAULT_HEIGHT = 400, 800
COLS, ROWS = 10, 20  # Play matrix dimensions
GRID_WIDTH, GRID_HEIGHT = 300, 600
LOCK_DELAY = 250  # Lock delay in milliseconds
DAS = 150  # Delayed Auto-Shift in milliseconds
ARR = 75  # Auto Repeat Rate in milliseconds
SOFT_DROP_DAS = 75  # Delay before repeated soft drops start (in milliseconds)
SOFT_DROP_ARR = 35  # Time between additional soft drops when held (in milliseconds)


# Track movement state
move_left_pressed = False
move_right_pressed = False
soft_drop_pressed = False
das_timer = 0
arr_timer = 0
soft_drop_das_timer = 0
soft_drop_arr_timer = 0


# Colors
GRID_BACKGROUND = (0, 0, 0)
OUTSIDE_BACKGROUND = (110, 110, 110)
GRID_LINES = (150, 150, 150)
PIECE_OUTLINE = (0, 0, 0)

# Tetrimino colors
TETRIMINO_COLORS = {
    "X": GRID_BACKGROUND,
    "Z": (255, 64, 32),
    "S": (64, 208, 64),
    "L": (255, 128, 32),
    "J": (64, 128, 255),
    "O": (255, 224, 32),
    "T": (160, 64, 240),
    "I": (0, 208, 255)
}

# Shape definitions with SRS spawn orientations
TETRIMINO_SHAPES = {
    "Z": [[(0, -1), (0, 0), (1, 0), (1, 1)]],
    "S": [[(1, -1), (1, 0), (0, 0), (0, 1)]],
    "L": [[(1, -1), (1, 0), (1, 1), (0, 1)]],
    "J": [[(1, -1), (1, 0), (1, 1), (0, -1)]],
    "O": [[(0, 0), (0, 1), (1, 0), (1, 1)]],
    "T": [[(1, -1), (1, 0), (1, 1), (0, 0)]],
    "I": [[(0, 0), (0, 1), (0, 2), (0, 3)]]
}

# Initialize grid
grid = np.full((ROWS, COLS), "X")

def is_valid_position(piece):
    """Check if a piece's position is valid (inside bounds and not colliding)."""
    for r, c in piece:
        if c < 0 or c >= COLS or r >= ROWS:  # Out of bounds
            return False
        if r >= 0 and grid[r, c] != "X":  # Collision
            return False
    return True

def lock_piece():
    """Locks the current piece into the grid and spawns a new piece."""
    global current_piece, current_piece_type, game_over
    for r, c in current_piece:
        if r >= 0:
            grid[r, c] = current_piece_type  # Lock piece into the grid
    
    # Spawn a new piece
    current_piece_type, current_piece = spawn_piece()
    
    # Check if the new piece is already colliding (Game Over)
    if not is_valid_position(current_piece):
        game_over = True  # Game over if the new piece cannot be placed

def move_piece(dx, dy):
    """Attempt to move the current piece by (dx, dy)."""
    global current_piece
    new_position = [(r + dy, c + dx) for r, c in current_piece]
    if is_valid_position(new_position):
        current_piece[:] = new_position
        return True
    return False

def hard_drop():
    """Instantly moves the piece downward until it collides, then locks."""
    global current_piece
    while move_piece(0, 1):  # Move down until collision
        pass
    lock_piece()  # Lock immediately

def soft_drop_or_lock():
    """Moves the piece down one step. If it can't move, it locks after 0.5s."""
    if not move_piece(0, 1):  # If piece can't move down
        time.sleep(LOCK_DELAY)  # Wait 0.5 seconds before locking
        if not move_piece(0, 1):  # Check again after delay
            lock_piece()

# Global piece bag (initialize empty)
piece_bag = []

def refill_bag():
    """Refills and shuffles the 7-bag when empty."""
    global piece_bag
    piece_bag = random.sample(list(TETRIMINO_SHAPES.keys()), len(TETRIMINO_SHAPES))  # Shuffle all 7 pieces

def spawn_piece():
    """Spawn a new piece from the 7-bag randomization system."""
    global piece_bag

    if not piece_bag:  # If the bag is empty, refill it
        refill_bag()

    piece_type = piece_bag.pop(0)  # Take the first piece from the bag
    piece = TETRIMINO_SHAPES[piece_type][0]

    # Adjust positions to align center to column 5
    adjusted_piece = [(r, c + 4) if piece_type != "I" else (r, c + 3) for r, c in piece]

    return piece_type, adjusted_piece


# Initialize game state
current_piece_type, current_piece = spawn_piece()
game_over = False

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Tetris")

def handle_movement():
    """Handles DAS and ARR for left/right movement."""
    global das_timer, arr_timer

    current_time = pygame.time.get_ticks()

    if move_left_pressed or move_right_pressed:
        if das_timer == 0:
            das_timer = current_time  # Start DAS timer

        elif current_time - das_timer >= DAS:
            # DAS threshold reached, start ARR movement
            if arr_timer == 0 or current_time - arr_timer >= ARR:
                direction = -1 if move_left_pressed else 1
                move_piece(direction, 0)
                arr_timer = current_time  # Reset ARR timer
    else:
        das_timer = 0  # Reset when key is released
        arr_timer = 0

soft_drop_lock_timer = 0  # Track time before locking after soft drop

def handle_soft_drop():
    """Handles DAS and ARR for soft dropping, with proper locking."""
    global soft_drop_das_timer, soft_drop_arr_timer, soft_drop_lock_timer

    current_time = pygame.time.get_ticks()

    if soft_drop_pressed:
        if soft_drop_das_timer == 0:
            soft_drop_das_timer = current_time  # Start DAS timer
            if not move_piece(0, 1):  # If move fails, start lock timer
                if soft_drop_lock_timer == 0:
                    soft_drop_lock_timer = current_time

        elif current_time - soft_drop_das_timer >= SOFT_DROP_DAS:
            if soft_drop_arr_timer == 0 or current_time - soft_drop_arr_timer >= SOFT_DROP_ARR:
                if not move_piece(0, 1):  # If move fails, start lock timer
                    if soft_drop_lock_timer == 0:
                        soft_drop_lock_timer = current_time
                soft_drop_arr_timer = current_time  # Reset ARR timer
    else:
        soft_drop_das_timer = 0  # Reset DAS
        soft_drop_arr_timer = 0  # Reset ARR
        soft_drop_lock_timer = 0  # Reset lock timer when released

    # **Handle Locking**: If the piece has been unable to move down for `LOCK_DELAY`, lock it.
    if soft_drop_lock_timer > 0 and current_time - soft_drop_lock_timer >= LOCK_DELAY:
        lock_piece()
        soft_drop_lock_timer = 0  # Reset lock timer after locking

def draw_grid(width, height):
    """Draws the Tetris grid centered within the window."""
    screen.fill(OUTSIDE_BACKGROUND)
    square_size = GRID_WIDTH // COLS
    margin_x = (width - GRID_WIDTH) // 2
    margin_y = (height - GRID_HEIGHT) // 2

    # Draw grid background
    pygame.draw.rect(screen, GRID_BACKGROUND, (margin_x, margin_y, GRID_WIDTH, GRID_HEIGHT))

    # Draw grid cells (locked pieces and empty spaces)
    for row in range(ROWS):
        for col in range(COLS):
            cell_value = grid[row, col]
            color = TETRIMINO_COLORS[cell_value] if cell_value in TETRIMINO_COLORS else GRID_BACKGROUND
            cell_rect = pygame.Rect(margin_x + col * square_size, margin_y + row * square_size, square_size, square_size)
            
            # Draw filled cells with black outline, empty cells with grid lines
            pygame.draw.rect(screen, color, cell_rect)
            if cell_value != "X":  
                pygame.draw.rect(screen, PIECE_OUTLINE, cell_rect, 1)  # Black outline for filled cells
            else:
                pygame.draw.rect(screen, GRID_LINES, cell_rect, 1)  # Grid lines for empty cells

    # Draw current piece (active falling piece)
    for r, c in current_piece:
        if 0 <= r < ROWS and 0 <= c < COLS:
            color = TETRIMINO_COLORS[current_piece_type]
            cell_rect = pygame.Rect(margin_x + c * square_size, margin_y + r * square_size, square_size, square_size)
            pygame.draw.rect(screen, color, cell_rect)
            pygame.draw.rect(screen, PIECE_OUTLINE, cell_rect, 1)  # Outline for active pieces


def main():
    global move_left_pressed, move_right_pressed, soft_drop_pressed
    running = True

    while running:
        if game_over:
            print("Game Over!")
            running = False

        handle_movement()  # Handle left/right DAS & ARR
        handle_soft_drop()  # Handle soft drop DAS & ARR

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    move_left_pressed = True
                    move_piece(-1, 0)  # Initial move instantly
                elif event.key == pygame.K_d:
                    move_right_pressed = True
                    move_piece(1, 0)  # Initial move instantly
                elif event.key == pygame.K_s:
                    soft_drop_pressed = True
                    move_piece(0, 1)  # Initial move instantly
                elif event.key == pygame.K_w:
                    hard_drop()  # Hard drop immediately places and locks piece
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_a:
                    move_left_pressed = False
                elif event.key == pygame.K_d:
                    move_right_pressed = False
                elif event.key == pygame.K_s:
                    soft_drop_pressed = False

        draw_grid(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
