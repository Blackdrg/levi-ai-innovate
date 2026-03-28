# pyright: reportMissingImports=false
"""
LEVI-AI Learning System
Collects conversation feedback, learns user preferences,
enriches the knowledge base, and prepares fine-tuning datasets.
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
try:
    from backend.firestore_db import db as firestore_db  # type: ignore
except ImportError:
    firestore_db = None

try:
    from backend.embeddings import embed_text, HAS_MODEL  # type: ignore
except ImportError:
    embed_text = lambda x: []
    HAS_MODEL = False

try:
    from backend.redis_client import (  # type: ignore
        get_cached_user_memory, cache_user_memory, invalidate_user_memory
    )
except ImportError:
    def get_cached_user_memory(x): return None
    def cache_user_memory(x, y): pass
    def invalidate_user_memory(x): pass

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
    user_message: str,
    bot_response: str,
    mood: str,
    rating: Optional[int],       # 1-5 from user, None if not rated
    session_id: str,
    user_id: Optional[str] = None,
) -> Any:
    """
    Store a conversation turn as a training sample in Firestore.
    """
    # Auto-score if no rating provided
    if rating is None:
        rating = _auto_score_response(user_message, bot_response)

    sample_data = {
        "user_message": user_message,
        "bot_response": bot_response,
        "mood": mood or "philosophical",
        "rating": rating,
        "session_id": session_id,
        "user_id": user_id,
        "fingerprint": _fingerprint(user_message, bot_response),
        "is_exported": False,
        "created_at": datetime.utcnow(),
    }
    
    # Add to Firestore collection
    update_time, doc_ref = firestore_db.collection("training_data").add(sample_data)

    # If high quality, augment the quote knowledge base
    if rating >= MIN_QUALITY_SCORE:
        _augment_knowledge_base(user_message, bot_response, mood)

    # Update Structured Memory Graph
    if user_id:
        try:
            update_memory_graph(user_id, user_message)
        except Exception as e:
            logger.warning(f"[Learning] Memory graph update failed: {e}")

    logger.info(f"[Learning] Collected sample rating={rating} mood={mood} user={user_id}")
    return doc_ref.id


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


def _augment_knowledge_base(question: str, answer: str, mood: str):
    """
    Add a high-quality AI response to the quotes collection in Firestore.
    """
    try:
        # Avoid exact duplicates
        existing = firestore_db.collection("quotes").where("text", "==", answer).limit(1).get()
        if len(existing) > 0:
            return

        # Cap knowledge base size (naive count)
        learned_quotes = firestore_db.collection("quotes").where("topic", "==", "__learned__").get()
        if len(learned_quotes) >= MAX_KNOWLEDGE_ENTRIES:
            # Remove oldest
            oldest = firestore_db.collection("quotes").where("topic", "==", "__learned__").order_by("created_at").limit(1).get()
            if oldest:
                oldest[0].reference.delete()

        emb = embed_text(answer)
        firestore_db.collection("quotes").add({
            "text": answer,
            "author": "LEVI-AI",
            "topic": "__learned__",
            "mood": mood,
            "embedding": emb,
            "likes": 0,
            "created_at": datetime.utcnow()
        })
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

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._profile: Optional[Dict[str, Any]] = None

    def get_profile(self) -> Dict[str, Any]:
        p = self._profile
        if p is not None:
            return p

        # Fetch last 40 rated interactions for this user from Firestore
        samples_ref = firestore_db.collection("training_data")
        query = samples_ref.where("user_id", "==", self.user_id).order_by("created_at", direction="DESCENDING").limit(40)
        samples_docs = query.get()
        
        samples = [doc.to_dict() for doc in samples_docs if doc.to_dict().get("rating") is not None]

        if not samples:
            prof = _default_profile()
            # Fetch structured memory
            memory_doc = firestore_db.collection("user_memory").document(self.user_id).get()
            prof["structured_memory"] = memory_doc.to_dict().get("structured_memory", {}) if memory_doc.exists else {}
            self._profile = prof
            return prof
        # Preferred moods (weight by rating)
        mood_scores: Dict[str, List[int]] = {}
        for s in samples:
            mood_scores.setdefault(s.get("mood", "philosophical"), []).append(s.get("rating", 3))

        preferred_moods_sorted = sorted(
            mood_scores.keys(),
            key=lambda m: sum(mood_scores[m]) / len(mood_scores[m]),
            reverse=True
        )
        preferred_moods = preferred_moods_sorted[:3]

        # Preferred response length
        lengths = [len(s.get("bot_response", "").split()) for s in samples if s.get("rating", 0) >= 4]
        avg_len = int(sum(lengths) / len(lengths)) if lengths else 40
        if avg_len < 20:   style = "extremely concise, one-line"
        elif avg_len < 50: style = "concise, 2-3 sentences"
        elif avg_len < 100: style = "moderate, 3-5 sentences"
        else:              style = "detailed and expansive"

        # High-rated topics keywords
        high_rated = [s for s in samples if s.get("rating", 0) >= 4]
        all_words = " ".join(s.get("user_message", "") for s in high_rated).lower().split()
        stop = {'the','a','an','is','are','to','of','and','or','in','it','you','i','me','my','can','do'}
        topic_words = [w for w in all_words if w not in stop and len(w) > 3]
        from collections import Counter
        top_topics = [w for w, _ in Counter(topic_words).most_common(5)]

        prof: Dict[str, Any] = {
            "preferred_moods": preferred_moods,
            "response_style": style,
            "top_topics": top_topics,
            "avg_rating": round(float(sum(s.get("rating", 0) for s in samples) / len(samples)), 2) if samples else 3.0,
            "total_interactions": len(samples),
        }

        # Fetch structured memory graph from Firestore
        memory_doc = firestore_db.collection("user_memory").document(self.user_id).get()
        prof["structured_memory"] = memory_doc.to_dict().get("structured_memory", {}) if memory_doc.exists else {}

        self._profile = prof
        return prof

    def build_system_prompt(self, base_prompt: str, current_mood: str) -> str:
        """
        Injects learned user preferences into the system prompt.
        """
        profile = self.get_profile()
        lines = [base_prompt]

        # ─── Structured Memory injection ───
        structured = profile.get("structured_memory", {})
        if structured:
            entities = structured.get("entities", {})
            for cat, items in entities.items():
                if items:
                    # e.g., "User interests: coffee, stoicism"
                    lines.append(f"User {cat}: {', '.join(items)}.")

        if profile.get("preferred_moods"):
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
# 2.5 STRUCTURED MEMORY GRAPH - EXTRACTOR
# ─────────────────────────────────────────────
def _extract_memory_insights(text: str) -> Dict[str, Any]:
    """
    Uses Groq to extract structured facts, interests, and goals from user text.
    """
    import groq  # type: ignore
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {}

    try:
        client = groq.Groq(api_key=api_key)
        system_prompt = """You are a profile extraction system for a philosophical AI. 
