"""
Startup and production-readiness helpers for the gateway.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

DEFAULT_SECRET_VALUES = {
    "JWT_SECRET": {
        "sovereign_monolith_default_secret",
    },
    "AUDIT_CHAIN_SECRET": {
        "change-me",
        "genesis_key",
        "sovereign_os_genesis_v14",
        "levi_ai_genesis_key",
    },
    "ENCRYPTION_KEY": {
        "kms_master_key",
    },
    "INTERNAL_SERVICE_KEY": {
        "svc_internal_grad_777_absolute",
    },
}


def _configured_and_not_default(name: str) -> bool:
    value = os.getenv(name, "")
    return bool(value) and value not in DEFAULT_SECRET_VALUES.get(name, set())


def collect_default_secret_warnings() -> List[str]:
    warnings: List[str] = []
    for key, defaults in DEFAULT_SECRET_VALUES.items():
        value = os.getenv(key)
        if value and value in defaults:
            warnings.append(f"{key} is still set to a default/insecure placeholder.")
    return warnings


def collect_startup_checks() -> Dict[str, Any]:
    environment = os.getenv("ENVIRONMENT", "development").lower()
    warnings: List[str] = []
    checks: Dict[str, bool] = {
        "jwt_secret_configured": _configured_and_not_default("JWT_SECRET"),
        "internal_service_key_configured": _configured_and_not_default("INTERNAL_SERVICE_KEY"),
        "audit_chain_secret_configured": _configured_and_not_default("AUDIT_CHAIN_SECRET"),
        "encryption_key_configured": _configured_and_not_default("ENCRYPTION_KEY"),
        "cors_configured": bool(os.getenv("CORS_ORIGINS")),
        "otel_export_configured": bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")),
        "redis_url_configured": bool(os.getenv("REDIS_URL")),
    }
    warnings.extend(collect_default_secret_warnings())

    if environment == "production":
        if not checks["jwt_secret_configured"]:
            warnings.append("JWT secret is missing or using the default production-insecure value.")
        if not checks["internal_service_key_configured"]:
            warnings.append("Internal service key is not configured.")
        if not checks["audit_chain_secret_configured"]:
            warnings.append("Audit chain secret is missing or still set to a default value.")
        if not checks["encryption_key_configured"]:
            warnings.append("Encryption key is missing or still set to a default value.")
        if not checks["otel_export_configured"]:
            warnings.append("OTEL exporter endpoint is not configured.")

    ready = all(
        checks[key]
        for key in (
            "cors_configured",
            "redis_url_configured",
            "jwt_secret_configured",
            "internal_service_key_configured",
            "audit_chain_secret_configured",
            "encryption_key_configured",
        )
    ) and (environment != "production" or not warnings)

    return {
        "environment": environment,
        "ready_for_production": ready,
        "checks": checks,
        "warnings": warnings,
    }
