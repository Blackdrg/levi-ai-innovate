import logging
import numpy as np
import json
import os
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger("ppo_trainer")

from .ppo_engine import ppo_engine
from .dataset_manager import dataset_manager

class PPOTrainer:
    """
    Sovereign v21.0: Hardened PPO Training Orchestrator.
    Manages the lifecycle of evolution pulses and dataset anchoring.
    """
    def __init__(self):
        self.engine = ppo_engine
        self.metrics_path = "d:\\LEVI-AI\\logs\\evolution\\ppo_metrics.v21.json"
        os.makedirs(os.path.dirname(self.metrics_path), exist_ok=True)

    async def train_step(self, mission_id: str, reward: float):
        """
        Executes a training step, anchors the experience, 
        and triggers optimization if the swarm is ready.
        """
        logger.info(f" 🧬 [Evolution] Pulse detected for mission {mission_id}. Reward: {reward:.4f}")
        
        # 1. Update engine trajectories
        await self.engine.record_experience(mission_id, reward)
        
        # 2. Anchor the state in the hardened dataset manager
        dataset_manager.anchor_batch([{
            "mission_id": mission_id,
            "reward": reward,
            "timestamp": datetime.now().isoformat()
        }])
        
        # 3. Persist forensic telemetry
        self._persist_metrics()

    def _persist_metrics(self):
        """Persists current engine state into the HMAC-ready audit ledger."""
        metrics = {
            "version": "v21.0-EVO",
            "timestamp": datetime.now().isoformat(),
            "trajectories": len(self.engine.trajectories),
            "reward_avg": float(np.mean(self.engine.reward_history[-10:])) if self.engine.reward_history else 0.0
        }
        try:
            with open(self.metrics_path, "a") as f:
                f.write(json.dumps(metrics) + "\n")
        except Exception as e:
            logger.error(f" [Evolution] Metrics persistence failure: {e}")

ppo_trainer = PPOTrainer()
