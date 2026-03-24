# pyright: reportMissingImports=false
"""
LEVI Self-Training Pipeline
Submits fine-tuning jobs to Together AI, tracks model versions,
and hot-switches to improved models automatically.
"""

import os
import json
import logging
import requests  # type: ignore
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from celery import Celery  # type: ignore

logger = logging.getLogger(__name__)

TOGETHER_API_KEY   = os.getenv("TOGETHER_API_KEY")
TOGETHER_FINETUNE  = "https://api.together.xyz/v1/fine-tuning/jobs"
TOGETHER_FILES     = "https://api.together.xyz/v1/files"
BASE_MODEL         = "meta-llama/Meta-Llama-3-8B-Instruct"
MIN_SAMPLES_TO_TRAIN = 200    # minimum high-quality samples before triggering a training run
FINETUNE_POLL_SEC    = 300    # check job status every 5 minutes
MAX_TRAINING_EPOCHS  = 3
QUALITY_THRESHOLD    = 0.62

# ─────────────────────────────────────────────
# Celery app reference (imported from tasks.py)
# ─────────────────────────────────────────────
try:
    from tasks import celery_app  # type: ignore
except ImportError:
    from backend.tasks import celery_app  # type: ignore


# ─────────────────────────────────────────────
# 1. TRAINING JOB SUBMISSION
# ─────────────────────────────────────────────
def _together_headers() -> Dict:
    return {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json",
    }


def upload_training_file(file_path: str) -> Optional[str]:
    """Upload a JSONL training file to Together AI. Returns file_id."""
    if not TOGETHER_API_KEY:
        logger.warning("[Trainer] TOGETHER_API_KEY not set — skipping upload.")
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
        logger.info(f"[Trainer] Uploaded training file: {file_id}")
        return file_id
    except Exception as e:
        logger.error(f"[Trainer] File upload failed: {e}")
        return None


