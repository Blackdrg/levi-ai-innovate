# backend/core/evolution/prompt_optimizer.py
import logging
import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptOptimizer:
    """
    Sovereign v22.1: DSPy-style Prompt Engineering Evolution.
    Replaces PPO policy network with autonomous prompt mutation and few-shot optimization.
    Grounded in linguistic resonance rather than black-box gradients.
    """
    
    OPTIMIZED_PROMPTS_PATH = "d:\\LEVI-AI\\data\\evolution\\optimized_prompts.json"
    
    def __init__(self):
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.history: List[Dict[str, Any]] = []
        self._load_prompts()

    def _load_prompts(self):
        if os.path.exists(self.OPTIMIZED_PROMPTS_PATH):
            try:
                with open(self.OPTIMIZED_PROMPTS_PATH, 'r') as f:
                    self.prompts = json.load(f)
                logger.info(f"🧠 [Evolution] Optimized prompts loaded from {self.OPTIMIZED_PROMPTS_PATH}")
            except Exception as e:
                logger.error(f"⚠️ [Evolution] Prompt load failure: {e}")
        else:
            logger.info("ℹ️ [Evolution] Initializing with base linguistic skeletons.")

    def _save_prompts(self):
        try:
            os.makedirs(os.path.dirname(self.OPTIMIZED_PROMPTS_PATH), exist_ok=True)
            with open(self.OPTIMIZED_PROMPTS_PATH, 'w') as f:
                json.dump(self.prompts, f, indent=4)
            logger.info(f"💾 [Evolution] Evolution CRYSTALLIZED to disk.")
        except Exception as e:
            logger.error(f"❌ [Evolution] Prompt persistence failure: {e}")

    def get_optimized_prompt(self, domain: str, base_prompt: str) -> str:
        """Retrieves the evolved prompt for a domain, or returns the base."""
        if domain in self.prompts:
            evo = self.prompts[domain]
            return f"{evo['instructions']}\n\nFew-shot Examples:\n{evo['examples']}\n\n{base_prompt}"
        return base_prompt

    async def optimize_cycle(self, domain: str, trajectories: List[Dict[str, Any]]):
        """
        Linguistic Mutation Pass.
        Analyzes successes and failures to update few-shot examples and instructions.
        """
        logger.info(f"🧬 [Evolution] Optimizing prompt for domain: {domain}")
        
        # Filter high-fidelity hits
        successes = [t for t in trajectories if t.get('fidelity', 0) > 0.9]
        failures = [t for t in trajectories if t.get('fidelity', 0) < 0.7]
        
        if not successes:
            logger.info(f" [Evolution] Insufficient success data for {domain}. Skipping cycle.")
            return

        # Simple few-shot update: keep latest successful examples
        new_examples = ""
        for s in successes[-3:]:
            new_examples += f"Q: {s['input']}\nA: {s['output']}\n---\n"
            
        current = self.prompts.get(domain, {"instructions": "You are a Sovereign Agent.", "examples": ""})
        current["examples"] = new_examples
        
        # Mutation: If many failures, tweak instructions (Simulated heuristic)
        if len(failures) > 3:
            logger.warning(f" [Evolution] High failure rate in {domain}. Applying linguistic mutation...")
            current["instructions"] += " Focus on precision and forensic verifiability."
            
        self.prompts[domain] = current
        self._save_prompts()
        logger.info(f"✅ [Evolution] Domain {domain} upgraded via DSPy-style refinement.")

prompt_optimizer = PromptOptimizer()

def get_optimizer() -> PromptOptimizer:
    return prompt_optimizer
