import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SecretManager:
    """Fetch secrets from env, AWS Secrets Manager, or HashiCorp Vault."""

    def __init__(self):
        self.backend = os.getenv("SECRET_BACKEND", "env").lower()
        self.client = None

        if self.backend == "aws":
            try:
                import boto3

                self.client = boto3.client(
                    "secretsmanager",
                    region_name=os.getenv("AWS_REGION", "us-east-1"),
                )
            except Exception as exc:
                logger.warning("[Secrets] AWS backend unavailable, falling back to env: %s", exc)
                self.backend = "env"
        elif self.backend == "vault":
            try:
                import hvac

                self.client = hvac.Client(
                    url=os.getenv("VAULT_ADDR", "http://localhost:8200"),
                    token=os.getenv("VAULT_TOKEN"),
                )
            except Exception as exc:
                logger.warning("[Secrets] Vault backend unavailable, falling back to env: %s", exc)
                self.backend = "env"

    def get_secret(self, secret_name: str) -> Optional[str]:
        if self.backend == "env":
            return os.getenv(secret_name)

        if self.backend == "aws":
            response = self.client.get_secret_value(SecretId=secret_name)
            return response.get("SecretString")

        if self.backend == "vault":
            response = self.client.secrets.kv.v2.read_secret_version(path=secret_name)
            return response["data"]["data"].get("value")

        return None


secret_manager = SecretManager()
