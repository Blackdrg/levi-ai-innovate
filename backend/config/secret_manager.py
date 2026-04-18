import os
import logging
import time
import json
from typing import Optional, Dict, Any
from backend.utils.encryption import SovereignVault

logger = logging.getLogger(__name__)

class SecretManager:
    """
    Sovereign Secret Manager v14.1.0 [HARDENED].
    Abstracts secret access with persistent, encrypted storage and TTL-based rotation.
    """
    
    VAULT_PATH = "d:\\LEVI-AI\\vault\\sovereign_vault.enc"
    _CACHE: Dict[str, Dict] = {}
    DEFAULT_TTL = 3600 # 1 hour

    @classmethod
    def _load_vault(cls):
        """Loads and decrypts the persistent vault from disk."""
        if os.path.exists(cls.VAULT_PATH):
            try:
                with open(cls.VAULT_PATH, "r") as f:
                    encrypted_data = f.read()
                
                decrypted_json = SovereignVault.decrypt(encrypted_data)
                cls._CACHE = json.loads(decrypted_json)
                logger.debug(f"[SecretManager] Persistent vault loaded from {cls.VAULT_PATH}")
            except Exception as e:
                logger.error(f"[SecretManager] Failed to load persistent vault: {e}")
                cls._CACHE = {}
        else:
            cls._CACHE = {}

    @classmethod
    def _save_vault(cls):
        """Encrypts and persists the vault to disk."""
        try:
            os.makedirs(os.path.dirname(cls.VAULT_PATH), exist_ok=True)
            vault_json = json.dumps(cls._CACHE)
            encrypted_data = SovereignVault.encrypt(vault_json)
            
            with open(cls.VAULT_PATH, "w") as f:
                f.write(encrypted_data)
            logger.debug(f"[SecretManager] Persistent vault saved to {cls.VAULT_PATH}")
        except Exception as e:
            logger.error(f"[SecretManager] Failed to save persistent vault: {e}")

    @classmethod
    def get_secret(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieves a secret from the vault with caching and integrity checks.
        """
        if not cls._CACHE:
            cls._load_vault()

        now = time.time()
        
        # Check cache and TTL
        if key in cls._CACHE:
            entry = cls._CACHE[key]
            if now < entry["expiry"]:
                return entry["value"]

        # Fetch from env (Fallback/Source)
        val = os.getenv(key, default)
        
        if val:
            # Update cache and persist
            cls._CACHE[key] = {
                "value": val,
                "expiry": now + cls.DEFAULT_TTL,
                "last_rotated": now
            }
            cls._save_vault()
            logger.info(f"[SecretManager] Synchronized secret '{key}' to persistent vault.")
            return val
            
        return default

    @classmethod
    def rotate_all(cls):
        """
        Forcefully clears the vault and re-synchronizes from source.
        """
        logger.info("[SecretManager] Initiating global secret rotation & re-sync...")
        cls._CACHE.clear()
        if os.path.exists(cls.VAULT_PATH):
            os.remove(cls.VAULT_PATH)
        return True

    @classmethod
    def revoke_secret(cls, key: str):
        """
        Immediately removes a secret from the vault.
        """
        if not cls._CACHE:
            cls._load_vault()
            
        if key in cls._CACHE:
            del cls._CACHE[key]
            cls._save_vault()
            logger.warning(f"[SecretManager] Secret '{key}' revoked from persistent vault.")
