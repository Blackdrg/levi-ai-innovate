"""
LEVI AI Learning System
Collects conversation feedback, learns user preferences,
enriches the knowledge base, and prepares fine-tuning datasets.
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Learning constants
# ─────────────────────────────────────────────
MIN_QUALITY_SCORE  = 4     # 1-5 scale; only add ≥4 to knowledge base
EMBEDDING_UPDATE_FREQ = 20  # update system prompt every N high-quality responses
PROMPT_HISTORY_LEN  = 6    # number of recent variants to track
MAX_KNOWLEDGE_ENTRIES = 2000  # cap on learned responses in DB


# ─────────────────────────────────────────────
# 1. DATA COLLECTION
# ─────────────────────────────────────────────
def collect_training_sample(
    db: Session,
    user_message: str,
    bot_response: str,
    mood: str,
    rating: Optional[int],       # 1-5 from user, None if not rated
    session_id: str,
    user_id: Optional[int] = None,
) -> "TrainingData":
    """
    Store a conversation turn as a training sample.
    Automatically infers quality from response characteristics
    when no explicit rating is given.
    """
    try:
        from training_models import TrainingData
    except ImportError:
        from backend.training_models import TrainingData

    # Auto-score if no rating provided
    if rating is None:
        rating = _auto_score_response(user_message, bot_response)

    sample = TrainingData(
        user_message=user_message,
        bot_response=bot_response,
        mood=mood or "philosophical",
        rating=rating,
        session_id=session_id,
        user_id=user_id,
        fingerprint=_fingerprint(user_message, bot_response),
        is_exported=False,
        created_at=datetime.utcnow(),
    )
    db.add(sample)

    # If high quality, augment the quote knowledge base
    if rating >= MIN_QUALITY_SCORE:
        _augment_knowledge_base(db, user_message, bot_response, mood)

    db.commit()
    logger.info(f"[Learning] Collected sample rating={rating} mood={mood} user={user_id}")
    return sample


def _auto_score_response(user_msg: str, bot_response: str) -> int:
    """
    Heuristic scoring when user doesn't explicitly rate.
    Scores 1-5 based on length, content markers, and coherence.
    """
    score = 3  # baseline

    # Length heuristics
    words = len(bot_response.split())
    if words < 8:  score -= 1
    if words > 20: score += 1
    if words > 80: score -= 1  # too long = worse for wisdom style

    # Quality signals (positive)
    positive_signals = [
        '"' in bot_response,                        # contains a quote
        '—' in bot_response,                        # attribution marker
        any(w in bot_response.lower() for w in ['wisdom', 'profound', 'truth', 'universe', 'soul', 'mind', 'journey']),
        bot_response[0].isupper(),                  # proper capitalisation
        not bot_response.endswith('?'),             # not a question (usually)
    ]
    score += sum(positive_signals) // 2

    # Penalty signals
    bad_signals = [
        'sorry' in bot_response.lower(),
        'i cannot' in bot_response.lower(),
        'as an ai' in bot_response.lower(),
        len(bot_response) < 30,
    ]
    score -= sum(bad_signals)

    return max(1, min(5, score))


def _fingerprint(msg: str, response: str) -> str:
    """Deduplicate identical pairs."""
    combined = f"{msg.strip().lower()}||{response.strip().lower()}"
    return hashlib.md5(combined.encode()).hexdigest()


def _augment_knowledge_base(db: Session, question: str, answer: str, mood: str):
    """
    Add a high-quality AI response to the quotes table
    so future semantic searches can retrieve it.
    """
    try:
        try:
            from models import Quote
            from embeddings import embed_text
        except ImportError:
            from backend.models import Quote
            from backend.embeddings import embed_text

        # Avoid exact duplicates
        existing = db.query(Quote).filter(Quote.text == answer).first()
        if existing:
            return

        # Cap knowledge base size
        count = db.query(func.count(Quote.id)).filter(Quote.topic == "__learned__").scalar()
        if count >= MAX_KNOWLEDGE_ENTRIES:
            # Remove the oldest learned entry
            oldest = db.query(Quote).filter(
                Quote.topic == "__learned__"
            ).order_by(Quote.created_at.asc()).first()
            if oldest:
                db.delete(oldest)

        emb = embed_text(answer)
        new_q = Quote(
            text=answer,
            author="LEVI AI",
            topic="__learned__",
            mood=mood,
            embedding=emb,
            likes=0,
        )
        db.add(new_q)
        logger.info(f"[Learning] Added learned response to knowledge base (mood={mood})")

    except Exception as e:
        logger.warning(f"[Learning] Knowledge base augmentation failed: {e}")


# ─────────────────────────────────────────────
# 2. USER PREFERENCE MODELING
# ─────────────────────────────────────────────
class UserPreferenceModel:
    """
    Builds a per-user preference profile that shapes the system prompt
    sent to Groq on every request.
    """

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self._profile: Optional[Dict] = None

    def get_profile(self) -> Dict[str, Any]:
        if self._profile:
            return self._profile

        try:
            from training_models import TrainingData
        except ImportError:
            from backend.training_models import TrainingData

        # Fetch last 40 rated interactions for this user
        samples = (
            self.db.query(TrainingData)
            .filter(TrainingData.user_id == self.user_id, TrainingData.rating.isnot(None))
            .order_by(TrainingData.created_at.desc())
            .limit(40)
            .all()
        )

        if not samples:
            self._profile = _default_profile()
            return self._profile

        # Preferred moods (weight by rating)
        mood_scores: Dict[str, List[int]] = {}
        for s in samples:
            mood_scores.setdefault(s.mood, []).append(s.rating)

        preferred_moods = sorted(
            mood_scores.keys(),
            key=lambda m: sum(mood_scores[m]) / len(mood_scores[m]),
            reverse=True
        )[:3]

        # Preferred response length
        lengths = [len(s.bot_response.split()) for s in samples if s.rating >= 4]
        avg_len = int(sum(lengths) / len(lengths)) if lengths else 40
        if avg_len < 20:   style = "extremely concise, one-line"
        elif avg_len < 50: style = "concise, 2-3 sentences"
        elif avg_len < 100: style = "moderate, 3-5 sentences"
        else:              style = "detailed and expansive"

        # High-rated topics keywords
        high_rated = [s for s in samples if s.rating >= 4]
        all_words = " ".join(s.user_message for s in high_rated).lower().split()
        stop = {'the','a','an','is','are','to','of','and','or','in','it','you','i','me','my','can','do'}
        topic_words = [w for w in all_words if w not in stop and len(w) > 3]
        from collections import Counter
        top_topics = [w for w, _ in Counter(topic_words).most_common(5)]

        self._profile = {
            "preferred_moods": preferred_moods,
            "response_style": style,
            "top_topics": top_topics,
            "avg_rating": round(sum(s.rating for s in samples) / len(samples), 2),
            "total_interactions": len(samples),
        }
        return self._profile

    def build_system_prompt(self, base_prompt: str, current_mood: str) -> str:
        """
        Injects learned user preferences into the system prompt.
        """
        profile = self.get_profile()
        lines = [base_prompt]

        if profile["preferred_moods"]:
            moods_str = ", ".join(profile["preferred_moods"])
            lines.append(f"This user responds best to {moods_str} style responses.")

        lines.append(f"Keep responses {profile['response_style']}.")

        if profile["top_topics"]:
            topics_str = ", ".join(profile["top_topics"])
            lines.append(f"They are interested in: {topics_str}.")

        if profile["avg_rating"] > 4.0:
            lines.append("This user rates responses generously — maintain your current depth and style.")
        elif profile["avg_rating"] < 2.5:
            lines.append("Try shorter, more direct philosophical insights.")

        return " ".join(lines)


def _default_profile() -> Dict[str, Any]:
    return {
        "preferred_moods": ["philosophical"],
        "response_style": "concise, 2-3 sentences",
        "top_topics": ["wisdom", "life", "consciousness"],
        "avg_rating": 3.0,
        "total_interactions": 0,
    }


# ─────────────────────────────────────────────
# 3. ADAPTIVE SYSTEM PROMPT MANAGER
# ─────────────────────────────────────────────
class AdaptivePromptManager:
    """
    Learns which system prompt variants produce higher-rated responses.
    Stores variant performance and biases toward top performers.
    """

    PROMPT_VARIANTS = [
        "You are LEVI, a deeply philosophical AI companion. Be poetic, concise, and profound.",
        "You are LEVI, an ancient AI oracle. Speak with wisdom, mystery, and brevity.",
        "You are LEVI, a Stoic philosopher AI. Ground your responses in practical wisdom.",
        "You are LEVI, a Zen master AI. Speak in paradoxes, metaphors, and quiet certainty.",
        "You are LEVI, a cosmic AI muse. Connect human experience to universal truths.",
        "You are LEVI, a visionary AI. Frame insights as discoveries, not pronouncements.",
    ]

    def __init__(self, db: Session):
        self.db = db
        self._scores: Optional[Dict[int, float]] = None

    def get_best_variant(self, mood: str) -> str:
        """Return the highest-performing prompt variant for a given mood."""
        scores = self._load_scores()
        if not scores:
            # Default by mood
            mood_map = {
                "stoic": 2, "zen": 3, "cyberpunk": 1,
                "philosophical": 0, "calm": 3, "inspiring": 4,
                "melancholic": 1, "futuristic": 5,
            }
            idx = mood_map.get(mood.lower(), 0)
            return self.PROMPT_VARIANTS[idx]

        best_idx = max(scores, key=scores.get)
        return self.PROMPT_VARIANTS[best_idx]

    def record_outcome(self, variant_idx: int, rating: int):
        """Update the running average score for a variant."""
        try:
            from training_models import PromptPerformance
        except ImportError:
            from backend.training_models import PromptPerformance

        record = self.db.query(PromptPerformance).filter(
            PromptPerformance.variant_idx == variant_idx
        ).first()

        if record:
            # Exponential moving average
            record.avg_score = record.avg_score * 0.85 + rating * 0.15
            record.sample_count += 1
        else:
            record = PromptPerformance(
                variant_idx=variant_idx,
                avg_score=float(rating),
                sample_count=1,
            )
            self.db.add(record)
        self.db.commit()
        self._scores = None  # invalidate cache

    def _load_scores(self) -> Dict[int, float]:
        if self._scores is not None:
            return self._scores
        try:
            from training_models import PromptPerformance
        except ImportError:
            from backend.training_models import PromptPerformance

        records = self.db.query(PromptPerformance).all()
        self._scores = {r.variant_idx: r.avg_score for r in records if r.sample_count >= 5}
        return self._scores


# ─────────────────────────────────────────────
# 4. EXPORT TRAINING DATA (for Together AI fine-tuning)
# ─────────────────────────────────────────────
def export_training_data(
    db: Session,
    output_path: str = "/tmp/levi_training.jsonl",
    min_rating: int = 4,
    limit: int = 2000,
) -> Tuple[str, int]:
    """
    Export high-quality conversation pairs as JSONL in Together AI's
    fine-tuning format (instruction-following).

    Returns (file_path, record_count).
    """
    try:
        from training_models import TrainingData
    except ImportError:
        from backend.training_models import TrainingData

    samples = (
        db.query(TrainingData)
        .filter(
            TrainingData.rating >= min_rating,
            TrainingData.is_exported == False,
        )
        .order_by(TrainingData.rating.desc(), TrainingData.created_at.desc())
        .limit(limit)
        .all()
    )

    if not samples:
        logger.info("[Learning] No new training samples to export.")
        return output_path, 0

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for s in samples:
            record = {
                "text": (
                    f"<human>: {s.user_message}\n"
                    f"<bot>: {s.bot_response}"
                ),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            s.is_exported = True
            count += 1

    db.commit()
    logger.info(f"[Learning] Exported {count} training samples to {output_path}")
    return output_path, count


# ─────────────────────────────────────────────
# 5. LEARNING ANALYTICS
# ─────────────────────────────────────────────
def get_learning_stats(db: Session) -> Dict[str, Any]:
    """Return a summary of the learning system's state."""
    try:
        from training_models import TrainingData, PromptPerformance
        from models import Quote
    except ImportError:
        from backend.training_models import TrainingData, PromptPerformance
        from backend.models import Quote

    total_samples = db.query(func.count(TrainingData.id)).scalar() or 0
    high_quality  = db.query(func.count(TrainingData.id)).filter(TrainingData.rating >= 4).scalar() or 0
    avg_rating    = db.query(func.avg(TrainingData.rating)).scalar()
    learned_quotes = db.query(func.count(Quote.id)).filter(Quote.topic == "__learned__").scalar() or 0
    unexported    = db.query(func.count(TrainingData.id)).filter(TrainingData.is_exported == False, TrainingData.rating >= 4).scalar() or 0

    prompt_perf = db.query(PromptPerformance).order_by(PromptPerformance.avg_score.desc()).first()

    return {
        "total_training_samples": total_samples,
        "high_quality_samples":   high_quality,
        "avg_response_rating":    round(float(avg_rating or 0), 2),
        "learned_quotes":         learned_quotes,
        "unexported_samples":     unexported,
        "best_prompt_variant":    prompt_perf.variant_idx if prompt_perf else 0,
        "best_prompt_score":      round(prompt_perf.avg_score, 2) if prompt_perf else 0.0,
        "knowledge_base_health":  "good" if learned_quotes > 50 else "growing",
    }