Analyze the user statement and extract key-value facts for user memory.
Return in STRICT JSON ONLY:
{
  "entities": {
     "interests": ["keyword 1", "keyword 2"],
     "goals": ["goal phrase 1"],
     "facts": ["general descriptive fact 1"]
  }
}"""
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract from: \"{text}\""}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        logger.warning(f"[MemoryExtractor] Extraction failed: {e}")
        return {}


def update_memory_graph(user_id: str, text: str):
    """
    Extracts insights from text and merges them into the user_memory collection in Firestore.
    """
    try:
        memory_ref = firestore_db.collection("user_memory").document(user_id)
        memory_doc = memory_ref.get()
        
        if not memory_doc.exists:
            memory_ref.set({"user_id": user_id, "structured_memory": {}})
            current = {}
        else:
            current = memory_doc.to_dict().get("structured_memory", {})

        extracted = _extract_memory_insights(text)
        if not extracted:
            return

        curr_entities = current.get("entities", {})
        new_entities = extracted.get("entities", {})

        updated_entities = {}
        for key in ["interests", "goals", "facts"]:
            list_curr = curr_entities.get(key, [])
            list_new = new_entities.get(key, [])
            
            merged_set = set()
            for item in (list_curr + list_new):
                if item:
                    merged_set.add(str(item))

            capped_list = list(merged_set)[:15]
            updated_entities[key] = capped_list

        current["entities"] = updated_entities
        memory_ref.update({"structured_memory": current})
        
        logger.info(f"[MemoryGraph] Updated memory graph for user {user_id}")
    except Exception as e:
        logger.warning(f"[MemoryGraph] Failed to update memory for user {user_id}: {e}")


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

    def __init__(self):
        self._scores: Optional[Dict[int, float]] = None

    def get_best_variant(self, mood: str) -> str:
        """Return the highest-performing prompt variant for a given mood via Firestore."""
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

        best_idx = max(scores.keys(), key=lambda k: scores[k])
        return self.PROMPT_VARIANTS[best_idx]

    def record_outcome(self, variant_idx: int, rating: int):
        """Update the running average score for a variant in Firestore."""
        try:
            record_ref = firestore_db.collection("prompt_performance").document(str(variant_idx))
            record_doc = record_ref.get()

            if record_doc.exists:
                record_data = record_doc.to_dict()
                avg_score = record_data.get("avg_score", 0.0)
                sample_count = record_data.get("sample_count", 0)
                # Exponential moving average
                new_avg_score = avg_score * 0.85 + rating * 0.15
                new_sample_count = sample_count + 1
                record_ref.update({
                    "avg_score": new_avg_score,
                    "sample_count": new_sample_count,
                })
            else:
                record_ref.set({
                    "variant_idx": variant_idx,
                    "avg_score": float(rating),
                    "sample_count": 1,
                })
            self._scores = None  # invalidate cache
        except Exception as e:
            logger.warning(f"[PromptManager] Failed to record outcome for variant {variant_idx}: {e}")

    def _load_scores(self) -> Dict[int, float]:
        s = self._scores
        if s is not None:
            return s
        
        records = firestore_db.collection("prompt_performance").get()
        self._scores = {int(r.id): r.to_dict()["avg_score"] for r in records if r.to_dict().get("sample_count", 0) >= 5}
        return self._scores  # type: ignore


# ─────────────────────────────────────────────
# 4. EXPORT TRAINING DATA (for Together AI fine-tuning)
# ─────────────────────────────────────────────
def export_training_data(
    output_path: str = "/tmp/levi_training.jsonl",
    min_rating: int = 4,
    limit: int = 2000,
) -> Tuple[str, int]:
    """
    Export high-quality conversation pairs from Firestore as JSONL in Together AI's
    fine-tuning format (instruction-following).

    Returns (file_path, record_count).
    """
    samples_ref = firestore_db.collection("training_data")
    query = samples_ref.where("rating", ">=", min_rating).where("is_exported", "==", False).order_by("rating", direction="DESCENDING").limit(limit)
    samples_docs = query.get()

    if not samples_docs:
        logger.info("[Learning] No new training samples to export.")
        return output_path, 0

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for doc in samples_docs:
            s = doc.to_dict()
            record = {
                "text": (
                    f"<human>: {s.get('user_message')}\n"
                    f"<bot>: {s.get('bot_response')}"
                ),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            doc.reference.update({"is_exported": True})
            count += 1

    logger.info(f"[Learning] Exported {count} training samples to {output_path}")
    return output_path, count


# ─────────────────────────────────────────────
# 5. LEARNING ANALYTICS
# ─────────────────────────────────────────────
def get_learning_stats():
    """Returns learning system statistics from Firestore."""
    try:
        # Firestore counts (Safe-access)
        total_samples = 0
        high_quality = 0
        avg_rating = 0
        learned_quotes = 0
        
        try:
            total_samples = len(firestore_db.collection("training_data").get())
            hq_docs = firestore_db.collection("training_data").where("rating", ">=", 4).get()
            high_quality = len(hq_docs)
            if high_quality > 0:
                avg_rating = sum(d.to_dict().get("rating", 0) for d in hq_docs) / high_quality
            learned_quotes = len(firestore_db.collection("quotes").where("topic", "==", "__learned__").get())
        except Exception as e:
            logger.warning(f"Firestore stats failed: {e}")

        # Prompt Performance from Firestore
        best_variant = 0
        best_score = 0.0
        try:
            perf_docs = firestore_db.collection("prompt_performance").order_by("avg_score", direction="DESCENDING").limit(1).get()
            if perf_docs:
                best_variant = int(perf_docs[0].id)
                best_score = perf_docs[0].to_dict().get("avg_score", 0.0)
        except Exception:
            pass

        return {
            "total_training_samples": total_samples,
            "high_quality_samples":   high_quality,
            "avg_response_rating":    round(float(avg_rating or 0), 2),
            "learned_quotes":         learned_quotes,
            "best_prompt_variant":    best_variant,
            "best_prompt_score":      round(best_score, 2),
            "knowledge_base_health":  "good" if learned_quotes > 50 else "growing",
        }
    except Exception as e:
        logger.error(f"Critical stats failure: {e}")
        return {"status": "error", "message": str(e)}


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
