import torch
import json
import subprocess
from evotorch import Problem, Solution
from evotorch.algorithms import SNES
from evotorch.logging import StdOutLogger
from blitz_heuristic_env import BlitzHeuristicEnv
import numpy as np

def weights_to_json(filename, weight_list):

    weight_dict = {
    "back_to_back": weight_list[0],
    "bumpiness": weight_list[1],
    "bumpiness_sq": weight_list[2],
    "row_transitions": weight_list[3],
    "height": weight_list[4],
    "top_half": weight_list[5],
    "top_quarter": weight_list[6],
    "jeopardy": weight_list[7],
    "cavity_cells": weight_list[8],
    "cavity_cells_sq": weight_list[9], 
    "overhang_cells": weight_list[10], 
    "overhang_cells_sq": weight_list[11], 
    "covered_cells": weight_list[12],
    "covered_cells_sq": weight_list[13],
    "tslot": weight_list[14:18], 
    "well_depth": weight_list[18],
    "max_well_depth": weight_list[19],
    "well_column": weight_list[20:30],

    "move_time": weight_list[30],
    "wasted_t": weight_list[31],
    "b2b_clear": weight_list[32],
    "clear1": weight_list[33],
    "clear2": weight_list[34],
    "clear3": weight_list[35],
    "clear4": weight_list[36],
    "tspin1": weight_list[37],
    "tspin2": weight_list[38],
    "tspin3": weight_list[39], 
    "mini_tspin1": weight_list[40],
    "mini_tspin2": weight_list[41],
    "perfect_clear": weight_list[42],
    "combo_garbage": weight_list[43]
    }
    
    formatted_json = json.dumps(weight_dict, indent = 2)

    with open(filename, "w") as f:
        f.write(formatted_json)

def write_compact_field_json(filename, game_state):
    # Manually extract and format the 'field' array
    field = game_state.pop("field")  # Temporarily remove it from the dict

    # Serialize the field with compact row formatting
    field_str = '  "field": [\n'
    for i, row in enumerate(field):
        row_str = "    " + json.dumps(row)
        if i != len(field) - 1:
            row_str += ","
        field_str += row_str + "\n"
    field_str += "  ],"  # <--- Add comma here to separate from next key

    # Serialize the rest of the dictionary as normal
    partial_json = json.dumps(game_state, indent=2)

    # Insert field block after the opening brace
    lines = partial_json.splitlines()
    lines.insert(1, field_str)
    final_json = "\n".join(lines)

    # Write to file
    with open(filename, "w") as f:
        f.write(final_json)

def unpack_game_actions(filename):
    with open(filename, "r") as f:
        return json.load(f)

use_established_weights = True

# Define the now less-than-lightweight problem
class HeuristicTetrisProblem(Problem):
    def __init__(self, lower_bound = -100, upper_bound = 100, render_env = False):
        super().__init__(
            objective_sense="max",
            solution_length=44,  # 44 weights (technically 32 since two of them are lists).
            initial_bounds=(lower_bound, upper_bound)
        )
        self.env = BlitzHeuristicEnv(render_env)

    def _evaluate(self, solution: Solution):
        raw_weights = solution.values.cpu().numpy() # Store the weights as a list.
        rounded_weights = np.round(raw_weights).astype(np.int32) # Convert to the i32 format the thinker expects
        weights = rounded_weights.tolist()
        episode_reward = 0.0
        self.env.reset()

        # Write weights to file. Only done once per episode, which is why it's outside the loop.
        weights_to_json("tetris_thinker/weights.json", weights)

        for step in range(1000):

            # Grab game state and write it to json.
            game_state = self.env.game.game_state_to_dict()
            write_compact_field_json("tetris_thinker/input.json", game_state)

            # Call `/tetris_thinker` and get the move sequence
            subprocess.run(
                ["cargo", "run"],
                cwd="tetris_thinker",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ) # Waits for program to finish before continuing code
            best_sequence = unpack_game_actions("tetris_thinker/selected_actions.json")

            episode_reward, done, _ = self.env.step(best_sequence)

            if done:
                print(f"[Episode {self.env.reset_tracker}] Done after {step+1} steps. Reward: {episode_reward}")
                break

        solution.set_evals(episode_reward)


# Training Parameters:
use_established_weights = True
established_weights_path = "default_cold_weights.json"
render_environment = True
lower_bound, upper_bound, initial_stdev = -100, 100, 15
population_size, num_generations = 10, 10

# Set up and run the search
if __name__ == "__main__":
    print("[SETUP] Initializing Heuristic Tetris Problem...")
    problem = HeuristicTetrisProblem(lower_bound, upper_bound, render_environment)

    # If weights are being imported:
    if use_established_weights:
        # Load predefined/pretrained weights.
        with open(established_weights_path) as f:
            saved_weights = json.load(f)

        # Convert back to a flat list
        established_weights = [
            saved_weights["back_to_back"],
            saved_weights["bumpiness"],
            saved_weights["bumpiness_sq"],
            saved_weights["row_transitions"],
            saved_weights["height"],
            saved_weights["top_half"],
            saved_weights["top_quarter"],
            saved_weights["jeopardy"],
            saved_weights["cavity_cells"],
            saved_weights["cavity_cells_sq"],
            saved_weights["overhang_cells"],
            saved_weights["overhang_cells_sq"],
            saved_weights["covered_cells"],
            saved_weights["covered_cells_sq"],
            *saved_weights["tslot"],
            saved_weights["well_depth"],
            saved_weights["max_well_depth"],
            *saved_weights["well_column"],
            saved_weights["move_time"],
            saved_weights["wasted_t"],
            saved_weights["b2b_clear"],
            saved_weights["clear1"],
            saved_weights["clear2"],
            saved_weights["clear3"],
            saved_weights["clear4"],
            saved_weights["tspin1"],
            saved_weights["tspin2"],
            saved_weights["tspin3"],
            saved_weights["mini_tspin1"],
            saved_weights["mini_tspin2"],
            saved_weights["perfect_clear"],
            saved_weights["combo_garbage"]
        ]

        # Convert to a torch tensor
        init_weights = torch.tensor(established_weights, dtype=torch.float32)

        # Manually set mean of SNES to this
        print("[SETUP] Initializing SNES optimizer with established weights...")
        searcher = SNES(problem, popsize = population_size, stdev_init = initial_stdev, center_init = init_weights)

    # Use random initial weights.
    else:
        print("[SETUP] Initializing SNES optimizer with random weights...")
        searcher = SNES(problem, popsize = population_size, stdev_init = initial_stdev)

    logger = StdOutLogger(searcher)

    print("[TRAINING] Starting evolutionary search...") 
    searcher.run(num_generations)
    print("[TRAINING] Finished.")

    best = searcher.status["best"]
    print("[RESULT] Best weights found:", best.values.tolist())

    # Empty the .json files at the end of the script.
    with open("tetris_thinker/selected_actions.json", 'w') as file:
        pass
    with open("tetris_thinker/input.json", 'w') as file:
        pass
    with open("tetris_thinker/weights.json", 'w') as file:
        json.dumps({})
