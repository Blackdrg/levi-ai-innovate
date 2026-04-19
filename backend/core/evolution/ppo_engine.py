import logging
import os
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from .dataset_manager import dataset_manager

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from backend.services.model_registry import model_registry, ModelMetadata

logger = logging.getLogger(__name__)

@dataclass
class Trajectory:
    states: List[Dict[str, Any] | str]
    actions: List[str]
    rewards: List[float]
    log_probs: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
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
    """
    Sovereign Evolution Engine v16.3 [PPO-HARDENED].
    Manages autonomous policy refinement for cognitive parameters.
    """
    
    WEIGHTS_PATH = "d:\\LEVI-AI\\data\\evolution\\ppo_policy.v2.pt"
    
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
        self._pending_steps: Dict[str, Dict[str, Any]] = {} # keyed by mission_id
        
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
        self.reward_history: List[float] = []
        self._load_weights()

    def _load_weights(self):
        """Loads evolved weights from Sovereign storage."""
        if os.path.exists(self.WEIGHTS_PATH):
            try:
                self.policy_net.load_state_dict(torch.load(self.WEIGHTS_PATH, map_location="cpu"))
                logger.info(f"🧠 [Evolution] Evolved weights loaded from {self.WEIGHTS_PATH}")
            except Exception as e:
                logger.error(f"⚠️ [Evolution] Weight load failure: {e}")
        else:
            logger.info("ℹ️ [Evolution] Initializing from base biological priors (default weights).")

    def _save_weights(self):
        """Persists evolved weights and creates a rolling backup."""
        try:
            os.makedirs(os.path.dirname(self.WEIGHTS_PATH), exist_ok=True)
            # Create backup before saving new
            if os.path.exists(self.WEIGHTS_PATH):
                import shutil
                shutil.copy2(self.WEIGHTS_PATH, self.WEIGHTS_PATH + ".bak")
            
            torch.save(self.policy_net.state_dict(), self.WEIGHTS_PATH)
            logger.info(f"💾 [Evolution] Weights PERSISTED and BACKUP Created.")
        except Exception as e:
            logger.error(f"❌ [Evolution] Weight persistence failure: {e}")

    def select_action(self, mission_id: str, state: List[float] | Dict[str, Any]) -> float:
        """Selects a cognitive action (hyper-param) via the current policy."""
        encoded = self._encode_states([state])
        state_tensor = torch.tensor(encoded, dtype=torch.float32)
        
        with torch.no_grad():
            policy_probs, value = self.policy_net(state_tensor)
            
        distribution = Categorical(policy_probs)
        action_tensor = distribution.sample()
        action_idx = int(action_tensor.item())
        
        self._pending_steps[mission_id] = {
            "state": state if isinstance(state, dict) else {"vector": list(state)},
            "action": self._idx_to_action(action_idx),
            "log_prob": float(distribution.log_prob(action_tensor).item()),
            "value": float(value.squeeze().item()),
        }
        
        return self.temperature_map[action_idx]

    async def record_experience(self, mission_id: str, reward: float):
        """Records the outcome (reward) for a specific mission step."""
        if mission_id not in self._pending_steps:
             # Fallback if mission_id wasn't tracked (legacy support)
             return

        step = self._pending_steps.pop(mission_id)
        trajectory = Trajectory(
            states=[step["state"]],
            actions=[step["action"]],
            rewards=[float(reward)],
            log_probs=[float(step["log_prob"])],
            values=[float(step["value"])],
        )
        
        self.trajectories.append(trajectory)
        if len(self.trajectories) >= 20: # Training batch threshold
            # Transform trajectories to JSON-serializable for anchoring
            batch_data = [
                {
                    "states": t.states,
                    "actions": t.actions,
                    "rewards": t.rewards
                } for t in self.trajectories
            ]
            dataset_manager.anchor_batch(batch_data)
            await self.train_step()

    def add_trajectory(self, trajectory: Trajectory):
        """Adds a reinforced trajectory to the training buffer."""
        self.trajectories.append(trajectory)
        logger.info(f"📥 [Evolution] Trajectory added. Buffer: {len(self.trajectories)}/20")

    async def train_step(self):
        """Executes a PPO optimization cycle on collected experiences."""
        if not self.trajectories:
            return

        logger.info(f"🌪️ [Evolution] Commencing training cycle on {len(self.trajectories)} experiences...")
        
        batch = self.trajectories[:]
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
        for _ in range(3): # Epochs
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

        logger.info("✅ [Evolution] PPO cycle complete. Loss: %.4f", float(total_loss.item()) if total_loss is not None else 0.0)
        
        # 📉 Performance Tracking & Rollback
        avg_reward = np.mean([np.mean(t.rewards) for t in batch])
        self.reward_history.append(float(avg_reward))
        
        logger.info(f"📊 [Evolution] Cycle Reward: {avg_reward:.4f}")
        
        if len(self.reward_history) > 5:
            baseline = np.mean(self.reward_history[-5:-1])
            if avg_reward < (baseline * 0.8): # 20% drop
                logger.warning(f"⚠️ [Evolution] FIDELITY COLLAPSE DETECTED ({avg_reward:.4f} vs {baseline:.4f}). Triggering Atomic Rollback...")
                self._rollback()
            else:
                self._save_weights()
                self._graduate_model(avg_reward)
        else:
            self._save_weights()
            self._graduate_model(avg_reward)

    def _graduate_model(self, reward: float):
        """Graduates the current evolved weights to the system Model Registry."""
        try:
            version = f"22.0.EVO-{int(datetime.now().timestamp()) % 10000}"
            metadata = ModelMetadata(
                model_id="ppo_sovereign_core",
                version=version,
                architecture="Transformer-PPO-Evolved",
                weights_path=self.WEIGHTS_PATH,
                hash_sha256="simulated_sha256",
                created_at=datetime.now().strftime("%Y-%m-%d"),
                metrics={"avg_reward": float(reward)}
            )
            model_registry.register_model(metadata)
            logger.info(f"🎓 [Evolution] Model Registered: {metadata.model_id} v{version}")
        except Exception as e:
            logger.error(f"❌ [Evolution] Graduation failure: {e}")

        self.trajectories = []

    def _rollback(self):
        """Rolls back policy weights to the last stable state."""
        BACKUP_PATH = self.WEIGHTS_PATH + ".bak"
        if os.path.exists(BACKUP_PATH):
            self.policy_net.load_state_dict(torch.load(BACKUP_PATH, map_location="cpu"))
            logger.info("♻️ [Evolution] Rollback complete. Stable weights restored.")
        else:
            logger.error("❌ [Evolution] Rollback failed: No backup weights found.")

    def _action_to_idx(self, action: str) -> int:
        return self.action_map.get(action, 2)

    def _idx_to_action(self, idx: int) -> str:
        reverse = {value: key for key, value in self.action_map.items()}
        return reverse.get(idx, "default")

    def _encode_states(self, states: List[Dict[str, Any] | List[float] | str]) -> np.ndarray:
        encoded = np.zeros((len(states), self.state_dim), dtype=np.float32)
        for i, state in enumerate(states):
            if isinstance(state, str):
                state = {"context": state}
            
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
            for ch in text.encode("utf-8"):
                idx = 5 + (ch % (self.state_dim - 5))
                encoded[i, idx] += 1.0 / 255.0
        return encoded

ppo_engine = PPOEngine()

def get_ppo_engine() -> PPOEngine:
    return ppo_engine