def submit_finetuning_job(file_id: str, suffix: str = "levi") -> Optional[str]:
    """
    Submit a fine-tuning job on Together AI.
    Returns the job_id if successful.
    """
    if not TOGETHER_API_KEY:
        return None
    try:
        payload = {
            "training_file": file_id,
            "model": BASE_MODEL,
            "n_epochs": MAX_TRAINING_EPOCHS,
            "suffix": suffix,
            "learning_rate": 1e-5,
            "batch_size": 16,
        }
        resp = requests.post(TOGETHER_FINETUNE, headers=_together_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        job_id = resp.json()["id"]
        logger.info(f"[Trainer] Fine-tuning job submitted: {job_id}")
        return job_id
    except Exception as e:
        logger.error(f"[Trainer] Fine-tuning submission failed: {e}")
        return None


def check_finetuning_job(job_id: str) -> Dict[str, Any]:
    """Poll the status of a fine-tuning job."""
    if not TOGETHER_API_KEY:
        return {"status": "error", "message": "No API key"}
    try:
        resp = requests.get(
            f"{TOGETHER_FINETUNE}/{job_id}",
            headers=_together_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": data.get("status", "unknown"),        # pending, running, completed, failed
            "model_id": data.get("fine_tuned_model"),       # set when completed
            "created_at": data.get("created_at"),
            "finished_at": data.get("finished_at"),
            "error": data.get("error"),
        }
    except Exception as e:
        logger.error(f"[Trainer] Job status check failed: {e}")
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────
# 2. MODEL VERSION MANAGEMENT
# ─────────────────────────────────────────────
def record_model_version(db, job_id: str, model_id: str, training_samples: int):
    """Save a successfully trained model version to the database."""
    try:
        from training_models import ModelVersion  # type: ignore
    except ImportError:
        from backend.training_models import ModelVersion  # type: ignore

    version = ModelVersion(
        job_id=job_id,
        model_id=model_id,
        training_samples=training_samples,
        is_active=False,
        created_at=datetime.utcnow(),
        eval_score=None,
    )
    db.add(version)
    db.commit()
    logger.info(f"[Trainer] Recorded model version {model_id}")
    return version


def activate_model_version(db, model_id: str):
    """Switch the active model to a new fine-tuned version."""
    try:
        from training_models import ModelVersion  # type: ignore
    except ImportError:
        from backend.training_models import ModelVersion  # type: ignore

    # Deactivate all
    db.query(ModelVersion).update({"is_active": False})
    # Activate target
    db.query(ModelVersion).filter(ModelVersion.model_id == model_id).update({"is_active": True})
    db.commit()
    # Update env-level override so generation.py picks it up
    os.environ["LEVI_ACTIVE_MODEL"] = model_id
    logger.info(f"[Trainer] Activated model: {model_id}")


def get_active_model_id() -> Optional[str]:
    """
    Returns the current fine-tuned model ID if available,
    otherwise None (falls back to base Groq Llama3).
    """
    return os.environ.get("LEVI_ACTIVE_MODEL")


def get_model_history(db) -> List[Dict]:
    """Return all model versions sorted newest first."""
    try:
        from training_models import ModelVersion  # type: ignore
    except ImportError:
        from backend.training_models import ModelVersion  # type: ignore

    versions = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()
    return [
        {
            "job_id": v.job_id,
            "model_id": v.model_id,
            "is_active": v.is_active,
            "training_samples": v.training_samples,
            "eval_score": v.eval_score,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


# ─────────────────────────────────────────────
# 3. MODEL EVALUATION (simple A/B scoring)
# ─────────────────────────────────────────────
def evaluate_candidate_model(model_id: str, eval_prompts: Optional[List[str]] = None) -> float:
    """
    Test a fine-tuned model against a small eval set.
    Returns average response quality score (0-1).
    Falls back to 0.5 if API unavailable.
    """
    if not TOGETHER_API_KEY:
        return 0.5

    if eval_prompts is None:
        eval_prompts = [
            "What is the meaning of consciousness?",
            "Give me wisdom about failure.",
            "How should I approach uncertainty in life?",
            "What does the Stoic philosophy teach about control?",
            "Describe the relationship between silence and wisdom.",
        ]

    scores = []
    for prompt in eval_prompts:
        try:
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=_together_headers(),
                json={
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": "You are LEVI, a philosophical AI muse. Be concise and profound."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 120,
                    "temperature": 0.7,
                },
                timeout=20,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()

            # Simple quality heuristics
            words = len(text.split())
            score = 0.5
            if 15 < words < 80:   score += 0.2
            if '"' in text:        score += 0.1
            if '—' in text:        score += 0.1
            if text[0].isupper():  score += 0.05
            if 'sorry' not in text.lower() and 'cannot' not in text.lower(): score += 0.05
            scores.append(min(1.0, score))
        except Exception as e:
            logger.warning(f"[Trainer] Eval prompt failed: {e}")
            scores.append(0.3)

    avg = sum(scores) / len(scores) if scores else 0.5
    logger.info(f"[Trainer] Model {model_id} eval score: {avg:.3f}")
    return avg


# ─────────────────────────────────────────────
# 4. CELERY TASKS FOR FULL PIPELINE
# ─────────────────────────────────────────────
@celery_app.task(name="levi.trigger_training_pipeline", bind=True, max_retries=2)
def trigger_training_pipeline(self):
    """
    Full self-training cycle:
    1. Check if enough new data exists
    2. Export training JSONL
    3. Upload to Together AI
    4. Submit fine-tuning job
    5. Store job ID for later polling
    """
    try:
        from db import SessionLocal  # type: ignore
        from learning import export_training_data, get_learning_stats  # type: ignore
        from training_models import TrainingJob  # type: ignore
    except ImportError:
        from backend.db import SessionLocal  # type: ignore
        from backend.learning import export_training_data, get_learning_stats  # type: ignore
        from backend.training_models import TrainingJob  # type: ignore

    db = SessionLocal()
    try:
        stats = get_learning_stats(db)
        unexported = stats.get("unexported_samples", 0)

        if unexported < MIN_SAMPLES_TO_TRAIN:
            logger.info(f"[Trainer] Only {unexported} unexported samples, need {MIN_SAMPLES_TO_TRAIN}. Skipping.")
            return {"status": "skipped", "reason": "insufficient_data", "samples": unexported}

        # Export data
        file_path, count = export_training_data(db, min_rating=4, limit=2000)
        logger.info(f"[Trainer] Exported {count} samples for training")

        # Upload file
        file_id = upload_training_file(file_path)
        if not file_id:
            return {"status": "failed", "reason": "file_upload_failed"}

        # Submit job
        job_id = submit_finetuning_job(file_id, suffix=f"levi-{datetime.utcnow().strftime('%Y%m%d')}")
        if not job_id:
            return {"status": "failed", "reason": "job_submission_failed"}

        # Record pending job
        job = TrainingJob(
            job_id=job_id,
            file_id=file_id,
            training_samples=count,
            status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()

        # Schedule polling
        poll_training_job.apply_async(args=[job_id], countdown=FINETUNE_POLL_SEC)
        logger.info(f"[Trainer] Training pipeline started. Job: {job_id}")
        return {"status": "started", "job_id": job_id, "samples": count}

    finally:
        db.close()


@celery_app.task(name="levi.poll_training_job", bind=True, max_retries=48)
def poll_training_job(self, job_id: str):
    """
    Poll a fine-tuning job until it completes or fails.
    Retries every 5 minutes, up to 4 hours.
    """
    try:
        from db import SessionLocal  # type: ignore
        from training_models import TrainingJob  # type: ignore
    except ImportError:
        from backend.db import SessionLocal  # type: ignore
        from backend.training_models import TrainingJob  # type: ignore

    db = SessionLocal()
    try:
        status_data = check_finetuning_job(job_id)
        status = status_data.get("status")

        job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
        if job:
            job.status = status
            db.commit()

        logger.info(f"[Trainer] Job {job_id} status: {status}")

        if status == "completed":
            model_id = status_data.get("model_id")
            if model_id:
                # Evaluate before activating
                eval_score = evaluate_candidate_model(model_id)
                version = record_model_version(db, job_id, model_id, job.training_samples if job else 0)
                version.eval_score = eval_score
                db.commit()

                if eval_score >= QUALITY_THRESHOLD:  # only activate if quality threshold met
                    activate_model_version(db, model_id)
                    logger.info(f"[Trainer] ✅ New model activated: {model_id} (score={eval_score:.2f})")
                else:
                    logger.warning(f"[Trainer] ⚠️  Model {model_id} eval score {eval_score:.2f} below threshold {QUALITY_THRESHOLD}. Not activating.")
            return {"status": "completed", "model_id": model_id}

        elif status == "failed":
            err = status_data.get("error", "unknown error")
            logger.error(f"[Trainer] ❌ Fine-tuning job failed: {err}")
            return {"status": "failed", "error": err}

        else:
            # Still running — retry after delay
            raise self.retry(countdown=FINETUNE_POLL_SEC)

    finally:
        db.close()


@celery_app.task(name="levi.update_embeddings")
def update_embeddings_task():
    """
    Recompute embeddings for any Quote rows that were added
    to the knowledge base with placeholder/null embeddings.
    Runs nightly.
    """
    try:
        from db import SessionLocal  # type: ignore
        from models import Quote  # type: ignore
        from embeddings import embed_text  # type: ignore
    except ImportError:
        from backend.db import SessionLocal  # type: ignore
        from backend.models import Quote  # type: ignore
        from backend.embeddings import embed_text  # type: ignore

    db = SessionLocal()
    try:
        missing = db.query(Quote).filter(Quote.embedding.is_(None)).limit(100).all()
        updated = 0
        for q in missing:
            try:
                q.embedding = embed_text(q.text)
                updated = int(updated) + 1  # type: ignore
            except Exception as e:
                logger.warning(f"[Trainer] Embedding update failed for quote {q.id}: {e}")
        db.commit()
        logger.info(f"[Trainer] Updated embeddings for {updated} quotes")
        return {"updated": updated}
    finally:
        db.close()


# ─────────────────────────────────────────────
# 5. PATCH generation.py TO USE FINE-TUNED MODEL
# ─────────────────────────────────────────────
def get_active_groq_model() -> str:
    """
    Returns the model ID to use for Groq requests.
    Prefers fine-tuned model if available and active.
    Note: Groq doesn't support custom model deployment yet —
    this function returns the Together AI model ID which is
    used via the Together API instead when a fine-tuned model
    is active.
    """
    fine_tuned = get_active_model_id()
    if fine_tuned:
        logger.debug(f"[Trainer] Using fine-tuned model: {fine_tuned}")
        return fine_tuned
    return "llama-3.1-8b-instant"  # default Groq base model


def generate_with_active_model(prompt: str, system_prompt: str, max_tokens: int = 150) -> Optional[str]:
    """
    Generate text using the currently active model.
    Falls back from fine-tuned → Together base → Groq in that order.
    """
    fine_tuned_id = get_active_model_id()

    if fine_tuned_id and TOGETHER_API_KEY:
        # Use fine-tuned model via Together AI
        try:
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {TOGETHER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": fine_tuned_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.75,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"[Trainer] Fine-tuned model call failed, falling back: {e}")

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
                    "temperature": 0.8,
                },
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"[Trainer] Groq fallback also failed: {e}")

    return None


# ─────────────────────────────────────────────
# 6. CELERY BEAT SCHEDULE (add to tasks.py)
# ─────────────────────────────────────────────
# Add these to celery_app.conf.beat_schedule in tasks.py:
TRAINING_BEAT_SCHEDULE = {
    "weekly-training-pipeline": {
        "task": "levi.trigger_training_pipeline",
        "schedule": 604800,  # every 7 days in seconds
    },
    "nightly-embedding-update": {
        "task": "levi.update_embeddings",
        "schedule": 86400,   # every 24 hours
    },
}
