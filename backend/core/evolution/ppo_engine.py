import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

logger = logging.getLogger(__name__)


@dataclass
class Trajectory:
    states: List[Dict[str, Any]]
    actions: List[str]
    rewards: List[float]
    log_probs: List[float]
    values: List[float]
    returns: List[float] = field(default_factory=list)


class PolicyNetwork(nn.Module):
    def __init__(self, state_dim: int = 256, hidden_dim: int = 128):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.policy_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 3),
        )
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, state: torch.Tensor):
        features = self.encoder(state)
        policy_logits = self.policy_head(features)
        policy_probs = torch.softmax(policy_logits, dim=-1)
        value = self.value_head(features)
        return policy_probs, value


class PPOEngine:
    def __init__(
        self,
        state_dim: int = 256,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        epsilon_clip: float = 0.2,
    ):
        self.state_dim = state_dim
        self.policy_net = PolicyNetwork(state_dim)
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        self.gamma = gamma
        self.epsilon_clip = epsilon_clip
        self.trajectories: List[Trajectory] = []
        self._pending_step: Optional[Dict[str, Any]] = None
        self.action_map = {
            "high_temp": 0,
            "low_temp": 1,
            "default": 2,
        }
        self.temperature_map = {
            0: 0.9,
            1: 0.2,
            2: 0.7,
        }

    def select_action(self, state: List[float] | Dict[str, Any]) -> float:
        encoded = self._encode_states([state])
        state_tensor = torch.tensor(encoded, dtype=torch.float32)
        policy_probs, value = self.policy_net(state_tensor)
        distribution = Categorical(policy_probs)
        action_tensor = distribution.sample()
        action_idx = int(action_tensor.item())
        self._pending_step = {
            "state": state if isinstance(state, dict) else {"vector": list(state)},
            "action": self._idx_to_action(action_idx),
            "log_prob": float(distribution.log_prob(action_tensor).item()),
            "value": float(value.squeeze().item()),
        }
        return self.temperature_map[action_idx]

    async def record_trajectory(self, trajectory: Trajectory):
        self.trajectories.append(trajectory)
        if len(self.trajectories) >= 10:
            await self.train_step()

    async def record_experience(self, reward: float, state: Optional[Dict[str, Any]] = None):
        """Compatibility bridge for older call sites that only emit reward."""
        if self._pending_step is None:
            base_state = state or {"context": "", "reward_only": True}
            encoded = self._encode_states([base_state])
            state_tensor = torch.tensor(encoded, dtype=torch.float32)
            policy_probs, value = self.policy_net(state_tensor)
            distribution = Categorical(policy_probs)
            action_tensor = distribution.sample()
            self._pending_step = {
                "state": base_state,
                "action": self._idx_to_action(int(action_tensor.item())),
                "log_prob": float(distribution.log_prob(action_tensor).item()),
                "value": float(value.squeeze().item()),
            }

        step = self._pending_step
        trajectory = Trajectory(
            states=[step["state"]],
            actions=[step["action"]],
            rewards=[float(reward)],
            log_probs=[float(step["log_prob"])],
            values=[float(step["value"])],
        )
        self._pending_step = None
        await self.record_trajectory(trajectory)

    async def train_step(self):
        if not self.trajectories:
            return

        batch = self.trajectories[-min(len(self.trajectories), 32):]
        for trajectory in batch:
            returns: List[float] = []
            cumulative = 0.0
            for reward in reversed(trajectory.rewards):
                cumulative = float(reward) + (self.gamma * cumulative)
                returns.insert(0, cumulative)
            trajectory.returns = returns

        all_states: List[Dict[str, Any]] = []
        all_actions: List[str] = []
        all_returns: List[float] = []
        all_old_log_probs: List[float] = []

        for trajectory in batch:
            all_states.extend(trajectory.states)
            all_actions.extend(trajectory.actions)
            all_returns.extend(trajectory.returns)
            all_old_log_probs.extend(trajectory.log_probs)

        states_tensor = torch.tensor(self._encode_states(all_states), dtype=torch.float32)
        returns_tensor = torch.tensor(all_returns, dtype=torch.float32)
        old_log_probs = torch.tensor(all_old_log_probs, dtype=torch.float32)
        actions_tensor = torch.tensor([self._action_to_idx(action) for action in all_actions], dtype=torch.long)

        total_loss = None
        for _ in range(3):
            self.optimizer.zero_grad()
            policy_probs, values = self.policy_net(states_tensor)
            values = values.squeeze(-1)

            advantages = returns_tensor - values.detach()
            distribution = Categorical(policy_probs)
            new_log_probs = distribution.log_prob(actions_tensor)

            ratio = torch.exp(new_log_probs - old_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.epsilon_clip, 1 + self.epsilon_clip) * advantages

            policy_loss = -torch.min(surr1, surr2).mean()
            value_loss = nn.functional.mse_loss(values, returns_tensor)
            entropy_bonus = distribution.entropy().mean()
            total_loss = policy_loss + (0.5 * value_loss) - (0.01 * entropy_bonus)

            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 0.5)
            self.optimizer.step()

        logger.info("✅ PPO training step complete. Loss: %.4f", float(total_loss.item()) if total_loss is not None else 0.0)
        self.trajectories = []

    def save_model(self, path: str):
        torch.save(self.policy_net.state_dict(), path)

    def load_model(self, path: str):
        self.policy_net.load_state_dict(torch.load(path, map_location="cpu"))

    def _action_to_idx(self, action: str) -> int:
        return self.action_map.get(action, 2)

    def _idx_to_action(self, idx: int) -> str:
        reverse = {value: key for key, value in self.action_map.items()}
        return reverse.get(idx, "default")

    def _encode_states(self, states: List[Dict[str, Any] | List[float]]) -> np.ndarray:
        encoded = np.zeros((len(states), self.state_dim), dtype=np.float32)
        for i, state in enumerate(states):
            if isinstance(state, list):
                arr = np.asarray(state, dtype=np.float32)
                encoded[i, : min(len(arr), self.state_dim)] = arr[: self.state_dim]
                continue

            text = str(state.get("context", ""))[:512]
            encoded[i, 0] = min(1.0, len(text.split()) / 100.0)
            encoded[i, 1] = float(state.get("complexity", 0.5))
            encoded[i, 2] = float(state.get("risk", 0.2))
            encoded[i, 3] = float(state.get("latency_ms", 0.0)) / 10000.0
            encoded[i, 4] = float(state.get("fidelity", state.get("reward", 0.5)))
            # Stable hashed text features
            for ch in text.encode("utf-8"):
                idx = 5 + (ch % (self.state_dim - 5))
                encoded[i, idx] += 1.0 / 255.0
        return encoded


ppo_engine = PPOEngine()
