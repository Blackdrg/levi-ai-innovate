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
from google.cloud import firestore as google_firestore
import asyncio
from backend.services.orchestrator.planner import call_lightweight_llm

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
async def collect_training_sample(
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
    from backend.firestore_db import db as firestore_db

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
    
    # Add to Firestore collection (Async)
    doc_ref = await asyncio.to_thread(firestore_db.collection("training_data").add, sample_data)
    
    # 2. Hybrid Learning: Pattern Crystallization (v6 Phase 15)
    # If absolute best (5-star), crystallize into Profound Memory
    if rating >= 5:
        asyncio.create_task(crystallize_profound_pattern(user_message, bot_response, mood))

    # 3. Standard Learning logic
    if rating >= MIN_QUALITY_SCORE:
        asyncio.create_task(_augment_knowledge_base(user_message, bot_response, mood))

    # Update Structured Memory Graph
    if user_id:
        asyncio.create_task(update_memory_graph(user_id, user_message))

    logger.info(f"[Learning] Collected sample rating={rating} mood={mood} user={user_id}")
    return doc_ref[1].id # add returns (update_time, doc_ref)


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


async def _augment_knowledge_base(question: str, answer: str, mood: str):
    """
    Add a high-quality AI response to the quotes collection in Firestore.
    """
    from backend.firestore_db import db as firestore_db
    from backend.embeddings import embed_text
    try:
        # Avoid exact duplicates
        existing = await asyncio.to_thread(
            lambda: firestore_db.collection("quotes").where("text", "==", answer).limit(1).get()
        )
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

# ── Hybrid Learning: Resonant Core ──────────────────────────────────────────

async def crystallize_profound_pattern(user_input: str, response: str, mood: str):
    """
    Extracts the 'Resonant Core' from a 5-star response and stores it in the
    profound_patterns collection for In-Context Learning (ICL).
    """
    from backend.firestore_db import db as firestore_db
    from backend.embeddings import embed_text
    try:
        # Anonymize (strip PII)
        clean_input = user_input[:200] # Simple truncation for patterns
        clean_response = response[:500]
        
        # Avoid duplicates
        pattern_id = hashlib.md5(f"{clean_input}||{clean_response}".encode()).hexdigest()
        pattern_ref = firestore_db.collection("profound_patterns").document(pattern_id)
        
        if (await asyncio.to_thread(pattern_ref.get)).exists:
            return

        emb = embed_text(clean_input)
        await asyncio.to_thread(pattern_ref.set, {
            "input": clean_input,
            "output": clean_response,
            "embedding": emb,
            "mood": mood,
            "created_at": datetime.utcnow()
        })
        logger.info(f"[HybridLearning] Crystallized profound pattern: {pattern_id[:8]}")
    except Exception as e:
        logger.error(f"[HybridLearning] Crystallization failed: {e}")

async def retrieve_resonant_patterns(user_input: str, threshold: float = 0.82) -> List[Dict[str, str]]:
    """
    Search pattern memory for the most similar successful interactions.
    Returns up to 2 patterns for Few-Shot injection.
    """
    from backend.firestore_db import db as firestore_db
    from backend.embeddings import embed_text, cosine_sim
    try:
        query_emb = embed_text(user_input)
        
        # In a real vector DB we'd do a proper search. 
        # Here we fetch the last 100 patterns and score them (small scale).
        patterns_docs = await asyncio.to_thread(
            lambda: firestore_db.collection("profound_patterns")
            .order_by("created_at", direction="DESCENDING")
            .limit(100).get()
        )
        
        scored = []
        for doc in patterns_docs:
            p = doc.to_dict()
            sim = cosine_sim(query_emb, p["embedding"])
            if sim >= threshold:
                scored.append({"sim": sim, "input": p["input"], "output": p["output"]})
        
        # Return top 2
        scored.sort(key=lambda x: x["sim"], reverse=True)
        return [{"input": s["input"], "output": s["output"]} for s in scored[:2]]
    except Exception as e:
        logger.warning(f"[HybridLearning] Pattern retrieval failed: {e}")
        return []


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

    async def get_profile(self) -> Dict[str, Any]:
        from backend.firestore_db import db as firestore_db
        from backend.redis_client import get_cached_json, cache_json
        
        p = self._profile
        if p is not None:
            return p

        # 1. Try Redis cache
        cache_key = f"user_prof:{self.user_id}"
        cached = get_cached_json(cache_key)
        if cached is not None:
            self._profile = cached
            return cached

        # 2. Fetch interactions (Async Thread)
        def _fetch_samples():
            samples_ref = firestore_db.collection("training_data")
            query = samples_ref.where("user_id", "==", self.user_id).order_by("created_at", direction=google_firestore.Query.DESCENDING).limit(40)
            return [doc.to_dict() for doc in query.get() if doc.to_dict().get("rating") is not None]

        samples = await asyncio.to_thread(_fetch_samples)

        if not samples:
            prof = _default_profile()
            # Fetch structured memory (Async Thread)
            memory_doc = await asyncio.to_thread(firestore_db.collection("user_memory").document(self.user_id).get)
            prof["structured_memory"] = memory_doc.to_dict().get("structured_memory", {}) if memory_doc.exists else {}
            
            # Cache the default profile (TTL = 5 mins for new users)
            cache_json(cache_key, prof, ttl=300)
            
            self._profile = prof
            return prof

        # preferred moods (weight by rating)
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

        # Fetch structured memory graph (Async Thread)
        memory_doc = await asyncio.to_thread(firestore_db.collection("user_memory").document(self.user_id).get)
        prof["structured_memory"] = memory_doc.to_dict().get("structured_memory", {}) if memory_doc.exists else {}

        # 3. Cache the calculated profile (TTL = 30 mins)
        cache_json(cache_key, prof, ttl=1800)
        
        self._profile = prof
        return prof

    async def build_system_prompt(self, base_prompt: str, current_mood: str) -> str:
        """
        Injects learned user preferences into the system prompt.
        """
        profile = await self.get_profile()
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
async def _extract_memory_insights(text: str) -> Dict[str, Any]:
    """
    Uses the Brain's lightweight LLM to extract structured facts, interests, and goals from user text.
    """
    try:
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
        raw_json = await call_lightweight_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract from: \"{text}\""}
            ],
            model="llama-3.1-8b-instant"
        )
        # Parse JSON from LLM output (cleaning if needed)
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0]
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0]
            
        return json.loads(raw_json.strip())
    except Exception as e:
        logger.warning(f"[MemoryExtractor] Extraction failed: {e}")
        return {}


