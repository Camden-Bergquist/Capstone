import torch
from sprint_env_lookahead import SprintHeuristicEnv
from debug_env import DebugHeuristicEnv

# Article's heuristic weights
# weights = torch.tensor([-0.510066, 0.760666, -0.35663, -0.184483], dtype=torch.float32)

# Trained heuristic weights [current best]. Batch size = 60, batches = 60, for 3600 total games played.
weights = torch.tensor([-1.6576130390167236, 0.7060774564743042, -1.2531158924102783, -0.38837742805480957], dtype=torch.float32)

# Trained heuristic weights, now with hold piece implementation. Batch size = 100, batches = 75, for 7500 total games played.
# Seems to play worse (slightly higher piece variance) than the first one.
# weights = torch.tensor([-1.176843285560608, 1.0206447839736938, -3.090824604034424, -0.2730691134929657], dtype=torch.float32)

# Number of games to test
num_games = 10
mode = "Sprint"
results = []

for game_index in range(num_games):
    if mode == "Sprint":
        env = SprintHeuristicEnv()
    elif mode == "Debug":
        env = DebugHeuristicEnv()

    obs = env.reset()
    total_reward = 0.0

    for step in range(1000000):  # Max steps per game
        _, depth_1_heuristics, _, depth_2_heuristics = env.game.get_all_viable_hard_drops(weights)

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

        obs, reward, done, _ = env.step(best_move)
        total_reward += reward

        if done:
            break

    results.append({
        "game": game_index + 1,
        "reward": total_reward,
        "lines_remaining": env.game.lines_cleared,
        "pieces_placed": env.game.total_pieces_placed
    })

# Display the results
import pandas as pd
df = pd.DataFrame(results)
print(df)