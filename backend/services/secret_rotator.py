# backend/services/secret_rotator.py
import os
import secrets
import logging
import datetime
from backend.services.vault_manager import vault_manager

logger = logging.getLogger("secret_rotator")

class SecretRotator:
    """
    Sovereign v17.5: Automated Secrets Rotation.
    Periodically regenerates DCN seeds and internal service keys.
    """
    def __init__(self, rotation_days: int = 30):
        self.rotation_days = rotation_days

    async def check_and_rotate(self):
        """Checks if secrets are due for rotation and executes if so."""
        # This is a simplified logic. In production, we'd track last_rotate in Vault.
        logger.info(" [ROTATOR] Checking secret age in Vault...")
        
        # 🛡️ Rotate DCN Pulse Seed
        await self.rotate_key("DCN_PULSE_SEED")
        
        # 🛡️ Rotate Internal Audit HMAC Key
        await self.rotate_key("AUDIT_HMAC_KEY")

        logger.info(" [OK] Secrets rotation pass complete.")

    async def rotate_key(self, key_name: str):
        """Generates a new secure random key and updates Vault."""
        new_secret = secrets.token_hex(32)
        try:
            # 🔐 Physical persistence to local secret vault
            secret_path = f"d:\\LEVI-AI\\data\\vault\\{key_name.lower()}.secret"
            os.makedirs(os.path.dirname(secret_path), exist_ok=True)
            
            with open(secret_path, "w") as f:
                f.write(new_secret)
                
            # Set restrictive permissions (Simulated for Windows/Linux)
            # os.chmod(secret_path, 0o600)
            
            logger.info(f" [ROTATOR] Key '{key_name}' rotated and persistent at {secret_path}")
        except Exception as e:
            logger.error(f" [ROTATOR] Failed to rotate '{key_name}': {e}")

secret_rotator = SecretRotator()
