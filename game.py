import pygame
import numpy as np
import random

# Constants
DEFAULT_WIDTH, DEFAULT_HEIGHT = 400, 800  # Initial window size
COLS, ROWS = 10, 20  # Tetris grid dimensions
GRID_WIDTH, GRID_HEIGHT = 300, 600  # Fixed grid size (10x20 squares)

# Colors
GRID_BACKGROUND = (0, 0, 0)  # Inside the grid
OUTSIDE_BACKGROUND = (110, 110, 110)  # Outside the grid
GRID_LINES = (150, 150, 150)  # Grid outline color for empty cells
PIECE_OUTLINE = (0, 0, 0)  # Outline for occupied cells

# Tetrimino colors
TETRIMINO_COLORS = {
    "X": GRID_BACKGROUND,  # Empty cells should match the grid color
    "Z": (255, 64, 32),  # Red
    "S": (64, 208, 64),  # Green
    "L": (255, 128, 32),  # Orange
    "J": (64, 128, 255),  # Blue
    "O": (255, 224, 32),  # Yellow
    "T": (160, 64, 240),  # Purple
    "I": (0, 208, 255)  # Cyan
}

# Shape definitions with proper SRS spawn orientations
TETRIMINO_SHAPES = {
    "Z": [[(0, -1), (0, 0), (1, 0), (1, 1)]],
    "S": [[(1, -1), (1, 0), (0, 0), (0, 1)]],
    "L": [[(1, -1), (1, 0), (1, 1), (0, 1)]],
    "J": [[(1, -1), (1, 0), (1, 1), (0, -1)]],
    "O": [[(0, 0), (0, 1), (1, 0), (1, 1)]],
    "T": [[(1, -1), (1, 0), (1, 1), (0, 0)]],  # T-piece now points up
    "I": [[(0, 0), (0, 1), (0, 2), (0, 3)]]  # I-piece centered
}

# Initialize grid
grid = np.full((ROWS, COLS), "X")  # Start with all cells empty

def spawn_piece():
    """Spawn a new random piece at the top of the grid, aligned to column 5 (index 4) using SRS."""
    piece_type = random.choice(list(TETRIMINO_SHAPES.keys()))
    piece = TETRIMINO_SHAPES[piece_type][0]  # Default rotation

    # Adjust positions to align center to column 5
    adjusted_piece = [(r, c + 4) if piece_type != "I" else (r, c + 3) for r, c in piece]  # I-piece fix

    return piece_type, adjusted_piece

def is_valid_position(piece):
    """Check if a piece's position is valid (inside bounds and not colliding)."""
    for r, c in piece:
        if c < 0 or c >= COLS or r >= ROWS:  # Out of horizontal/vertical bounds
            return False
        if r >= 0 and grid[r, c] != "X":  # Collision with another block
            return False
    return True

def move_piece(dx, dy):
    """Attempt to move the current piece by (dx, dy)."""
    global current_piece
    new_position = [(r + dy, c + dx) for r, c in current_piece]

    if is_valid_position(new_position):
        current_piece[:] = new_position  # Update piece position

def hard_drop():
    """Instantly moves the piece downward until it collides with an obstacle."""
    global current_piece

    drop_distance = 0
    test_position = current_piece[:]

    # Move the piece down step by step until collision
    while is_valid_position([(r + 1, c) for r, c in test_position]):
        drop_distance += 1
        test_position = [(r + 1, c) for r, c in test_position]

    # Apply final position
    current_piece[:] = test_position

current_piece_type, current_piece = spawn_piece()

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Tetris")

def draw_grid(width, height):
    """Draws the Tetris grid centered within the window, with each cell having an individual outline."""
    screen.fill(OUTSIDE_BACKGROUND)  # Fill the screen with the outside background color
    square_size = GRID_WIDTH // COLS  # Fixed square size
    margin_x = (width - GRID_WIDTH) // 2
    margin_y = (height - GRID_HEIGHT) // 2

    # Draw the grid background
    pygame.draw.rect(screen, GRID_BACKGROUND, (margin_x, margin_y, GRID_WIDTH, GRID_HEIGHT))

    # Draw grid cells with individual outlines
    for row in range(ROWS):
        for col in range(COLS):
            cell_value = grid[row, col]
            color = TETRIMINO_COLORS[cell_value]
            outline_color = PIECE_OUTLINE if cell_value != "X" else GRID_LINES
            cell_rect = pygame.Rect(margin_x + col * square_size, margin_y + row * square_size, square_size, square_size)
            pygame.draw.rect(screen, color, cell_rect)
            pygame.draw.rect(screen, outline_color, cell_rect, 1)

    # Draw current piece
    for r, c in current_piece:
        if 0 <= r < ROWS and 0 <= c < COLS:
            color = TETRIMINO_COLORS[current_piece_type]
            cell_rect = pygame.Rect(margin_x + c * square_size, margin_y + r * square_size, square_size, square_size)
            pygame.draw.rect(screen, color, cell_rect)
            pygame.draw.rect(screen, PIECE_OUTLINE, cell_rect, 1)  # Outline for active pieces

def main():
    global current_piece, current_piece_type
    running = True
    width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT

    while running:
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
                elif event.key == pygame.K_s:  # Move down
                    move_piece(dx=0, dy=1)
                elif event.key == pygame.K_w:  # Hard drop
                    hard_drop()

        draw_grid(width, height)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
