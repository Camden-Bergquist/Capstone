import gym
import numpy as np
import random
from gym import spaces
from game_class import TetrisGame

class TetrisEnv(gym.Env):
    def __init__(self, mode="Blitz"):
        super().__init__()

        self.mode = mode
        self.game = TetrisGame(render = False, game_mode = mode)
        self.last_score = 0
        self.last_pieces_placed = 0


        self.action_space = spaces.Discrete(8)
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(296,),
            dtype=np.float32
        )

    def reset(self):
        # Reset the game logic
        self.game.reset_game_state()
        self.last_score = 0
        self.last_pieces_placed = 0

        # Simulate one tick to process gravity/locking logic
        self.game.tick(10)

        # Reset any environment-specific counters
        self.steps = 0

        # Get and return the initial observation
        return self.get_observation()

    def step(self, action):
        # Let the game process the action and simulate time
        self.game.game_step(action)
        self.steps += 1

        # Determine if the game is done
        done = self.game.game_over

        # Compute reward
        if self.mode == "Blitz":
            reward = self.game.score - self.last_score
            self.last_score = self.game.score

        elif self.mode == "Sprint":
            if done:
                if self.game.lines_cleared == 0:
                    # Agent completed the challenge (cleared all 40 lines)
                    reward = -self.game.total_pieces_placed  # Fewer pieces = better
                else:
                    # Agent failed to complete (top-out loss). The maximum theoretical number of pieces placed in a 40-line sprint
                    # is ~226. The reward is set to 230 (a few-point buffer) minus the lines_cleared value (40 for none, 1 for 39).
                    # This means that a loss is always more punishing than the theoretically worst win, but that the AI is still
                    # Rewarded along the way for clearing lines so that it eventually (hopefully) starts winning.
                    reward = 230 - self.game.lines_cleared
            else:
                reward = 0  # No intermediate reward

        else:
            raise ValueError("Error: Mode not Blitz or Sprint.")

        # Get the next observation
        obs = self.get_observation()

        # Optional info dictionary (empty for now)
        info = {}

        return obs, reward, done, info

    def get_observation(self):
        game = self.game  # for cleaner access

        # --- 1. Grid (binary: 0 = empty, 1 = filled) ---
        grid_obs = (game.grid != "X").astype(np.float32).flatten()

        # --- 2. Current piece type ---
        piece_types = ["Z", "S", "L", "J", "O", "T", "I"]
        current_piece_onehot = np.zeros(len(piece_types), dtype=np.float32)
        if game.current_piece_type in piece_types:
            idx = piece_types.index(game.current_piece_type)
            current_piece_onehot[idx] = 1.0

        # --- 3. Current rotation ---
        rotations = [0, "R", 2, "L"]
        rotation_onehot = np.zeros(len(rotations), dtype=np.float32)
        if game.current_rotation in rotations:
            idx = rotations.index(game.current_rotation)
            rotation_onehot[idx] = 1.0

        # --- 4. Piece position ---
        if game.current_piece:
            avg_row = sum(r for r, _ in game.current_piece) / len(game.current_piece)
            avg_col = sum(c for _, c in game.current_piece) / len(game.current_piece)
        else:
            avg_row = 0
            avg_col = 0
        position = np.array([avg_row / 24, avg_col / 10], dtype=np.float32)  # Normalize

        # --- 5. Held piece ---
        hold_onehot = np.zeros(len(piece_types) + 1, dtype=np.float32)  # +1 for "no hold"
        if game.held_piece in piece_types:
            idx = piece_types.index(game.held_piece)
            hold_onehot[idx] = 1.0
        else:
            hold_onehot[-1] = 1.0  # No piece held

        # --- 6. Next queue (5 pieces) ---
        next_onehot = np.zeros((5, len(piece_types)), dtype=np.float32)
        for i, piece in enumerate(game.next_queue[:5]):
            if piece in piece_types:
                idx = piece_types.index(piece)
                next_onehot[i, idx] = 1.0
        next_flat = next_onehot.flatten()

        # --- Combine all parts ---
        observation = np.concatenate([
            grid_obs,
            current_piece_onehot,
            rotation_onehot,
            position,
            hold_onehot,
            next_flat
        ])

        return observation

