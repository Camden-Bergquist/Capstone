import torch
from sprint_env import SprintHeuristicEnv
from debug_env import DebugHeuristicEnv

# Article's heuristic weights
# weights = torch.tensor([-0.510066, 0.760666, -0.35663, -0.184483], dtype=torch.float32)
# Trained heuristic weights (batch size = 60, batches = 60, for 3600 total games played.)
weights = torch.tensor([-1.6576130390167236, 0.7060774564743042, -1.2531158924102783, -0.38837742805480957], dtype=torch.float32)


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
        drop_dict, drop_heuristics = env.game.get_all_viable_hard_drops(weights)

        if not drop_heuristics:
            break

        # Debug
        """ for key, heur_score in drop_heuristics.items():
            if env.game.current_piece_type == "I" and key[1] in ("L", "R"):  # vertical rotation
                print(f"[DEBUG] I-piece (vertical) move: key = {key}, score = {heur_score:.3f}") """

        best_key = max(drop_heuristics.items(), key=lambda x: x[1])[0]
        # print(f"Selected Key {best_key}.")
        obs, reward, done, _ = env.step(best_key)
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