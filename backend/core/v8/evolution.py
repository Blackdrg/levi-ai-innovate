"""
Sovereign Evolution Engine v8.
The autonomous intelligence layer of the LEVI-AI OS.
Orchestrates the Scrape -> Appraisal -> Crystallization -> Fine-Tuning cycle.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from .agents.critic import CriticAgentV8, CriticInput
from backend.services.learning.scraper import scraper
# Note: Trainer imports kept for future LoRA push enablement
# from backend.services.learning.trainer import upload_training_file, submit_finetuning_job

logger = logging.getLogger(__name__)

class EvolutionEngine:
    """
    Sovereign Evolution Engine (Unbound Array Phase 8).
    Filtering wisdom and generating autonomous training datasets for LEVI-AI.
    """
    
    WIZDOM_BUDGET_TOKENS = 5_000_000 
    MIN_WISDOM_SCORE = 0.75
    
    def __init__(self):
        self.critic = CriticAgentV8()
        self.output_dir = Path("backend/data/evolution_batches")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def calculate_wisdom_density(self, title: str, content: str) -> float:
        """
        Uses CriticAgentV8 to score the 'Wisdom Density' of a content segment.
        """
        input_data = CriticInput(
            goal=f"Evaluate the philosophical and architectural depth of: {title}",
            success_criteria=["High structural density", "Profound resonance", "Logical consistency"],
            response=content[:5000],
            user_input="Sovereign Audit for Unbound Training Array."
        )
        
        try:
            # Analyze quality via the V8 Critic's internal appraisal logic
            metrics = await self.critic._analyze_quality(input_data)
            score = metrics.get("quality_score", 0.5)
            logger.info(f"[Evolution] Wisdom density for '{title[:30]}...': {score}")
            return score
        except Exception as e:
            logger.error(f"[Evolution] Wisdom audit failure: {e}")
            return 0.4

    def generate_instruction_pair(self, content_segment: str) -> Dict[str, Any]:
        """
        Synthesizes a wisdom-dense segment into a high-fidelity instruction pair.
        """
        return {
            "messages": [
                {"role": "system", "content": "You are LEVI, a Sovereign AI. Your purpose is to synthesize ancient Stoic wisdom with cutting-edge system architecture."},
                {"role": "user", "content": f"Analyze and internalize the following architectural or philosophical seed: {content_segment[:1000]}"},
                {"role": "assistant", "content": f"Internalizing. This seed provides a framework for {content_segment[:200]}... [Neural Optimization Protocol Initialized]."}
            ]
        }

    async def run_evolution_cycle(self):
        """
        Autonomous Evolution: Scrape -> Filter -> format -> Batch.
        """
        logger.info("[Evolution] Initiating autonomous neural growth cycle...")
        
        # 1. Scrape raw data (Arxiv, GitHub, Web)
        raw_seeds = await scraper.run_cycle()
        if not raw_seeds:
            logger.warning("[Evolution] No high-fidelity seeds harvested.")
            return []
        
        # 2. Appraisal Gating
        hq_seeds = []
        for seed in raw_seeds:
            score = await self.calculate_wisdom_density(seed["title"], seed["content"])
            if score >= self.MIN_WISDOM_SCORE:
                hq_seeds.append(seed)
        
        logger.info(f"[Evolution] Appraisal complete: {len(hq_seeds)}/{len(raw_seeds)} seeds accepted.")
        
        if not hq_seeds:
            return []
            
        # 3. Batch Dataset Generation (JSONL)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file = self.output_dir / f"evolution_v8_{timestamp}.jsonl"
        
        with open(batch_file, "w", encoding="utf-8") as f:
            for seed in hq_seeds:
                pair = self.generate_instruction_pair(seed["content"])
                f.write(json.dumps(pair) + "\n")
        
        logger.info(f"[Evolution] Neural growth batch crystallized: {batch_file}")
        return [str(batch_file)]

# Global instance for the Sovereign OS
evolution_engine = EvolutionEngine()
