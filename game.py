import pygame
import numpy as np
import random
import time
import threading

# Constants
DEFAULT_WIDTH, DEFAULT_HEIGHT = 800, 700
COLS, ROWS = 10, 24  # Play matrix dimensions
VISIBLE_ROWS = 20 # Play matrix rows visible to the plauyer
GRID_WIDTH, GRID_HEIGHT = 300, 600
LOCK_DELAY = 250  # Lock delay in milliseconds
DAS = 150  # Delayed Auto-Shift in milliseconds
ARR = 75  # Auto Repeat Rate in milliseconds
SOFT_DROP_DAS = 75  # Delay before repeated soft drops start (in milliseconds)
SOFT_DROP_ARR = 35  # Time between additional soft drops when held (in milliseconds)
GRAVITY = 1000  # Default fall speed in milliseconds (1000ms = 1 second per row)
LOCKOUT_OVERRIDE = 2000  # Time in milliseconds before forced lockout

# Tracking variables
move_left_pressed = False
move_right_pressed = False
soft_drop_pressed = False
das_timer = 0
arr_timer = 0
soft_drop_das_timer = 0
soft_drop_arr_timer = 0
soft_drop_lock_timer = 0  # Track time before locking after soft drop
gravity_timer = 0  # Tracks last gravity update
gravity_lock_timer = 0  # Tracks when the piece should lock due to gravity
lockout_override_timer = 0  # Track time for lockout override
held_piece = None  # Stores the currently held piece type
hold_used = False  # Lockout to prevent indefinite swapping
primary_bag = []    # The active bag for spawning pieces
secondary_bag = []  # The backup bag (future pieces)
next_queue = []     # Holds the next five pieces to display
bag_piece_count = 0  # Tracks how many pieces have spawned
score = 0  # Track player's score
lines_cleared = 0  # Track number of lines cleared
start_time = time.time()  # Track game start time
total_pieces_placed = 0  # Track the number of pieces placed
b2b = False # Track whether or not the player currently has back-to-back status
clear_combo = 0 # Track line clear combos for scoring.
qualified_for_T_spin = False  # Tracks if the current piece is eligible for a T-spin
wall_kick_5_used = False # Tracks if the wall-kick used is the fifth and final kick, which results in an auto T-spin detection
clear_text = "" # Displays the type of clear most recently achieved (e.g., "Double!")
clear_text_color = (255, 255, 255) # Sets the base color for the clear text to white, to be changed to gold if a b2b was present.
clear_text_timer = None # Track clear text timer.

# Colors
GRID_BACKGROUND = (0, 0, 0)
OUTSIDE_BACKGROUND = (90, 90, 90)
GRID_LINES = (60, 60, 60)
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

PIECE_PIVOTS = {
    "L": 1,  # Middle of three-segment row
    "J": 1,  # Middle of three-segment row
    "T": 1,  # Middle of three-segment row
    "S": 1,  # Lower of vertical two-stack
    "Z": 2,  # Lower of vertical two-stack
    "I": 1,  # Center horizontally, bottom-most square vertically
    "O": 0  # True center, does not move
}

# SRS Wall Kick Data (J, L, S, T, Z)
SRS_WALL_KICKS = {
    (0, "R"): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],  # 0 → R
    ("R", 0): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],  # R → 0
    ("R", 2): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],  # R → 2
    (2, "R"): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],  # 2 → R
    (2, "L"): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],  # 2 → L
    ("L", 2): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],  # L → 2
    ("L", 0): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],  # L → 0
    (0, "L"): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],  # 0 → L
}

