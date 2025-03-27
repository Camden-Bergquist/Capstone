import torch
from evotorch import Problem, Solution
from evotorch.algorithms import SNES
from evotorch.logging import StdOutLogger
from sprint_env import SprintHeuristicEnv
import numpy as np

# Define the lightweight problem
class HeuristicTetrisProblem(Problem):
    def __init__(self):
        super().__init__(
            objective_sense="max",
            solution_length=4,  # a, b, c, d
            initial_bounds=(-1.0, 1.0)
        )
        self.env = SprintHeuristicEnv()

    def _evaluate(self, solution: Solution):
        weights = solution.values.cpu().numpy()
        total_reward = 0.0
        self.env.reset()

        for step in range(1000):
            _, drop_heuristics = self.env.game.get_all_viable_hard_drops(weights)

            if not drop_heuristics:
                print(f"[Step {step}] No viable placements. Ending early.")
                break

            # Choose best move based on heuristic score
            best_move = max(drop_heuristics.items(), key=lambda x: x[1])[0]

            _, reward, done, _ = self.env.step(best_move)
            total_reward += reward

            if done:
                print(f"[Episode {self.env.reset_tracker}] Done after {step+1} steps. Reward: {total_reward}")
                break

        solution.set_evals(total_reward)

# Set up and run the search
if __name__ == "__main__":
    print("[SETUP] Initializing Heuristic Tetris Problem...")
    problem = HeuristicTetrisProblem()

    print("[SETUP] Initializing SNES optimizer...")
    searcher = SNES(problem, popsize=60, stdev_init=0.5)
    logger = StdOutLogger(searcher)

    print("[TRAINING] Starting evolutionary search...")
    searcher.run(60)
    print("[TRAINING] Finished.")

    best = searcher.status["best"]
    print("[RESULT] Best weights found:", best.values.tolist())