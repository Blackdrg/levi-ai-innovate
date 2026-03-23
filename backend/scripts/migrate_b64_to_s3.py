# pyright: reportMissingImports=false
import os
import sys

# Ensure project root is in path for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import base64
import logging
from sqlalchemy.orm import Session
from backend.db import SessionLocal
from backend.models import FeedItem
from backend.tasks import upload_image_to_s3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def migrate_b64_to_s3():
    """
    Finds all FeedItems with image_b64 data but no image_url,
    uploads them to S3, and updates the record.
    """
    db = SessionLocal()
    try:
        # Find items that need migration
        items = db.query(FeedItem).filter(
            FeedItem.image_b64.isnot(None),
            FeedItem.image_url.is_(None)
        ).all()

        logger.info(f"Found {len(items)} items to migrate to S3.")

        for item in items:
            try:
                # Extract bytes from data URI
                if not item.image_b64.startswith("data:image"):
                    continue
                
                header, encoded = item.image_b64.split(",", 1)
                img_bytes = base64.b64decode(encoded)
                
                # Upload to S3
                logger.info(f"Migrating item {item.id} (User: {item.user_id})...")
                s3_url = upload_image_to_s3(img_bytes, item.user_id or 0)
                
                # Update record
                item.image_url = s3_url
                # We optionally keep image_b64 for now to avoid data loss until migration is verified
            except Exception as e:
                logger.error(f"Failed to migrate item {item.id}: {e}")

        db.commit()
        logger.info("Migration completed successfully.")
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_b64_to_s3()
