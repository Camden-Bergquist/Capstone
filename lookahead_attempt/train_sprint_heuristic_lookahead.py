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
            _, depth_1_heuristics, _, depth_2_heuristics = self.env.game.get_all_viable_hard_drops(weights)

            if not depth_1_heuristics:
                print(f"[Step {step}] No viable placements. Ending early.")
                break

            best_combined_score = float('-inf')
            best_move = None

            for key, score1 in depth_1_heuristics.items():
                # Find all depth-2 scores associated with this depth-1 move
                depth2_scores = [score2 for (dx2, rot2, hold2, prev_key), score2 in depth_2_heuristics.items() if prev_key == key]

                # Compute the best depth-2 score, decayed by 0.95
                best_depth2 = max(depth2_scores) if depth2_scores else 0.0
                combined_score = score1 + 0.95 * best_depth2

                if combined_score > best_combined_score:
                    best_combined_score = combined_score
                    best_move = key

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

    print("[SETUP] Initializing optimizer...")
    searcher = SNES(problem, popsize=50, stdev_init=0.15)
    logger = StdOutLogger(searcher)

    print("[TRAINING] Starting evolutionary search...")
    searcher.run(50)
    print("[TRAINING] Finished.")

    best = searcher.status["best"]
    print("[RESULT] Best weights found:", best.values.tolist())