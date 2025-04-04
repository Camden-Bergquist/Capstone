import gym
import time
import numpy as np
from gym import spaces
from game_class import TetrisGame
import json
import subprocess

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

# Initialize Game
game = TetrisGame(render=True, game_mode="Blitz")
game.reset_game_state()

for i in range(361):

    if game.game_over:
        break

    # Grab game state and pass it to Rust
    game_state = game.game_state_to_dict()
    write_compact_field_json("tetris_thinker/input.json", game_state)
    subprocess.run(["cargo", "run"], cwd="tetris_thinker") # Waits for program to finish before continuing code

    # Extract moves and run them:
    action_sequence = unpack_game_actions("tetris_thinker/selected_actions.json")
    print(f"Action Sequence: {action_sequence}")
    
    for action in action_sequence:

        match action:
            case "Hold":
                game.game_step(7)
            case "Left":
                game.game_step(1)
            case "Right":
                game.game_step(2)
            case "Ccw":
                game.game_step(3)
            case "Cw":
                game.game_step(4)
            case "SonicDrop":
                game.game_step(8)
    
    # time.sleep(0.05)
    
    game.game_step(6) # Always Hard Drop at the end of a sequence.

    # time.sleep(1)

print("360 Moves Played!")

# Empty the .json files at the end of the script.
with open("tetris_thinker/selected_actions.json", 'w') as file:
    pass
with open("tetris_thinker/input.json", 'w') as file:
    pass  # Do nothing, just open and close the file to clear it

