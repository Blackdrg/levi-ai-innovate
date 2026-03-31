"""
backend/services/orchestrator/fine_tune_tasks.py

Autonomous Fine-Tuning Orchestration for LEVI AI.
Monitors dataset readiness, exports training samples, and triggers 
LoRA fine-tuning jobs on Together AI.
"""

import os
import logging
import json
import asyncio
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from backend.learning import export_training_data, get_learning_stats
from backend.redis_client import r as redis_client, HAS_REDIS
from backend.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
BASE_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-Reference"
TRAINING_THRESHOLD = 500  # Minimum HQ samples to trigger fine-tune

async def check_fine_tune_readiness() -> bool:
    """
    Checks if we have enough new high-quality training samples to start a job.
    """
    stats = get_learning_stats()
    hq_count = stats.get("high_quality_samples", 0)
    
    # 1. Check if a job is already in progress
    is_training = redis_client.get("system:finetuning:active") == b"1" if HAS_REDIS else False
    
    # 2. LEVI v6 Phase 18: The Learning Escalation Gatekeeper
    # Only fire training if samples are high AND quality is dropping (or for structural refinement)
    from .learning_escalation import EscalationManager
    is_allowed = await EscalationManager.should_allow_finetune(hq_count)
    
    if hq_count >= TRAINING_THRESHOLD and not is_training and is_allowed:
        logger.info(f"[FineTuner] READINESS: {hq_count} samples found. Escalation Engine APPROVED.")
        return True
    return False

async def is_finetune_mandatory(avg_rating: float, hq_count: int) -> bool:
    """
    Deprecated: Replaced by EscalationManager.should_allow_finetune
    """
    return False

async def orchestrate_together_finetune():
    """
    Main orchestration logic for Together AI fine-tuning.
    """
    if not TOGETHER_API_KEY:
        logger.error("[FineTuner] TOGETHER_API_KEY mission missing.")
        return

    # 1. Export Data
    output_path = f"/tmp/levi_train_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
    path, count = export_training_data(output_path, limit=2000)
    
    if count < 100: # Final safety check
        logger.warning(f"[FineTuner] Exported only {count} samples. Scaling back.")
        return

    # 2. Upload to Together AI
    try:
        file_id = await _upload_to_together(path)
        if not file_id: return

        # 3. Create Fine-Tuning Job
        job_id = await _create_finetune_job(file_id)
        if job_id:
            # 4. Mark system as training
            if HAS_REDIS:
                redis_client.set("system:finetuning:active", "1")
                redis_client.set("system:finetuning:job_id", job_id)
                redis_client.set("system:finetuning:start_time", datetime.utcnow().isoformat())
            
            logger.info(f"[FineTuner] SUCCESS: Fine-tuning job {job_id} initiated.")
    except Exception as e:
        logger.error(f"[FineTuner] Orchestration failed: {e}")

async def _upload_to_together(file_path: str) -> Optional[str]:
    """Uploads JSONL file to Together AI Files API."""
    url = "https://api.together.xyz/v1/files"
    headers = {"Authorization": f"Bearer {TOGETHER_API_KEY}"}
    
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/jsonl")}
            data = {"purpose": "fine-tune"}
            response = await client.post(url, headers=headers, files=files, data=data, timeout=60.0)
            
            if response.status_code == 200:
                res_data = response.json()
                logger.info(f"[FineTuner] File uploaded: {res_data['id']}")
                return res_data["id"]
            else:
                logger.error(f"[FineTuner] Upload failed ({response.status_code}): {response.text}")
                return None

async def _create_finetune_job(file_id: str) -> Optional[str]:
    """Creates a LoRA fine-tuning job on Together AI."""
    url = "https://api.together.xyz/v1/fine-tuning"
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    suffix = f"levi-evolution-{datetime.utcnow().strftime('%Y%m%d')}"
    
    payload = {
        "training_file": file_id,
        "model": BASE_MODEL,
        "n_epochs": 3,
        "n_checkpoints": 1,
        "batch_size": 4,
        "learning_rate": 1e-5,
        "suffix": suffix,
        "lora_r": 8,
        "lora_alpha": 16,
        "lora_dropout": 0.05
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        if response.status_code == 200:
            res_data = response.json()
            return res_data["id"]
        else:
            logger.error(f"[FineTuner] Job creation failed ({response.status_code}): {response.text}")
            return None

async def poll_finetune_status():
    """
    Background worker task to check job status and update model switcher.
    """
    if not HAS_REDIS: return
    
    job_id = redis_client.get("system:finetuning:job_id")
    if not job_id: return
    
    job_id = job_id.decode()
    url = f"https://api.together.xyz/v1/fine-tuning/{job_id}"
    headers = {"Authorization": f"Bearer {TOGETHER_API_KEY}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            logger.info(f"[FineTuner] Job {job_id} Status: {status}")
            
            if status == "completed":
                model_id = data.get("model_output_name")
                if model_id:
                    # Closing the loop: Update Orchestrator Switcher
                    redis_client.set("system:finetuning:active", "0")
                    redis_client.set("system:finetuning:last_model_id", model_id)
                    redis_client.delete("system:finetuning:job_id")
                    logger.info(f"[FineTuner] COMPLETED: Model {model_id} is now LIVE.")
            elif status in ["failed", "cancelled"]:
                redis_client.set("system:finetuning:active", "0")
                redis_client.delete("system:finetuning:job_id")
                logger.error(f"[FineTuner] Job {job_id} {status.upper()}. Resetting.")