# SRS Wall Kick Data for I-Piece (Different from other pieces)
SRS_WALL_KICKS_I = {
    (0, "R"): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    ("R", 0): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    ("R", 2): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
    (2, "R"): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (2, "L"): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    ("L", 2): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    ("L", 0): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (0, "L"): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
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
    global current_piece, current_piece_type, current_rotation, game_over, hold_used, total_pieces_placed

    # **Lock the piece into the grid**
    for r, c in current_piece:
        if r >= 0:
            grid[r, c] = current_piece_type  

    # **Check for and clear full lines**
    clear_lines()

    # **Spawn a new piece from the updated queue**
    current_piece_type, current_piece, current_rotation = spawn_piece()

    # Increment piece counter.
    total_pieces_placed += 1

    # **Reset hold usage (holding is allowed again)**
    hold_used = False

    # **Check if the new piece is already colliding (Game Over)**
    if not is_valid_position(current_piece):
        game_over = True  # Game over if the new piece cannot be placed

    # **Ensure the display updates immediately**
    draw_grid()
    pygame.display.flip()

def move_piece(dx, dy):
    """Attempt to move the current piece by (dx, dy)."""
    global current_piece, qualified_for_T_spin, wall_kick_5_used

    new_position = [(r + dy, c + dx) for r, c in current_piece]
    
    if is_valid_position(new_position):
        current_piece[:] = new_position

        # Disqualify T-spin if the move was a successful left/right shift
        if dx != 0:
            qualified_for_T_spin = False
            wall_kick_5_used = False

        return True

    return False


def hard_drop():
    """Instantly moves the piece downward until it collides, then locks.
       Awards 2 points for each space the piece moves down."""
    global current_piece, score, qualified_for_T_spin, wall_kick_5_used

    drop_distance = 0  # Track how many spaces the piece moves

    while move_piece(0, 1):  # Move down until collision
        drop_distance += 1  # Count the movement steps

    # Only disqualify T-spin if the piece actually moved downward
    if drop_distance > 0:
        qualified_for_T_spin = False 
        wall_kick_5_used = False # Only disqualify if it actually moves

    # Award hard drop points (2 points per space moved)
    score += drop_distance * 2

    # Lock immediately after reaching the lowest position
    lock_piece()

def soft_drop_or_lock():
    """Moves the piece down one step. If it can't move, it locks after 0.5s."""
    if not move_piece(0, 1):  # If piece can't move down
        time.sleep(LOCK_DELAY)  # Wait 0.5 seconds before locking
        if not move_piece(0, 1):  # Check again after delay
            lock_piece()


def refill_bag():
    """Refills the piece bags, maintaining two bags at all times and printing their contents."""
    global primary_bag, secondary_bag

    full_bag = ["I", "O", "T", "L", "J", "S", "Z"]  # Correct 7-bag with all pieces

    # If both bags are empty, fill both
    if not primary_bag and not secondary_bag:
        primary_bag = random.sample(full_bag, len(full_bag))  # Shuffle first bag
        secondary_bag = random.sample(full_bag, len(full_bag))  # Shuffle second bag

    # If only the primary bag is empty, refill it from the secondary and create a new secondary
    elif not primary_bag:
        primary_bag = secondary_bag
        secondary_bag = random.sample(full_bag, len(full_bag))  # Shuffle new secondary bag


def spawn_piece():
    """Spawns a new piece from the next queue, ensuring the queue remains filled."""
    global primary_bag, secondary_bag, next_queue, bag_piece_count, wall_kick_5_used

    wall_kick_5_used = False # Reset to False when a new piece is spawned.

    # Ensure next_queue has at least 5 pieces
    while len(next_queue) < 5:
        if not primary_bag:
            refill_bag()
        next_queue.append(primary_bag.pop(0))

    # **Take the first piece from the queue**
    current_piece_type = next_queue.pop(0)

    # **Increment piece count when a new piece spawns**
    if bag_piece_count < 7:
        bag_piece_count += 1
    else:
        bag_piece_count = 1
    # **Ensure the queue remains filled**
    while len(next_queue) < 5:
        if not primary_bag:
            refill_bag()
        next_queue.append(primary_bag.pop(0))

    # Get the shape of the new piece
    piece = TETRIMINO_SHAPES[current_piece_type][0]

    # **Spawn the piece at the correct position**
    adjusted_piece = [(r + 2, c + 4) if current_piece_type != "I" else (r + 2, c + 3) for r, c in piece]

    return current_piece_type, adjusted_piece, 0  # (0 = spawn state)

def hold_piece():
    """Handles the hold mechanic. Can only be used once per active piece."""
    global held_piece, current_piece_type, current_piece, current_rotation, hold_used

    if hold_used:
        return  # Can't hold again until a new piece locks

    if held_piece is None:
        # If no piece is held, store the current piece and spawn a new one
        held_piece = current_piece_type
        current_piece_type, current_piece, current_rotation = spawn_piece()
    else:
        # If a piece is already held, swap it with the current piece
        held_piece, current_piece_type = current_piece_type, held_piece
        current_piece, current_rotation = TETRIMINO_SHAPES[current_piece_type][0], 0

        # Adjust position for spawning
        current_piece = [(r + 2, c + 4) if current_piece_type != "I" else (r + 2, c + 3) for r, c in current_piece]

    hold_used = True  # Mark hold as used until next piece locks

# Initialize game state
current_piece_type, current_piece, current_rotation = spawn_piece()
game_over = False

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Tetris")

def is_grounded():
    """Returns True if the piece is directly above a solid block or the floor."""
    for r, c in current_piece:
        if r + 1 >= ROWS or (r + 1 >= 0 and grid[r + 1, c] != "X"):  # Check if a block is below
            return True
    return False

def detect_T_spin():
    """Determines if the last move was a T-Spin, returning False if not a T piece."""
    global current_piece_type, current_rotation, grid

    # If the piece is not a T or the last action wasn't a rotation, there is no T-spin.
    if current_piece_type != "T" or not qualified_for_T_spin:
        return False

    # Initialize localized variables for corner checks. Front is the direction the T-piece is 'pointing' in, while back is the opposite.
    front_left_filled = False
    front_right_filled = False
    back_right_filled = False
    back_left_filled = False

    # Identify the pivot position (center of the T piece).
    pivot_index = PIECE_PIVOTS["T"]
    pivot_r, pivot_c = current_piece[pivot_index]

    # **Handle corner checking for each rotation state
    if current_rotation == 0:
        # **Check front-facing squares**
        front_left_filled = (
            pivot_r - 1 >= 0 and pivot_c - 1 >= 0 and grid[pivot_r - 1, pivot_c - 1] != "X"
        )
        front_right_filled = (
            pivot_r - 1 >= 0 and pivot_c + 1 < COLS and grid[pivot_r - 1, pivot_c + 1] != "X"
        )

        # **Check bottom-facing squares (considering out-of-bounds cases)**
        back_left_filled = (
            pivot_r + 1 >= ROWS or  # Back touching grid floor
            grid[pivot_r + 1, pivot_c - 1] != "X"  # Cell is filled
        )
        back_right_filled = (
            pivot_r + 1 >= ROWS or  # Back touching grid floor
            grid[pivot_r + 1, pivot_c + 1] != "X"  # Cell is filled
        )

    elif current_rotation == "R":
        # **Check front-facing squares**
        front_left_filled = (
            pivot_r - 1 >= 0 and pivot_c - 1 >= 0 and grid[pivot_r - 1, pivot_c + 1] != "X"
        )
        front_right_filled = (
            pivot_r - 1 >= 0 and pivot_c + 1 < COLS and grid[pivot_r + 1, pivot_c + 1] != "X"
        )

        # **Check bottom-facing squares (considering out-of-bounds cases)**
        back_left_filled = (
            pivot_c - 1 < 0 or  # Touching left wall
            grid[pivot_r - 1, pivot_c - 1] != "X"  # Cell is filled
        )
        back_right_filled = (
            pivot_c - 1 < 0 or  # Touching left wall
            grid[pivot_r + 1, pivot_c - 1] != "X"  # Cell is filled
        )

    elif current_rotation == 2:
        # **Check front-facing squares**
        front_left_filled = (
            pivot_r - 1 >= 0 and pivot_c - 1 >= 0 and grid[pivot_r + 1, pivot_c + 1] != "X"
        )
        front_right_filled = (
            pivot_r - 1 >= 0 and pivot_c + 1 < COLS and grid[pivot_r + 1, pivot_c - 1] != "X"
        )

        # Check bottom-facing squares (no out-of-bounds cases for down-facing T-piece)
        back_left_filled = (
            grid[pivot_r - 1, pivot_c + 1] != "X"  # Cell is filled
        )
        back_right_filled = (
            grid[pivot_r - 1, pivot_c - 1] != "X"  # Cell is filled
        )

    elif current_rotation == "L":
        # **Check front-facing squares**
        front_left_filled = (
            pivot_r - 1 >= 0 and pivot_c - 1 >= 0 and grid[pivot_r + 1, pivot_c - 1] != "X"
        )
        front_right_filled = (
            pivot_r - 1 >= 0 and pivot_c + 1 < COLS and grid[pivot_r - 1, pivot_c - 1] != "X"
        )

        # **Check bottom-facing squares (considering out-of-bounds cases)**
        back_left_filled = (
            pivot_c + 1 >= COLS or  # Touching right wall
            grid[pivot_r + 1, pivot_c + 1] != "X"  # Cell is filled
        )
        back_right_filled = (
            pivot_c + 1 >= COLS or  # Touching right wall
            grid[pivot_r - 1, pivot_c + 1] != "X"  # Cell is filled
        )

    # Return T-Spin state if detected.
    if front_left_filled and front_right_filled and (back_left_filled or back_right_filled):
        return "T-Spin"
    elif wall_kick_5_used: # Could technically be added to the first conditional above, but would be difficult to read.
        return "T-Spin"
    elif back_left_filled and back_right_filled and (front_left_filled or front_right_filled):
        return "Mini T-Spin"
    else:
        return False

def handle_clear_text(text, has_b2b):
    """Sets the global clear_text variable to the given string for two seconds before clearing it.
    If called again before the timer expires, the timer resets.
    """
    global clear_text, b2b, clear_text_color, clear_text_timer

    clear_text = text  # Set the text

    # Determine the text color based on B2B status
    if has_b2b and b2b:
        clear_text_color = (255, 215, 0)  # Gold for B2B
    else:
        clear_text_color = (255, 255, 255)  # White otherwise

    # Cancel any existing timer to reset the countdown
    if clear_text_timer is not None:
        clear_text_timer.cancel()

    # Start a new timer to clear the text after 2 seconds
    clear_text_timer = threading.Timer(2, clear_clear_text)
    clear_text_timer.start()

def clear_clear_text():
    """Clears the clear_text after the timer expires."""
    global clear_text
    clear_text = ""  # Reset the text

def clear_lines():
    """Checks for full lines, clears them, shifts the above lines down, detects perfect clear, and awards points."""
    global grid, lines_cleared, score, b2b, clear_combo

    # Initialize local variables:
    full_rows = [r for r in range(ROWS) if all(grid[r, c] != "X" for c in range(COLS))] # Identify full rows
    num_cleared = len(full_rows)  # Number of lines cleared
    T_spin = detect_T_spin() # Detect T-Spin (False, "Mini T-Spin", "T-Spin")
    score_awarded = 0 # Score to be awarded to the player at the end of the function.
    unique_b2b = False # Identifier for cases when b2b isn't a simple 1.5x score multiplier
    has_b2b = b2b # Checks whether the player had b2b *before* all the scoring logic changes it. Otherwise, initial 'difficult' clears would award b2b-modified points.

    if num_cleared == 0:
        clear_combo = 0

    elif num_cleared > 0:
        # Remove full rows and insert new empty rows at the top
        new_grid = np.full((ROWS, COLS), "X")  # Start with an empty grid
        new_row_idx = ROWS - 1  # Start from the bottom

        # Fill the new grid with non-cleared rows
        for r in range(ROWS - 1, -1, -1):
            if r not in full_rows:  # If row is not full, copy it down
                new_grid[new_row_idx] = grid[r]
                new_row_idx -= 1

        # **Check for a perfect clear before updating the grid**
        perfect_clear = np.all(new_grid == "X")  # If all cells are empty, it's a perfect clear

        # Update the grid
        grid = new_grid

        # Increment total cleared lines
        lines_cleared += num_cleared

    # Award points based on the number of lines cleared (T-spins give points even without lines cleared)
    # No lines cleared:
    if num_cleared == 0 and T_spin == "Mini T-Spin":
        score_awarded = 100 # Mini non-clear T-spin
        handle_clear_text("Mini T-Spin!", has_b2b)
        # Non-clear mini T-spins don't break b2b, but don't start it either
    elif num_cleared == 0 and T_spin == "T-Spin":
        score_awarded = 400  # Non-clear T-spin
        handle_clear_text("T-Spin!", has_b2b)
        # Non-clear T-spins don't break b2b, but don't start it either

    # Single line clears:
    elif num_cleared == 1 and not perfect_clear and not T_spin:
        score_awarded = 100  # Single
        b2b = False
        handle_clear_text("Single!", has_b2b)
    elif num_cleared == 1 and not perfect_clear and T_spin == "Mini T-Spin":
        score_awarded = 200 # Mini TSS
        b2b = True
        handle_clear_text("Mini TSS!", has_b2b)
    elif num_cleared == 1 and not perfect_clear and T_spin == "T-Spin":
        score_awarded = 800 # TSS
        b2b = True
        handle_clear_text("TSS!", has_b2b)
    elif num_cleared == 1 and perfect_clear:
        score_awarded = 900 # PC Single
        b2b = False
        handle_clear_text("Perfect Clear!", has_b2b)
    # Not possible to perfect clear with either form of TSS, so no need to handle it
    
    # Double line clears:
    elif num_cleared == 2 and not perfect_clear and not T_spin:
        score_awarded = 300  # Double
        b2b = False
        handle_clear_text("Double!", has_b2b)
    elif num_cleared == 2 and not perfect_clear and T_spin == "Mini T-Spin":
        score_awarded = 400 # Mini TSD
        b2b = True
        handle_clear_text("Mini TSD!", has_b2b)
    elif num_cleared == 2 and not perfect_clear and T_spin == "T-Spin":
        score_awarded = 1200 # TSD
        b2b = True
        handle_clear_text("TSD!", has_b2b)
    elif num_cleared == 2 and perfect_clear:
        score_awarded = 1500  # PC Double 
        b2b = False
        handle_clear_text("Perfect Clear!", has_b2b)
    # Not possible to perfect clear with either form of TSD, so no need to handle it

    # Triple line clears:
    elif num_cleared == 3 and not perfect_clear and not T_spin:
        score_awarded = 500  # Triple
        b2b = False
        handle_clear_text("Triple!", has_b2b)
    elif num_cleared == 3 and not perfect_clear and T_spin:
        score_awarded = 1600 # TST
        b2b = True
        handle_clear_text("TST!", has_b2b)
    elif num_cleared == 3 and perfect_clear and not T_spin:
        score_awarded = 2300  # PC Triple
        b2b = False
        handle_clear_text("Perfect Clear!", has_b2b)
    elif num_cleared == 3 and perfect_clear and T_spin:
        score_awarded = 3400  # PC TST
        b2b = True
        unique_b2b = 800
        handle_clear_text("Perfect TST!", has_b2b)
    # No such thing as a mini TST, since all four corners are necessarily covered.

    # Quadruple line clears (Tetrises):
    elif num_cleared == 4 and not perfect_clear:
        score_awarded = 800  # Tetris
        b2b = True
        handle_clear_text("Tetris!", has_b2b)
    elif num_cleared == 4 and perfect_clear:
        score_awarded = 2800  # PC Tetris
        b2b = True
        unique_b2b = 1200
        handle_clear_text("Perfect Tetris!", has_b2b)

    # Point assignment:
    if not has_b2b: # No b2b
        score += score_awarded
    elif has_b2b and b2b and not unique_b2b: # Non-PC b2b. Must have had b2b and also not broken it with the clear.
        score += (score_awarded * 1.5)
    else: # PC b2b
        score += unique_b2b

    # Finally, assign bonus points for combo and round score to nearest whole number to avoid floating point shenanigans
    score += (50 * clear_combo)
    score = round(score)

    # Increment combo counter only *after* adding the combo score
    if num_cleared > 0:
        clear_combo += 1

def handle_movement():
    """Handles DAS and ARR for left/right movement and resets lock delay when moving."""
    global das_timer, arr_timer, gravity_lock_timer, soft_drop_lock_timer

    current_time = pygame.time.get_ticks()
    direction = 0  # Default no movement

    if move_left_pressed:
        direction = -1  # Move left
    elif move_right_pressed:
        direction = 1  # Move right

    if direction != 0:
        if das_timer == 0:
            das_timer = current_time  # Start DAS timer
            move_piece(direction, 0)  # Move once on initial press
            gravity_lock_timer = 0
            soft_drop_lock_timer = 0

        elif current_time - das_timer >= DAS:
            # DAS threshold reached, start ARR movement
            if arr_timer == 0 or current_time - arr_timer >= ARR:
                move_piece(direction, 0)  # Move at ARR interval
                gravity_lock_timer = 0
                soft_drop_lock_timer = 0
                arr_timer = current_time  # Reset ARR timer
    else:
        das_timer = 0  # Reset DAS when no key is pressed
        arr_timer = 0  # Reset ARR

def handle_soft_drop():
    """Handles DAS and ARR for soft dropping, with proper locking and lockout override.
       Awards 1 point per space a piece is soft dropped."""
    global soft_drop_das_timer, soft_drop_arr_timer, soft_drop_lock_timer, lockout_override_timer, score, qualified_for_T_spin, wall_kick_5_used

    current_time = pygame.time.get_ticks()

    if soft_drop_pressed:
        if soft_drop_das_timer == 0:
            soft_drop_das_timer = current_time  # Start DAS timer
            if move_piece(0, 1):  # Successfully moved down
                score += 1  # Award soft drop point
                qualified_for_T_spin = False  # Only disqualify if it actually moves
                wall_kick_5_used = False # Only disqualify if it actually moves
            elif is_grounded():  # If grounded, start lock timer
                if soft_drop_lock_timer == 0:
                    soft_drop_lock_timer = current_time
                if lockout_override_timer == 0:  # Start override timer if not started
                    lockout_override_timer = current_time

        elif current_time - soft_drop_das_timer >= SOFT_DROP_DAS:
            if soft_drop_arr_timer == 0 or current_time - soft_drop_arr_timer >= SOFT_DROP_ARR:
                if move_piece(0, 1):  # If successfully moved down
                    score += 1  # Award soft drop point
                    qualified_for_T_spin = False  # Only disqualify if it actually moves
                    wall_kick_5_used = False # Only disqualify if it actually moves
                elif is_grounded():
                    if soft_drop_lock_timer == 0:
                        soft_drop_lock_timer = current_time
                    if lockout_override_timer == 0:
                        lockout_override_timer = current_time
                soft_drop_arr_timer = current_time  # Reset ARR timer
    else:
        soft_drop_das_timer = 0  # Reset DAS
        soft_drop_arr_timer = 0  # Reset ARR
        soft_drop_lock_timer = 0  # Reset lock timer when released

    # **Handle Locking**: If the piece is grounded and hasn't moved for LOCK_DELAY, lock it.
    if soft_drop_lock_timer > 0 and current_time - soft_drop_lock_timer >= LOCK_DELAY and is_grounded():
        lock_piece()
        soft_drop_lock_timer = 0  # Reset lock timer after locking
        lockout_override_timer = 0  # Reset override timer after locking

    # **Force lock if lockout override timer exceeds LOCKOUT_OVERRIDE**
    if lockout_override_timer > 0 and current_time - lockout_override_timer >= LOCKOUT_OVERRIDE and is_grounded():
        lock_piece()
        lockout_override_timer = 0  # Reset override timer after locking


def handle_gravity():
    """Handles automatic piece falling at GRAVITY intervals and triggers lockout if needed."""
    global gravity_timer, gravity_lock_timer, lockout_override_timer

    current_time = pygame.time.get_ticks()

    # Apply gravity
    if current_time - gravity_timer >= GRAVITY:
        if not move_piece(0, 1):
            if is_grounded():  # Only start lock timer if grounded
                if gravity_lock_timer == 0:
                    gravity_lock_timer = current_time
                
                if lockout_override_timer == 0:  # Start override timer if not started
                    lockout_override_timer = current_time
        else:
            gravity_lock_timer = 0  # Reset lock timer if the piece moves down
            lockout_override_timer = 0  # Reset override timer on downward movement

        gravity_timer = current_time  # Reset gravity timer

    # **Lock the piece if grounded and unable to move for LOCK_DELAY**
    if gravity_lock_timer > 0 and current_time - gravity_lock_timer >= LOCK_DELAY and is_grounded():
        lock_piece()
        gravity_lock_timer = 0  # Reset lock timer after locking
        lockout_override_timer = 0  # Reset override timer after locking

    # **Lock piece if override timer exceeds LOCKOUT_OVERRIDE**
    if lockout_override_timer > 0 and current_time - lockout_override_timer >= LOCKOUT_OVERRIDE and is_grounded():
        lock_piece()
        lockout_override_timer = 0  # Reset override timer after locking

def rotate_piece(direction):
    """Rotates the current piece using SRS with wall kicks, handling I-piece separately."""
    global current_piece, current_piece_type, current_rotation, qualified_for_T_spin, wall_kick_5_used
    global gravity_lock_timer, soft_drop_lock_timer

    # Rotation states order
    rotation_states = [0, "R", 2, "L"]

    # O-piece does not rotate at all
    if current_piece_type == "O":
        gravity_lock_timer = 0  # Reset lock delay
        soft_drop_lock_timer = 0
        return

    # Determine the new rotation state
    if direction == "R":  # Clockwise
        new_rotation = rotation_states[(rotation_states.index(current_rotation) + 1) % 4]
    else:  # Counter-clockwise
        new_rotation = rotation_states[(rotation_states.index(current_rotation) - 1) % 4]

    # Special case for I-piece (different pivot point logic)
    if current_piece_type == "I":
        rotate_I_piece(direction, new_rotation)
        return

    # Find pivot block index based on piece type
    pivot_index = PIECE_PIVOTS[current_piece_type]
    pivot_r, pivot_c = current_piece[pivot_index]  # Get pivot position

    # Rotate each block around the pivot
    if direction == "R":  # Clockwise 90°
        new_piece = [(pivot_r + (c - pivot_c), pivot_c - (r - pivot_r)) for r, c in current_piece]
    else:  # Counter-clockwise 90°
        new_piece = [(pivot_r - (c - pivot_c), pivot_c + (r - pivot_r)) for r, c in current_piece]

    # Choose correct SRS wall kick data
    kick_data = SRS_WALL_KICKS
    kick_tests = kick_data.get((current_rotation, new_rotation), [(0, 0)])

    wall_kick_5_used = False # Reset to false since a rotation is being attempted.

    # Try applying each kick (track index for final kick detection)
    for i, (kick_x, kick_y) in enumerate(kick_tests):
        kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
        if is_valid_position(kicked_piece):  # If no collision, apply rotation
            current_piece = kicked_piece
            current_rotation = new_rotation
            qualified_for_T_spin = True
            wall_kick_5_used = (i == len(kick_tests) - 1) # Set wall_kick_5_used to True only if it's the final wall kick attempt
            gravity_lock_timer = 0  # Reset lock delay
            soft_drop_lock_timer = 0
            return True  # Rotation succeeded

    return False  # Rotation failed, piece stays the same


def rotate_I_piece(direction, new_rotation):
    """Handles I-piece rotation using correct pivot alignment in SRS."""
    global current_piece, current_rotation, qualified_for_T_spin
    global gravity_lock_timer, soft_drop_lock_timer
    
    if current_rotation == 0:  # Horizontal (Facing Upward)
        # Extract mino positions sorted by column to correctly identify mino indexes
        mino_positions = sorted(current_piece, key=lambda pos: pos[1])  # Sort by column

        if direction == "L":  # Left Rotation
            pivot_col = mino_positions[1][1]  # Mino 1's column (Pivot)
            pivot_row = mino_positions[1][0]  # Mino 1's row
            new_piece = [
                (pivot_row + 2, pivot_col),  # Mino 0 (Lowest)
                (pivot_row + 1, pivot_col),  # Mino 1 (Below)
                (pivot_row, pivot_col),      # Mino 2 (Pivot)
                (pivot_row - 1, pivot_col)   # Mino 3 (Above)
            ]

        else:  # Right Rotation
            pivot_col = mino_positions[2][1]  # Mino 2's column (Pivot)
            pivot_row = mino_positions[2][0]  # Mino 2's row
            new_piece = [
                (pivot_row - 1, pivot_col),  # Mino 0 (Above)
                (pivot_row, pivot_col),      # Mino 1 (Pivot)
                (pivot_row + 1, pivot_col),  # Mino 2 (Below)
                (pivot_row + 2, pivot_col)   # Mino 3 (Lowest)
            ]

        # Apply SRS wall kicks
        kick_tests = SRS_WALL_KICKS_I.get((current_rotation, new_rotation), [(0, 0)])
        for kick_x, kick_y in kick_tests:
            kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
            if is_valid_position(kicked_piece):
                current_piece = kicked_piece
                current_rotation = new_rotation
                gravity_lock_timer = 0  # Reset lock delay
                soft_drop_lock_timer = 0
                return True  # Rotation succeeded
            
        return False  # Rotation failed, piece stays the same

    elif current_rotation == "R":  # Vertical "R" Position
            # Extract mino positions sorted by row to correctly identify mino indexes
            mino_positions = sorted(current_piece, key=lambda pos: pos[0])  # Sort by row

            if direction == "R":  # Right Rotation (Aligns Horizontally)
                pivot_row = mino_positions[2][0]  # Mino 2's row (Pivot)
                pivot_col = mino_positions[2][1]  # Mino 2's column (Pivot)
                new_piece = [
                    (pivot_row, pivot_col - 2),  # Mino 3 (Leftmost)
                    (pivot_row, pivot_col - 1),  # Mino 2 (Left)
                    (pivot_row, pivot_col),      # Mino 1 (Pivot)
                    (pivot_row, pivot_col + 1)   # Mino 0 (Rightmost)
                ]

            else:  # Left Rotation (Aligns Horizontally)
                pivot_row = mino_positions[1][0]  # Mino 1's row (Pivot)
                pivot_col = mino_positions[1][1]  # Mino 1's column (Pivot)
                new_piece = [
                    (pivot_row, pivot_col - 2),  # Mino 0 (Leftmost)
                    (pivot_row, pivot_col - 1),  # Mino 1 (Left)
                    (pivot_row, pivot_col),      # Mino 2 (Pivot)
                    (pivot_row, pivot_col + 1)   # Mino 3 (Rightmost)
                ]

            # Apply SRS wall kicks
            kick_tests = SRS_WALL_KICKS_I.get((current_rotation, new_rotation), [(0, 0)])
            for kick_x, kick_y in kick_tests:
                kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
                if is_valid_position(kicked_piece):
                    current_piece = kicked_piece
                    current_rotation = new_rotation
                    gravity_lock_timer = 0  # Reset lock delay
                    soft_drop_lock_timer = 0
                    return True  # Rotation succeeded

            return False  # Rotation failed, piece stays the same
    
    elif current_rotation == 2:  # Horizontal "Upside-Down"
        # Extract mino positions sorted by column to correctly identify mino indexes
        mino_positions = sorted(current_piece, key=lambda pos: pos[1])  # Sort by column
        mino_positions.reverse()  # Ensure order matches expected mino indices in state 2

        if direction == "L":  # Left Rotation (Aligns Vertically)
            pivot_row = mino_positions[1][0]  # Mino 1's row (Pivot)
            pivot_col = mino_positions[1][1]  # Mino 1's column (Pivot)
            new_piece = [
                (pivot_row - 2, pivot_col),  # Mino 0 (Topmost)
                (pivot_row - 1, pivot_col),  # Mino 1 (Above Pivot)
                (pivot_row, pivot_col),      # Mino 2 (Pivot)
                (pivot_row + 1, pivot_col)   # Mino 3 (Below Pivot)
            ]

        else:  # Right Rotation (Aligns Vertically)
            pivot_row = mino_positions[2][0]  # Mino 2's row (Pivot)
            pivot_col = mino_positions[2][1]  # Mino 2's column (Pivot)
            new_piece = [
                (pivot_row - 2, pivot_col),  # Mino 3 (Topmost)
                (pivot_row - 1, pivot_col),  # Mino 2 (Above Pivot)
                (pivot_row, pivot_col),      # Mino 1 (Pivot)
                (pivot_row + 1, pivot_col)   # Mino 0 (Lowest)
            ]

        # Apply SRS wall kicks
        kick_tests = SRS_WALL_KICKS_I.get((current_rotation, new_rotation), [(0, 0)])
        for kick_x, kick_y in kick_tests:
            kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
            if is_valid_position(kicked_piece):
                current_piece = kicked_piece
                current_rotation = new_rotation
                gravity_lock_timer = 0  # Reset lock delay
                soft_drop_lock_timer = 0
                return True  # Rotation succeeded

        return False  # Rotation failed, piece stays the same

    elif current_rotation == "L":  # Vertical "L" Position
        # Extract mino positions sorted by row to correctly identify mino indexes
        mino_positions = sorted(current_piece, key=lambda pos: pos[0])  # Sort by row
        mino_positions.reverse()  # Ensure order matches expected mino indices in state "L"

        if direction == "L":  # Left Rotation (Aligns Horizontally)
            pivot_row = mino_positions[1][0]  # Mino 1's row (Pivot)
            pivot_col = mino_positions[1][1]  # Mino 1's column (Pivot)
            new_piece = [
                (pivot_row, pivot_col - 1),  # Mino 3 (Leftmost)
                (pivot_row, pivot_col),      # Mino 2 (Pivot)
                (pivot_row, pivot_col + 1),  # Mino 1 (Right)
                (pivot_row, pivot_col + 2)   # Mino 0 (Rightmost)
            ]

        else:  # Right Rotation (Aligns Horizontally)
            pivot_row = mino_positions[2][0]  # Mino 2's row (Pivot)
            pivot_col = mino_positions[2][1]  # Mino 2's column (Pivot)
            new_piece = [
                (pivot_row, pivot_col - 1),  # Mino 0 (Leftmost)
                (pivot_row, pivot_col),      # Mino 1 (Pivot)
                (pivot_row, pivot_col + 1),  # Mino 2 (Right)
                (pivot_row, pivot_col + 2)   # Mino 3 (Rightmost)
            ]

        # Apply SRS wall kicks
        kick_tests = SRS_WALL_KICKS_I.get((current_rotation, new_rotation), [(0, 0)])
        for kick_x, kick_y in kick_tests:
            kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
            if is_valid_position(kicked_piece):
                current_piece = kicked_piece
                current_rotation = new_rotation
                gravity_lock_timer = 0  # Reset lock delay
                soft_drop_lock_timer = 0
                return True  # Rotation succeeded

        return False  # Rotation failed, piece stays the same

def get_ghost_piece():
    """Returns the lowest valid position for the current piece (ghost piece)."""
    ghost_piece = list(current_piece)  # Copy the current piece

    # Move the ghost piece down until it collides
    while is_valid_position([(r + 1, c) for r, c in ghost_piece]):
        ghost_piece = [(r + 1, c) for r, c in ghost_piece]

    return ghost_piece

def draw_hold_box():
    """Draws the hold box aligned with the top half-cell margin, with proper sizing."""
    width, height = screen.get_size()

    # Sets color of text to red if hold is currently locked.
    if hold_used:
        hold_text_color = (255, 150, 150)
    else:
        hold_text_color = (255, 255, 255)

    # Calculate square size dynamically
    square_size = min(width // COLS, height // (VISIBLE_ROWS + 1))  # Adjust size dynamically
    grid_width = square_size * COLS
    grid_height = square_size * (VISIBLE_ROWS + 1)  # Include margins

    # Centering the grid in the window
    margin_x = (width - grid_width) // 2
    margin_y = (height - grid_height) // 2

    # Hold box position
    hold_box_width = square_size * 5  
    hold_box_height = square_size * 4  
    hold_box_x = margin_x - hold_box_width - 10  
    hold_box_y = margin_y + square_size * 0.5  

    # Draw hold box
    pygame.draw.rect(screen, GRID_BACKGROUND, (hold_box_x, hold_box_y, hold_box_width, hold_box_height))
    pygame.draw.rect(screen, GRID_LINES, (hold_box_x, hold_box_y, hold_box_width, hold_box_height), 2)

    # Draw the held piece
    if held_piece:
        piece_shape = TETRIMINO_SHAPES[held_piece][0]
        piece_color = TETRIMINO_COLORS[held_piece]

        min_x = min(c for r, c in piece_shape)
        min_y = min(r for r, c in piece_shape)
        max_x = max(c for r, c in piece_shape)
        max_y = max(r for r, c in piece_shape)

        piece_width = (max_x - min_x + 1) * square_size
        piece_height = (max_y - min_y + 1) * square_size

        # Center the piece in the hold box
        offset_x = hold_box_x + (hold_box_width - piece_width) // 2
        offset_y = hold_box_y + (hold_box_height - piece_height) // 2

        for r, c in piece_shape:
            piece_rect = pygame.Rect(
                offset_x + (c - min_x) * square_size,
                offset_y + (r - min_y) * square_size,
                square_size, square_size
            )
            pygame.draw.rect(screen, piece_color, piece_rect)
            pygame.draw.rect(screen, PIECE_OUTLINE, piece_rect, 1)

    # **Ensure the "HOLD" text is the same distance from the box as "NEXT" text**
    font = pygame.font.Font(None, 40)
    text = font.render("HOLD", True, hold_text_color)

    # **Align text exactly one grid square below the hold box (same as NEXT)**
    text_y = hold_box_y + hold_box_height + square_size  # Matches `draw_next_box()`
    text_rect = text.get_rect(center=(hold_box_x + hold_box_width // 2, text_y))
    screen.blit(text, text_rect)

def draw_next_box():
    """Draws the next piece box aligned with the top half-cell margin, mirrored on the right side,
       and positions the 'NEXT' text correctly between the two next queues with a 2-grid-square margin.
       Adds a horizontal separator if `bag_piece_count == 7` or `bag_piece_count == 0`."""
    global bag_piece_count

    width, height = screen.get_size()

    # Calculate square size dynamically
    square_size = min(width // COLS, height // (VISIBLE_ROWS + 1))  # +1 for margin
    grid_width = square_size * COLS
    grid_height = square_size * (VISIBLE_ROWS + 1)  # Include margin

    # Centering grid in the window
    margin_x = (width - grid_width) // 2
    margin_y = (height - grid_height) // 2

    # Next box position: mirrored to the right
    next_box_width = square_size * 5  # Same width as hold box
    next_box_height = square_size * 4  # Same height as hold box
    next_box_x = margin_x + grid_width + 10  # Right side of grid
    next_box_y = margin_y + square_size * 0.5  # Align with top half-cell margin

    # Draw next box background
    pygame.draw.rect(screen, GRID_BACKGROUND, (next_box_x, next_box_y, next_box_width, next_box_height))
    pygame.draw.rect(screen, GRID_LINES, (next_box_x, next_box_y, next_box_width, next_box_height), 2)

    # **Draw the next piece**
    if next_queue:
        piece_type = next_queue[0]  # Extract only the piece type
        piece_shape = TETRIMINO_SHAPES[piece_type][0]
        piece_color = TETRIMINO_COLORS[piece_type]

        # Find min/max positions of the piece
        min_x = min(c for r, c in piece_shape)
        min_y = min(r for r, c in piece_shape)
        max_x = max(c for r, c in piece_shape)
        max_y = max(r for r, c in piece_shape)

        piece_width = (max_x - min_x + 1) * square_size
        piece_height = (max_y - min_y + 1) * square_size

        # Center the piece in the next box
        offset_x = next_box_x + (next_box_width - piece_width) // 2
        offset_y = next_box_y + (next_box_height - piece_height) // 2

        for r, c in piece_shape:
            piece_rect = pygame.Rect(
                offset_x + (c - min_x) * square_size,
                offset_y + (r - min_y) * square_size,
                square_size, square_size
            )
            pygame.draw.rect(screen, piece_color, piece_rect)
            pygame.draw.rect(screen, PIECE_OUTLINE, piece_rect, 1)

    # **Draw horizontal separator line if `bag_piece_count == 7` or `bag_piece_count == 0`**
    if bag_piece_count == 6:
        separator_y = next_box_y + next_box_height - (square_size * 0.35)  # 0.35 cells above bottom edge
        pygame.draw.line(screen, OUTSIDE_BACKGROUND, 
                         (next_box_x + 2, separator_y), 
                         (next_box_x + next_box_width - 2, separator_y), 2)

    elif bag_piece_count == 7:
        separator_y = next_box_y + (square_size * 0.35)  # 0.35 cells below top edge
        pygame.draw.line(screen, OUTSIDE_BACKGROUND, 
                         (next_box_x + 2, separator_y), 
                         (next_box_x + next_box_width - 2, separator_y), 2)

    # **Ensure "NEXT" text is positioned exactly in the middle of the 2-square gap**
    font = pygame.font.Font(None, 40)
    text = font.render("NEXT", True, (255, 255, 255))
    
    # **Position the text exactly one grid square below the next box**
    text_y = next_box_y + next_box_height + square_size  # One square below next box
    text_rect = text.get_rect(center=(next_box_x + next_box_width // 2, text_y))
    screen.blit(text, text_rect)

    # **Return required values for extended queue alignment**
    return next_box_y, next_box_height

def draw_extended_next_queue(next_box_y, next_box_height):
    """Draws a box below the next piece box displaying the next four upcoming pieces,
       ensuring it starts two grid squares below the next box and ends half a square from the bottom.
       Draws a horizontal separator line based on `bag_piece_count` conditions."""
    global bag_piece_count

    width, height = screen.get_size()

    # Calculate square size dynamically
    square_size = min(width // COLS, height // (VISIBLE_ROWS + 1))
    grid_width = square_size * COLS
    grid_height = square_size * (VISIBLE_ROWS + 1)

    # Centering the grid
    margin_x = (width - grid_width) // 2

    # **Position the extended queue exactly 2 grid squares below the next box**
    extended_box_x = margin_x + grid_width + 10  # Right side of grid
    extended_box_y = next_box_y + next_box_height + (square_size * 2)

    # **Adjust the height to align the bottom with half a square from the bottom of the screen**
    margin_y = (height - GRID_HEIGHT) // 2  # Center the grid vertically
    extended_box_height = GRID_HEIGHT - (next_box_y - margin_y + next_box_height) - (square_size * 1.1)


    # Extended queue width remains the same as the next box
    extended_box_width = square_size * 5  

    # Draw extended queue background
    pygame.draw.rect(screen, GRID_BACKGROUND, (extended_box_x, extended_box_y, extended_box_width, extended_box_height))
    pygame.draw.rect(screen, GRID_LINES, (extended_box_x, extended_box_y, extended_box_width, extended_box_height), 2)

    # **Determine vertical spacing for pieces**
    num_pieces = min(4, len(next_queue) - 1)  # Ensure up to 4 pieces are displayed
    if num_pieces > 0:
        piece_spacing = extended_box_height / num_pieces  # Distribute pieces evenly

    # **Determine where to place the separator line**
    separator_index = None
    extra_separator_position = None  # Used for bag_piece_count == 6 or 2

    if bag_piece_count == 6:
        extra_separator_position = "top"  # Line near the top edge
    elif bag_piece_count == 5:
        separator_index = 0  # Line between first and second piece
    elif bag_piece_count == 4:
        separator_index = 1  # Line between second and third piece
    elif bag_piece_count == 3:
        separator_index = 2  # Line between third and fourth piece
    elif bag_piece_count == 2:
        extra_separator_position = "bottom"  # Line near the bottom edge

    # **Draw next four pieces in order**
    for i, piece_type in enumerate(next_queue[1:num_pieces+1]):  # Skip first element (it's in next box)
        piece_shape = TETRIMINO_SHAPES[piece_type][0]
        piece_color = TETRIMINO_COLORS[piece_type]

        # Find min/max positions of the piece
        min_x = min(c for r, c in piece_shape)
        min_y = min(r for r, c in piece_shape)
        max_x = max(c for r, c in piece_shape)
        max_y = max(r for r, c in piece_shape)

        piece_width = (max_x - min_x + 1) * square_size
        piece_height = (max_y - min_y + 1) * square_size

        # Positioning: Evenly distribute pieces vertically
        offset_x = extended_box_x + (extended_box_width - piece_width) // 2
        offset_y = extended_box_y + (i * piece_spacing) + (piece_spacing - piece_height) / 2  # Center each piece

        # **Draw the piece**
        for r, c in piece_shape:
            piece_rect = pygame.Rect(
                offset_x + (c - min_x) * square_size,
                offset_y + (r - min_y) * square_size,
                square_size, square_size
            )
            pygame.draw.rect(screen, piece_color, piece_rect)
            pygame.draw.rect(screen, PIECE_OUTLINE, piece_rect, 1)

        # **Draw separator line in the correct position**
        if separator_index is not None and i == separator_index:
            separator_y = offset_y + piece_height + (piece_spacing - piece_height) / 2  # Center between pieces
            pygame.draw.line(screen, OUTSIDE_BACKGROUND, 
                             (extended_box_x + 2, separator_y), 
                             (extended_box_x + extended_box_width - 2, separator_y), 2)

    # **Extra separators for bag_piece_count == 6 or 2**
    if extra_separator_position == "top":
        separator_y = extended_box_y + (square_size * 0.35)  # 0.35 grid cells from the top
        pygame.draw.line(screen, OUTSIDE_BACKGROUND, 
                         (extended_box_x + 2, separator_y), 
                         (extended_box_x + extended_box_width - 2, separator_y), 2)

    elif extra_separator_position == "bottom":
        separator_y = extended_box_y + extended_box_height - (square_size * 0.35)  # 0.35 grid cells from the bottom
        pygame.draw.line(screen, OUTSIDE_BACKGROUND, 
                         (extended_box_x + 2, separator_y), 
                         (extended_box_x + extended_box_width - 2, separator_y), 2)

def draw_stats_box():
    """Draws a single unified box containing TIME, SCORE, LINES, PIECES, and an additional clear text message."""
    global score, lines_cleared, total_pieces_placed, start_time, clear_text, clear_text_color

    width, height = screen.get_size()

    # Calculate square size dynamically
    square_size = min(width // COLS, height // (VISIBLE_ROWS + 1))
    grid_width = square_size * COLS
    grid_height = square_size * (VISIBLE_ROWS + 1)

    # Centering the grid
    margin_x = (width - grid_width) // 2
    margin_y = (height - grid_height) // 2

    # **Base stats box dimensions**
    extended_box_bottom = margin_y + GRID_HEIGHT
    stats_box_y = margin_y + (square_size * 6.5)  # Start below hold box
    stats_box_x = margin_x - (square_size * 5) - 10  # Left side of grid
    stats_box_width = square_size * 5  # Matches extended next queue width
    stats_box_height = extended_box_bottom - stats_box_y  # Default bottom alignment

    # **Calculate additional height for clear_text**
    font = pygame.font.Font(None, 40)
    clear_font = pygame.font.Font(None, 30)
    clear_text_render = clear_font.render(clear_text, True, clear_text_color)
    clear_text_height = clear_text_render.get_height() + (square_size * 0.5)  # Extra padding

    # **Extend stats box height for clear_text + one extra grid square**
    stats_box_height += clear_text_height + square_size  # <--- Extra square added here

    # **Draw extended stats box**
    pygame.draw.rect(screen, GRID_BACKGROUND, (stats_box_x, stats_box_y, stats_box_width, stats_box_height))
    pygame.draw.rect(screen, GRID_LINES, (stats_box_x, stats_box_y, stats_box_width, stats_box_height), 2)

    # **Calculate elapsed time in MM:SS.M format**
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    milliseconds = int((elapsed_time % 1) * 10)  # Correctly scale to 0-9 range

    # Format as MM:SS.M (single-digit milliseconds)
    time_display = f"{minutes:02}:{seconds:02}.{milliseconds}"

    # Divide the box into evenly spaced sections
    labels = ["TIME:", "SCORE:", "LINES:", "PIECES:"]
    values = [time_display, score, lines_cleared, total_pieces_placed]
    section_height = stats_box_height / 5  # Now divided into five sections (including clear_text space)

    for i, (label, value) in enumerate(zip(labels, values)):
        section_y = stats_box_y + (i * section_height)

        # Render text
        label_render = font.render(label, True, (255, 255, 255))
        value_render = font.render(str(value), True, (255, 255, 255))

        # Center text within its section
        label_rect = label_render.get_rect(center=(stats_box_x + stats_box_width // 2, section_y + square_size * 0.75))
        value_rect = value_render.get_rect(center=(stats_box_x + stats_box_width // 2, section_y + square_size * 2))

        # Draw text
        screen.blit(label_render, label_rect)
        screen.blit(value_render, value_rect)

    # **Draw horizontal line below "PIECES"**
    line_y = stats_box_y + (section_height * 4.1)  # Positioned just below "PIECES"
    pygame.draw.line(screen, (255, 255, 255), (stats_box_x + 5, line_y), (stats_box_x + stats_box_width - 5, line_y), 2)

    # **Render and draw clear_text below the line**
    clear_text_rect = clear_text_render.get_rect(center=(stats_box_x + stats_box_width // 2, line_y + square_size * 1.5))
    screen.blit(clear_text_render, clear_text_rect)







def draw_grid():
    """Draws only the visible part of the Tetris grid, with a half-cell-high margin at the top and bottom,
       and colors those margins with OUTSIDE_BACKGROUND."""
    width, height = screen.get_size()

    # Calculate square size dynamically
    square_size = min(width // COLS, height // (VISIBLE_ROWS + 1))  # +1 ensures space for half-cell margins
    grid_width = square_size * COLS
    grid_height = square_size * (VISIBLE_ROWS + 1)  # Expanded to include margins

    # Center the grid in the window
    margin_x = (width - grid_width) // 2
    margin_y = (height - grid_height) // 2

    # Fill entire screen with OUTSIDE_BACKGROUND
    screen.fill(OUTSIDE_BACKGROUND)

    # Draw extra half-cell margins at the top and bottom
    top_margin_rect = pygame.Rect(margin_x, margin_y, grid_width, square_size * 0.5)
    bottom_margin_rect = pygame.Rect(margin_x, margin_y + grid_height - square_size * 0.5, grid_width, square_size * 0.5)

    pygame.draw.rect(screen, OUTSIDE_BACKGROUND, top_margin_rect)
    pygame.draw.rect(screen, OUTSIDE_BACKGROUND, bottom_margin_rect)

    # Draw grid background (only inside the main play area)
    pygame.draw.rect(screen, GRID_BACKGROUND, (margin_x, margin_y + square_size * 0.5, grid_width, grid_height - square_size))

    # Get ghost piece position
    ghost_piece = get_ghost_piece()
    ghost_color = TETRIMINO_COLORS[current_piece_type]

    # Shift row rendering by exactly 3.5 rows to create the half-cell margins
    for row in range(4, ROWS):  # Start from row 4 (hide first 4 rows)
        for col in range(COLS):
            cell_value = grid[row, col]
            color = TETRIMINO_COLORS[cell_value] if cell_value in TETRIMINO_COLORS else GRID_BACKGROUND

            # Correctly align each cell to create a half-cell margin
            adjusted_row = row - 3.5  # Shifts everything down by half a cell
            cell_rect = pygame.Rect(
                margin_x + col * square_size,
                margin_y + adjusted_row * square_size,
                square_size,
                square_size
            )

            pygame.draw.rect(screen, color, cell_rect)
            if cell_value != "X":
                pygame.draw.rect(screen, PIECE_OUTLINE, cell_rect, 1)
            else:
                pygame.draw.rect(screen, GRID_LINES, cell_rect, 1)

    # Draw ghost piece (hollow outline)
    for r, c in ghost_piece:
        if 4 <= r < ROWS:  # Only draw ghost if in visible area
            adjusted_row = r - 3.5
            ghost_rect = pygame.Rect(
                margin_x + c * square_size,
                margin_y + adjusted_row * square_size,
                square_size,
                square_size
            )
            pygame.draw.rect(screen, ghost_color, ghost_rect, 2)

    # Draw current falling piece
    for r, c in current_piece:
        if 4 <= r < ROWS:  # Only draw piece if in visible area
            adjusted_row = r - 3.5
            cell_rect = pygame.Rect(
                margin_x + c * square_size,
                margin_y + adjusted_row * square_size,
                square_size,
                square_size
            )
            pygame.draw.rect(screen, TETRIMINO_COLORS[current_piece_type], cell_rect)
            pygame.draw.rect(screen, PIECE_OUTLINE, cell_rect, 1)

    draw_hold_box()
    draw_next_box()
    draw_stats_box()

    next_box_y, next_box_height = draw_next_box()
    draw_extended_next_queue(next_box_y, next_box_height)
    pygame.display.flip()

def main():
    global move_left_pressed, move_right_pressed, soft_drop_pressed
    running = True

    while running:
        if game_over:
            print("Game Over!")
            running = False

        handle_movement()  # Handle left/right DAS & ARR
        handle_soft_drop()  # Handle soft drop DAS & ARR
        handle_gravity() # Handle gravity

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    move_left_pressed = True
                elif event.key == pygame.K_d:
                    move_right_pressed = True
                elif event.key == pygame.K_s:
                    soft_drop_pressed = True
                elif event.key == pygame.K_w:
                    hard_drop()  # Hard drop immediately
                elif event.key == pygame.K_LEFT:  # Counter-clockwise rotation
                    rotate_piece("L")
                elif event.key == pygame.K_RIGHT:  # Clockwise rotation
                    rotate_piece("R")
                elif event.key == pygame.K_LSHIFT:
                    hold_piece()  # Trigger hold mechanic

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_a:
                    move_left_pressed = False
                elif event.key == pygame.K_d:
                    move_right_pressed = False
                elif event.key == pygame.K_s:
                    soft_drop_pressed = False

        draw_grid()
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()