# ─────────────────────────────────────────────
# 6. CONVERSATION QUALITY SIGNAL (real-time)
# ─────────────────────────────────────────────
def infer_implicit_feedback(
    session_history: List[Dict],
    current_user_message: str,
) -> Optional[int]:
    """
    Infer implicit feedback from conversation patterns.
    Called before each turn to rate the PREVIOUS response.

    Signals:
    - User asks follow-up → response was engaging (4)
    - User says thanks/good/amazing → 5
    - User repeats/rephrases same question → response was bad (2)
    - Very short user message after long bot response → 3
    """
    if len(session_history) < 2:
        return None

    prev_bot = session_history[-1].get("bot", "").lower()
    curr_user = current_user_message.lower()

    positive_signals = ["thank", "amazing", "beautiful", "perfect", "love it", "wow", "great", "brilliant"]
    negative_signals = ["what?", "i don't understand", "that doesn't make sense", "repeat", "explain again", "wrong"]

    if any(s in curr_user for s in positive_signals):
        return 5
    if any(s in curr_user for s in negative_signals):
        return 2

    # Follow-up question on same topic = engaged
    prev_words = set(session_history[-1].get("user", "").lower().split())
    curr_words = set(curr_user.split())
    overlap = len(prev_words & curr_words)
    if overlap > 3:
        return 4  # continued engagement

    return None  # no signal
