import gym
import time
import numpy as np
from gym import spaces
from game_class import TetrisGame

class SprintHeuristicEnv(gym.Env):
    def __init__(self):
        super().__init__()

        self.game = TetrisGame(render=True, game_mode="Sprint")
        self.last_lines_cleared = 0
        self.reset_tracker = 0

        self.action_space = None  # AI chooses from dictionary keys

    def reset(self):
        self.game.reset_game_state()
        self.last_lines_cleared = self.game.lines_cleared
        self.reset_tracker += 1
        print(f"[RESET] New game started.")

        # Force a tick to process piece spawn
        self.game.tick(100)
        self.steps = 0

        return self.get_observation()

    def step(self, action_tuple):
        self.steps += 1
        dx, rotation, hold = action_tuple

        # Small sleep on startup
        if self.steps == 1:
            time.sleep(2.0)

        # Hold
        if hold:
            self.game.game_step(7)

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
                    self.game.game_step(1)
            elif dx > 0:
                for _ in range(dx):
                    self.game.game_step(2)

        # --- Hard drop ---
        self.game.game_step(6)

        # --- Reward calculation ---
        done = self.game.game_over
        reward = 0

        # Holdover
        # lines_cleared_now = self.last_lines_cleared - self.game.lines_cleared
        # self.last_lines_cleared = self.game.lines_cleared

        if done:
            lines_actually_cleared = abs(40 - self.game.lines_cleared) # reverse the lines_cleared value because it counts down in sprint
            if self.game.lines_cleared == 0:
                reward = -self.game.total_pieces_placed # Maximum theoretical value of -100
            else:
                reward = self.game.total_pieces_placed + (lines_actually_cleared * 5) - 550 
                ## The -450 calculated based on the following logic:
                    # We're rewarding piece placements on a loss, and punishing them on a win. To offset this, roughly 350 is
                    # subtracted from the score, as in theory, it isn't possible to lose a game of sprint AND place ~230+ pieces—
                    # -100 to offset the base penalized pieces placed, -230 to offset the max theoretical, and an extra -20 as a buffer.
                    # We're rewarding lines cleared on a loss, but not on a win. A win necessarily implies 40 lines cleared (+200),
                    # and so an extra -200 is added to offset this and make a consistent starting value.

        # Unused holdover from last version of script, but keeping it in case I want it later.
        """ else:
            reward += lines_cleared_now * 5
            reward += 0.005 * self.game.lock_reward
            if self.game.flat_placement:
                reward += 3
            if self.game.height_gap:
                reward -= 0.5
            else:
                reward += 0.25
            if lines_cleared_now:
                print(f"Line(s) Cleared: {lines_cleared_now}") """

        obs = self.get_observation()
        info = {}

        # Time between actions (comment out when training)
        time.sleep(0.1)

        return obs, reward, done, info

    def get_observation(self):
        piece_types = ["Z", "S", "L", "J", "O", "T", "I"]
        rotations = [0, "R", 2, "L"]

        # Current grid (binary: 0 = empty, 1 = filled)
        grid_obs = (self.game.grid != "X").astype(np.float32).flatten()

        # Current piece type (onehot)
        current_piece_onehot = np.zeros(len(piece_types), dtype=np.float32)
        if self.game.current_piece_type in piece_types:
            current_piece_onehot[piece_types.index(self.game.current_piece_type)] = 1.0

        # Current rotation (onehot)
        rotation_onehot = np.zeros(len(rotations), dtype=np.float32)
        if self.game.current_rotation in rotations:
            rotation_onehot[rotations.index(self.game.current_rotation)] = 1.0

        # Position (placeholder)
        position = np.array([0.0, 0.5], dtype=np.float32)

        # Hold piece onehot
        hold_onehot = np.zeros(len(piece_types) + 1, dtype=np.float32)
        if self.game.held_piece in piece_types:
            hold_onehot[piece_types.index(self.game.held_piece)] = 1.0
        else:
            hold_onehot[-1] = 1.0

        # Next queue (5 pieces = 5 combined onehot lists)
        next_onehot = np.zeros((5, len(piece_types)), dtype=np.float32)
        for i, piece in enumerate(self.game.next_queue[:5]):
            if piece in piece_types:
                next_onehot[i, piece_types.index(piece)] = 1.0
        next_flat = next_onehot.flatten()

        # Combine all parts
        observation = np.concatenate([
            grid_obs, # 240
            current_piece_onehot, # 7
            rotation_onehot, # 4
            position, # 2
            hold_onehot, # 8
            next_flat # 35
        ])

        return observation