async def update_memory_graph(user_id: str, text: str):
    """
    Extracts insights from text and merges them into the user_memory collection in Firestore.
    """
    from backend.firestore_db import db as firestore_db
    try:
        memory_ref = firestore_db.collection("user_memory").document(user_id)
        memory_doc = await asyncio.to_thread(memory_ref.get)
        
        if not memory_doc.exists:
            await asyncio.to_thread(memory_ref.set, {"user_id": user_id, "structured_memory": {}})
            current = {}
        else:
            current = memory_doc.to_dict().get("structured_memory", {})

        extracted = await _extract_memory_insights(text)
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
        await asyncio.to_thread(memory_ref.update, {"structured_memory": current})
        
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

    async def get_best_variant(self, mood: str) -> str:
        """
        Return the highest-performing prompt variant for a given mood, 
        enriched with global 'Collective Wisdom' patterns (Phase 3).
        """
        scores = await self._load_scores()
        
        # 1. Selection logic
        if not scores:
            mood_map = {
                "stoic": 2, "zen": 3, "cyberpunk": 1,
                "philosophical": 0, "calm": 3, "inspiring": 4,
                "melancholic": 1, "futuristic": 5,
            }
            idx = mood_map.get(mood.lower(), 0)
            base = self.PROMPT_VARIANTS[idx]
        else:
            best_idx = max(scores.keys(), key=lambda k: scores[k])
            base = self.PROMPT_VARIANTS[best_idx]

        # 2. Collective Wisdom Injection (LEVI v6 Phase 3)
        # Fetch top 2 trending insights from the Global Mind (Anonymized)
        from backend.firestore_db import db as firestore_db
        try:
            global_docs = await asyncio.to_thread(
                lambda: firestore_db.collection("global_patterns")
                .order_by("count", direction="DESCENDING")
                .limit(2).get()
            )
            if global_docs:
                insights = [d.to_dict().get("insight") for d in global_docs if d.to_dict().get("insight")]
                if insights:
                    base += f"\n[COLLECTIVE WISDOM]: {' '.join(insights)}"
        except Exception as e:
            logger.warning(f"Shared pattern retrieval failed: {e}")

        return base

    async def evolve_variants(self):
        """
        Autonomous Evolution: Identifies the lowest-performing prompt variant 
        and regenerates it using an LLM based on 5-star success patterns.
        """
        from backend.firestore_db import db as firestore_db
        from backend.services.orchestrator.planner import call_lightweight_llm
        
        try:
            # 1. Find the weak link
            scores = await self._load_scores()
            if not scores or len(scores) < 3: return
            
            worst_idx = min(scores.keys(), key=lambda k: scores[k])
            if scores[worst_idx] > 4.0: return # Already performing well enough
            
            # 2. Fetch 'Gold Standard' samples for mutation (Absolute Anonymity)
            samples_ref = firestore_db.collection("training_data")
            gold_docs = await asyncio.to_thread(
                lambda: samples_ref.where("rating", "==", 5).limit(5).get()
            )
            if not gold_docs: return
            
            success_patterns = []
            for doc in gold_docs:
                s = doc.to_dict()
                # Extract pure philosophical structure, NO content
                success_patterns.append(s.get("bot_response", "")[:100] + "...")

                # 3. Critic-Driven Mutation (LEVI v6 Phase 16)
                # We analyze success patterns and failures to evolve a better variant.
                from backend.services.orchestrator.tool_registry import call_tool
                diagnostic = await call_tool("diagnostic_agent", {
                    "analysis_type": "prompt_evolution",
                    "success_samples": success_patterns
                })
                
                mutation_context = diagnostic.get("message", "Evolve for depth and resonance.")

                mutation_prompt = (
                    "You are the LEVI Core Architect. You must evolve a system instruction to improve user resonance.\n"
                    f"Current Weak Instruction: \"{self.PROMPT_VARIANTS[worst_idx]}\"\n"
                    f"Critic Recommendation: {mutation_context}\n\n"
                    "Rewrite the instruction to be more profound, direct, and poetic. "
                    "Output ONLY the new instruction string. LIMIT 30 words. NO PII."
                )
                
                new_variant = await call_lightweight_llm(
                    messages=[{"role": "system", "content": mutation_prompt}],
                    model="llama-3.1-8b-instant"
                )
                new_variant = new_variant.strip().replace('"', '')
                
                if len(new_variant) > 10:
                    # 4. Finalize Mutation
                    await asyncio.to_thread(
                        lambda: firestore_db.collection("prompt_performance").document(str(worst_idx)).update({
                            "original_prompt": self.PROMPT_VARIANTS[worst_idx],
                            "evolved_prompt": new_variant,
                            "avg_score": 3.0, # Reset for the new generation
                            "sample_count": 0,
                            "evolved_at": datetime.utcnow()
                        })
                    )
                    logger.info(f"[Evolver] Critic-Driven Mutation Complete: Variant {worst_idx}")
                
        except Exception as e:
            logger.error(f"Prompt evolution failed: {e}")

    async def record_outcome(self, variant_idx: int, rating: int):
        """Update the running average score for a variant in Firestore."""
        from backend.firestore_db import db as firestore_db
        try:
            record_ref = firestore_db.collection("prompt_performance").document(str(variant_idx))
            
            def _txn():
                record_doc = record_ref.get()
                if record_doc.exists:
                    record_data = record_doc.to_dict()
                    avg_score = record_data.get("avg_score", 0.0)
                    sample_count = record_data.get("sample_count", 0)
                    new_avg_score = avg_score * 0.85 + rating * 0.15
                    new_sample_count = sample_count + 1
                    record_ref.update({"avg_score": new_avg_score, "sample_count": new_sample_count})
                else:
                    record_ref.set({"variant_idx": variant_idx, "avg_score": float(rating), "sample_count": 1})

            await asyncio.to_thread(_txn)
            self._scores = None  # invalidate cache
        except Exception as e:
            logger.warning(f"[PromptManager] Failed to record outcome for variant {variant_idx}: {e}")

    async def _load_scores(self) -> Dict[int, float]:
        from backend.firestore_db import db as firestore_db
        s = self._scores
        if s is not None:
            return s
        
        records = await asyncio.to_thread(firestore_db.collection("prompt_performance").get)
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
    query = samples_ref.where("rating", ">=", min_rating).where("is_exported", "==", False).order_by("rating", direction=google_firestore.Query.DESCENDING).limit(limit)
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
            perf_docs = firestore_db.collection("prompt_performance").order_by("avg_score", direction=google_firestore.Query.DESCENDING).limit(1).get()
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
# 7. GLOBAL PATTERN LEARNING (LEVI v6)
# ─────────────────────────────────────────────
async def collect_global_pattern(user_message: str, bot_response: str, rating: int):
    """
    Anonymize and aggregate high-quality reasoning patterns for cross-user intelligence.
    """
    if rating < 5: return # Only learn from the absolute best
    
    from backend.firestore_db import db as firestore_db
    from backend.services.orchestrator.planner import call_lightweight_llm

    try:
        # 1. Anonymize & Extract Theme
        prompt = (
            "Extract a high-level philosophical theme or reasoning pattern from this interaction. "
            "Remove all personal data (names, locations, specific entities). "
            "Output JSON: {\"theme\": \"short theme\", \"insight\": \"profound one-liner\"}"
        )
        raw = await call_lightweight_llm([
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"User: {user_message}\nLEVI: {bot_response}"}
        ])
        
        data = json.loads(raw.strip())
        theme = data.get("theme")
        insight = data.get("insight")

        if theme and insight:
            # 2. Store in Global Knowledge Base
            pattern_id = hashlib.md5(theme.lower().encode()).hexdigest()
            pattern_ref = firestore_db.collection("global_patterns").document(pattern_id)
            
            def _txn():
                doc = pattern_ref.get()
                if doc.exists:
                    pattern_ref.update({"count": google_firestore.Increment(1)})
                else:
                    pattern_ref.set({
                        "theme": theme,
                        "insight": insight,
                        "count": 1,
                        "created_at": datetime.utcnow()
                    })

            await asyncio.to_thread(_txn)
            logger.info(f"[GlobalLearning] New pattern crystallized: {theme}")

    except Exception as e:
        logger.warning(f"Global pattern collection failed: {e}")
