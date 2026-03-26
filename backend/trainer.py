#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""
LEVI Self-Training Pipeline v3.0 (Firestore-Native)
- Exports high-quality conversation data from Firestore
- Submits fine-tuning jobs to Together AI
- Monitors job progress and records status in Firestore
- Activates improved models automatically
- Weekly automated training cycle
"""

import os
import json
import logging
import requests  # type: ignore
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_FINETUNE = "https://api.together.xyz/v1/fine-tuning/jobs"
TOGETHER_FILES = "https://api.together.xyz/v1/files"
BASE_MODEL = "meta-llama/Llama-3-8b-chat-hf"
MIN_SAMPLES_TO_TRAIN = 150
MAX_TRAINING_EPOCHS = 2
QUALITY_THRESHOLD = 0.62  # Minimum eval score to activate model

try:
    from backend.firestore_db import db as firestore_db # type: ignore
    from backend.tasks import celery_app # type: ignore
except ImportError:
    from firestore_db import db as firestore_db # type: ignore
    try:
        from tasks import celery_app # type: ignore
    except ImportError:
        celery_app = None

def _headers() -> Dict:
    return {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json",
    }

# ─────────────────────────────────────────────
# Training Data Export
# ─────────────────────────────────────────────

def export_training_data(output_path: str = "/tmp/levi_training.jsonl",
                          min_rating: int = 4, limit: int = 2000) -> tuple:
    """Export high-quality conversation pairs from Firestore."""
    try:
        from backend.learning import export_training_data as exp_logic  # type: ignore
    except ImportError:
        from learning import export_training_data as exp_logic # type: ignore
    
    return exp_logic(output_path=output_path, min_rating=min_rating, limit=limit)

# ─────────────────────────────────────────────
# Together AI File & Job Management
# ─────────────────────────────────────────────

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
        resp = requests.get(
            f"{TOGETHER_FINETUNE}/{job_id}",
            headers=_headers(),
            timeout=15,
        )
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

# ─────────────────────────────────────────────
# Model Version Management (Firestore)
# ─────────────────────────────────────────────

def record_model_version(job_id: str, model_id: str, training_samples: int, eval_score: float = 0.0):
    """Save trained model version to Firestore."""
    version_data = {
        "job_id": job_id,
        "model_id": model_id,
        "training_samples": training_samples,
        "eval_score": eval_score,
        "is_active": False,
        "created_at": datetime.utcnow(),
    }
    firestore_db.collection("model_versions").document(model_id).set(version_data)
    logger.info(f"[Trainer] Recorded model version in Firestore: {model_id}")
    return model_id

def activate_model_version(model_id: str):
    """Set a model as active in Firestore."""
    # Deactivate currently active models
    active_docs = firestore_db.collection("model_versions").where("is_active", "==", True).get()
    for doc in active_docs:
        doc.reference.update({"is_active": False})
    
    # Activate the target model
    firestore_db.collection("model_versions").document(model_id).update({"is_active": True})

    os.environ["LEVI_ACTIVE_MODEL"] = model_id
    logger.info(f"[Trainer] Activated model version: {model_id}")

def get_active_model_id() -> Optional[str]:
    """Get active model ID from environment or Firestore."""
    env_model = os.environ.get("LEVI_ACTIVE_MODEL")
    if env_model:
        return env_model
    
    # Fallback to Firestore lookup
    active_docs = firestore_db.collection("model_versions").where("is_active", "==", True).limit(1).get()
    if active_docs:
        model_id = active_docs[0].to_dict().get("model_id")
        os.environ["LEVI_ACTIVE_MODEL"] = model_id # type: ignore
        return model_id
    return None

def get_model_history() -> List[Dict]:
    """Retrieve all model versions from Firestore."""
    docs = firestore_db.collection("model_versions").order_by("created_at", direction="DESCENDING").get()
    return [
        {
            "job_id": d.to_dict().get("job_id"),
            "model_id": d.id,
            "is_active": d.to_dict().get("is_active"),
            "training_samples": d.to_dict().get("training_samples"),
            "eval_score": d.to_dict().get("eval_score"),
            "created_at": d.to_dict().get("created_at").isoformat() if d.to_dict().get("created_at") else None,
        }
        for d in docs
    ]

# ─────────────────────────────────────────────
# Model Evaluation
# ─────────────────────────────────────────────

EVAL_PROMPTS = [
    "What is the nature of consciousness?",
    "How should I approach fear in my life?",
    "Explain the Stoic concept of the dichotomy of control.",
    "What does silence teach us that words cannot?",
    "How does one find meaning in suffering?",
]

def evaluate_model(model_id: str) -> float:
    """Evaluate a fine-tuned model. Returns 0-1 score."""
    if not TOGETHER_API_KEY:
        return 0.5

    scores = []
    for prompt in EVAL_PROMPTS:
        try:
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=_headers(),
                json={
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": "You are LEVI, a philosophical AI. Be concise and profound."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.75,
                },
                timeout=20,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()

            score = 0.5
            words = len(text.split())
            if 15 < words < 100:
                score += 0.2
            if '"' in text or "'" in text:
                score += 0.1
            if not any(c in text.lower() for c in ['sorry', 'i cannot', 'as an ai']):
                score += 0.1
            if text[0].isupper():
                score += 0.05
            if len(text) > 30:
                score += 0.05
            scores.append(min(1.0, score))
        except Exception as e:
            logger.warning(f"[Eval] Prompt failed for {model_id}: {e}")
            scores.append(0.3)

    avg = sum(scores) / len(scores) if scores else 0.5
    logger.info(f"[Eval] Model {model_id} score: {avg:.3f}")
    return avg

# ─────────────────────────────────────────────
# Generation with Active Model
# ─────────────────────────────────────────────

def generate_with_active_model(prompt: str, system_prompt: str,
                                max_tokens: int = 200) -> Optional[str]:
    """Generate text using active fine-tuned model, fall back to base Groq."""
    fine_tuned_id = get_active_model_id()

    # Try fine-tuned model via Together AI
    if fine_tuned_id and TOGETHER_API_KEY:
        try:
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=_headers(),
                json={
                    "model": fine_tuned_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.80,
                    "frequency_penalty": 0.4,
                    "presence_penalty": 0.3,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"[Trainer] Fine-tuned model failed, falling back: {e}")

    # Fall back to Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.85,
                    "frequency_penalty": 0.4,
                },
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"[Trainer] Groq fallback failed: {e}")

    return None

# ─────────────────────────────────────────────
# Celery Tasks (Firestore-Native)
# ─────────────────────────────────────────────

if celery_app:
    @celery_app.task(name="levi.trigger_training_pipeline", bind=True, max_retries=2)
    def trigger_training_pipeline(self):
        """Full self-training pipeline as Celery task using Firestore."""
        try:
            from backend.learning import get_learning_stats, export_training_data as exp_data # type: ignore
        except ImportError:
            return {"status": "skipped", "reason": "learning module missing"}
        
        try:
            stats = get_learning_stats()
            unexported = stats.get("unexported_samples", 0)

            if unexported < MIN_SAMPLES_TO_TRAIN:
                logger.info(f"[Trainer] Only {unexported} samples, need {MIN_SAMPLES_TO_TRAIN}")
                return {"status": "skipped", "samples": unexported}

            file_path, count = exp_data(min_rating=4, limit=2000)
            logger.info(f"[Trainer] Exported {count} samples")

            file_id = upload_training_file(file_path)
            if not file_id:
                return {"status": "failed", "reason": "upload_failed"}

            suffix = f"levi-{datetime.utcnow().strftime('%Y%m%d')}"
            job_id = submit_finetuning_job(file_id, suffix)
            if not job_id:
                return {"status": "failed", "reason": "job_submission_failed"}

            # Record job in Firestore
            firestore_db.collection("training_jobs").document(job_id).set({
                "job_id": job_id,
                "file_id": file_id,
                "training_samples": count,
                "status": "pending",
                "created_at": datetime.utcnow(),
            })

            # Schedule polling
            poll_training_job.apply_async(args=[job_id], countdown=300)

            return {"status": "started", "job_id": job_id, "samples": count}
        except Exception as e:
            logger.error(f"[Trainer] Pipeline failed: {e}")
            return {"status": "error", "error": str(e)}

    @celery_app.task(name="levi.poll_training_job", bind=True, max_retries=48)
    def poll_training_job(self, job_id: str):
        """Poll fine-tuning job status from Firestore every 5 minutes."""
        try:
            status_data = check_finetuning_job(job_id)
            status = status_data.get("status")

            job_ref = firestore_db.collection("training_jobs").document(job_id)
            job_doc = job_ref.get()
            
            if job_doc.exists:
                job_ref.update({"status": status})

            if status == "completed":
                model_id = status_data.get("model_id")
                if model_id:
                    eval_score = evaluate_model(model_id)
                    samples_count = job_doc.to_dict().get("training_samples", 0) if job_doc.exists else 0
                    record_model_version(job_id, model_id, samples_count, eval_score)
                    
                    if eval_score >= QUALITY_THRESHOLD:
                        activate_model_version(model_id)
                        logger.info(f"[Trainer] ✅ Model activated in Firestore: {model_id} (score={eval_score:.2f})")
                    else:
                        logger.warning(f"[Trainer] Model score {eval_score:.2f} below threshold. Not activating.")
                return {"status": "completed", "model_id": model_id}

            elif status == "failed":
                logger.error(f"[Trainer] Job failed for {job_id}: {status_data.get('error')}")
                return {"status": "failed"}

            else:
                raise self.retry(countdown=300)

        except Exception as e:
            logger.error(f"[Trainer] Polling failed for {job_id}: {e}")
            raise self.retry(countdown=300)

# Beat schedule for training
TRAINING_BEAT_SCHEDULE = {
    "weekly-training": {
        "task": "levi.trigger_training_pipeline",
        "schedule": 604800,  # 7 days
    },
}
