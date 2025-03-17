import pygame
import numpy as np
import random

# Constants
DEFAULT_WIDTH, DEFAULT_HEIGHT = 400, 800  # Initial window size
COLS, ROWS = 10, 20  # Tetris grid dimensions
GRID_WIDTH, GRID_HEIGHT = 300, 600  # Fixed grid size (10x20 squares)

THIN_LINE = 1  # Normal grid lines
THICK_LINE = 2  # Every fourth row and center line

# Colors
GRID_BACKGROUND = (0, 0, 0)  # Inside the grid
OUTSIDE_BACKGROUND = (110, 110, 110)  # Outside the grid
GRID_LINES = (150, 150, 150)  # Grid outline color

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

# Shape definitions (4x4 grids for easy rotation)
TETRIMINO_SHAPES = {
    "Z": [[(0, 0), (0, 1), (1, 1), (1, 2)]],
    "S": [[(1, 0), (1, 1), (0, 1), (0, 2)]],
    "L": [[(0, 0), (1, 0), (2, 0), (2, 1)]],
    "J": [[(0, 1), (1, 1), (2, 1), (2, 0)]],
    "O": [[(0, 0), (0, 1), (1, 0), (1, 1)]],
    "T": [[(0, 0), (0, 1), (0, 2), (1, 1)]],
    "I": [[(0, 0), (1, 0), (2, 0), (3, 0)]]
}

# Initialize grid
grid = np.full((ROWS, COLS), "X")  # Start with all cells empty

def spawn_piece():
    """Spawn a new random piece at the top of the grid."""
    piece_type = random.choice(list(TETRIMINO_SHAPES.keys()))
    piece = TETRIMINO_SHAPES[piece_type][0]  # Start with default orientation
    return piece_type, [(r, c + COLS // 2 - 1) for r, c in piece]  # Adjust for center spawn

current_piece_type, current_piece = spawn_piece()

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Tetris")

def draw_grid(width, height):
    """Draws the Tetris grid centered within the window with a thick center line."""
    screen.fill(OUTSIDE_BACKGROUND)  # Fill the screen with the outside background color
    square_size = GRID_WIDTH // COLS  # Fixed square size
    margin_x = (width - GRID_WIDTH) // 2
    margin_y = (height - GRID_HEIGHT) // 2

    # Draw the grid background
    pygame.draw.rect(screen, GRID_BACKGROUND, (margin_x, margin_y, GRID_WIDTH, GRID_HEIGHT))
    
    # Draw grid cells
    for row in range(ROWS):
        for col in range(COLS):
            cell_value = grid[row, col]
            color = TETRIMINO_COLORS[cell_value]
            cell_rect = pygame.Rect(margin_x + col * square_size, margin_y + row * square_size, square_size, square_size)
            pygame.draw.rect(screen, color, cell_rect)
            grid_line_color = (0, 0, 0) if cell_value != "X" else GRID_LINES  # Black for occupied, grey for empty
            pygame.draw.rect(screen, grid_line_color, cell_rect, 1)
    
    # Draw current piece
    for r, c in current_piece:
        if 0 <= r < ROWS and 0 <= c < COLS:
            color = TETRIMINO_COLORS[current_piece_type]
            cell_rect = pygame.Rect(margin_x + c * square_size, margin_y + r * square_size, square_size, square_size)
            pygame.draw.rect(screen, color, cell_rect)
            pygame.draw.rect(screen, (0, 0, 0), cell_rect, 1)  # Black outline for active pieces

    # Draw vertical grid lines
    for col in range(COLS + 1):
        x = margin_x + col * square_size
        thickness = THICK_LINE if col == 5 else THIN_LINE  # Make center line thick
        pygame.draw.line(screen, GRID_LINES, (x, margin_y), (x, margin_y + GRID_HEIGHT), thickness)

    # Draw horizontal grid lines
    for row in range(ROWS + 1):
        y = margin_y + row * square_size
        thickness = THICK_LINE if row % 4 == 0 else THIN_LINE  # Thicker line every 4 rows
        pygame.draw.line(screen, GRID_LINES, (margin_x, y), (margin_x + GRID_WIDTH, y), thickness)

def main():
    running = True
    width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.w, event.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)

        draw_grid(width, height)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
