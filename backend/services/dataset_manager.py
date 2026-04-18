# backend/services/dataset_manager.py
import os
import shutil
import hashlib
import datetime
import json
from typing import List, Optional

class DatasetVersion:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.version_id = self._generate_id()
        self.checksum = self._calculate_checksum()
        self.timestamp = datetime.datetime.now().isoformat()

    def _generate_id(self) -> str:
        return hashlib.md5(f"{self.path}-{datetime.datetime.now()}".encode()).hexdigest()[:8]

    def _calculate_checksum(self) -> str:
        """Calculates a recursive hash of the dataset directory for integrity validation."""
        sha256 = hashlib.sha256()
        for root, _, files in os.walk(self.path):
            for names in sorted(files):
                filepath = os.path.join(root, names)
                with open(filepath, "rb") as f:
                    while chunk := f.read(4096):
                        sha256.update(chunk)
        return sha256.hexdigest()

class DatasetManager:
    def __init__(self, base_path: str = "backend/data/training/datasets"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
        self.versions_log = os.path.join(self.base_path, "versions.json")
        self._load_log()

    def _load_log(self):
        if os.path.exists(self.versions_log):
            with open(self.versions_log, "r") as f:
                self.log = json.load(f)
        else:
            self.log = []

    def _save_log(self):
        with open(self.versions_log, "w") as f:
            json.dump(self.log, f, indent=4)

    def checkpoint_current_data(self, dataset_name: str, source_dir: str):
        """Creates a versioned snapshot of the current training data."""
        version = DatasetVersion(dataset_name, source_dir)
        dest_dir = os.path.join(self.base_path, f"{dataset_name}_v{version.version_id}")
        
        # In a real system, we'd use DVC or Git LFS, but for sovereign local, we copy/hardlink
        shutil.copytree(source_dir, dest_dir)
        
        entry = {
            "dataset": dataset_name,
            "version": version.version_id,
            "path": dest_dir,
            "checksum": version.checksum,
            "timestamp": version.timestamp
        }
        self.log.append(entry)
        self._save_log()
        print(f" 📦 [DATASET] Checkpointed {dataset_name} version {version.version_id} (SHA256: {version.checksum[:16]}...)")

    def verify_dataset(self, version_id: str) -> bool:
        """Verifies if the dataset has been tampered with or corrupted."""
        for entry in self.log:
            if entry["version"] == version_id:
                current_checksum = self._calculate_dir_checksum(entry["path"])
                if current_checksum == entry["checksum"]:
                    print(f" ✅ [DATASET] Integrity verified for v{version_id}")
                    return True
                else:
                    print(f" 🚨 [DATASET] CORRUPTION DETECTED in v{version_id}!")
                    return False
        return False

    def _calculate_dir_checksum(self, path: str) -> str:
        sha256 = hashlib.sha256()
        for root, _, files in os.walk(path):
            for names in sorted(files):
                filepath = os.path.join(root, names)
                with open(filepath, "rb") as f:
                    while chunk := f.read(4096):
                        sha256.update(chunk)
        return sha256.hexdigest()

    def get_version_path(self, version_id: str) -> Optional[str]:
        for entry in self.log:
            if entry["version"] == version_id:
                return entry["path"]
        return None

dataset_manager = DatasetManager()
