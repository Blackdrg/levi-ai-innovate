"""
PromptShield v1.0 — Agent Boundary Content Safety Contract.
Enforces NSFW/copyright/size rules before any image inference call.
Must be the FIRST gate called in ImageAgent._run().
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hard-blocked token patterns (NSFW + copyrighted character surnames)
# ---------------------------------------------------------------------------
_NSFW_PATTERNS = [
    r"\bnude\b", r"\bnaked\b", r"\bpornograph\w*\b", r"\bexplicit\b",
    r"\bsex(?:ual)?\b", r"\berotic\b", r"\bnsfw\b", r"\bgenitali\w*\b",
    r"\bpenis\b", r"\bvagina\b", r"\bbreasts?\b(?!\s+cancer)",  # allow medical context
    r"\bhentai\b", r"\bxxxxx?\b",
]

_COPYRIGHT_PATTERNS = [
    # Disney / Marvel / DC fictional characters (surname or full name)
    r"\bspiderman\b", r"\bbatman\b", r"\bsuperman\b", r"\biron\s*man\b",
    r"\bwonder\s*woman\b", r"\bmickey\s*mouse\b", r"\bhermione\b",
    r"\bdarth\s*vader\b", r"\byoda\b", r"\bpikachu\b", r"\bnaruto\b",
    # Real living people (first+last name trigger)
    r"\belon\s+musk\b", r"\bjoe\s+biden\b", r"\bdonald\s+trump\b",
    r"\btaylor\s+swift\b",
]

# Compile once at module load
_NSFW_RE = re.compile("|".join(_NSFW_PATTERNS), re.IGNORECASE)
_COPYRIGHT_RE = re.compile("|".join(_COPYRIGHT_PATTERNS), re.IGNORECASE)

# ---------------------------------------------------------------------------
# Resolution caps (width × height must not exceed this)
# ---------------------------------------------------------------------------
MAX_PIXELS = 1_048_576          # 1 MP  (e.g. 1024×1024)
MAX_SIDE   = 2048               # no single dimension > 2048 px
ALLOWED_ASPECT_RATIOS = {
    "1:1":  (1024, 1024),
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "4:3":  (1024, 768),
    "3:4":  (768, 1024),
}


class PromptShieldViolation(ValueError):
    """Raised when a prompt fails the PromptShield safety gate."""
    def __init__(self, reason: str, category: str):
        super().__init__(f"[PromptShield/{category}] {reason}")
        self.category = category
        self.reason   = reason


class PromptShield:
    """
    Stateless safety contract evaluated at the ImageAgent boundary.
    Raises PromptShieldViolation on any policy breach.
    Returns the sanitised (stripped) prompt on success.
    """

    @staticmethod
    def validate(
        prompt: str,
        width: int,
        height: int,
    ) -> str:
        """
        Gate all image-generation requests through this method.

        Args:
            prompt:  Raw user prompt string.
            width:   Output image width in pixels.
            height:  Output image height in pixels.

        Returns:
            Sanitised prompt (whitespace-stripped) if safe.

        Raises:
            PromptShieldViolation: on NSFW, copyright, or resolution breach.
        """
        clean = prompt.strip()

        # 1. NSFW check
        match = _NSFW_RE.search(clean)
        if match:
            logger.warning("[PromptShield] NSFW token blocked: '%s'", match.group())
            raise PromptShieldViolation(
                f"Prompt contains disallowed content near '{match.group()}'.",
                "NSFW",
            )

        # 2. Copyright / real-person check
        match = _COPYRIGHT_RE.search(clean)
        if match:
            logger.warning("[PromptShield] Copyright token blocked: '%s'", match.group())
            raise PromptShieldViolation(
                f"Prompt references a copyrighted character or real person ('{match.group()}').",
                "COPYRIGHT",
            )

        # 3. Resolution caps
        if width > MAX_SIDE or height > MAX_SIDE:
            raise PromptShieldViolation(
                f"Requested resolution {width}×{height} exceeds max side {MAX_SIDE}px.",
                "RESOLUTION",
            )
        if width * height > MAX_PIXELS:
            raise PromptShieldViolation(
                f"Requested resolution {width}×{height} exceeds {MAX_PIXELS} total pixels.",
                "RESOLUTION",
            )

        logger.debug("[PromptShield] Prompt cleared for inference: %s…", clean[:40])
        return clean

    @staticmethod
    def clamp_size(aspect_ratio: str) -> Tuple[int, int]:
        """Returns the canonical (width, height) for the given aspect ratio string."""
        return ALLOWED_ASPECT_RATIOS.get(aspect_ratio, (1024, 1024))
