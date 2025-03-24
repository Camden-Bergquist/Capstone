import numpy as np
from tetris_env import TetrisEnv

# Create the environment (Blitz or Sprint)
env = TetrisEnv(mode="Blitz")

# Reset the environment and get the first observation
obs = env.reset()
print(f"Initial observation shape: {obs.shape}")

# Run a few random steps
done = False
step_count = 0

while not done and step_count < 10:
    action = env.action_space.sample()  # Random action
    obs, reward, done, info = env.step(action)

    print(f"\nStep {step_count + 1}")
    print(f"  Action: {action}")
    print(f"  Reward: {reward}")
    print(f"  Done: {done}")
    print(f"  Observation shape: {obs.shape}")

    step_count += 1

env.close()
