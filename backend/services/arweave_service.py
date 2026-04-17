# backend/services/arweave_service.py
# DEPRECATED: Sovereign v16.3 Graduation
# Replaced by backend.services.audit_ledger.audit_ledger

import logging
from .audit_ledger import audit_ledger as arweave_audit

logger = logging.getLogger(__name__)
logger.warning("⚠️ [Legacy] Arweave Service is DEPRECATED. Redirecting to Sovereign Audit Ledger.")

# Alias for backward compatibility during migration
ArweaveAuditService = lambda: arweave_audit
