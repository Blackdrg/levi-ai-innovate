import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def generate_keys():
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Serialize private key
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Serialize public key
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    cert_dir = os.path.join(os.path.dirname(__file__), "..", "..", "certs")
    os.makedirs(cert_dir, exist_ok=True)

    priv_path = os.path.join(cert_dir, "jwt_rs256_private.pem")
    pub_path = os.path.join(cert_dir, "jwt_rs256_public.pem")

    with open(priv_path, "wb") as f:
        f.write(pem)
    
    with open(pub_path, "wb") as f:
        f.write(pub_pem)

    print(f"Generated RSA Key Pair in {cert_dir}")
    print(f"Private: {priv_path}")
    print(f"Public: {pub_path}")

if __name__ == "__main__":
    generate_keys()
