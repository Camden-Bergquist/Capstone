from evotorch import Problem, Solution
from evotorch.algorithms import SNES
from evotorch.logging import StdOutLogger
from tetris_env import TetrisEnv
import torch
import torch.nn as nn
import numpy as np

class LinearMLP(nn.Module):
    def __init__(self, input_dim=536, hidden_dim=64, output_dim=1):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )

    def forward(self, x, weights):
        with torch.no_grad():
            idx = 0
            for layer in self.model:
                if isinstance(layer, nn.Linear):
                    weight_shape = layer.weight.shape
                    bias_shape = layer.bias.shape

                    weight_numel = weight_shape.numel()
                    bias_numel = bias_shape.numel()

                    layer.weight.copy_(weights[idx:idx + weight_numel].view(weight_shape))
                    idx += weight_numel

                    layer.bias.copy_(weights[idx:idx + bias_numel].view(bias_shape))
                    idx += bias_numel

            return self.model(x)  # Returns shape (N, 1) for N observations


# Step 1: Define a custom Problem class
class TetrisSprintProblem(Problem):
    def __init__(self):
        super().__init__(
            objective_sense="max",       
            solution_length=34433,  # Updated for new MLP: (536 * 64) + 64 + (64 * 1) + 1
            initial_bounds=(-1, 1),
        )
        self.env = TetrisEnv(mode="Sprint")
        self.policy_model = LinearMLP(input_dim=536, hidden_dim=64, output_dim=1)


    def _evaluate(self, solution: Solution):
        weights = solution.values
        total_reward = 0.0
        self.env.reset()  # No longer assigned to obs

        for step in range(25000):
            drop_dict = self.env.game.get_all_viable_hard_drops()
            placement_keys = list(drop_dict.keys())
            placement_grids = list(drop_dict.values())

            if not placement_keys:
                print("[DEBUG] No viable placements found. Ending episode.")
                break

            # Debug: Print number of drop options available
            # print(f"[DEBUG] Step {step:04}: {len(placement_keys)} drop options")

            # Store both current and future grid together in the observation
            current_grid = self.env.game.grid
            piece_type = self.env.game.current_piece_type
            hold = self.env.game.held_piece
            queue = self.env.game.next_queue
            current_rotation = self.env.game.current_rotation

            observations = []

            for i, future_grid in enumerate(placement_grids):

                obs_vec = self.env.get_observation(
                    grid=future_grid,
                    piece_type=piece_type,
                    rotation=current_rotation,
                    hold=hold,
                    next_queue=queue,
                    current_grid=current_grid  # <-- add current grid here
                )
                observations.append(obs_vec)

            obs_tensor = torch.tensor(np.stack(observations), dtype=torch.float32)  # (N, D)
            scores = self.policy_model(obs_tensor, weights).squeeze(dim=1)  # (N,)

            chosen_idx = torch.argmax(scores).item()
            chosen_move = placement_keys[chosen_idx]

            # Debug: Show the selected move and its score
            # print(f"[DEBUG] Chose move: {chosen_move}, score: {scores[chosen_idx].item():.4f}")

            obs, reward, done, _ = self.env.step(chosen_move)
            total_reward += reward

            if done:
                print(f"[Episode {self.env.reset_tracker} Ended] Lines Remaining: {self.env.game.lines_cleared}, Total Reward: {total_reward}, in {step + 1} steps.")
                break

        solution.set_evals(total_reward)

# Step 2: Initialize the problem
print("[SETUP] Initializing problem...")
problem = TetrisSprintProblem()

# Step 3: Set up the SNES searcher
print("[SETUP] Initializing SNES optimizer...")
searcher = SNES(problem, popsize=100, stdev_init=1.0)

# Step 4: Attach a logger to track progress
logger = StdOutLogger(searcher)

# Step 5: Run the training loop
print("[TRAINING] Starting evolutionary training...")
searcher.run(500)
print("[TRAINING] Finished training loop.")

# Step 6: Save the best solution
print("[SAVE] Saving best model...")
best = searcher.status["best"]
torch.save(best.values, "sprint_best_snes.pt")
print("[DONE] Training complete! Best model saved to sprint_best_snes.pt")
