# backend/services/model_registry.py
import os
import json
import datetime
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ModelMetadata(BaseModel):
    model_id: str
    version: str
    architecture: str
    weights_path: str
    hash_sha256: str
    created_at: str
    metrics: Dict[str, float]
    status: str = "stable"  # stable, experimental, deprecated

class ModelRegistry:
    def __init__(self, registry_path: str = "backend/data/models/registry"):
        self.registry_path = registry_path
        os.makedirs(self.registry_path, exist_ok=True)
        self.manifest_file = os.path.join(self.registry_path, "manifest.json")
        self._load_manifest()

    def _load_manifest(self):
        if os.path.exists(self.manifest_file):
            with open(self.manifest_file, "r") as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {"models": {}}

    def _save_manifest(self):
        with open(self.manifest_file, "w") as f:
            json.dump(self.manifest, f, indent=4)

    def register_model(self, metadata: ModelMetadata):
        """Registers a new model version in the registry."""
        model_id = metadata.model_id
        if model_id not in self.manifest["models"]:
            self.manifest["models"][model_id] = []
        
        # Append new version
        self.manifest["models"][model_id].append(metadata.dict())
        self._save_manifest()
        print(f" [REGISTRY] Model {model_id} v{metadata.version} registered.")

    def get_latest_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Retrieves the latest version of a specific model."""
        versions = self.manifest["models"].get(model_id, [])
        if not versions:
            return None
        # Sort by created_at or just take the last one
        latest = versions[-1]
        return ModelMetadata(**latest)

    def rollback_model(self, model_id: str):
        """Rolls back the model to the previous stable version."""
        versions = self.manifest["models"].get(model_id, [])
        if len(versions) > 1:
            versions.pop() # Remove latest
            self._save_manifest()
            print(f" 🛡️ [REGISTRY] Rolled back {model_id} to v{versions[-1]['version']}")

    def verify_model_integrity(self, model_id: str, version: str) -> bool:
        """Verifies the SHA256 integrity of a model file against its registry entry."""
        versions = self.manifest["models"].get(model_id, [])
        entry = next((v for v in versions if v["version"] == version), None)
        if not entry:
            return False
        
        weights_path = entry["weights_path"]
        if not os.path.exists(weights_path):
            print(f" ❌ [REGISTRY] Integrity check failed: File missing at {weights_path}")
            return False

        # Calculate actual hash
        sha256_hash = hashlib.sha256()
        with open(weights_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_hash = sha256_hash.hexdigest()
        if actual_hash == entry["hash_sha256"]:
            print(f" ✅ [REGISTRY] Integrity verified for {model_id} v{version}")
            return True
        else:
            print(f" 🚨 [REGISTRY] CORRUPTION DETECTED: {model_id} v{version} hash mismatch!")
            return False

model_registry = ModelRegistry()
