import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from backend.core.v8.agents.critic import CriticAgentV8, CriticInput
from backend.services.learning.scraper import scraper
from backend.services.learning.trainer import upload_training_file, submit_finetuning_job

logger = logging.getLogger(__name__)

class UnboundEngine:
    """
    Sovereign Unbound Engine: The Intelligence layer for Phase 6.
    Filtering wisdom and generating autonomous training datasets.
    """
    
    WIZDOM_BUDGET_TOKENS = 5_000_000 # 5M tokens per week limit
    MIN_WISDOM_SCORE = 0.75
    
    def __init__(self):
        self.critic = CriticAgentV8()
        self.output_dir = Path("backend/data/training_batches")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def calculate_wisdom_density(self, title: str, content: str) -> float:
        """
        Uses CriticAgentV8 to score the 'Wisdom Density' of a content segment.
        """
        # Adapt content for CriticV8 appraisal
        input_data = CriticInput(
            goal=f"Evaluate the philosophical and architectural depth of: {title}",
            success_criteria=["High structural density", "Profound resonance", "Logical consistency"],
            response=content[:5000], # Appraise first 5000 chars
            user_input="Sovereign Audit for Unbound Training Array."
        )
        
        try:
            # We bypass the full _execute_system and use _analyze_quality for speed
            metrics = await self.critic._analyze_quality(input_data)
            score = metrics.get("quality_score", 0.5)
            logger.info(f"[Unbound] Audit result for '{title[:20]}...': {score}")
            return score
        except Exception as e:
            logger.error(f"[Unbound] Wisdom audit failed: {e}")
            return 0.4

    def generate_instruction_pair(self, content_segment: str) -> Dict[str, Any]:
        """
        Converts a wisdom-dense segment into a fine-tuning instruction pair.
        """
        # Standard Sovereign format for Llama-3-8B
        return {
            "messages": [
                {"role": "system", "content": "You are LEVI, a Sovereign AI. Your purpose is to synthesize ancient Stoic wisdom with cutting-edge system architecture."},
                {"role": "user", "content": f"Analyze and internalize the following architectural or philosophical seed: {content_segment[:1000]}"},
                {"role": "assistant", "content": f"Internalizing. This seed provides a framework for {content_segment[:200]}... [Self-Optimization Protocol Initialized]."}
            ]
        }

    async def run_unbound_cycle(self):
        """
        Orchestrates the full Scrape -> Filter -> Format -> Upload cycle.
        """
        logger.info("[Unbound] Initiating autonomous evolution cycle...")
        
        # 1. Scrape raw data
        raw_seeds = await scraper.run_cycle()
        if not raw_seeds:
            logger.warning("[Unbound] No seeds harvested. Cycle aborted.")
            return
        
        # 2. Filter for high wisdom
        hq_seeds = []
        for seed in raw_seeds:
            score = await self.calculate_wisdom_density(seed["title"], seed["content"])
            if score >= self.MIN_WISDOM_SCORE:
                hq_seeds.append(seed)
        
        logger.info(f"[Unbound] Filter complete: {len(hq_seeds)}/{len(raw_seeds)} seeds accepted.")
        
        if not hq_seeds:
            return
            
        # 3. Generate JSONL dataset
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file = self.output_dir / f"unbound_batch_{timestamp}.jsonl"
        
        with open(batch_file, "w", encoding="utf-8") as f:
            for seed in hq_seeds:
                # Split large content into chunks if needed
                pair = self.generate_instruction_pair(seed["content"])
                f.write(json.dumps(pair) + "\n")
        
        logger.info(f"[Unbound] Dataset generated: {batch_file}")
        
        # 4. Trigger Training (Optional/Gated)
        # file_id = upload_training_file(str(batch_file))
        # if file_id:
        #    submit_finetuning_job(file_id, suffix=f"unbound_{timestamp}")
        
        return str(batch_file)

# Singleton
unbound_engine = UnboundEngine()
