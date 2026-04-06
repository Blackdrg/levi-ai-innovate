import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class PromptSanitizer:
    """
    Sovereign Shield: Prompt Injection Defense v13.0.0.
    Implements multi-layer sanitization and instruction-boundary enforcement.
    """
    
    # Common adversarial patterns
    ADVERSARIAL_PATTERNS = [
        r"(?i)ignore all (previous )?instructions",
        r"(?i)system (prompt|message):",
        r"(?i)you are now a",
        r"(?i)bypass (all )?restrictions",
        r"(?i)dan:", # Do Anything Now
        r"(?i)jailbreak",
        r"(?i)reveal (your )?mission",
        r"(?i)override (your )?behavior"
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        Main entry point for input sanitization.
        Filters adversarial strings and tags intent boundaries.
        """
        if not text:
            return ""
            
        sanitized = text
        for pattern in cls.ADVERSARIAL_PATTERNS:
            if re.search(pattern, sanitized):
                logger.warning(f"[Shield] Adversarial pattern detected and neutralized: {pattern}")
                sanitized = re.sub(pattern, "[FILTERED_INTENT]", sanitized)
        
        # Enforce boundary tags
        return f"<USER_MISSION>\n{sanitized}\n</USER_MISSION>"

    @classmethod
    def enforce_boundaries(cls, messages: List[Dict]) -> List[Dict]:
        """
        Wraps user messages in mission-boundary tags to prevent instruction hijack.
        """
        shielded_messages = []
        for msg in messages:
            if msg["role"] == "user":
                shielded_messages.append({
                    "role": "user",
                    "content": cls.sanitize(msg["content"])
                })
            else:
                shielded_messages.append(msg)
        return shielded_messages

    @classmethod
    def mask_pii(cls, text: str, user_id: str = "global") -> str:
        """
        Sovereign Shield v1.0.0-RC1: Hardened PII Encryption.
        Encrypts sensitive vectors using AES-256 GCM before model handoff.
        """
        from backend.utils.kms import SovereignKMS
        if not text: return ""
        
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        phone_pattern = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
        
        masked = text
        # Process Emails
        for match in reversed(list(re.finditer(email_pattern, masked))):
            val = match.group()
            cipher = SovereignKMS.encrypt(f"{user_id}:{val}")
            placeholder = f"[EMAIL_KMS_{cipher}]"
            masked = masked[:match.start()] + placeholder + masked[match.end():]
            
        # Process Phones
        for match in reversed(list(re.finditer(phone_pattern, masked))):
            val = match.group()
            cipher = SovereignKMS.encrypt(f"{user_id}:{val}")
            placeholder = f"[PHONE_KMS_{cipher}]"
            masked = masked[:match.start()] + placeholder + masked[match.end():]
            
        return masked

    @classmethod
    def demask_pii(cls, text: str) -> str:
        """
        Restores original values from encrypted placeholders.
        """
        from backend.utils.kms import SovereignKMS
        if not text: return ""
        
        demasked = text
        # Pattern for KMS placeholders: [TYPE_KMS_...]
        kms_pattern = r"\[[A-Z]+_KMS_([a-zA-Z0-9+/=]+)\]"
        
        for match in reversed(list(re.finditer(kms_pattern, demasked))):
            cipher = match.group(1)
            decrypted = SovereignKMS.decrypt(cipher)
            if ":" in decrypted:
                _, raw_val = decrypted.split(":", 1)
                demasked = demasked[:match.start()] + raw_val + demasked[match.end():]
                
        return demasked

class ResultSanitizer:
    """
    Sovereign v13.1.0: Output scrubbing and XSS neutralization.
    Ensures model-produced Markdown doesn't contain malicious injection.
    """

    @classmethod
    def sanitize_bot_response(cls, text: str) -> str:
        """Hardens the bot response before user delivery."""
        if not text: return ""
        
        # 1. Neutralize PII Shards
        scrubbed = PromptSanitizer.mask_pii(text)
        
        # 2. XSS / Markdown Injection Neutralization
        # Prevents <script> or event handlers in markdown-rendered output
        scrubbed = re.sub(r"<script.*?>.*?</script>", "[SCRIPT_FILTERED]", scrubbed, flags=re.DOTALL | re.IGNORECASE)
        scrubbed = re.sub(r"on\w+=", "filtered_attr=", scrubbed, flags=re.IGNORECASE)
        
        # 3. Instruction Residue Cleanup
        scrubbed = scrubbed.replace("<USER_MISSION>", "").replace("</USER_MISSION>", "")
        
        return scrubbed.strip()
