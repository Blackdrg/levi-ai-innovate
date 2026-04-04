import json
import subprocess
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sbom")

def generate_sbom():
    """
    Sovereign SBOM Generator v13.0.0.
    Produces a CycloneDX-compatible JSON manifest of all system dependencies.
    Used for Phase 13 Supply Chain Hardening.
    """
    logger.info("Generating Sovereign OS Software Bill of Materials...")
    
    # 1. Fetch Python Dependencies (pip freeze)
    try:
        pip_output = subprocess.check_output(["pip", "freeze"]).decode("utf-8")
        python_deps = [line.strip() for line in pip_output.split("\n") if line.strip()]
    except Exception as e:
        logger.error(f"Failed to fetch pip dependencies: {e}")
        python_deps = []

    # 2. Map Architectural Core Components
    core_manifest = {
        "engine": "v13.0.0 Alpha",
        "persistence": ["Postgres 16", "Neo4j 5.x", "Redis 7.x", "FAISS/HNSW"],
        "sovereign_shield": "v5.0 Hardened",
        "brain": "v8.0 Cognitive"
    }

    # 3. Assemble SBOM
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{os.urandom(16).hex()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "component": {
                "name": "LEVI-AI Sovereign OS",
                "version": "13.0.0",
                "type": "operating-system"
            }
        },
        "components": [
            {
                "name": dep.split("==")[0],
                "version": dep.split("==")[1] if "==" in dep else "latest",
                "type": "library",
                "purl": f"pkg:pypi/{dep.split('==')[0]}"
            } for dep in python_deps
        ],
        "arch_core": core_manifest
    }

    # 4. Save to Disk
    output_path = "backend/data/sbom.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(sbom, f, indent=2)
    
    logger.info(f"SBOM successfully generated at {output_path}")

if __name__ == "__main__":
    generate_sbom()
