import torch
import torch.nn as nn
import torch.optim as optim
import gym
import numpy as np
from blitz_env import BlitzEnv

# Define a simple feedforward model
class PolicyNetwork(nn.Module):
    def __init__(self, input_dim, max_output_dim):
        super(PolicyNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU(),
            nn.Linear(32, max_output_dim),  # Large enough to cover max actions
            nn.Softmax(dim=-1)
        )

    def forward(self, x):
        return self.net(x)

# Training parameters
num_episodes = 1000
learning_rate = 0.005
gamma = 0.99
max_actions = 75  # Upper bound on how many actions to allow (theoretical max should be 70, but using 75 for a buffer).

# Initialize environment and model
env = BlitzEnv()
dummy_obs = env.reset()
input_dim = dummy_obs.shape[0]

model = PolicyNetwork(input_dim, max_actions)
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

for episode in range(num_episodes):
    obs = env.reset()
    done = False
    episode_rewards = []
    log_probs = []

    while not done:
        # Dynamically get viable actions
        action_dict, _ = env.game.get_all_viable_hard_drops()
        action_list = list(action_dict.keys())
        output_dim = len(action_list)

        if output_dim == 0:
            print("No viable actions found!")
            break

        # Convert observation
        obs_tensor = torch.tensor(obs, dtype=torch.float32)
        action_probs = model(obs_tensor)

        # Only keep probs for valid actions
        valid_probs = action_probs[:output_dim]
        dist = torch.distributions.Categorical(valid_probs)
        action_idx = dist.sample()
        log_prob = dist.log_prob(action_idx)

        # Step environment with selected action
        action = action_list[action_idx.item()]
        next_obs, reward, done, _ = env.step(action)

        log_probs.append(log_prob)
        episode_rewards.append(reward)
        obs = next_obs

    # Compute returns
    returns = []
    G = 0
    for r in reversed(episode_rewards):
        G = r + gamma * G
        returns.insert(0, G)
    returns = torch.tensor(returns, dtype=torch.float32)
    returns = (returns - returns.mean()) / (returns.std() + 1e-8)

    # Policy gradient update
    loss = -torch.stack(log_probs) * returns
    loss = loss.sum()

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    print(f"Episode {episode + 1}: Total Reward = {sum(episode_rewards):.2f}")
