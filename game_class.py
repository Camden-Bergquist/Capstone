import pygame
import numpy as np
import random
import time
import threading

class TetrisGame:
    def __init__(self, render = True, game_mode = None):
    # Constants
        self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT = 800, 700
        self.COLS, self.ROWS = 10, 24  # Play matrix dimensions
        self.VISIBLE_ROWS = 20 # Play matrix rows visible to the player
        self.GRID_WIDTH, self.GRID_HEIGHT = 300, 600
        self.LOCK_DELAY = 250  # Lock delay in milliseconds
        self.DAS = 150  # Delayed Auto-Shift in milliseconds
        self.ARR = 75  # Auto Repeat Rate in milliseconds
        self.SOFT_DROP_DAS = 75  # Delay before repeated soft drops start (in milliseconds)
        self.SOFT_DROP_ARR = 35  # Time between additional soft drops when held (in milliseconds)
        self.GRAVITY = 100  # Default fall speed in milliseconds (1000ms = 1 second per row)
        self.LOCKOUT_OVERRIDE = 2000  # Time in milliseconds before forced lockout
        self.RENDER = render # Boolean value for whether or not to render the game.
        self.TICK_BASED = False # Gets set to True if tick() is called.

        # Tracking variables
        self.move_left_pressed = False
        self.move_right_pressed = False
        self.soft_drop_pressed = False
        self.das_timer = 0
        self.arr_timer = 0
        self.soft_drop_das_timer = 0
        self.soft_drop_arr_timer = 0
        self.soft_drop_lock_timer = 0  # Track time before locking after soft drop
        self.gravity_timer = 0  # Tracks last gravity update
        self.gravity_lock_timer = 0  # Tracks when the piece should lock due to gravity
        self.lockout_override_timer = 0  # Track time for lockout override
        self.held_piece = None  # Stores the currently held piece type
        self.hold_used = False  # Lockout to prevent indefinite swapping
        self.primary_bag = []    # The active bag for spawning pieces
        self.secondary_bag = []  # The backup bag (future pieces)
        self.next_queue = []     # Holds the next five pieces to display
        self.bag_piece_count = 0  # Tracks how many pieces have spawned
        self.score = 0  # Track player's self.score
        self.lines_cleared = 0  # Track number of lines cleared
        self.start_time = None  # Track game start time 
        self.total_pieces_placed = 0  # Track the number of pieces placed
        self.b2b = False # Track whether or not the player currently has back-to-back status
        self.clear_combo = 0 # Track line clear combos for scoring.
        self.qualified_for_T_spin = False  # Tracks if the current piece is eligible for a T-spin
        self.wall_kick_5_used = False # Tracks if the wall-kick used is the fifth and final kick, which results in an auto T-spin detection
        self.clear_text = "" # Displays the type of clear most recently achieved (e.g., "Double!")
        self.clear_text_color = (255, 255, 255) # Sets the base color for the clear text to white, to be changed to gold if a self.b2b was present.
        self.clear_text_timer = None # Track clear text timer.
        self.game_mode = game_mode # Tracks gamemode.
        self.game_over_condition = "Top Out!" # Tracks game over condition.
        self.advanced_controls = False # Used to modify ARR and DAS to Camden-prefered values.
        self.current_piece_type = None
        self.current_piece = None
        self.current_rotation = None
        self.lock_reward = 0 # Counts the number of occupied cells in the row each mino of a piece occupies, and then returns it for AI reward.
        self.flat_placement = False # Set to true if none of the spaces immediately under a piece are empty. For AI reward.
        self.height_gap = False # Set to true if the bottom-most space a piece occupies is 8 or more spaces above the next-highest filled grid space.

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GRAY = (200, 200, 200)
        self.DARK_GRAY = (100, 100, 100)
        self.OUTSIDE_BACKGROUND = (90, 90, 90)
        self.GRID_LINES = (60, 60, 60)

        # Tetrimino colors
        self.TETRIMINO_COLORS = {
            "X": self.BLACK,
            "Z": (255, 64, 32),
            "S": (64, 208, 64),
            "L": (255, 128, 32),
            "J": (64, 128, 255),
            "O": (255, 224, 32),
            "T": (160, 64, 240),
            "I": (0, 208, 255)
        }

        # Shape definitions with SRS spawn orientations
        self.TETRIMINO_SHAPES = {
            "Z": [[(0, -1), (0, 0), (1, 0), (1, 1)]],
            "S": [[(1, -1), (1, 0), (0, 0), (0, 1)]],
            "L": [[(1, -1), (1, 0), (1, 1), (0, 1)]],
            "J": [[(1, -1), (1, 0), (1, 1), (0, -1)]],
            "O": [[(0, 0), (0, 1), (1, 0), (1, 1)]],
            "T": [[(1, -1), (1, 0), (1, 1), (0, 0)]],
            "I": [[(0, 0), (0, 1), (0, 2), (0, 3)]]
        }

        self.PIECE_PIVOTS = {
            "L": 1,  # Middle of three-segment row
            "J": 1,  # Middle of three-segment row
            "T": 1,  # Middle of three-segment row
            "S": 1,  # Lower of vertical two-stack
            "Z": 2,  # Lower of vertical two-stack
            "I": 1,  # Center horizontally, bottom-most square vertically
            "O": 0  # True center, does not move
        }

        # SRS Wall Kick Data (J, L, S, T, Z)
        self.SRS_WALL_KICKS = {
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
        self.SRS_WALL_KICKS_I = {
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
        self.grid = np.full((self.ROWS, self.COLS), "X")

        # Initialize game state
        self.current_piece_type, self.current_piece, self.current_rotation = self.spawn_piece()
        self.game_over = False

        self.screen = None
        # Initialize pygame if render is set to True
        if render:
            pygame.init()
            self.screen = pygame.display.set_mode((self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT), pygame.RESIZABLE)
            pygame.display.set_caption("Tetris")

    def is_valid_position(self, piece):
        """Check if a piece's position is valid (inside bounds and not colliding)."""
        for r, c in piece:
            if c < 0 or c >= self.COLS or r >= self.ROWS:  # Out of bounds
                return False
            if r >= 0 and self.grid[r, c] != "X":  # Collision
                return False
        return True

    def lock_piece(self):
        """Locks the current piece into the self.grid and spawns a new piece."""

        # **Lock the piece into the self.grid**
        for r, c in self.current_piece:
            if r >= 0:
                self.grid[r, c] = self.current_piece_type  

        # Increment or decrement total pieces placed
        if self.game_mode == "Blitz":
            self.total_pieces_placed -= 1
        else:
            self.total_pieces_placed += 1

        # Identify occupied rows
        occupied_rows = set()
        for r, _ in self.current_piece:
            if r >= 0:
                occupied_rows.add(r)
        
        # Update lock reward
        self.lock_reward = 0
        for row in occupied_rows:
            self.lock_reward += np.count_nonzero(self.grid[row] != "X")

        # Debug print for lock reward
        # print(f"Rows occupied: {occupied_rows}. Lock Reward Factor: {self.lock_reward}.")

        self.flat_placement = False # Set to False for new piece.
        flat = True # Helper necessary for loop logic; not redundant for once.

        for r, c in self.current_piece:
            below_r = r + 1
            if below_r >= self.ROWS:
                continue  # On floor = flat
            if self.grid[below_r, c] == "X":
                flat = False
                break  # Not flat if any cell is unsupported
        self.flat_placement = flat

        # Check for height gap 
        self.height_gap = False  # Default to False

        # Get the lowest row the current piece occupies
        piece_lowest_row = max(r for r, _ in self.current_piece if r >= 0)

        # Get the lowest occupied row in the grid
        occupied_cells = np.argwhere(self.grid != "X")
        if len(occupied_cells) > 0:
            grid_lowest_row = max(r for r, _ in occupied_cells)

            # Debug Print
            # print(f"Grid Low: {grid_lowest_row}. Piece Low: {piece_lowest_row}. Total Gap: {grid_lowest_row - piece_lowest_row}")

            # Compare
            if grid_lowest_row - piece_lowest_row >= 8:
                self.height_gap = True
        else:
            # If the grid is entirely empty below the piece, treat as no gap
            self.height_gap = False


        # **Check for and clear full lines**
        self.clear_lines()

        # **Spawn a new piece from the updated queue**
        self.current_piece_type, self.current_piece, self.current_rotation = self.spawn_piece()

        # Increment piece counter.
        self.total_pieces_placed += 1

        # **Reset hold usage (holding is allowed again)**
        self.hold_used = False

        # **Check if the new piece is already colliding (Game Over)**
        if not self.is_valid_position(self.current_piece):
            self.game_over = True  # Game over if the new piece cannot be placed

        # **Ensure the display updates immediately**
        if self.RENDER:
            self.draw_grid()
            pygame.display.flip()

        # Handle game over if AI is out of pieces to place
        if self.total_pieces_placed <= 0:
            self.game_over = True


    def move_piece(self, dx, dy):
        """Attempt to move the current piece by (dx, dy)."""

        new_position = [(r + dy, c + dx) for r, c in self.current_piece]
        
        if self.is_valid_position(new_position):
            self.current_piece[:] = new_position

            # Disqualify T-spin if the move was a successful left/right shift
            if dx != 0:
                self.qualified_for_T_spin = False
                self.wall_kick_5_used = False

            self.last_move_success = True
            return True

        self.last_move_success = False
        return False


    def hard_drop(self):
        """Instantly moves the piece downward until it collides, then locks.
        Awards 2 points for each space the piece moves down."""

        drop_distance = 0  # Track how many spaces the piece moves

        while self.move_piece(0, 1):  # Move down until collision
            drop_distance += 1  # Count the movement steps

        # Only disqualify T-spin if the piece actually moved downward
        if drop_distance > 0:
            self.qualified_for_T_spin = False 
            self.wall_kick_5_used = False # Only disqualify if it actually moves

        # Award hard drop points (2 points per space moved)
        self.score += drop_distance * 2

        # Lock immediately after reaching the lowest position
        self.lock_piece()

    # Doesn't look like this is being called ever. Remove?
    def soft_drop_or_lock(self):
        """Moves the piece down one step. If it can't move, it locks after 0.5s."""
        if not self.move_piece(0, 1):  # If piece can't move down
            time.sleep(self.LOCK_DELAY)  # Wait 0.5 seconds before locking
            if not self.move_piece(0, 1):  # Check again after delay
                self.lock_piece()

    def refill_bag(self):
        """Refills the piece bags, maintaining two bags at all times and printing their contents."""

        full_bag = ["I", "O", "T", "L", "J", "S", "Z"]  # Correct 7-bag with all pieces

        # If both bags are empty, fill both
        if not self.primary_bag and not self.secondary_bag:
            self.primary_bag = random.sample(full_bag, len(full_bag))  # Shuffle first bag
            self.secondary_bag = random.sample(full_bag, len(full_bag))  # Shuffle second bag

        # If only the primary bag is empty, refill it from the secondary and create a new secondary
        elif not self.primary_bag:
            self.primary_bag = self.secondary_bag
            self.secondary_bag = random.sample(full_bag, len(full_bag))  # Shuffle new secondary bag


    def spawn_piece(self):
        """Spawns a new piece from the next queue, ensuring the queue remains filled."""

        self.wall_kick_5_used = False # Reset to False when a new piece is spawned.

        # Ensure self.next_queue has at least 5 pieces
        while len(self.next_queue) < 5:
            if not self.primary_bag:
                self.refill_bag()
            self.next_queue.append(self.primary_bag.pop(0))

        # **Take the first piece from the queue**
        self.current_piece_type = self.next_queue.pop(0)

        # **Increment piece count when a new piece spawns**
        if self.bag_piece_count < 7:
            self.bag_piece_count += 1
        else:
            self.bag_piece_count = 1
        # **Ensure the queue remains filled**
        while len(self.next_queue) < 5:
            if not self.primary_bag:
                self.refill_bag()
            self.next_queue.append(self.primary_bag.pop(0))

        # Get the shape of the new piece
        piece = self.TETRIMINO_SHAPES[self.current_piece_type][0]

        # **Spawn the piece at the correct position**
        adjusted_piece = [(r + 2, c + 4) if self.current_piece_type != "I" else (r + 2, c + 3) for r, c in piece]

        return self.current_piece_type, adjusted_piece, 0  # (0 = spawn state)

    def hold_piece(self):
        """Handles the hold mechanic. Can only be used once per active piece."""

        if self.hold_used:
            return  # Can't hold again until a new piece locks

        if self.held_piece is None:
            # If no piece is held, store the current piece and spawn a new one
            self.held_piece = self.current_piece_type
            self.current_piece_type, self.current_piece, self.current_rotation = self.spawn_piece()
        else:
            # If a piece is already held, swap it with the current piece
            self.held_piece, self.current_piece_type = self.current_piece_type, self.held_piece
            self.current_piece, self.current_rotation = self.TETRIMINO_SHAPES[self.current_piece_type][0], 0

            # Adjust position for spawning
            self.current_piece = [(r + 2, c + 4) if self.current_piece_type != "I" else (r + 2, c + 3) for r, c in self.current_piece]

        self.hold_used = True  # Mark hold as used until next piece locks

    def is_grounded(self):
        """Returns True if the piece is directly above a solid block or the floor."""
        for r, c in self.current_piece:
            if r + 1 >= self.ROWS or (r + 1 >= 0 and self.grid[r + 1, c] != "X"):  # Check if a block is below
                return True
        return False

    def detect_T_spin(self):
        """Determines if the last move was a T-Spin, returning False if not a T piece."""

        # If the piece is not a T or the last action wasn't a rotation, there is no T-spin.
        if self.current_piece_type != "T" or not self.qualified_for_T_spin:
            return False

        # Initialize localized variables for corner checks. Front is the direction the T-piece is 'pointing' in, while back is the opposite.
        front_left_filled = False
        front_right_filled = False
        back_right_filled = False
        back_left_filled = False

        # Identify the pivot position (center of the T piece).
        pivot_index = self.PIECE_PIVOTS["T"]
        pivot_r, pivot_c = self.current_piece[pivot_index]

        # **Handle corner checking for each rotation state
        if self.current_rotation == 0:
            # **Check front-facing squares**
            front_left_filled = (
                pivot_r - 1 >= 0 and pivot_c - 1 >= 0 and self.grid[pivot_r - 1, pivot_c - 1] != "X"
            )
            front_right_filled = (
                pivot_r - 1 >= 0 and pivot_c + 1 < self.COLS and self.grid[pivot_r - 1, pivot_c + 1] != "X"
            )

            # **Check bottom-facing squares (considering out-of-bounds cases)**
            back_left_filled = (
                pivot_r + 1 >= self.ROWS or  # Back touching self.grid floor
                self.grid[pivot_r + 1, pivot_c - 1] != "X"  # Cell is filled
            )
            back_right_filled = (
                pivot_r + 1 >= self.ROWS or  # Back touching self.grid floor
                self.grid[pivot_r + 1, pivot_c + 1] != "X"  # Cell is filled
            )

        elif self.current_rotation == "R":
            # **Check front-facing squares**
            front_left_filled = (
                pivot_r - 1 >= 0 and pivot_c - 1 >= 0 and self.grid[pivot_r - 1, pivot_c + 1] != "X"
            )
            front_right_filled = (
                pivot_r - 1 >= 0 and pivot_c + 1 < self.COLS and self.grid[pivot_r + 1, pivot_c + 1] != "X"
            )

            # **Check bottom-facing squares (considering out-of-bounds cases)**
            back_left_filled = (
                pivot_c - 1 < 0 or  # Touching left wall
                self.grid[pivot_r - 1, pivot_c - 1] != "X"  # Cell is filled
            )
            back_right_filled = (
                pivot_c - 1 < 0 or  # Touching left wall
                self.grid[pivot_r + 1, pivot_c - 1] != "X"  # Cell is filled
            )

        elif self.current_rotation == 2:
            # **Check front-facing squares**
            front_left_filled = (
                pivot_r - 1 >= 0 and pivot_c - 1 >= 0 and self.grid[pivot_r + 1, pivot_c + 1] != "X"
            )
            front_right_filled = (
                pivot_r - 1 >= 0 and pivot_c + 1 < self.COLS and self.grid[pivot_r + 1, pivot_c - 1] != "X"
            )

            # Check bottom-facing squares (no out-of-bounds cases for down-facing T-piece)
            back_left_filled = (
                self.grid[pivot_r - 1, pivot_c + 1] != "X"  # Cell is filled
            )
            back_right_filled = (
                self.grid[pivot_r - 1, pivot_c - 1] != "X"  # Cell is filled
            )

        elif self.current_rotation == "L":
            # **Check front-facing squares**
            front_left_filled = (
                pivot_r - 1 >= 0 and pivot_c - 1 >= 0 and self.grid[pivot_r + 1, pivot_c - 1] != "X"
            )
            front_right_filled = (
                pivot_r - 1 >= 0 and pivot_c + 1 < self.COLS and self.grid[pivot_r - 1, pivot_c - 1] != "X"
            )

            # **Check bottom-facing squares (considering out-of-bounds cases)**
            back_left_filled = (
                pivot_c + 1 >= self.COLS or  # Touching right wall
                self.grid[pivot_r + 1, pivot_c + 1] != "X"  # Cell is filled
            )
            back_right_filled = (
                pivot_c + 1 >= self.COLS or  # Touching right wall
                self.grid[pivot_r - 1, pivot_c + 1] != "X"  # Cell is filled
            )

        # Return T-Spin state if detected.
        if front_left_filled and front_right_filled and (back_left_filled or back_right_filled):
            return "T-Spin"
        elif self.wall_kick_5_used: # Could technically be added to the first conditional above, but would be difficult to read.
            return "T-Spin"
        elif back_left_filled and back_right_filled and (front_left_filled or front_right_filled):
            return "Mini T-Spin"
        else:
            return False

    def handle_clear_text(self, text, has_b2b):
        """Sets the global self.clear_text variable to the given string for two seconds before clearing it.
        If called again before the timer expires, the timer resets.
        """

        self.clear_text = text  # Set the text

        # Determine the text color based on B2B status
        if has_b2b and self.b2b:
            self.clear_text_color = (255, 215, 0)  # Gold for B2B
        else:
            self.clear_text_color = (255, 255, 255)  # White otherwise

        # Cancel any existing timer to reset the countdown
        if self.clear_text_timer is not None:
            self.clear_text_timer.cancel()

        # Start a new timer to clear the text after 2 seconds
        self.clear_text_timer = threading.Timer(2, self.clear_clear_text)
        self.clear_text_timer.start()

    def clear_clear_text(self):
        """Clears the self.clear_text after the timer expires."""
        self.clear_text = ""  # Reset the text

    def clear_lines(self):
        """Checks for full lines, clears them, shifts the above lines down, detects perfect clear, and awards points."""

        # Initialize local variables:
        full_rows = [r for r in range(self.ROWS) if all(self.grid[r, c] != "X" for c in range(self.COLS))] # Identify full rows
        num_cleared = len(full_rows)  # Number of lines cleared
        T_spin = self.detect_T_spin() # Detect T-Spin (False, "Mini T-Spin", "T-Spin")
        score_awarded = 0 # Score to be awarded to the player at the end of the function.
        unique_b2b = False # Identifier for cases when self.b2b isn't a simple 1.5x self.score multiplier
        has_b2b = self.b2b # Checks whether the player had self.b2b *before* all the scoring logic changes it. Otherwise, initial 'difficult' clears would award self.b2b-modified points.

        if num_cleared == 0:
            self.clear_combo = 0

        elif num_cleared > 0:
            # Debug print statement:
            # print("One or more lines has been cleared!")
            # Remove full rows and insert new empty rows at the top
            new_grid = np.full((self.ROWS, self.COLS), "X")  # Start with an empty self.grid
            new_row_idx = self.ROWS - 1  # Start from the bottom

            # Fill the new self.grid with non-cleared rows
            for r in range(self.ROWS - 1, -1, -1):
                if r not in full_rows:  # If row is not full, copy it down
                    new_grid[new_row_idx] = self.grid[r]
                    new_row_idx -= 1

            # **Check for a perfect clear before updating the self.grid**
            perfect_clear = np.all(new_grid == "X")  # If all cells are empty, it's a perfect clear

            # Update the self.grid
            self.grid = new_grid

        # Increment or decrement total cleared lines differently based on gamemode.
        if self.game_mode == "Sprint" and self.lines_cleared > num_cleared:
            self.lines_cleared -= num_cleared
        elif self.game_mode == "Sprint" and self.lines_cleared <= num_cleared:
            self.lines_cleared = 0
            self.game_over_condition = "Clear!"
            self.game_over = True
        else:
            self.lines_cleared += num_cleared

        # Award points based on the number of lines cleared (T-spins give points even without lines cleared)
        # No lines cleared:
        if num_cleared == 0 and T_spin == "Mini T-Spin":
            score_awarded = 100 # Mini non-clear T-spin
            # self.handle_clear_text("Mini T-Spin!", has_b2b)
            # Non-clear mini T-spins don't break self.b2b, but don't start it either
        elif num_cleared == 0 and T_spin == "T-Spin":
            score_awarded = 400  # Non-clear T-spin
            # self.handle_clear_text("T-Spin!", has_b2b)
            # Non-clear T-spins don't break self.b2b, but don't start it either

        # Single line clears:
        elif num_cleared == 1 and not perfect_clear and not T_spin:
            score_awarded = 100  # Single
            self.b2b = False
            self.handle_clear_text("Single!", has_b2b)
        elif num_cleared == 1 and not perfect_clear and T_spin == "Mini T-Spin":
            score_awarded = 200 # Mini TSS
            self.b2b = True
            self.handle_clear_text("Mini TSS!", has_b2b)
        elif num_cleared == 1 and not perfect_clear and T_spin == "T-Spin":
            score_awarded = 800 # TSS
            self.b2b = True
            self.handle_clear_text("TSS!", has_b2b)
        elif num_cleared == 1 and perfect_clear:
            score_awarded = 900 # PC Single
            self.b2b = False
            self.handle_clear_text("Perfect Clear!", has_b2b)
        # Not possible to perfect clear with either form of TSS, so no need to handle it
        
        # Double line clears:
        elif num_cleared == 2 and not perfect_clear and not T_spin:
            score_awarded = 300  # Double
            self.b2b = False
            self.handle_clear_text("Double!", has_b2b)
        elif num_cleared == 2 and not perfect_clear and T_spin == "Mini T-Spin":
            score_awarded = 400 # Mini TSD
            self.b2b = True
            self.handle_clear_text("Mini TSD!", has_b2b)
        elif num_cleared == 2 and not perfect_clear and T_spin == "T-Spin":
            score_awarded = 1200 # TSD
            self.b2b = True
            self.handle_clear_text("TSD!", has_b2b)
        elif num_cleared == 2 and perfect_clear:
            score_awarded = 1500  # PC Double 
            self.b2b = False
            self.handle_clear_text("Perfect Clear!", has_b2b)
        # Not possible to perfect clear with either form of TSD, so no need to handle it

        # Triple line clears:
        elif num_cleared == 3 and not perfect_clear and not T_spin:
            score_awarded = 500  # Triple
            self.b2b = False
            self.handle_clear_text("Triple!", has_b2b)
        elif num_cleared == 3 and not perfect_clear and T_spin:
            score_awarded = 1600 # TST
            self.b2b = True
            self.handle_clear_text("TST!", has_b2b)
        elif num_cleared == 3 and perfect_clear and not T_spin:
            score_awarded = 2300  # PC Triple
            self.b2b = False
            self.handle_clear_text("Perfect Clear!", has_b2b)
        elif num_cleared == 3 and perfect_clear and T_spin:
            score_awarded = 3400  # PC TST
            self.b2b = True
            unique_b2b = 800
            self.handle_clear_text("Perfect TST!", has_b2b)
        # No such thing as a mini TST, since all four corners are necessarily covered.

        # Quadruple line clears (Tetrises):
        elif num_cleared == 4 and not perfect_clear:
            score_awarded = 800  # Tetris
            self.b2b = True
            self.handle_clear_text("Tetris!", has_b2b)
        elif num_cleared == 4 and perfect_clear:
            score_awarded = 2800  # PC Tetris
            self.b2b = True
            unique_b2b = 1200
            self.handle_clear_text("Perfect Tetris!", has_b2b)

        # Point assignment:
        if not has_b2b or not self.b2b: # No self.b2b
            self.score += score_awarded
        elif has_b2b and self.b2b and not unique_b2b: # Non-PC self.b2b. Must have had self.b2b and also not broken it with the clear.
            self.score += (score_awarded * 1.5)
        else: # PC self.b2b
            self.score += (score_awarded + unique_b2b)

        # Finally, assign bonus points for combo and round self.score to nearest whole number to avoid floating point shenanigans
        self.score += (50 * self.clear_combo)
        self.score = round(self.score)

        # Increment combo counter only *after* adding the combo self.score
        if num_cleared > 0:
            self.clear_combo += 1

    def handle_movement(self, direction = 0):
        """Handles self.DAS and self.ARR for left/right movement and resets lock delay when moving."""

        current_time = pygame.time.get_ticks()

        if self.move_left_pressed:
            direction = -1  # Move left
        elif self.move_right_pressed:
            direction = 1  # Move right

        if direction != 0:
            if self.das_timer == 0:
                self.das_timer = current_time  # Start self.DAS timer
                self.move_piece(direction, 0)  # Move once on initial press
                self.gravity_lock_timer = 0
                self.soft_drop_lock_timer = 0

            elif current_time - self.das_timer >= self.DAS:
                # self.DAS threshold reached, start self.ARR movement
                if self.arr_timer == 0 or current_time - self.arr_timer >= self.ARR:
                    self.move_piece(direction, 0)  # Move at self.ARR interval
                    self.gravity_lock_timer = 0
                    self.soft_drop_lock_timer = 0
                    self.arr_timer = current_time  # Reset self.ARR timer
        else:
            self.das_timer = 0  # Reset self.DAS when no key is pressed
            self.arr_timer = 0  # Reset self.ARR

    def handle_soft_drop(self, AI = False):
        """Handles DAS and ARR for soft dropping with proper locking and lockout override.
        If manual=True, moves the piece down by one row and skips input timing logic.
        """

        current_time = pygame.time.get_ticks()

        if AI:
            # Direct one-step drop
            if self.move_piece(0, 1):
                self.score += 1
                self.qualified_for_T_spin = False
                self.wall_kick_5_used = False
            elif self.is_grounded():
                if self.soft_drop_lock_timer == 0:
                    self.soft_drop_lock_timer = current_time
                if self.lockout_override_timer == 0:
                    self.lockout_override_timer = current_time
        else:
            # Original key-holding logic
            if self.soft_drop_pressed:
                if self.soft_drop_das_timer == 0:
                    self.soft_drop_das_timer = current_time
                    if self.move_piece(0, 1):
                        self.score += 1
                        self.qualified_for_T_spin = False
                        self.wall_kick_5_used = False
                    elif self.is_grounded():
                        if self.soft_drop_lock_timer == 0:
                            self.soft_drop_lock_timer = current_time
                        if self.lockout_override_timer == 0:
                            self.lockout_override_timer = current_time

                elif current_time - self.soft_drop_das_timer >= self.SOFT_DROP_DAS:
                    if self.soft_drop_arr_timer == 0 or current_time - self.soft_drop_arr_timer >= self.SOFT_DROP_ARR:
                        if self.move_piece(0, 1):
                            self.score += 1
                            self.qualified_for_T_spin = False
                            self.wall_kick_5_used = False
                        elif self.is_grounded():
                            if self.soft_drop_lock_timer == 0:
                                self.soft_drop_lock_timer = current_time
                            if self.lockout_override_timer == 0:
                                self.lockout_override_timer = current_time
                        self.soft_drop_arr_timer = current_time
            else:
                self.soft_drop_das_timer = 0
                self.soft_drop_arr_timer = 0
                self.soft_drop_lock_timer = 0

        # Shared locking behavior (manual or not)
        if self.soft_drop_lock_timer > 0 and current_time - self.soft_drop_lock_timer >= self.LOCK_DELAY and self.is_grounded():
            self.lock_piece()
            self.soft_drop_lock_timer = 0
            self.lockout_override_timer = 0

        if self.lockout_override_timer > 0 and current_time - self.lockout_override_timer >= self.LOCKOUT_OVERRIDE and self.is_grounded():
            self.lock_piece()
            self.lockout_override_timer = 0


    def handle_gravity(self):
        """Handles automatic piece falling at self.GRAVITY intervals and triggers lockout if needed."""

        if not self.TICK_BASED:

            current_time = pygame.time.get_ticks()

            # Apply gravity
            if current_time - self.gravity_timer >= self.GRAVITY:
                if not self.move_piece(0, 1):
                    if self.is_grounded():  # Only start lock timer if grounded
                        if self.gravity_lock_timer == 0:
                            self.gravity_lock_timer = current_time
                        
                        if self.lockout_override_timer == 0:  # Start override timer if not started
                            self.lockout_override_timer = current_time
                else:
                    self.gravity_lock_timer = 0  # Reset lock timer if the piece moves down
                    self.lockout_override_timer = 0  # Reset override timer on downward movement

                self.gravity_timer = current_time  # Reset gravity timer

            # **Lock the piece if grounded and unable to move for self.LOCK_DELAY**
            if self.gravity_lock_timer > 0 and current_time - self.gravity_lock_timer >= self.LOCK_DELAY and self.is_grounded():
                self.lock_piece()
                self.gravity_lock_timer = 0  # Reset lock timer after locking
                self.lockout_override_timer = 0  # Reset override timer after locking

            # **Lock piece if override timer exceeds self.LOCKOUT_OVERRIDE**
            if self.lockout_override_timer > 0 and current_time - self.lockout_override_timer >= self.LOCKOUT_OVERRIDE and self.is_grounded():
                self.lock_piece()
                self.lockout_override_timer = 0  # Reset override timer after locking

        else:
            # Apply gravity
            if self.gravity_timer >= self.GRAVITY:
                if not self.move_piece(0, 1):
                    if self.is_grounded():  # Only start lock timer if grounded
                        if self.gravity_lock_timer == 0:
                            self.gravity_lock_timer = self.gravity_timer

                        if self.lockout_override_timer == 0:
                            self.lockout_override_timer = self.gravity_timer
                else:
                    self.gravity_lock_timer = 0
                    self.lockout_override_timer = 0

                self.gravity_timer = 0  # Reset gravity accumulation

            # Lock the piece if grounded and gravity lock delay exceeded
            if self.gravity_lock_timer > 0 and self.gravity_lock_timer >= self.LOCK_DELAY and self.is_grounded():
                self.lock_piece()
                self.gravity_lock_timer = 0
                self.lockout_override_timer = 0

            # Lock the piece if override delay exceeded
            if self.lockout_override_timer > 0 and self.lockout_override_timer >= self.LOCKOUT_OVERRIDE and self.is_grounded():
                self.lock_piece()
                self.lockout_override_timer = 0

    def rotate_piece(self, direction):
        """Rotates the current piece using SRS with wall kicks, handling I-piece separately."""

        # Rotation states order
        rotation_states = [0, "R", 2, "L"]

        # O-piece does not rotate at all
        if self.current_piece_type == "O":
            self.gravity_lock_timer = 0  # Reset lock delay
            self.soft_drop_lock_timer = 0
            return

        # Determine the new rotation state
        if direction == "R":  # Clockwise
            new_rotation = rotation_states[(rotation_states.index(self.current_rotation) + 1) % 4]
        else:  # Counter-clockwise
            new_rotation = rotation_states[(rotation_states.index(self.current_rotation) - 1) % 4]

        # Special case for I-piece (different pivot point logic)
        if self.current_piece_type == "I":
            self.rotate_I_piece(direction, new_rotation)
            return

        # Find pivot block index based on piece type
        pivot_index = self.PIECE_PIVOTS[self.current_piece_type]
        pivot_r, pivot_c = self.current_piece[pivot_index]  # Get pivot position

        # Rotate each block around the pivot
        if direction == "R":  # Clockwise 90°
            new_piece = [(pivot_r + (c - pivot_c), pivot_c - (r - pivot_r)) for r, c in self.current_piece]
        else:  # Counter-clockwise 90°
            new_piece = [(pivot_r - (c - pivot_c), pivot_c + (r - pivot_r)) for r, c in self.current_piece]

        # Choose correct SRS wall kick data
        kick_data = self.SRS_WALL_KICKS
        kick_tests = kick_data.get((self.current_rotation, new_rotation), [(0, 0)])

        self.wall_kick_5_used = False # Reset to false since a rotation is being attempted.

        # Try applying each kick (track index for final kick detection)
        for i, (kick_x, kick_y) in enumerate(kick_tests):
            kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
            if self.is_valid_position(kicked_piece):  # If no collision, apply rotation
                self.current_piece = kicked_piece
                self.current_rotation = new_rotation
                self.qualified_for_T_spin = True
                self.wall_kick_5_used = (i == len(kick_tests) - 1) # Set self.wall_kick_5_used to True only if it's the final wall kick attempt
                self.gravity_lock_timer = 0  # Reset lock delay
                self.soft_drop_lock_timer = 0
                return True  # Rotation succeeded

        return False  # Rotation failed, piece stays the same


    def rotate_I_piece(self, direction, new_rotation):
        """Handles I-piece rotation using correct pivot alignment in SRS."""
        
        if self.current_rotation == 0:  # Horizontal (Facing Upward)
            # Extract mino positions sorted by column to correctly identify mino indexes
            mino_positions = sorted(self.current_piece, key=lambda pos: pos[1])  # Sort by column

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
            kick_tests = self.SRS_WALL_KICKS_I.get((self.current_rotation, new_rotation), [(0, 0)])
            for kick_x, kick_y in kick_tests:
                kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
                if self.is_valid_position(kicked_piece):
                    self.current_piece = kicked_piece
                    self.current_rotation = new_rotation
                    self.gravity_lock_timer = 0  # Reset lock delay
                    self.soft_drop_lock_timer = 0
                    return True  # Rotation succeeded
                
            return False  # Rotation failed, piece stays the same

        elif self.current_rotation == "R":  # Vertical "R" Position
                # Extract mino positions sorted by row to correctly identify mino indexes
                mino_positions = sorted(self.current_piece, key=lambda pos: pos[0])  # Sort by row

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
                kick_tests = self.SRS_WALL_KICKS_I.get((self.current_rotation, new_rotation), [(0, 0)])
                for kick_x, kick_y in kick_tests:
                    kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
                    if self.is_valid_position(kicked_piece):
                        self.current_piece = kicked_piece
                        self.current_rotation = new_rotation
                        self.gravity_lock_timer = 0  # Reset lock delay
                        self.soft_drop_lock_timer = 0
                        return True  # Rotation succeeded

                return False  # Rotation failed, piece stays the same
        
        elif self.current_rotation == 2:  # Horizontal "Upside-Down"
            # Extract mino positions sorted by column to correctly identify mino indexes
            mino_positions = sorted(self.current_piece, key=lambda pos: pos[1])  # Sort by column
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
            kick_tests = self.SRS_WALL_KICKS_I.get((self.current_rotation, new_rotation), [(0, 0)])
            for kick_x, kick_y in kick_tests:
                kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
                if self.is_valid_position(kicked_piece):
                    self.current_piece = kicked_piece
                    self.current_rotation = new_rotation
                    self.gravity_lock_timer = 0  # Reset lock delay
                    self.soft_drop_lock_timer = 0
                    return True  # Rotation succeeded

            return False  # Rotation failed, piece stays the same

        elif self.current_rotation == "L":  # Vertical "L" Position
            # Extract mino positions sorted by row to correctly identify mino indexes
            mino_positions = sorted(self.current_piece, key=lambda pos: pos[0])  # Sort by row
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
            kick_tests = self.SRS_WALL_KICKS_I.get((self.current_rotation, new_rotation), [(0, 0)])
            for kick_x, kick_y in kick_tests:
                kicked_piece = [(r + kick_y, c + kick_x) for r, c in new_piece]
                if self.is_valid_position(kicked_piece):
                    self.current_piece = kicked_piece
                    self.current_rotation = new_rotation
                    self.gravity_lock_timer = 0  # Reset lock delay
                    self.soft_drop_lock_timer = 0
                    return True  # Rotation succeeded

            return False  # Rotation failed, piece stays the same

    def get_ghost_piece(self):
        """Returns the lowest valid position for the current piece (ghost piece)."""
        ghost_piece = list(self.current_piece)  # Copy the current piece

        # Move the ghost piece down until it collides
        while self.is_valid_position([(r + 1, c) for r, c in ghost_piece]):
            ghost_piece = [(r + 1, c) for r, c in ghost_piece]

        return ghost_piece
    
    def aggregate_height(self, grid=None):
        """
        Computes the aggregate height of the given grid.
        If no grid is provided, uses self.grid.
        """
        if grid is None:
            grid = self.grid

        height_sum = 0
        for col in range(self.COLS):
            for row in range(self.ROWS):
                if grid[row, col] != "X":
                    height_sum += self.ROWS - row
                    break  # Only count the height of the first filled cell in this column

        return height_sum
    
    def check_complete_lines(self, grid=None):
        """
        Returns the number of complete lines in the grid.
        A line is complete if it contains no "X" values.
        """
        if grid is None:
            grid = self.grid

        complete_lines = 0
        for row in grid:
            if "X" not in row:
                complete_lines += 1

        return complete_lines

    def count_holes(self, grid=None):
        """
        Counts the number of holes in the grid.
        A hole is an empty cell ("X") that has at least one filled cell above it in the same column.
        """
        if grid is None:
            grid = self.grid

        holes = 0
        for col in range(self.COLS):
            block_found = False
            for row in range(self.ROWS):
                if grid[row, col] != "X":
                    block_found = True  # Start counting holes only after first block is found
                elif block_found:
                    holes += 1

        return holes

    def calculate_bumpiness(self, grid=None):
        """
        Calculates the bumpiness of the grid.
        Bumpiness is the sum of the absolute differences in heights between adjacent columns.
        """
        if grid is None:
            grid = self.grid

        # First, calculate heights for each column
        heights = []
        for col in range(self.COLS):
            col_height = 0
            for row in range(self.ROWS):
                if grid[row, col] != "X":
                    col_height = self.ROWS - row
                    break
            heights.append(col_height)

        # Now calculate bumpiness
        bumpiness = 0
        for i in range(self.COLS - 1):
            bumpiness += abs(heights[i] - heights[i + 1])

        return bumpiness

    def evaluate_heuristics(self, grid, weights):
        """
        Compute the weighted score of a grid based on four heuristics.
        
        Parameters:
            grid (np.ndarray): The Tetris grid to evaluate.
            weights (tuple or list of 4 floats): The weights (a, b, c, d) for
                aggregate height, complete lines, holes, and bumpiness.
        
        Returns:
            float: The total weighted score for the grid.
        """
        a, b, c, d = weights

        agg_height = self.aggregate_height(grid)
        completed = self.check_complete_lines(grid)
        holes = self.count_holes(grid)
        bumpiness = self.calculate_bumpiness(grid)

        score = (
            a * agg_height +
            b * completed +
            c * holes +
            d * bumpiness
        )

        return score

    def get_all_viable_hard_drops(self, weights = None):
        """Returns a list of every possible resulting grid for a given piece for the AI to choose from."""
        original_next_queue = self.next_queue # To account for the hold piece being empty and having to potentially reset the next queue
        original_held_piece = self.held_piece # Same deal here
        viable_drops = {} # To be appended to before returning
        drop_heuristics = {} # to be appended to before returning
        active_piece = list(self.current_piece)
        rotations = [0, "L", 2, "R"] # Looping variable
        checks = {
            0 : ["I", "J", "L", "O", "S", "T", "Z"],
            "L" : ["I", "J", "L", "S", "T", "Z"], # No duplicate O-piece checks
            2 : ["J", "L", "T"], # No duplicate I-/S-/T-piece checks
            "R" : ["J", "L", "T"] # These three have four distinct rotational states.
        }

        weights = weights if weights is not None else (1, 1, 1, 1)
        
        # Current Piece Calculations:
        for rotation in rotations:

            if self.current_piece_type in checks[rotation]:

                # One space to the left
                if self.is_valid_position([(r, c - 1) for r, c in active_piece]):
                    shifted_piece = [(r, c - 1) for r, c in active_piece]

                    # Simulate the hard drop
                    dropped_piece = list(shifted_piece)
                    while True:
                        next_pos = [(r + 1, c) for r, c in dropped_piece]
                        if self.is_valid_position(next_pos):
                            dropped_piece = next_pos
                        else:
                            break

                    # Fill the piece into a copy of the grid
                    grid_copy = np.copy(self.grid)
                    for r, c in dropped_piece:
                        if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                            grid_copy[r, c] = self.current_piece_type

                    # Save the result
                    viable_drops[(-1, rotation, False)] = grid_copy
                    drop_heuristics[(-1, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                    # This feels like a war crime but the nested if statements make sense here.
                    # Two spaces to the left
                    if self.is_valid_position([(r, c - 2) for r, c in active_piece]):
                        shifted_piece = [(r, c - 2) for r, c in active_piece]

                        # Simulate the hard drop
                        dropped_piece = list(shifted_piece)
                        while True:
                            next_pos = [(r + 1, c) for r, c in dropped_piece]
                            if self.is_valid_position(next_pos):
                                dropped_piece = next_pos
                            else:
                                break

                        # Fill the piece into a copy of the grid
                        grid_copy = np.copy(self.grid)
                        for r, c in dropped_piece:
                            if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                grid_copy[r, c] = self.current_piece_type

                        # Save the result
                        viable_drops[(-2, rotation, False)] = grid_copy
                        drop_heuristics[(-2, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                        # Three spaces to the left
                        if self.is_valid_position([(r, c - 3) for r, c in active_piece]):
                            shifted_piece = [(r, c - 3) for r, c in active_piece]

                            # Simulate the hard drop
                            dropped_piece = list(shifted_piece)
                            while True:
                                next_pos = [(r + 1, c) for r, c in dropped_piece]
                                if self.is_valid_position(next_pos):
                                    dropped_piece = next_pos
                                else:
                                    break

                            # Fill the piece into a copy of the grid
                            grid_copy = np.copy(self.grid)
                            for r, c in dropped_piece:
                                if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                    grid_copy[r, c] = self.current_piece_type

                            # Save the result
                            viable_drops[(-3, rotation, False)] = grid_copy
                            drop_heuristics[(-3, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                            # Four spaces to the left
                            if self.is_valid_position([(r, c - 4) for r, c in active_piece]):
                                shifted_piece = [(r, c - 4) for r, c in active_piece]

                                # Simulate the hard drop
                                dropped_piece = list(shifted_piece)
                                while True:
                                    next_pos = [(r + 1, c) for r, c in dropped_piece]
                                    if self.is_valid_position(next_pos):
                                        dropped_piece = next_pos
                                    else:
                                        break

                                # Fill the piece into a copy of the grid
                                grid_copy = np.copy(self.grid)
                                for r, c in dropped_piece:
                                    if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                        grid_copy[r, c] = self.current_piece_type

                                # Save the result
                                viable_drops[(-4, rotation, False)] = grid_copy
                                drop_heuristics[(-4, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                # One space to the right
                if self.is_valid_position([(r, c + 1) for r, c in active_piece]):
                    shifted_piece = [(r, c + 1) for r, c in active_piece]

                    # Simulate the hard drop
                    dropped_piece = list(shifted_piece)
                    while True:
                        next_pos = [(r + 1, c) for r, c in dropped_piece]
                        if self.is_valid_position(next_pos):
                            dropped_piece = next_pos
                        else:
                            break

                    # Fill the piece into a copy of the grid
                    grid_copy = np.copy(self.grid)
                    for r, c in dropped_piece:
                        if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                            grid_copy[r, c] = self.current_piece_type

                    # Save the result
                    viable_drops[(1, rotation, False)] = grid_copy
                    drop_heuristics[(1, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                    # Two spaces to the right
                    if self.is_valid_position([(r, c + 2) for r, c in active_piece]):
                        shifted_piece = [(r, c + 2) for r, c in active_piece]

                        # Simulate the hard drop
                        dropped_piece = list(shifted_piece)
                        while True:
                            next_pos = [(r + 1, c) for r, c in dropped_piece]
                            if self.is_valid_position(next_pos):
                                dropped_piece = next_pos
                            else:
                                break

                        # Fill the piece into a copy of the grid
                        grid_copy = np.copy(self.grid)
                        for r, c in dropped_piece:
                            if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                grid_copy[r, c] = self.current_piece_type

                        # Save the result
                        viable_drops[(2, rotation, False)] = grid_copy
                        drop_heuristics[(2, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                        # Three spaces to the right
                        if self.is_valid_position([(r, c + 3) for r, c in active_piece]):
                            shifted_piece = [(r, c + 3) for r, c in active_piece]

                            # Simulate the hard drop
                            dropped_piece = list(shifted_piece)
                            while True:
                                next_pos = [(r + 1, c) for r, c in dropped_piece]
                                if self.is_valid_position(next_pos):
                                    dropped_piece = next_pos
                                else:
                                    break

                            # Fill the piece into a copy of the grid
                            grid_copy = np.copy(self.grid)
                            for r, c in dropped_piece:
                                if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                    grid_copy[r, c] = self.current_piece_type

                            # Save the result
                            viable_drops[(3, rotation, False)] = grid_copy
                            drop_heuristics[(3, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                            # Four spaces to the right
                            if self.is_valid_position([(r, c + 4) for r, c in active_piece]):
                                shifted_piece = [(r, c + 4) for r, c in active_piece]

                                # Simulate the hard drop
                                dropped_piece = list(shifted_piece)
                                while True:
                                    next_pos = [(r + 1, c) for r, c in dropped_piece]
                                    if self.is_valid_position(next_pos):
                                        dropped_piece = next_pos
                                    else:
                                        break

                                # Fill the piece into a copy of the grid
                                grid_copy = np.copy(self.grid)
                                for r, c in dropped_piece:
                                    if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                        grid_copy[r, c] = self.current_piece_type

                                # Save the result
                                viable_drops[(4, rotation, False)] = grid_copy
                                drop_heuristics[(4, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                                # Five spaces to the right
                                if self.is_valid_position([(r, c + 5) for r, c in active_piece]):
                                    shifted_piece = [(r, c + 5) for r, c in active_piece]

                                    # Simulate the hard drop
                                    dropped_piece = list(shifted_piece)
                                    while True:
                                        next_pos = [(r + 1, c) for r, c in dropped_piece]
                                        if self.is_valid_position(next_pos):
                                            dropped_piece = next_pos
                                        else:
                                            break

                                    # Fill the piece into a copy of the grid
                                    grid_copy = np.copy(self.grid)
                                    for r, c in dropped_piece:
                                        if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                            grid_copy[r, c] = self.current_piece_type

                                    # Save the result
                                    viable_drops[(5, rotation, False)] = grid_copy
                                    drop_heuristics[(5, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

                # Simulate the hard drop in place (necessarily viable so no if statement):
                dropped_piece = list(active_piece)
                while True:
                    next_pos = [(r + 1, c) for r, c in dropped_piece]
                    if self.is_valid_position(next_pos):
                        dropped_piece = next_pos
                    else:
                        break

                # Fill the piece into a copy of the grid
                grid_copy = np.copy(self.grid)
                for r, c in dropped_piece:
                    if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                        grid_copy[r, c] = self.current_piece_type

                # Save the result
                viable_drops[(0, rotation, False)] = grid_copy
                drop_heuristics[(0, rotation, False)] = self.evaluate_heuristics(grid_copy, weights)

            # Rotate piece before iterating (or back to original iteration in case of the final loop).
            self.rotate_piece("L")

            active_piece = list(self.current_piece) # Re-initialize at new rotation

        # Do the same calculations for the hold piece, so long as it isn't the same piece type as the active piece.
        if self.held_piece != self.current_piece_type:

            self.hold_piece() # Swap current piece w/ either held piece (or next-up, if hold is empty).
            self.hold_used = False # Allow for the hold action to be used again afterwards


            for rotation in rotations:

                if self.current_piece_type in checks[rotation]:

                    # One space to the left
                    if self.is_valid_position([(r, c - 1) for r, c in active_piece]):
                        shifted_piece = [(r, c - 1) for r, c in active_piece]

                        # Simulate the hard drop
                        dropped_piece = list(shifted_piece)
                        while True:
                            next_pos = [(r + 1, c) for r, c in dropped_piece]
                            if self.is_valid_position(next_pos):
                                dropped_piece = next_pos
                            else:
                                break

                        # Fill the piece into a copy of the grid
                        grid_copy = np.copy(self.grid)
                        for r, c in dropped_piece:
                            if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                grid_copy[r, c] = self.current_piece_type

                        # Save the result
                        viable_drops[(-1, rotation, True)] = grid_copy
                        drop_heuristics[(-1, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                        # This feels like a war crime but the nested if statements make sense here.
                        # Two spaces to the left
                        if self.is_valid_position([(r, c - 2) for r, c in active_piece]):
                            shifted_piece = [(r, c - 2) for r, c in active_piece]

                            # Simulate the hard drop
                            dropped_piece = list(shifted_piece)
                            while True:
                                next_pos = [(r + 1, c) for r, c in dropped_piece]
                                if self.is_valid_position(next_pos):
                                    dropped_piece = next_pos
                                else:
                                    break

                            # Fill the piece into a copy of the grid
                            grid_copy = np.copy(self.grid)
                            for r, c in dropped_piece:
                                if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                    grid_copy[r, c] = self.current_piece_type

                            # Save the result
                            viable_drops[(-2, rotation, True)] = grid_copy
                            drop_heuristics[(-2, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                            # Three spaces to the left
                            if self.is_valid_position([(r, c - 3) for r, c in active_piece]):
                                shifted_piece = [(r, c - 3) for r, c in active_piece]

                                # Simulate the hard drop
                                dropped_piece = list(shifted_piece)
                                while True:
                                    next_pos = [(r + 1, c) for r, c in dropped_piece]
                                    if self.is_valid_position(next_pos):
                                        dropped_piece = next_pos
                                    else:
                                        break

                                # Fill the piece into a copy of the grid
                                grid_copy = np.copy(self.grid)
                                for r, c in dropped_piece:
                                    if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                        grid_copy[r, c] = self.current_piece_type

                                # Save the result
                                viable_drops[(-3, rotation, True)] = grid_copy
                                drop_heuristics[(-3, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                                # Four spaces to the left
                                if self.is_valid_position([(r, c - 4) for r, c in active_piece]):
                                    shifted_piece = [(r, c - 4) for r, c in active_piece]

                                    # Simulate the hard drop
                                    dropped_piece = list(shifted_piece)
                                    while True:
                                        next_pos = [(r + 1, c) for r, c in dropped_piece]
                                        if self.is_valid_position(next_pos):
                                            dropped_piece = next_pos
                                        else:
                                            break

                                    # Fill the piece into a copy of the grid
                                    grid_copy = np.copy(self.grid)
                                    for r, c in dropped_piece:
                                        if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                            grid_copy[r, c] = self.current_piece_type

                                    # Save the result
                                    viable_drops[(-4, rotation, True)] = grid_copy
                                    drop_heuristics[(-4, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                    # One space to the right
                    if self.is_valid_position([(r, c + 1) for r, c in active_piece]):
                        shifted_piece = [(r, c + 1) for r, c in active_piece]

                        # Simulate the hard drop
                        dropped_piece = list(shifted_piece)
                        while True:
                            next_pos = [(r + 1, c) for r, c in dropped_piece]
                            if self.is_valid_position(next_pos):
                                dropped_piece = next_pos
                            else:
                                break

                        # Fill the piece into a copy of the grid
                        grid_copy = np.copy(self.grid)
                        for r, c in dropped_piece:
                            if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                grid_copy[r, c] = self.current_piece_type

                        # Save the result
                        viable_drops[(1, rotation, True)] = grid_copy
                        drop_heuristics[(1, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                        # Two spaces to the right
                        if self.is_valid_position([(r, c + 2) for r, c in active_piece]):
                            shifted_piece = [(r, c + 2) for r, c in active_piece]

                            # Simulate the hard drop
                            dropped_piece = list(shifted_piece)
                            while True:
                                next_pos = [(r + 1, c) for r, c in dropped_piece]
                                if self.is_valid_position(next_pos):
                                    dropped_piece = next_pos
                                else:
                                    break

                            # Fill the piece into a copy of the grid
                            grid_copy = np.copy(self.grid)
                            for r, c in dropped_piece:
                                if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                    grid_copy[r, c] = self.current_piece_type

                            # Save the result
                            viable_drops[(2, rotation, True)] = grid_copy
                            drop_heuristics[(2, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                            # Three spaces to the right
                            if self.is_valid_position([(r, c + 3) for r, c in active_piece]):
                                shifted_piece = [(r, c + 3) for r, c in active_piece]

                                # Simulate the hard drop
                                dropped_piece = list(shifted_piece)
                                while True:
                                    next_pos = [(r + 1, c) for r, c in dropped_piece]
                                    if self.is_valid_position(next_pos):
                                        dropped_piece = next_pos
                                    else:
                                        break

                                # Fill the piece into a copy of the grid
                                grid_copy = np.copy(self.grid)
                                for r, c in dropped_piece:
                                    if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                        grid_copy[r, c] = self.current_piece_type

                                # Save the result
                                viable_drops[(3, rotation, True)] = grid_copy
                                drop_heuristics[(3, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                                # Four spaces to the right
                                if self.is_valid_position([(r, c + 4) for r, c in active_piece]):
                                    shifted_piece = [(r, c + 4) for r, c in active_piece]

                                    # Simulate the hard drop
                                    dropped_piece = list(shifted_piece)
                                    while True:
                                        next_pos = [(r + 1, c) for r, c in dropped_piece]
                                        if self.is_valid_position(next_pos):
                                            dropped_piece = next_pos
                                        else:
                                            break

                                    # Fill the piece into a copy of the grid
                                    grid_copy = np.copy(self.grid)
                                    for r, c in dropped_piece:
                                        if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                            grid_copy[r, c] = self.current_piece_type

                                    # Save the result
                                    viable_drops[(4, rotation, True)] = grid_copy
                                    drop_heuristics[(4, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                                    # Five spaces to the right
                                    if self.is_valid_position([(r, c + 5) for r, c in active_piece]):
                                        shifted_piece = [(r, c + 5) for r, c in active_piece]

                                        # Simulate the hard drop
                                        dropped_piece = list(shifted_piece)
                                        while True:
                                            next_pos = [(r + 1, c) for r, c in dropped_piece]
                                            if self.is_valid_position(next_pos):
                                                dropped_piece = next_pos
                                            else:
                                                break

                                        # Fill the piece into a copy of the grid
                                        grid_copy = np.copy(self.grid)
                                        for r, c in dropped_piece:
                                            if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                                                grid_copy[r, c] = self.current_piece_type

                                        # Save the result
                                        viable_drops[(5, rotation, True)] = grid_copy
                                        drop_heuristics[(5, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                    # Simulate the hard drop in place (necessarily viable so no if statement):
                    dropped_piece = list(active_piece)
                    while True:
                        next_pos = [(r + 1, c) for r, c in dropped_piece]
                        if self.is_valid_position(next_pos):
                            dropped_piece = next_pos
                        else:
                            break

                    # Fill the piece into a copy of the grid
                    grid_copy = np.copy(self.grid)
                    for r, c in dropped_piece:
                        if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                            grid_copy[r, c] = self.current_piece_type

                    # Save the result
                    viable_drops[(0, rotation, True)] = grid_copy
                    drop_heuristics[(0, rotation, True)] = self.evaluate_heuristics(grid_copy, weights)

                # Rotate piece before iterating (or back to original iteration in case of the final loop).
                self.rotate_piece("L")

                active_piece = list(self.current_piece) # Re-initialize at new rotation

            self.hold_piece() # Swap back
            self.hold_used = False # Allow for the hold action to be used again afterwards

            # Replaces held piece and next queue as they were in case the hold queue was empty.
            # No if statement since it should essentially just do nothing if the queue wasn't empty.
            self.next_queue = original_next_queue
            self.held_piece = original_held_piece

        return viable_drops, drop_heuristics


    def draw_hold_box(self):
        """Draws the hold box aligned with the top half-cell margin, with proper sizing."""
        width, height = self.screen.get_size()

        # Sets color of text to red if hold is currently locked.
        if self.hold_used:
            hold_text_color = (255, 150, 150)
        else:
            hold_text_color = (255, 255, 255)

        # Calculate square size dynamically
        square_size = min(width // self.COLS, height // (self.VISIBLE_ROWS + 1))  # Adjust size dynamically
        grid_width = square_size * self.COLS
        grid_height = square_size * (self.VISIBLE_ROWS + 1)  # Include margins

        # Centering the self.grid in the window
        margin_x = (width - grid_width) // 2
        margin_y = (height - grid_height) // 2

        # Hold box position
        hold_box_width = square_size * 5  
        hold_box_height = square_size * 4  
        hold_box_x = margin_x - hold_box_width - 10  
        hold_box_y = margin_y + square_size * 0.5  

        # Draw hold box
        pygame.draw.rect(self.screen, self.BLACK, (hold_box_x, hold_box_y, hold_box_width, hold_box_height))
        pygame.draw.rect(self.screen, self.GRID_LINES, (hold_box_x, hold_box_y, hold_box_width, hold_box_height), 2)

        # Draw the held piece
        if self.held_piece:
            piece_shape = self.TETRIMINO_SHAPES[self.held_piece][0]
            piece_color = self.TETRIMINO_COLORS[self.held_piece]

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
                pygame.draw.rect(self.screen, piece_color, piece_rect)
                pygame.draw.rect(self.screen, self.BLACK, piece_rect, 1)

        # **Ensure the "HOLD" text is the same distance from the box as "NEXT" text**
        font = pygame.font.Font(None, 40)
        text = font.render("HOLD", True, hold_text_color)

        # **Align text exactly one self.grid square below the hold box (same as NEXT)**
        text_y = hold_box_y + hold_box_height + square_size  # Matches `self.draw_next_box()`
        text_rect = text.get_rect(center=(hold_box_x + hold_box_width // 2, text_y))
        self.screen.blit(text, text_rect)

    def draw_next_box(self):
        """Draws the next piece box aligned with the top half-cell margin, mirrored on the right side,
        and positions the 'NEXT' text correctly between the two next queues with a 2-self.grid-square margin.
        Adds a horizontal separator if `self.bag_piece_count == 7` or `self.bag_piece_count == 0`."""

        width, height = self.screen.get_size()

        # Calculate square size dynamically
        square_size = min(width // self.COLS, height // (self.VISIBLE_ROWS + 1))  # +1 for margin
        grid_width = square_size * self.COLS
        grid_height = square_size * (self.VISIBLE_ROWS + 1)  # Include margin

        # Centering self.grid in the window
        margin_x = (width - grid_width) // 2
        margin_y = (height - grid_height) // 2

        # Next box position: mirrored to the right
        next_box_width = square_size * 5  # Same width as hold box
        next_box_height = square_size * 4  # Same height as hold box
        next_box_x = margin_x + grid_width + 10  # Right side of self.grid
        next_box_y = margin_y + square_size * 0.5  # Align with top half-cell margin

        # Draw next box background
        pygame.draw.rect(self.screen, self.BLACK, (next_box_x, next_box_y, next_box_width, next_box_height))
        pygame.draw.rect(self.screen, self.GRID_LINES, (next_box_x, next_box_y, next_box_width, next_box_height), 2)

        # **Draw the next piece**
        if self.next_queue:
            piece_type = self.next_queue[0]  # Extract only the piece type
            piece_shape = self.TETRIMINO_SHAPES[piece_type][0]
            piece_color = self.TETRIMINO_COLORS[piece_type]

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
                pygame.draw.rect(self.screen, piece_color, piece_rect)
                pygame.draw.rect(self.screen, self.BLACK, piece_rect, 1)

        # **Draw horizontal separator line if `self.bag_piece_count == 7` or `self.bag_piece_count == 0`**
        if self.bag_piece_count == 6:
            separator_y = next_box_y + next_box_height - (square_size * 0.35)  # 0.35 cells above bottom edge
            pygame.draw.line(self.screen, self.OUTSIDE_BACKGROUND, 
                            (next_box_x + 2, separator_y), 
                            (next_box_x + next_box_width - 2, separator_y), 2)

        elif self.bag_piece_count == 7:
            separator_y = next_box_y + (square_size * 0.35)  # 0.35 cells below top edge
            pygame.draw.line(self.screen, self.OUTSIDE_BACKGROUND, 
                            (next_box_x + 2, separator_y), 
                            (next_box_x + next_box_width - 2, separator_y), 2)

        # **Ensure "NEXT" text is positioned exactly in the middle of the 2-square gap**
        font = pygame.font.Font(None, 40)
        text = font.render("NEXT", True, (255, 255, 255))
        
        # **Position the text exactly one self.grid square below the next box**
        text_y = next_box_y + next_box_height + square_size  # One square below next box
        text_rect = text.get_rect(center=(next_box_x + next_box_width // 2, text_y))
        self.screen.blit(text, text_rect)

        # **Return required values for extended queue alignment**
        return next_box_y, next_box_height

    def draw_extended_next_queue(self, next_box_y, next_box_height):
        """Draws a box below the next piece box displaying the next four upcoming pieces,
        ensuring it starts two self.grid squares below the next box and ends half a square from the bottom.
        Draws a horizontal separator line based on `self.bag_piece_count` conditions."""

        width, height = self.screen.get_size()

        # Calculate square size dynamically
        square_size = min(width // self.COLS, height // (self.VISIBLE_ROWS + 1))
        grid_width = square_size * self.COLS
        grid_height = square_size * (self.VISIBLE_ROWS + 1)

        # Centering the self.grid
        margin_x = (width - grid_width) // 2

        # **Position the extended queue exactly 2 self.grid squares below the next box**
        extended_box_x = margin_x + grid_width + 10  # Right side of self.grid
        extended_box_y = next_box_y + next_box_height + (square_size * 2)

        # **Adjust the height to align the bottom with half a square from the bottom of the self.screen**
        margin_y = (height - self.GRID_HEIGHT) // 2  # Center the self.grid vertically
        extended_box_height = self.GRID_HEIGHT - (next_box_y - margin_y + next_box_height) - (square_size * 1.1)


        # Extended queue width remains the same as the next box
        extended_box_width = square_size * 5  

        # Draw extended queue background
        pygame.draw.rect(self.screen, self.BLACK, (extended_box_x, extended_box_y, extended_box_width, extended_box_height))
        pygame.draw.rect(self.screen, self.GRID_LINES, (extended_box_x, extended_box_y, extended_box_width, extended_box_height), 2)

        # **Determine vertical spacing for pieces**
        num_pieces = min(4, len(self.next_queue) - 1)  # Ensure up to 4 pieces are displayed
        if num_pieces > 0:
            piece_spacing = extended_box_height / num_pieces  # Distribute pieces evenly

        # **Determine where to place the separator line**
        separator_index = None
        extra_separator_position = None  # Used for self.bag_piece_count == 6 or 2

        if self.bag_piece_count == 6:
            extra_separator_position = "top"  # Line near the top edge
        elif self.bag_piece_count == 5:
            separator_index = 0  # Line between first and second piece
        elif self.bag_piece_count == 4:
            separator_index = 1  # Line between second and third piece
        elif self.bag_piece_count == 3:
            separator_index = 2  # Line between third and fourth piece
        elif self.bag_piece_count == 2:
            extra_separator_position = "bottom"  # Line near the bottom edge

        # **Draw next four pieces in order**
        for i, piece_type in enumerate(self.next_queue[1:num_pieces+1]):  # Skip first element (it's in next box)
            piece_shape = self.TETRIMINO_SHAPES[piece_type][0]
            piece_color = self.TETRIMINO_COLORS[piece_type]

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
                pygame.draw.rect(self.screen, piece_color, piece_rect)
                pygame.draw.rect(self.screen, self.BLACK, piece_rect, 1)

            # **Draw separator line in the correct position**
            if separator_index is not None and i == separator_index:
                separator_y = offset_y + piece_height + (piece_spacing - piece_height) / 2  # Center between pieces
                pygame.draw.line(self.screen, self.OUTSIDE_BACKGROUND, 
                                (extended_box_x + 2, separator_y), 
                                (extended_box_x + extended_box_width - 2, separator_y), 2)

        # **Extra separators for self.bag_piece_count == 6 or 2**
        if extra_separator_position == "top":
            separator_y = extended_box_y + (square_size * 0.35)  # 0.35 self.grid cells from the top
            pygame.draw.line(self.screen, self.OUTSIDE_BACKGROUND, 
                            (extended_box_x + 2, separator_y), 
                            (extended_box_x + extended_box_width - 2, separator_y), 2)

        elif extra_separator_position == "bottom":
            separator_y = extended_box_y + extended_box_height - (square_size * 0.35)  # 0.35 self.grid cells from the bottom
            pygame.draw.line(self.screen, self.OUTSIDE_BACKGROUND, 
                            (extended_box_x + 2, separator_y), 
                            (extended_box_x + extended_box_width - 2, separator_y), 2)

    def draw_stats_box(self):
        """Draws a single unified box containing TIME, SCORE, LINES, PIECES, and an additional clear text message."""

        remaining_time = None # Initialize

        width, height = self.screen.get_size()

        # Calculate square size dynamically
        square_size = min(width // self.COLS, height // (self.VISIBLE_ROWS + 1))
        grid_width = square_size * self.COLS
        grid_height = square_size * (self.VISIBLE_ROWS + 1)

        # Centering the self.grid
        margin_x = (width - grid_width) // 2
        margin_y = (height - grid_height) // 2

        # **Base stats box dimensions**
        extended_box_bottom = margin_y + self.GRID_HEIGHT
        stats_box_y = margin_y + (square_size * 6.5)  # Start below hold box
        stats_box_x = margin_x - (square_size * 5) - 10  # Left side of self.grid
        stats_box_width = square_size * 5  # Matches extended next queue width
        stats_box_height = extended_box_bottom - stats_box_y  # Default bottom alignment

        # **Calculate additional height for self.clear_text**
        font = pygame.font.Font(None, 40)
        clear_font = pygame.font.Font(None, 30)
        clear_text_render = clear_font.render(self.clear_text, True, self.clear_text_color)
        clear_text_height = clear_text_render.get_height() + (square_size * 0.5)  # Extra padding

        # **Extend stats box height for self.clear_text + one extra self.grid square**
        stats_box_height += clear_text_height + square_size  # <--- Extra square added here

        # **Draw extended stats box**
        pygame.draw.rect(self.screen, self.BLACK, (stats_box_x, stats_box_y, stats_box_width, stats_box_height))
        pygame.draw.rect(self.screen, self.GRID_LINES, (stats_box_x, stats_box_y, stats_box_width, stats_box_height), 2)

        # Calculate elapsed time in MM:SS.M format based on gamemode:
        if self.game_mode == "Blitz":
            game_duration = 180  # 3 minutes in seconds
            elapsed_time = time.time() - self.start_time
            remaining_time = max(0, game_duration - elapsed_time)  # Prevent negative time

            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            milliseconds = int((remaining_time % 1) * 10)  # Correctly scale to 0-9 range
        else:
            elapsed_time = time.time() - self.start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            milliseconds = int((elapsed_time % 1) * 10)  # Correctly scale to 0-9 range
        if remaining_time == 0:
            self.game_over_condition = "Time's Up!"
            self.game_over = True
            self.game_over_screen()


        # Format as MM:SS.M (single-digit milliseconds)
        time_display = f"{minutes:02}:{seconds:02}.{milliseconds}"

        # Divide the box into evenly spaced sections
        labels = ["TIME:", "SCORE:", "LINES:", "PIECES:"]
        values = [time_display, self.score, self.lines_cleared, self.total_pieces_placed]
        section_height = stats_box_height / 5  # Now divided into five sections (including self.clear_text space)

        for i, (label, value) in enumerate(zip(labels, values)):
            section_y = stats_box_y + (i * section_height)

            # Render text
            label_render = font.render(label, True, (255, 255, 255))
            value_render = font.render(str(value), True, (255, 255, 255))

            # Center text within its section
            label_rect = label_render.get_rect(center=(stats_box_x + stats_box_width // 2, section_y + square_size * 0.75))
            value_rect = value_render.get_rect(center=(stats_box_x + stats_box_width // 2, section_y + square_size * 2))

            # Draw text
            self.screen.blit(label_render, label_rect)
            self.screen.blit(value_render, value_rect)

        # **Draw horizontal line below "PIECES"**
        line_y = stats_box_y + (section_height * 4.1)  # Positioned just below "PIECES"
        pygame.draw.line(self.screen, (255, 255, 255), (stats_box_x + 5, line_y), (stats_box_x + stats_box_width - 5, line_y), 2)

        # **Render and draw self.clear_text below the line**
        clear_text_rect = clear_text_render.get_rect(center=(stats_box_x + stats_box_width // 2, line_y + square_size * 1.5))
        self.screen.blit(clear_text_render, clear_text_rect)

    def draw_grid(self):
        """Draws only the visible part of the Tetris self.grid, with a half-cell-high margin at the top and bottom,
        and colors those margins with self.OUTSIDE_BACKGROUND."""
        width, height = self.screen.get_size()

        # Calculate square size dynamically
        square_size = min(width // self.COLS, height // (self.VISIBLE_ROWS + 1))  # +1 ensures space for half-cell margins
        grid_width = square_size * self.COLS
        grid_height = square_size * (self.VISIBLE_ROWS + 1)  # Expanded to include margins

        # Center the self.grid in the window
        margin_x = (width - grid_width) // 2
        margin_y = (height - grid_height) // 2

        # Fill entire self.screen with self.OUTSIDE_BACKGROUND
        self.screen.fill(self.OUTSIDE_BACKGROUND)

        # Draw extra half-cell margins at the top and bottom
        top_margin_rect = pygame.Rect(margin_x, margin_y, grid_width, square_size * 0.5)
        bottom_margin_rect = pygame.Rect(margin_x, margin_y + grid_height - square_size * 0.5, grid_width, square_size * 0.5)

        pygame.draw.rect(self.screen, self.OUTSIDE_BACKGROUND, top_margin_rect)
        pygame.draw.rect(self.screen, self.OUTSIDE_BACKGROUND, bottom_margin_rect)

        # Draw self.grid background (only inside the main play area)
        pygame.draw.rect(self.screen, self.BLACK, (margin_x, margin_y + square_size * 0.5, grid_width, grid_height - square_size))

        # Get ghost piece position
        ghost_piece = self.get_ghost_piece()
        ghost_color = self.TETRIMINO_COLORS[self.current_piece_type]

        # Shift row rendering by exactly 3.5 rows to create the half-cell margins
        for row in range(4, self.ROWS):  # Start from row 4 (hide first 4 rows)
            for col in range(self.COLS):
                cell_value = self.grid[row, col]
                color = self.TETRIMINO_COLORS[cell_value] if cell_value in self.TETRIMINO_COLORS else self.BLACK

                # Correctly align each cell to create a half-cell margin
                adjusted_row = row - 3.5  # Shifts everything down by half a cell
                cell_rect = pygame.Rect(
                    margin_x + col * square_size,
                    margin_y + adjusted_row * square_size,
                    square_size,
                    square_size
                )

                pygame.draw.rect(self.screen, color, cell_rect)
                if cell_value != "X":
                    pygame.draw.rect(self.screen, self.BLACK, cell_rect, 1)
                else:
                    pygame.draw.rect(self.screen, self.GRID_LINES, cell_rect, 1)

        # Draw ghost piece (hollow outline)
        for r, c in ghost_piece:
            if 4 <= r < self.ROWS:  # Only draw ghost if in visible area
                adjusted_row = r - 3.5
                ghost_rect = pygame.Rect(
                    margin_x + c * square_size,
                    margin_y + adjusted_row * square_size,
                    square_size,
                    square_size
                )
                pygame.draw.rect(self.screen, ghost_color, ghost_rect, 2)

        # Draw current falling piece
        for r, c in self.current_piece:
            if 4 <= r < self.ROWS:  # Only draw piece if in visible area
                adjusted_row = r - 3.5
                cell_rect = pygame.Rect(
                    margin_x + c * square_size,
                    margin_y + adjusted_row * square_size,
                    square_size,
                    square_size
                )
                pygame.draw.rect(self.screen, self.TETRIMINO_COLORS[self.current_piece_type], cell_rect)
                pygame.draw.rect(self.screen, self.BLACK, cell_rect, 1)

        self.draw_hold_box()
        self.draw_next_box()
        self.draw_stats_box()

        next_box_y, next_box_height = self.draw_next_box()
        self.draw_extended_next_queue(next_box_y, next_box_height)
        pygame.display.flip()

    def draw_button(self, x, y, width, height, text, action=None, mode=None):
        """Draws a button and handles clicks."""
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()

        button_color = self.GRAY
        if x < mouse[0] < x + width and y < mouse[1] < y + height:
            button_color = self.DARK_GRAY
            if click[0] == 1 and action:
                if mode is not None:
                    action(mode)
                else:
                    action()

        pygame.draw.rect(self.screen, button_color, (x, y, width, height))
        font = pygame.font.Font(None, 36)
        text_surf = font.render(text, True, self.BLACK)
        text_rect = text_surf.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(text_surf, text_rect)

    def draw_checkbox(self, x, y, label, checked):
        """Draws a checkbox with a label. Returns the rect so we can check clicks elsewhere."""
        box_size = 20
        font = pygame.font.Font(None, 28)

        checkbox_rect = pygame.Rect(x, y, box_size, box_size)
        pygame.draw.rect(self.screen, self.WHITE, checkbox_rect, 2)

        if checked:
            pygame.draw.rect(self.screen, self.WHITE, (x + 4, y + 4, box_size - 8, box_size - 8))

        label_surface = font.render(label, True, self.WHITE)
        self.screen.blit(label_surface, (x + box_size + 10, y - 2))

        return checkbox_rect  # <-- just return the rectangle for click detection



    def reset_game_state(self):

        # Reset self.grid and movement states
        self.grid = np.full((self.ROWS, self.COLS), "X")
        self.move_left_pressed = self.move_right_pressed = self.soft_drop_pressed = False
        self.das_timer = self.arr_timer = self.soft_drop_das_timer = self.soft_drop_arr_timer = 0
        self.soft_drop_lock_timer = self.gravity_timer = self.gravity_lock_timer = self.lockout_override_timer = 0

        # Reset piece management
        self.held_piece = None
        self.hold_used = False
        self.primary_bag = []
        self.secondary_bag = []
        self.next_queue = []
        self.bag_piece_count = 0

        # Reset self.score and stats
        self.score = 0
        self.total_pieces_placed = 0
        self.b2b = False
        self.clear_combo = 0
        self.start_time = None

        if self.game_mode == "Sprint":
            self.lines_cleared = 40
        else:
            self.lines_cleared = 0
        
        if self.game_mode == "Blitz":
            self.total_pieces_placed = 600
        else:
            self.total_pieces_placed = 0

        # Reset rotation-related flags
        self.qualified_for_T_spin = False
        self.wall_kick_5_used = False

        # Reset clear text
        self.clear_text = ""
        self.clear_text_color = (255, 255, 255)
        if self.clear_text_timer is not None:
            self.clear_text_timer.cancel()
        self.clear_text_timer = None

        # Reset game over flags
        self.game_over = False
        self.game_over_condition = "Top Out!"

        # Refill the queue before spawning the first piece
        self.refill_bag()
        while len(self.next_queue) < 5:
            self.next_queue.append(self.primary_bag.pop(0))

        # Re-initialize current piece
        self.current_piece_type, self.current_piece, self.current_rotation = self.spawn_piece()


    def set_game_mode(self, mode):
        """Sets the global game mode, initializes variables differently based on mode, and starts the game."""

        self.game_mode = mode

        self.reset_game_state()

        if mode == "Sprint":
            self.lines_cleared = 40
        elif mode == "Blitz":
            self.total_pieces_placed = 600

        self.main()  # Start the game

    def start_menu(self):

        menu_running = True

        while menu_running:
            self.screen.fill(self.BLACK)

            font = pygame.font.Font(None, 50)
            title = font.render("TETRIS", True, self.WHITE)
            self.screen.blit(title, (self.DEFAULT_WIDTH // 2 - title.get_width() // 2, 100))

            self.draw_button(300, 200, 200, 50, "Sprint", action=self.set_game_mode, mode="Sprint")
            self.draw_button(300, 300, 200, 50, "Blitz", action=self.set_game_mode, mode="Blitz")
            self.draw_button(300, 400, 200, 50, "Test/Debug", action=self.set_game_mode, mode="Test")
            self.draw_button(300, 500, 200, 50, "Quit", action=pygame.quit)

            # Draw checkbox and get the rect to check clicks
            checkbox_rect = self.draw_checkbox(296, 600, "Advanced Controls", self.advanced_controls)

            # Handle input events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if checkbox_rect.collidepoint(event.pos) and not self.advanced_controls:
                        self.advanced_controls = True
                        self.DAS = 150  # Delayed Auto-Shift in milliseconds
                        self.ARR = 0  # Auto Repeat Rate in milliseconds
                        self.SOFT_DROP_DAS = 70  # Delay before repeated soft drops start (in milliseconds)
                        self.SOFT_DROP_ARR = 15  # Time between additional soft drops when held (in milliseconds)
                        print("Advanced Controls:", self.advanced_controls)
                    elif checkbox_rect.collidepoint(event.pos) and self.advanced_controls:
                        self.advanced_controls = False
                        self.DAS = 150  # Delayed Auto-Shift in milliseconds
                        self.ARR = 75  # Auto Repeat Rate in milliseconds
                        self.SOFT_DROP_DAS = 75  # Delay before repeated soft drops start (in milliseconds)
                        self.SOFT_DROP_ARR = 35  # Time between additional soft drops when held (in milliseconds)
                        print("Advanced Controls:", self.advanced_controls)

            pygame.display.update()


    def game_over_screen(self):

        font_large = pygame.font.Font(None, 60)
        font_small = pygame.font.Font(None, 36)
        running = True

        # Initialize
        lines_display = None 
        time_text = None 

        if self.game_mode != "Blitz":
            time_text = "Time Elapsed:"
        else:
            time_text = "Time Remaining:"

        if self.game_mode == "Sprint":
            lines_display = 40 - self.lines_cleared
        else:
            lines_display = self.lines_cleared


        # Calculate elapsed time in MM:SS.M format based on gamemode:
        if self.game_mode == "Blitz":
            game_duration = 180  # 3 minutes in seconds
            elapsed_time = time.time() - self.start_time
            remaining_time = max(0, game_duration - elapsed_time)  # Prevent negative time

            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            milliseconds = int((remaining_time % 1) * 10)  # Correctly scale to 0-9 range
        else:
            elapsed_time = time.time() - self.start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            milliseconds = int((elapsed_time % 1) * 10)  # Correctly scale to 0-9 range

        # Format as MM:SS.M (single-digit milliseconds)
        time_display = f"{minutes:02}:{seconds:02}.{milliseconds}"

        while running:
            self.screen.fill((0, 0, 0))

            # Title / Game over reason
            title = font_large.render(self.game_over_condition, True, (255, 255, 255))
            title_rect = title.get_rect(center=(self.DEFAULT_WIDTH // 2, 100))
            self.screen.blit(title, title_rect)

            # Stats
            lines = [
                f"Mode: {self.game_mode}",
                f"{time_text} {time_display}",
                f"Score: {self.score}",
                f"Lines Cleared: {lines_display}",
                f"Pieces Placed: {self.total_pieces_placed}",
                f"Pieces Per Second: {round(self.total_pieces_placed / elapsed_time, 2)}"
            ]

            for i, line in enumerate(lines):
                text_surface = font_small.render(line, True, (200, 200, 200))
                text_rect = text_surface.get_rect(center=(self.DEFAULT_WIDTH // 2, 180 + i * 40))
                self.screen.blit(text_surface, text_rect)

            # Draw buttons
            self.draw_button(250, 450, 140, 50, "Main Menu", action=self.start_menu)
            self.draw_button(450, 450, 140, 50, "Quit", action=pygame.quit)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            pygame.display.flip()

    def main(self):
        running = True
        self.start_time = time.time()

        while running:
            if self.game_over:
                self.game_over_screen()

            self.handle_movement()  # Handle left/right, DAS, and ARR
            self.handle_soft_drop()  # Handle soft drop, DAS, and ARR
            self.handle_gravity() # Handle gravity

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        self.move_left_pressed = True
                    elif event.key == pygame.K_d:
                        self.move_right_pressed = True
                    elif event.key == pygame.K_s:
                        self.soft_drop_pressed = True
                    elif event.key == pygame.K_w:
                        self.hard_drop()  # Hard drop immediately
                    elif event.key == pygame.K_LEFT:  # Counter-clockwise rotation
                        self.rotate_piece("L")
                    elif event.key == pygame.K_RIGHT:  # Clockwise rotation
                        self.rotate_piece("R")
                    elif event.key == pygame.K_LSHIFT:
                        self.hold_piece()  # Trigger hold mechanic

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        self.move_left_pressed = False
                    elif event.key == pygame.K_d:
                        self.move_right_pressed = False
                    elif event.key == pygame.K_s:
                        self.soft_drop_pressed = False

            self.draw_grid()
            pygame.display.flip()

        pygame.quit()

    def tick(self, dt):
        # dt = delta time, or how much virtual time passes in this frame

        self.TICK_BASED = True

        if not self.start_time: # Sets new start time if there is none.
            self.start_time = time.time()

        self.soft_drop_lock_timer += dt  # Track time before locking after soft drop
        self.gravity_timer += dt  # Tracks last gravity update
        self.gravity_lock_timer += dt  # Tracks when the piece should lock due to gravity
        self.lockout_override_timer += dt  # Track time for lockout override

        self.handle_gravity()
        self.handle_soft_drop()
        self.handle_movement()

        if self.RENDER:
            pygame.event.pump()
            self.draw_grid()
            

    def game_step(self, action_index):
        """
        Advances the game by one logical step based on the given action.
        This version avoids rendering or user input and handles Blitz timing.
        """
        if not self.start_time: # Sets new start time if there is none.
            self.start_time = time.time()

        # Execute the action using a match statement
        match action_index:
            case 0:
                pass  # No-op
            case 1: # Move left
                self.move_piece(-1, 0)     
            case 2: # Move right
                self.move_piece(1, 0)      
            case 3: # Rotate left
                self.rotate_piece("L")     
            case 4: # Rotate right
                self.rotate_piece("R")     
            case 5: # Move down one
                self.handle_soft_drop(AI=True)  
            case 6: # Hard drop
                self.hard_drop() 
            case 7: # Hold
                self.hold_piece()

        # Handle automatic game updates like gravity at a tick speed of 10ms
        self.tick(10)

        # Update game-over condition for Blitz (time expiration)
        if self.game_mode == "Blitz":
            elapsed = time.time() - self.start_time
            if elapsed >= 180:  # 3 minutes
                self.game_over = True

if __name__ == "__main__":
    game = TetrisGame()
    game.start_menu()