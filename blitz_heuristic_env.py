import gym
import time
import numpy as np
from gym import spaces
from game_class import TetrisGame

class BlitzHeuristicEnv(gym.Env):
    def __init__(self):
        super().__init__()

        self.game = TetrisGame(render=True, game_mode="Blitz")
        self.game.lines_cleared = 360 # Two pieces per second
        self.reset_tracker = 0

        self.action_space = None  # Rust script selecting move.

    def reset(self):
        self.game.reset_game_state()
        self.reset_tracker += 1
        print(f"[RESET] New game started.")

        # Force a tick to process piece spawn
        self.game.tick(100)
        self.steps = 0

        return

    def step(self, action_sequence):
        self.steps += 1

        # Small sleep on startup
        # if self.steps == 1:
        #    time.sleep(2.0)

        for action in action_sequence:

            match action:
                case "Hold":
                    self.game.game_step(7)
                case "Left":
                    self.game.game_step(1)
                case "Right":
                    self.game.game_step(2)
                case "Ccw":
                    self.game.game_step(3)
                case "Cw":
                    self.game.game_step(4)
                case "SonicDrop":
                    self.game.game_step(8)

        # Always hard drop to lock the piece at the end of a sequence.
        self.game.game_step(6)

        # Check for game over and set reward.
        done = self.game.game_over
        reward = self.game.score

        info = {} # Placeholder in case it's wanted down the line.

        # Time between actions (comment out when training)
        # time.sleep(0.1)

        return reward, done, info

