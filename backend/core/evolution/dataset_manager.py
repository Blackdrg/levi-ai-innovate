import os
import json
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DatasetManager:
    """
    Sovereign Dataset Lifecycle Manager.
    Enforces SHA-256 integrity and versioning for all Agent trajectories.
    """
    
    DATASET_ROOT = "d:\\LEVI-AI\\data\\evolution\\datasets"
    MANIFEST_PATH = os.path.join(DATASET_ROOT, "manifest.json")

    def __init__(self):
        os.makedirs(self.DATASET_ROOT, exist_ok=True)
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        if os.path.exists(self.MANIFEST_PATH):
            with open(self.MANIFEST_PATH, "r") as f:
                return json.load(f)
        return {"versions": [], "last_graduation": None}

    def _save_manifest(self):
        with open(self.MANIFEST_PATH, "w") as f:
            json.dump(self.manifest, f, indent=4)

    def anchor_batch(self, batch_data: List[Dict[str, Any]]) -> str:
        """Anchors a training batch with a unique SHA-256 hash and version ID."""
        timestamp = datetime.now().isoformat()
        raw_content = json.dumps(batch_data, sort_keys=True)
        batch_hash = hashlib.sha256(raw_content.encode()).hexdigest()
        
        version_id = f"v{len(self.manifest['versions']) + 1}_{batch_hash[:8]}"
        filename = f"batch_{version_id}.json"
        filepath = os.path.join(self.DATASET_ROOT, filename)
        
        with open(filepath, "w") as f:
            f.write(raw_content)
        
        self.manifest["versions"].append({
            "id": version_id,
            "hash": batch_hash,
            "path": filepath,
            "timestamp": timestamp,
            "sample_count": len(batch_data)
        })
        self._save_manifest()
        
        logger.info(f"⚓ [Dataset] Batch anchored: {version_id} (Hash: {batch_hash[:32]}...)")
        return version_id

    def get_latest_batch_path(self) -> str:
        if not self.manifest["versions"]:
            return None
        return self.manifest["versions"][-1]["path"]

dataset_manager = DatasetManager()

def get_dataset_manager() -> DatasetManager:
    return dataset_manager
