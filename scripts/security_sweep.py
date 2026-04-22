# scripts/security_sweep.py
import subprocess
import os
import sys

def run_audit(command, description):
    print(f"🔍 Running {description}...")
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"✅ {description} PASSED.")
    except subprocess.CalledProcessError:
        print(f"❌ {description} FAILED. High severity findings must be resolved.")
        sys.exit(1)

if __name__ == "__main__":
    # 1. Bandit (Python static analysis)
    run_audit("bandit -r backend/", "Bandit Python Security Audit")
    
    # 2. Cargo Audit (Rust dependencies)
    if os.path.exists("backend/kernel/Cargo.toml"):
        run_audit("cd backend/kernel && cargo audit", "Cargo Rust Dependency Audit")
    
    # 3. Trivy (Docker Image Scan)
    run_audit("trivy image levi-ai-base:latest", "Trivy Docker Content Scan")
    
    print("🛡️ [Security] All Sovereign v22.1 CI audits PASSED.")
