import pygame
import numpy as np
import random
import time

# Constants
DEFAULT_WIDTH, DEFAULT_HEIGHT = 400, 800
COLS, ROWS = 10, 20  # Tetris grid dimensions
GRID_WIDTH, GRID_HEIGHT = 300, 600
LOCK_DELAY = 0.5  # Lock delay in seconds

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

def spawn_piece():
    """Spawn a new random piece at the top of the grid, centered at column 5."""
    piece_type = random.choice(list(TETRIMINO_SHAPES.keys()))
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
    global current_piece, current_piece_type, game_over
    running = True
    width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT

    while running:
        if game_over:
            print("Game Over!")
            running = False  # Stop the game loop

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.w, event.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:  # Move left
                    move_piece(dx=-1, dy=0)
                elif event.key == pygame.K_d:  # Move right
                    move_piece(dx=1, dy=0)
                elif event.key == pygame.K_s:  # Soft drop
                    soft_drop_or_lock()
                elif event.key == pygame.K_w:  # Hard drop
                    hard_drop()

        draw_grid(width, height)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
