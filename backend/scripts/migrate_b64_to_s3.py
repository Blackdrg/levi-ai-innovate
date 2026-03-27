# pyright: reportMissingImports=false
import os
import sys

# Ensure project root is in path for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import base64
import logging
from backend.firestore_db import db as firestore_db  # type: ignore
from backend.tasks import upload_image_to_s3  # type: ignore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def migrate_b64_to_s3():
    """
    Finds all feed_items in Firestore with image_b64 data but no image_url,
    uploads them to S3, and updates the record.
    """
    try:
        # Find items that need migration (Firestore doesn't support complex null filters easily, 
        # so we fetch and filter in memory if needed, or just iterate)
        feed_ref = firestore_db.collection("feed_items")
        docs = feed_ref.get()
        
        count = 0
        for doc in docs:
            item = doc.to_dict()
            item_id = doc.id
            
            # Check if needs migration
            image_b64 = item.get("image_b64")
            image_url = item.get("image_url")
            
            if image_b64 and not image_url:
                try:
                    # Extract bytes from data URI
                    if not image_b64.startswith("data:image"):
                        continue
                    
                    header, encoded = image_b64.split(",", 1)
                    img_bytes = base64.b64decode(encoded)
                    
                    user_id = item.get("user_id", "0")
                    
                    # Upload to S3
                    logger.info(f"Migrating item {item_id} (User: {user_id})...")
                    s3_url = upload_image_to_s3(img_bytes, user_id)
                    
                    # Update record
                    feed_ref.document(item_id).update({
                        "image_url": s3_url
                    })
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to migrate item {item_id}: {e}")

        logger.info(f"Migration completed successfully. Migrated {count} items.")
    except Exception as e:
        logger.error(f"Migration script failed: {e}")

if __name__ == "__main__":
    migrate_b64_to_s3()
