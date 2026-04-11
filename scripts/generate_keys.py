import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

def generate_rs256_keys():
    """
    Generates RS256 private and public keys for Sovereign Identity Layer.
    """
    cert_dir = os.path.join(os.path.dirname(__file__), "..", "certs")
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
        print(f"Created directory: {cert_dir}")

    priv_path = os.path.join(cert_dir, "jwt_rs256_private.pem")
    pub_path = os.path.join(cert_dir, "jwt_rs256_public.pem")

    if os.path.exists(priv_path) or os.path.exists(pub_path):
        print("⚠️  Warning: RS256 keys already exist. Skipping generation to avoid overwriting.")
        return

    print("🔑 Generating 2048-bit RSA key pair...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Serialize Private Key
    print(f"💾 Saving private key to {priv_path}...")
    with open(priv_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Serialize Public Key
    public_key = private_key.public_key()
    print(f"💾 Saving public key to {pub_path}...")
    with open(pub_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print("✅ RS256 keys generated successfully.")

if __name__ == "__main__":
    generate_rs256_keys()
