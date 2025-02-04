import numpy as np
import random

class LearningSystem:
    def __init__(self, actions):
        self.q_table = {}  # Dictionary to store Q-values
        self.actions = actions
        self.learning_rate = 0.1
        self.discount_factor = 0.95

    def choose_action(self, state):
        if state not in self.q_table:
            # Initialize Q-values for the new state
            self.q_table[state] = {action: 0 for action in self.actions}
        # Choose action with highest Q-value (or random for exploration)
        return max(self.q_table[state], key=self.q_table[state].get)

    def update(self, state, action, reward, next_state):
        if next_state not in self.q_table:
            self.q_table[next_state] = {action: 0 for action in self.actions}
        # Update Q-value using the Q-learning formula
        old_value = self.q_table[state][action]
        future_reward = max(self.q_table[next_state].values())
        self.q_table[state][action] = old_value + self.learning_rate * (
            reward + self.discount_factor * future_reward - old_value
        )

# Test Learning System
learning = LearningSystem(actions=["move_left", "move_right"])
state = "state1"
next_state = "state2"
learning.update(state, "move_right", reward=10, next_state=next_state)
print("Q-Table:", learning.q_table)
