# pyright: reportMissingImports=false
"""
LEVI-AI Trainer Logic (v7 Sovereign)
Hardened production implementation for model evaluation,
fine-tuning job submission, and activation gating.
"""

import os
import json
import logging
import requests  # type: ignore
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from backend.db.firestore_db import db as firestore_db
from backend.services.learning.logic import export_training_data as exp_logic

logger = logging.getLogger(__name__)

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_FINETUNE = "https://api.together.xyz/v1/fine-tuning/jobs"
TOGETHER_FILES = "https://api.together.xyz/v1/files"
BASE_MODEL = "meta-llama/Llama-3-8b-chat-hf"
MIN_SAMPLES_TO_TRAIN = 150
MAX_TRAINING_EPOCHS = 2
QUALITY_THRESHOLD = 0.62  # Minimum eval score to activate model

EVAL_PROMPTS = [
    "What is the nature of consciousness?",
    "How should I approach fear in my life?",
    "Explain the Stoic concept of the dichotomy of control.",
    "What does silence teach us that words cannot?",
    "How does one find meaning in suffering?",
]

def _headers() -> Dict:
    return {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json",
    }

def upload_training_file(file_path: str) -> Optional[str]:
    """Upload JSONL file to Together AI. Returns file_id."""
    if not TOGETHER_API_KEY:
        logger.warning("[Trainer] TOGETHER_API_KEY not set")
        return None
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                TOGETHER_FILES,
                headers={"Authorization": f"Bearer {TOGETHER_API_KEY}"},
                files={"file": (os.path.basename(file_path), f, "application/jsonl")},
                data={"purpose": "fine-tune"},
                timeout=120,
            )
        resp.raise_for_status()
        file_id = resp.json()["id"]
        logger.info(f"[Trainer] Uploaded: {file_id}")
        return file_id
    except Exception as e:
        logger.error(f"[Trainer] Upload failed: {e}")
        return None

def submit_finetuning_job(file_id: str, suffix: str = "levi") -> Optional[str]:
    """Submit fine-tuning job. Returns job_id."""
    if not TOGETHER_API_KEY:
        return None
    try:
        payload = {
            "training_file": file_id,
            "model": BASE_MODEL,
            "n_epochs": MAX_TRAINING_EPOCHS,
            "suffix": suffix,
            "learning_rate": 2e-5,
            "batch_size": 8,
            "warmup_ratio": 0.05,
        }
        resp = requests.post(TOGETHER_FINETUNE, headers=_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        job_id = resp.json()["id"]
        logger.info(f"[Trainer] Job submitted: {job_id}")
        return job_id
    except Exception as e:
        logger.error(f"[Trainer] Job submission failed: {e}")
        return None

def check_finetuning_job(job_id: str) -> Dict[str, Any]:
    """Poll fine-tuning job status from Together AI."""
    if not TOGETHER_API_KEY:
        return {"status": "error"}
    try:
        resp = requests.get(f"{TOGETHER_FINETUNE}/{job_id}", headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": data.get("status", "unknown"),
            "model_id": data.get("fine_tuned_model"),
            "error": data.get("error"),
        }
    except Exception as e:
        logger.error(f"[Trainer] Status check failed: {e}")
        return {"status": "error", "message": str(e)}

def record_model_version(job_id: str, model_id: str, training_samples: int, eval_score: float = 0.0):
    """Save trained model version to Firestore."""
    version_data = {
        "job_id": job_id,
        "model_id": model_id,
        "training_samples": training_samples,
        "eval_score": eval_score,
        "is_active": False,
        "created_at": datetime.now(timezone.utc),
    }
    firestore_db.collection("model_versions").document(model_id).set(version_data)
    logger.info(f"[Trainer] Model version {model_id} registered.")
    return model_id

def activate_model_version(model_id: str):
    """Set a model as active in Firestore and Environment."""
    active_docs = firestore_db.collection("model_versions").where("is_active", "==", True).get()
    for doc in active_docs:
        doc.reference.update({"is_active": False})
    
    firestore_db.collection("model_versions").document(model_id).update({"is_active": True})
    os.environ["LEVI_ACTIVE_MODEL"] = model_id
    logger.info(f"[Trainer] Activated model version: {model_id}")

def get_active_model_id() -> Optional[str]:
    """Get active model ID from environment or Firestore."""
    env_model = os.environ.get("LEVI_ACTIVE_MODEL")
    if env_model: return env_model
    
    active_docs = firestore_db.collection("model_versions").where("is_active", "==", True).limit(1).get()
    if active_docs:
        model_id = active_docs[0].to_dict().get("model_id")
        os.environ["LEVI_ACTIVE_MODEL"] = model_id # type: ignore
        return model_id
    return None

def evaluate_model(model_id: str) -> float:
    """Evaluate a fine-tuned model against Sovereign resonance prompts."""
    if not TOGETHER_API_KEY: return 0.5
    scores = []
    for prompt in EVAL_PROMPTS:
        try:
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=_headers(),
                json={
                    "model": model_id,
                    "messages": [{"role": "system", "content": "You are LEVI, a philosophical AI."}, {"role": "user", "content": prompt}],
                    "max_tokens": 150, "temperature": 0.75,
                }, timeout=20,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()

            score = 0.5
            words = len(text.split())
            if 15 < words < 100: score += 0.2
            if '"' in text: score += 0.1
            if not any(c in text.lower() for c in ['sorry', 'i cannot', 'as an ai']): score += 0.2
            scores.append(min(1.0, score))
        except: scores.append(0.3)
    
    avg = sum(scores) / len(scores) if scores else 0.5
    logger.info(f"[Trainer] Model {model_id} evaluation score: {avg:.3f}")
    return avg

def generate_with_active_model(prompt: str, system_prompt: str, max_tokens: int = 200) -> Optional[str]:
    """Generate text using active fine-tuned model via Together AI, with Groq fallback."""
    fine_tuned_id = get_active_model_id()
    if fine_tuned_id and TOGETHER_API_KEY:
        try:
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=_headers(),
                json={
                    "model": fine_tuned_id,
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    "max_tokens": max_tokens, "temperature": 0.80,
                }, timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"[Trainer] Together AI fine-tuned model failed: {e}")

    # Fallback to Groq Primary
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    "max_tokens": max_tokens, "temperature": 0.85,
                }, timeout=10,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except: pass
    return None
