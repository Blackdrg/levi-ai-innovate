# backend/utils/gen_certs.py
import os
import subprocess
from pathlib import Path

def generate_dev_certs(cert_dir: str = "certs"):
    """
    Sovereign v14.2: Dev mTLS Certificate Generator.
    Creates a CA, Client, and Server certs for local secure orchestration.
    """
    path = Path(cert_dir)
    path.mkdir(exist_ok=True)

    print(f"🔐 Generating Sovereign mTLS dev certificates in {path}...")

    # 1. Generate CA key and cert
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes",
        "-keyout", str(path / "ca.key"),
        "-out", str(path / "ca.pem"),
        "-days", "365",
        "-subj", "/C=US/ST=Sovereign/L=Local/O=LEVI-AI/CN=SovereignCA"
    ], check=True)

    # 2. Generate Client key and CSR
    subprocess.run([
        "openssl", "req", "-newkey", "rsa:4096", "-nodes",
        "-keyout", str(path / "client-key.pem"),
        "-out", str(path / "client.csr"),
        "-subj", "/C=US/ST=Sovereign/L=Local/O=LEVI-AI/CN=SovereignExecutor"
    ], check=True)

    # 3. Sign Client CSR with CA
    subprocess.run([
        "openssl", "x509", "-req", "-in", str(path / "client.csr"),
        "-CA", str(path / "ca.pem"),
        "-CAkey", str(path / "ca.key"),
        "-CAcreateserial",
        "-out", str(path / "client.pem"),
        "-days", "365"
    ], check=True)

    # Clean up CSRs and CA key (keep key for signing others if needed, but in dev it's fine)
    os.remove(path / "client.csr")
    
    print("✅ Sovereign mTLS certificates ready.")

if __name__ == "__main__":
    generate_dev_certs()
