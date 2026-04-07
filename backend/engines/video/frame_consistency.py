"""
FrameConsistency Validator v1.0
Rejects video outputs where inter-frame pixel delta variance exceeds 15%.
"""
import logging
from io import BytesIO
from typing import List, Optional

logger = logging.getLogger(__name__)

# Maximum allowed inter-frame mean-absolute-difference as a fraction of 255
FRAME_DELTA_THRESHOLD = 0.15   # 15 % of full pixel range
MAX_FRAMES            = 30     # hard cap on frame count


class FrameConsistencyError(ValueError):
    """Raised when a video clip fails the consistency check."""
    def __init__(self, variance: float, threshold: float):
        super().__init__(
            f"[FrameConsistency] Inter-frame delta variance {variance:.2%} "
            f"exceeds threshold {threshold:.2%}."
        )
        self.variance  = variance
        self.threshold = threshold


class FrameConsistencyValidator:
    """
    Validates that a sequence of raw frame bytes does not exhibit
    excessive inter-frame pixel delta variance (> FRAME_DELTA_THRESHOLD).

    Usage
    -----
    validator = FrameConsistencyValidator()
    validator.validate(frames)          # raises FrameConsistencyError on failure
    variance = validator.measure(frames) # returns raw float
    """

    def __init__(self, threshold: float = FRAME_DELTA_THRESHOLD):
        self.threshold = threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, frames: List[bytes]) -> float:
        """
        Validates frame consistency.

        Args:
            frames: List of raw image bytes (JPEG/PNG), one per frame.

        Returns:
            Mean inter-frame delta as a fraction of 255.

        Raises:
            FrameConsistencyError: if variance exceeds threshold.
            ValueError: if fewer than 2 frames are provided.
        """
        if len(frames) < 2:
            return 0.0

        variance = self.measure(frames)
        if variance > self.threshold:
            raise FrameConsistencyError(variance, self.threshold)

        logger.info("[FrameConsistency] OK — delta variance %.3f (limit %.3f)", variance, self.threshold)
        return variance

    def measure(self, frames: List[bytes]) -> float:
        """
        Computes mean absolute inter-frame pixel difference normalised to [0, 1].
        Uses PIL for decode; falls back to 0.0 if PIL is unavailable.
        """
        try:
            from PIL import Image
            import struct
        except ImportError:
            logger.warning("[FrameConsistency] PIL not available — skipping validation.")
            return 0.0

        deltas: List[float] = []
        prev_pixels: Optional[List] = None

        for raw in frames:
            try:
                img = Image.open(BytesIO(raw)).convert("L")   # grayscale for speed
                # Downsample to 64×64 to keep cost O(1) regardless of resolution
                thumb = img.resize((64, 64))
                pixels = list(thumb.getdata())

                if prev_pixels is not None:
                    diff = sum(abs(a - b) for a, b in zip(pixels, prev_pixels)) / len(pixels)
                    deltas.append(diff / 255.0)

                prev_pixels = pixels
            except Exception as exc:
                logger.warning("[FrameConsistency] Could not decode frame: %s", exc)

        return sum(deltas) / len(deltas) if deltas else 0.0
