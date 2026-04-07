import logging
from backend.celery_app import celery_app # type: ignore
from google.cloud import firestore
from backend.db.firestore_db import db as firestore_db
from backend.db.redis_client import distributed_lock
from backend.config.system import TIERS

logger = logging.getLogger(__name__)

def _refund_credits(user_id: str, amount: int) -> None:
    """Refund credits to user after task failure in Firestore (Atomic)."""
    try:
        user_ref = firestore_db.collection("users").document(user_id)
        
        with distributed_lock(f"credits:{user_id}", ttl=10, retries=3) as acquired:
            if not acquired:
                logger.warning(f"[Refund] Lock busy for user {user_id}. Refund deferred.")
                return
            
            user_ref.update({
                "credits": firestore.Increment(amount),
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            logger.info(f"[Refund] Atomic refund of {amount} units to {user_id}.")
    except Exception as e:
        logger.error(f"[Refund] Critical failure for {user_id}: {e}")

@celery_app.task
def reset_monthly_credits():
    """Reset credits for paid users on the 1st of each month in Firestore."""
    try:
        users_ref = firestore_db.collection("users").where("tier", "in", ["pro", "creator"])
        count = 0
        batch_size = 500
        last_doc = None

        while True:
            query = users_ref.limit(batch_size)
            if last_doc:
                query = query.start_after(last_doc)
            
            docs = list(query.get())
            if not docs:
                break
                
            for user_doc in docs:
                tier = user_doc.to_dict().get("tier", "free")
                tier_config = TIERS.get(tier, TIERS["free"])
                base_credits = tier_config.get("monthly_credits", 100 if tier == "pro" else 500 if tier == "creator" else 0)
                
                user_doc.reference.update({
                    "credits": base_credits,
                    "updated_at": firestore.SERVER_TIMESTAMP
                })
                count += 1
            
            last_doc = docs[-1]

        logger.info(f"[Credits] Reset {count} users")
        return {"status": "completed", "reset": count}
    except Exception as e:
        logger.error(f"[Credits] Reset failed: {e}")
        return {"error": str(e)}
