import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from blitz_env import BlitzEnv
import math
import random

# === Model ===
class ActionScoringModel(nn.Module):
    def __init__(self, input_dim):
        super(ActionScoringModel, self).__init__()
        self.net = nn.Sequential(   
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)

# === Action Encoder ===
def encode_action(dx, rot, hold):
    dx_encoded = np.zeros(10)  # -4 to +5
    dx_encoded[dx + 4] = 1

    rot_types = [0, "R", 2, "L"]
    rot_encoded = np.zeros(len(rot_types))
    rot_encoded[rot_types.index(rot)] = 1

    hold_encoded = np.array([1.0 if hold else 0.0])

    return np.concatenate([dx_encoded, rot_encoded, hold_encoded])

# === Shared Action Application ===
def apply_action(game, action):
    dx, rot, hold = action
    if hold:
        game.game_step(7)
    if rot == "L":
        game.game_step(3)
    elif rot == 2:
        game.game_step(3); game.game_step(3)
    elif rot == "R":
        game.game_step(3); game.game_step(3); game.game_step(3)
    if isinstance(dx, int):
        if dx < 0:
            for _ in range(abs(dx)):
                game.game_step(1)
        elif dx > 0:
            for _ in range(dx):
                game.game_step(2)
    game.game_step(6)

# === MCTS Node ===
class Node:
    def __init__(self, game, parent=None, prior=0.0, action=None):
        self.game = game
        self.parent = parent
        self.prior = prior
        self.action = action
        self.children = dict()
        self.visit_count = 0
        self.value_sum = 0.0

    def is_expanded(self):
        return len(self.children) > 0

    def value(self):
        if self.visit_count == 0:
            return 0.0
        return self.value_sum / self.visit_count

    def ucb_score(self, cpuct):
        if self.parent is None:
            return float('inf')
        q = self.value()
        u = cpuct * self.prior * math.sqrt(self.parent.visit_count) / (1 + self.visit_count)
        return q + u

    def expand(self, action_priors, valid_actions):
        for (action, prob) in zip(valid_actions, action_priors):
            sim_game = self.game.clone()
            apply_action(sim_game, action)
            if sim_game.game_over and sim_game.total_pieces_placed > 0:
                continue  # Skip actions that end the game mid-play
            self.children[action] = Node(sim_game, parent=self, prior=prob, action=action)

    def backup(self, value):
        node = self
        while node is not None:
            node.visit_count += 1
            node.value_sum += value
            node = node.parent

# === MCTS ===
class MCTS:
    def __init__(self, model, cpuct=1.0, n_simulations=25, device='cpu'):
        self.model = model
        self.cpuct = cpuct
        self.n_simulations = n_simulations
        self.device = device

    def run(self, obs, game, valid_actions):
        root = Node(game.clone(), prior=1.0)

        if not valid_actions:
            print("[MCTS WARNING] No valid actions. Returning empty root.")
            return root

        priors = self.evaluate_policy(obs, valid_actions)
        root.expand(priors, valid_actions)

        for action, child in root.children.items():
            value = float(child.game.score)
            child.backup(value)

        if not root.children:
            print("[MCTS WARNING] All moves led to top-out. Selecting random action.")
            random_action = random.choice(valid_actions)
            sim_game = game.clone()
            apply_action(sim_game, random_action)
            root.children[random_action] = Node(sim_game, parent=root, prior=1.0, action=random_action)

        print("\n[MCTS] Action Scores and Visit Counts:")
        for action, child in root.children.items():
            print(f"Action: {action}, Score: {child.game.score}, Visits: {child.visit_count}")
        print("-" * 40)

        return root

    def evaluate_policy(self, obs, valid_actions):
        num_actions = len(valid_actions)
        priors = np.ones(num_actions, dtype=np.float32) / num_actions
        return priors

    def select_child(self, node):
        best_score = -float('inf')
        best_action, best_child = None, None
        for action, child in node.children.items():
            score = child.ucb_score(self.cpuct)
            if score > best_score:
                best_score = score
                best_action, best_child = action, child
        return best_action, best_child

    def get_policy_distribution(self, root, temperature=1.0):
        visits = np.array([child.visit_count for child in root.children.values()], dtype=np.float32)
        actions = list(root.children.keys())

        if visits.sum() == 0:
            print("[MCTS WARNING] All children have zero visits — defaulting to uniform probs.")
            probs = np.ones(len(actions), dtype=np.float32) / len(actions)
            return actions, probs

        scores = np.array([child.game.score for child in root.children.values()])
        best_idx = np.argmax(scores)
        best_action = actions[best_idx]
        best_score = scores[best_idx]

        probs = np.zeros(len(actions), dtype=np.float32)
        probs[best_idx] = 1.0

        print(f"[MCTS] Selected action: {best_action}, Score: {best_score}")
        return actions, probs

# === Training Loop ===
def main():
    env = BlitzEnv()
    obs = env.reset()
    obs_dim = obs.shape[0]
    action_dim = 15  # dx(10) + rot(4) + hold(1)
    input_dim = obs_dim + action_dim

    model = ActionScoringModel(input_dim)
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    mcts = MCTS(model, n_simulations=25)

    num_episodes = 100
    for episode in range(num_episodes):
        obs = env.reset()
        done = False
        total_reward = 0

        while not done:
            action_dict, _ = env.game.clone().get_all_viable_hard_drops()
            valid_actions = list(action_dict.keys())
            root = mcts.run(obs, env.game, valid_actions)
            actions, probs = mcts.get_policy_distribution(root)

            action_idx = np.random.choice(len(actions), p=probs)
            action = actions[action_idx]

            next_obs, reward, done, _ = env.step(action)
            total_reward += reward
            obs = next_obs

        print(f"Episode {episode+1}: Total Score = {total_reward:.2f}")

if __name__ == "__main__":
    main()
