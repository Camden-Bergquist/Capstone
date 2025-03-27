import gym
import time
import numpy as np
from gym import spaces
from game_class import TetrisGame

class TetrisEnv(gym.Env):
    def __init__(self, mode="Blitz"):
        super().__init__()

        self.mode = mode
        self.game = TetrisGame(render = True, game_mode = mode)
        self.last_score = 0
        self.last_pieces_placed = 0
        self.last_lines_cleared = 0
        self.reset_tracker = 0

        self.action_space = None # No actions to partake after making choice

    def reset(self):
        # Reset the game logic
        self.game.reset_game_state()
        self.last_score = 0
        self.last_pieces_placed = 0
        self.last_lines_cleared = self.game.lines_cleared
        self.reset_tracker += 1
        print(f"Commencing with reset.")

        # Simulate one tick to process gravity/locking logic
        self.game.tick(100)

        # Reset any environment-specific counters
        self.steps = 0

        # Get and return the initial observation
        return self.get_observation()

    def step(self, action_tuple):
        """
        Executes the planned sequence to reach (dx, rotation), drops the piece,
        and returns (observation, reward, done, info) per Gym format.
        """
        self.steps += 1
        dx, rotation = action_tuple

        # --- Rotation ---
        match rotation:
            case "L":
                self.game.game_step(3)
            case 2:
                for _ in range(2):
                    self.game.game_step(3)
            case "R":
                for _ in range(3):
                    self.game.game_step(3)

        # --- Horizontal movement or hold ---
        if dx == "Hold":
            self.game.game_step(7)
        elif isinstance(dx, int):
            if dx < 0:
                for _ in range(abs(dx)):
                    self.game.game_step(1)  # move left
            elif dx > 0:
                for _ in range(dx):
                    self.game.game_step(2)  # move right

        # --- Hard drop ---
        self.game.game_step(6)

        # --- Reward / done ---
        done = self.game.game_over
        reward = 0

        if self.mode == "Blitz":
            reward = self.game.score - self.last_score
            self.last_score = self.game.score

        elif self.mode == "Sprint":
            lines_cleared_now = self.last_lines_cleared - self.game.lines_cleared
            self.last_lines_cleared = self.game.lines_cleared
            

            if done:
                if self.game.lines_cleared == 0:
                    reward = -self.game.total_pieces_placed
                else:
                    reward = -2650 + self.game.total_pieces_placed
            else:
                reward += lines_cleared_now * 500
                reward += 0.005 * self.game.lock_reward
                if self.game.flat_placement:
                    reward += 3
                    # print("Flat Placement Detected!") # Debug
                if self.game.height_gap:
                    reward -= 0.5
                else:
                    reward += 0.25
                    # print("Height Gap of 8 or More Detected!") # Debug
                # print(f"Lock Reward Awarded: {0.01 * self.game.lock_reward}")
                # print(f"Lines Cleared Now: {lines_cleared_now}. Lines Remaining: {self.game.lines_cleared}")
                if lines_cleared_now:
                    print(f"Line(s) Cleared! Amount: {lines_cleared_now}.")

        else:
            raise ValueError("Error: Mode not Blitz or Sprint.")

        obs = self.get_observation()
        info = {}

        # Adds a buffer in-between steps so that training is more-easily monitored.
        # time.sleep(0.5) 

        return obs, reward, done, info

    def get_observation(self, grid=None, piece_type=None, rotation=None, hold=None, next_queue=None, current_grid=None):
        """
        Builds an observation from either:
        - the current game state (if no arguments are passed)
        - a hypothetical state (if arguments are passed)
        - or a combination of current grid and future grid for forward evaluation
        """
        piece_types = ["Z", "S", "L", "J", "O", "T", "I"]
        rotations = [0, "R", 2, "L"]

        # Fallbacks to current game state if not provided
        if current_grid is None:
            current_grid = self.game.grid
        if grid is None:
            grid = self.game.grid
        if piece_type is None:
            piece_type = self.game.current_piece_type
        if rotation is None:
            rotation = self.game.current_rotation
        if hold is None:
            hold = self.game.held_piece
        if next_queue is None:
            next_queue = self.game.next_queue

        # --- 1. Current grid (binary: 0 = empty, 1 = filled) ---
        grid_obs_current = (current_grid != "X").astype(np.float32).flatten()

        # --- 2. Future grid (resulting from hypothetical drop) ---
        grid_obs_future = (grid != "X").astype(np.float32).flatten()

        # --- 3. Current piece type ---
        current_piece_onehot = np.zeros(len(piece_types), dtype=np.float32)
        if piece_type in piece_types:
            idx = piece_types.index(piece_type)
            current_piece_onehot[idx] = 1.0

        # --- 4. Current rotation ---
        rotation_onehot = np.zeros(len(rotations), dtype=np.float32)
        if rotation in rotations:
            idx = rotations.index(rotation)
            rotation_onehot[idx] = 1.0

        # --- 5. Placeholder position (not used for future grids) ---
        position = np.array([0.0, 0.5], dtype=np.float32)

        # --- 6. Held piece ---
        hold_onehot = np.zeros(len(piece_types) + 1, dtype=np.float32)  # +1 for "no hold"
        if hold in piece_types:
            idx = piece_types.index(hold)
            hold_onehot[idx] = 1.0
        else:
            hold_onehot[-1] = 1.0  # No piece held

        # --- 7. Next queue (5 pieces) ---
        next_onehot = np.zeros((5, len(piece_types)), dtype=np.float32)
        for i, piece in enumerate(next_queue[:5]):
            if piece in piece_types:
                idx = piece_types.index(piece)
                next_onehot[i, idx] = 1.0
        next_flat = next_onehot.flatten()

        # --- Combine all parts ---
        observation = np.concatenate([
            grid_obs_current,        # 240
            grid_obs_future,         # 240
            current_piece_onehot,    # 7
            rotation_onehot,         # 4
            position,                # 2
            hold_onehot,             # 8
            next_flat                # 35
        ])

        return observation



