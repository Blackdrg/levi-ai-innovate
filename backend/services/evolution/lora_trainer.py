"""
Sovereign Autonomous LoRA Trainer v15.0 (Engine 9).
Handles periodic fine-tuning of local models based on high-fidelity mission data.
Utilizes PEFT (Parameter-Efficient Fine-Tuning) and 4-bit quantization for local hardware efficiency.
"""

import os
import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.db.postgres import PostgresDB
from backend.db.models import Mission
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

class LoRATrainer:
    """
    Sovereign v16.1 AI Model Evolution Service.
    Transitions successful cognition into crystallized model weights.
    """
    
    TRAINING_DATA_DIR = "backend/data/training"
    MODEL_BASE = os.getenv("MODEL_BASE_PATH", "models/llama-3-8b")
    MIN_SAMPLES = 5 
    
    def __init__(self):
        os.makedirs(self.TRAINING_DATA_DIR, exist_ok=True)

    async def collect_training_samples(self) -> List[Dict[str, str]]:
        """Gathers Instruction/Response pairs from missions with fidelity > 0.95."""
        logger.info("[LoRA] Harvesting high-fidelity mission data...")
        
        async with PostgresDB._session_factory() as session:
            stmt = (
                select(Mission)
                .where(Mission.status == "completed")
                .where(Mission.fidelity_score >= 0.95)
                .order_by(Mission.updated_at.desc())
                .limit(500)
            )
            result = await session.execute(stmt)
            missions = result.scalars().all()
            
        dataset = []
        for m in missions:
            # Extract instruction/response from mission payload
            response = ""
            if isinstance(m.payload, dict):
                response = str(m.payload.get("output", ""))
            
            if response:
                dataset.append({
                    "instruction": m.objective,
                    "input": "", # Optional context
                    "output": response
                })
        
        return dataset

    async def prepare_dataset(self, samples: List[Dict[str, str]]) -> str:
        """Saves samples to a JSONL file for the training engine."""
        filename = f"training_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        path = os.path.join(self.TRAINING_DATA_DIR, filename)
        
        with open(path, "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")
        
        return path

    async def trigger_training_pulse(self, dataset_path: str):
        """
        Executes a local training pulse using the Sovereign LoRA Trainer.
        Ensures local-first model crystallization on Drive D.
        """
        logger.info(f"🔥 [LoRA] Triggering training pulse with dataset: {dataset_path}")
        
        # Path resolution in v16.2
        backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        training_script = os.path.join(backend_root, "backend", "scripts", "train_lora.py")
        
        if not os.path.exists(training_script):
            logger.error(f"❌ [LoRA] Training script missing: {training_script}")
            return

        async def run_training():
            cmd = [
                "python", training_script,
                "--dataset", dataset_path,
                "--output", f"artifacts/weights/lora/adapter_{datetime.now().strftime('%Y%m%d')}"
            ]
            
            try:
                logger.info(f"🚀 [LoRA] Launching local trainer: {' '.join(cmd)}")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    logger.info("✅ [LoRA] Training pulse SUCCESS. Model crystallized.")
                    
                    # 🪐 Sovereign v16.2: Autonomous Deployment (Reload)
                    from backend.services.local_llm import local_llm
                    # Check if GGUF export is requested (Simulated for MVP)
                    local_llm.reload_model() 
                    logger.info("🚀 [LoRA] Model RELOAD signaled to inference engine.")
                else:
                    logger.error(f"❌ [LoRA] Training pulse FAILED (Code {process.returncode}): {stderr.decode()}")
                    
            except Exception as e:
                logger.error(f"❌ [LoRA] Execution crash: {e}")

        # 🛡️ Graduation #30: Tracked Background Task
        from backend.utils.runtime_tasks import create_tracked_task
        create_tracked_task(run_training(), name=f"lora-pulse-{datetime.now().strftime('%H%M%S')}")

    async def run_maintenance_cycle(self):
        """Standard maintenance loop for LoRA fine-tuning."""
        samples = await self.collect_training_samples()
        if len(samples) >= self.MIN_SAMPLES:
            path = await self.prepare_dataset(samples)
            await self.trigger_training_pulse(path)
        else:
            logger.info(f"[LoRA] Insufficient new data ({len(samples)}/{self.MIN_SAMPLES}). Cycle deferred.")

lora_trainer = LoRATrainer()
