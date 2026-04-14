import re
import logging
import unicodedata
from typing import List, Dict

logger = logging.getLogger(__name__)

class PromptSanitizer:
    """
    Sovereign Shield: Prompt Injection Defense v14.0.0.
    Implements multi-layer sanitization and instruction-boundary enforcement.
    """
    
    # Common adversarial patterns
    ADVERSARIAL_PATTERNS = [
        r"(?i)ignore (all )?(previous )?instructions",
        r"(?i)system (prompt|message):",
        r"(?i)you are now a",
        r"(?i)bypass (all )?restrictions",
        r"(?i)dan:", # Do Anything Now
        r"(?i)jailbreak",
        r"(?i)reveal (your )?mission",
        r"(?i)override (your )?behavior",
        r"\[INST\]",   # Llama-style instruction start
        r"\[/INST\]",  # Llama-style instruction end
        r"<<SYS>>",     # Llama-style system prompt
        r"\[INST\s",   # Malformed instruction
        r"JAILBREAK",
    ]

    @staticmethod
    def normalize_homoglyphs(text: str) -> str:
        """
        Sovereign v14.0.0: Unicode Homoglyph Normalization.
        Converts fancy/adversarial characters (e.g. 𝐢 -> i) to prevent filter bypass.
        """
        return "".join(
            c for c in unicodedata.normalize('NFKD', text)
            if not unicodedata.combining(c)
        )

    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        Main entry point for input sanitization.
        Implements a deterministic pre-NER pass for high-fidelity defense.
        """
        if not text:
            return ""
            
        # 1. Homoglyph Normalization
        sanitized = cls.normalize_homoglyphs(text)
        
        # 2. Token Boundary Check (>> , ]])
        # These are often used to 'escape' system prompts or encapsulate missions
        if ">>" in sanitized or "]]" in sanitized:
            logger.warning("[Shield] Forbidden token boundaries detected (>> or ]]). Neutralizing.")
            sanitized = sanitized.replace(">>", "[PROTECTED_BOUNDARY]").replace("]]", "[PROTECTED_BOUNDARY]")

        # 3. Deterministic Regex Pass
        for pattern in cls.ADVERSARIAL_PATTERNS:
            if re.search(pattern, sanitized):
                logger.warning(f"[Shield] Deterministic adversarial pattern detected: {pattern}")
                sanitized = re.sub(pattern, "[FILTERED_INTENT]", sanitized)
        
        # 4. Enforce boundary tags
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

    @staticmethod
    def sorensen_dice_similarity(s1: str, s2: str) -> float:
        """
        Sovereign v15.0: Fuzzy PII Detection.
        Calculates Sörensen-Dice coefficient for two strings.
        """
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        
        # Bi-gram approach
        def get_bigrams(s):
            return set(s[i:i+2] for i in range(len(s)-1))
        
        set1 = get_bigrams(s1.lower())
        set2 = get_bigrams(s2.lower())
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1.intersection(set2))
        return 2.0 * intersection / (len(set1) + len(set2))

    @classmethod
    def mask_pii(cls, text: str, user_id: str = "global", context_pii: List[str] = None) -> str:
        """
        Sovereign Shield v15.0: Hardened PII Encryption.
        Encrypts sensitive vectors using AES-256 GCM before model handoff.
        Includes fuzzy Sörensen-Dice check for context-aware redaction.
        """
        from backend.utils.kms import SovereignKMS
        if not text: return ""
        
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        phone_pattern = r"\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b"
        
        masked = text
        # 1. Regex Pass (Emails)
        for match in reversed(list(re.finditer(email_pattern, masked))):
            val = match.group()
            cipher = SovereignKMS.encrypt(f"{user_id}:{val}")
            placeholder = f"[EMAIL_KMS_{cipher}]"
            masked = masked[:match.start()] + placeholder + masked[match.end():]
            
        # 2. Regex Pass (Phones)
        for match in reversed(list(re.finditer(phone_pattern, masked))):
            val = match.group()
            cipher = SovereignKMS.encrypt(f"{user_id}:{val}")
            placeholder = f"[PHONE_KMS_{cipher}]"
            masked = masked[:match.start()] + placeholder + masked[match.end():]
            
        # 3. Fuzzy Pass (Sörensen-Dice)
        # Redacts words that are too similar to provided context PII (e.g. real names)
        if context_pii:
            words = re.findall(r"\b\w+\b", masked)
            for word in words:
                if len(word) < 4: continue # Skip short words to avoid false positives
                for target in context_pii:
                    if cls.sorensen_dice_similarity(word, target) > 0.85:
                        cipher = SovereignKMS.encrypt(f"{user_id}:{word}")
                        placeholder = f"[PII_KMS_{cipher}]"
                        masked = masked.replace(word, placeholder)
                        logger.info(f"[Shield] Fuzzy PII Redacted: '{word}' matched '{target}' via Dice coefficient.")
            
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
    Sovereign v14.0.0: Output scrubbing and XSS neutralization.
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
