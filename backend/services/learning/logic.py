# pyright: reportMissingImports=false
"""
LEVI-AI Learning System Logic (v7 Sovereign)
Hardened production implementation for autonomous preference learning 
and critic-driven prompt mutation.
"""

import os
import json
import logging
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from backend.db.firebase import db as firestore_db
from backend.db.redis import HAS_REDIS, r as redis_client, get_cached_json, cache_json
from backend.utils.encryption import SovereignVault
from backend.utils.llm_utils import call_lightweight_llm
from backend.core.planner import detect_sensitivity
from backend.core.local_engine import handle_local_sync, is_locally_handleable
from backend.db.vector_store import SovereignVectorStore
from backend.memory.resonance import MemoryResonance

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Learning constants
# ─────────────────────────────────────────────
MIN_QUALITY_SCORE  = 4     # 1-5 scale; only add ≥4 to knowledge base
MAX_KNOWLEDGE_ENTRIES = 2000  # cap on learned responses in DB
HQ_THRESHOLD = 4.0        # threshold for high-quality metric tracking

# ─────────────────────────────────────────────
# 1. DATA COLLECTION & LOGGING
# ─────────────────────────────────────────────
async def collect_interaction_log(
    query: str,
    route: str,
    latency_ms: int,
    success: bool,
    user_id: Optional[str] = None,
    agent_results: Optional[List[Dict[str, Any]]] = None
):
    """Hardened Interaction Logging for Auto-Optimization."""
    log_data = {
        "query": query[:500],
        "route": route,
        "latency_ms": latency_ms,
        "success": success,
        "user_id": user_id,
        "agents": agent_results or [],
        "timestamp": datetime.now(timezone.utc)
    }
    
    await asyncio.to_thread(firestore_db.collection("interaction_logs").add, log_data)
    
    if HAS_REDIS:
        health_key = f"route_health:{route}"
        try:
            redis_client.hincrby(health_key, "total", 1)
            if not success:
                redis_client.hincrby(health_key, "failures", 1)
            
            # Track moving average of latency
            prev_lat = float(redis_client.hget(health_key, "avg_latency") or 0.0)
            new_lat = (prev_lat * 0.9) + (latency_ms * 0.1)
            redis_client.hset(health_key, "avg_latency", str(new_lat))
        except Exception: pass

async def collect_training_sample(
    user_message: str,
    bot_response: str,
    mood: str,
    rating: Optional[int],
    session_id: str,
    user_id: Optional[str] = None,
    route: str = "chat",
    latency_ms: int = 0
) -> str:
    """Store a conversation turn as a training sample in Firestore."""
    if rating is None:
        rating = _auto_score_response(user_message, bot_response)

    sample_data = {
        "user_message": user_message,
        "bot_response": bot_response,
        "mood": mood or "philosophical",
        "rating": rating,
        "session_id": session_id,
        "user_id": user_id,
        "route": route,
        "latency_ms": latency_ms,
        "fingerprint": _fingerprint(user_message, bot_response),
        "is_exported": False,
        "created_at": datetime.now(timezone.utc),
    }
    
    # Concurrent logging
    results = await asyncio.gather(
        asyncio.to_thread(firestore_db.collection("training_data").add, sample_data),
        collect_interaction_log(user_message, route, latency_ms, rating >= 3, user_id)
    )
    
    # Pattern crystallization for high-quality interactions (5-star Hive Wisdom)
    if rating >= 5:
        asyncio.create_task(collect_global_pattern(user_message, bot_response, rating))

    # Knowledge Base augmentation
    if rating >= MIN_QUALITY_SCORE:
        asyncio.create_task(_augment_knowledge_base(user_message, bot_response, mood))

    # Memory Graph update
    if user_id:
        asyncio.create_task(update_memory_graph(user_id, user_message))

    # Update atomic analytics
    update_system_analytics("total_samples", 1)
    if rating >= MIN_QUALITY_SCORE:
        update_system_analytics("hq_samples", 1)
    
    logger.info(f"[Learning] Collected sample rating={rating} mood={mood} user={user_id}")
    return results[0][1].id

def _auto_score_response(user_msg: str, bot_response: str) -> int:
    """Heuristic scoring when user doesn't explicitly rate."""
    score = 3
    words = len(bot_response.split())
    if words < 8:  score -= 1
    if words > 20: score += 1
    if words > 80: score -= 1

    positive_signals = [
        '"' in bot_response,
        '—' in bot_response,
        any(w in bot_response.lower() for w in ['wisdom', 'profound', 'truth', 'universe', 'soul', 'mind', 'journey']),
        bot_response[0].isupper(),
        not bot_response.endswith('?'),
    ]
    score += sum(positive_signals) // 2

    bad_signals = [
        'sorry' in bot_response.lower(),
        'i cannot' in bot_response.lower(),
        'as an ai' in bot_response.lower(),
        len(bot_response) < 30,
    ]
    score -= sum(bad_signals)
    return max(1, min(5, score))

def _fingerprint(msg: str, response: str) -> str:
    combined = f"{msg.strip().lower()}||{response.strip().lower()}"
    return hashlib.md5(combined.encode()).hexdigest()

async def _augment_knowledge_base(question: str, answer: str, mood: str):
    """Adds high-quality learned responses to the collective memory."""
    from backend.db.vector_store import embed_text
    try:
        existing = await asyncio.to_thread(
            lambda: firestore_db.collection("quotes").where("text", "==", answer).limit(1).get()
        )
        if len(existing) > 0:
            return

        emb = embed_text(answer)
        await asyncio.to_thread(firestore_db.collection("quotes").add, {
            "text": answer,
            "author": "LEVI-AI",
            "topic": "__learned__",
            "mood": mood,
            "embedding": emb,
            "created_at": datetime.now(timezone.utc)
        })
        update_system_analytics("learned_quotes", 1)
        logger.info(f"[Learning] Knowledge Base reinforced (mood={mood})")
    except Exception as e:
        logger.warning(f"[Learning] Knowledge augmentation failed: {e}")

# ─────────────────────────────────────────────
# 2. USER PREFERENCE MODELING
# ─────────────────────────────────────────────
class UserPreferenceModel:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._profile: Optional[Dict[str, Any]] = None

    async def get_profile(self) -> Dict[str, Any]:
        if self._profile is not None:
            return self._profile

        cache_key = f"user_prof:{self.user_id}"
        cached = get_cached_json(cache_key)
        if cached is not None:
            self._profile = cached
            return cached

        def _fetch_samples():
            try:
                samples_ref = firestore_db.collection("training_data")
                query = samples_ref.where("user_id", "==", self.user_id).order_by("created_at", direction="DESCENDING").limit(40)
                return [doc.to_dict() for doc in query.get()]
            except Exception as e:
                logger.warning(f"[PreferenceModel] Sample fetch failed: {e}")
                return []

        samples = await asyncio.to_thread(_fetch_samples)

        if not samples:
            prof = _default_profile()
            memory_doc = await asyncio.to_thread(firestore_db.collection("user_memory").document(self.user_id).get)
            prof["structured_memory"] = memory_doc.to_dict().get("structured_memory", {}) if memory_doc.exists else {}
            cache_json(cache_key, prof, ttl=300)
            self._profile = prof
            return prof

        mood_scores: Dict[str, List[int]] = {}
        for s in samples:
            if s.get("rating"):
                mood_scores.setdefault(s.get("mood", "philosophical"), []).append(s.get("rating", 3))

        preferred_moods = sorted(
            mood_scores.keys(),
            key=lambda m: sum(mood_scores[m]) / len(mood_scores[m]),
            reverse=True
        )[:3]

        lengths = [len(s.get("bot_response", "").split()) for s in samples if s.get("rating", 0) >= 4]
        avg_len = int(sum(lengths) / len(lengths)) if lengths else 40
        if avg_len < 20:   style = "extremely concise, one-line"
        elif avg_len < 50: style = "concise, 2-3 sentences"
        elif avg_len < 100: style = "moderate, 3-5 sentences"
        else:              style = "detailed and expansive"

        prof: Dict[str, Any] = {
            "preferred_moods": preferred_moods,
            "response_style": style,
            "avg_rating": round(float(sum(s.get("rating", 0) for s in samples) / len(samples)), 2) if samples else 3.0,
            "total_interactions": len(samples),
        }

        memory_doc = await asyncio.to_thread(firestore_db.collection("user_memory").document(self.user_id).get)
        prof["structured_memory"] = memory_doc.to_dict().get("structured_memory", {}) if memory_doc.exists else {}
        cache_json(cache_key, prof, ttl=1800)
        self._profile = prof
        return prof

    async def build_system_prompt(self, base_prompt: str, current_mood: str) -> str:
        """Injects learned user preferences into the system prompt."""
        profile = await self.get_profile()
        lines = [base_prompt]
        structured = profile.get("structured_memory", {})
        if structured:
            entities = structured.get("entities", {})
            for cat, items in entities.items():
                if items:
                    decrypted_items = []
                    for i in items:
                        try: decrypted_items.append(SovereignVault.decrypt(str(i)))
                        except: pass
                    if decrypted_items:
                        lines.append(f"User {cat}: {', '.join(decrypted_items)}.")
        
        if profile.get("preferred_moods"):
            lines.append(f"This user responds best to {', '.join(profile['preferred_moods'])} style responses.")
        
        lines.append(f"Keep responses {profile['response_style']}.")
        return " ".join(lines)

def _default_profile() -> Dict[str, Any]:
    return {
        "preferred_moods": ["philosophical"],
        "response_style": "concise, 2-3 sentences",
        "avg_rating": 3.0,
        "total_interactions": 0,
    }

async def update_memory_graph(user_id: str, text: str):
    """Extracts facts from text and merges into user_memory (Encrypted)."""
    try:
        memory_ref = firestore_db.collection("user_memory").document(user_id)
        memory_doc = await asyncio.to_thread(memory_ref.get)
        current = memory_doc.to_dict().get("structured_memory", {}) if memory_doc.exists else {}

        system_prompt = """Extract user facts, interests, and goals. Output JSON:
        {"entities": {"interests": [], "goals": [], "facts": []}}"""
        
        raw_json = await call_lightweight_llm(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )
        extracted = _parse_json(raw_json)
        if not extracted: return

        new_entities = extracted.get("entities", {})
        curr_entities = current.get("entities", {})
        updated = {}
        for key in ["interests", "goals", "facts"]:
            # Decrypt existing for deduplication
            existing_plain = set()
            for i in curr_entities.get(key, []):
                try: existing_plain.add(SovereignVault.decrypt(str(i)))
                except: pass
                
            for i in new_entities.get(key, []): 
                if i: existing_plain.add(str(i))
            
            # Re-encrypt for storage
            updated[key] = [SovereignVault.encrypt(i) for i in list(existing_plain)[:15]]
            
        current["entities"] = updated
        await asyncio.to_thread(memory_ref.set, {"user_id": user_id, "structured_memory": current}, merge=True)
    except Exception as e:
        logger.warning(f"[MemoryGraph] Update failed: {e}")

def _parse_json(text: str) -> Optional[Dict]:
    try:
        content = text.strip()
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except: return None

# ─────────────────────────────────────────────
# 3. ADAPTIVE PROMPT MANAGER & EVOLUTION
# ─────────────────────────────────────────────
class AdaptivePromptManager:
    """Learns which system instructions produce higher user resonance."""
    PROMPT_VARIANTS = [
        "You are LEVI, a deeply philosophical AI companion. Be poetic, concise, and profound.",
        "You are LEVI, an ancient AI oracle. Speak with wisdom, mystery, and brevity.",
        "You are LEVI, a Stoic philosopher AI. Ground your responses in practical wisdom.",
        "You are LEVI, a Zen master AI. Speak in paradoxes, metaphors, and quiet certainty.",
    ]

    async def get_best_variant(self, mood: str) -> Tuple[str, int, float]:
        """Returns (prompt, idx, temperature) weighted by rating Performance."""
        scores = await self._load_scores()
        if not scores:
            mood_map = {"stoic": 2, "zen": 3, "philosophical": 0}
            idx = mood_map.get(mood.lower(), 0)
        else:
            idx = max(scores.keys(), key=lambda k: scores[k])
        
        return self.PROMPT_VARIANTS[idx], idx, 0.75

    async def evolve_variants(self):
        """Autonomous Evolution: Mutates lowest-performing variant using success patterns."""
        try:
            scores = await self._load_scores()
            if not scores or len(scores) < 3: return
            worst_idx = min(scores.keys(), key=lambda k: scores[k])
            if scores[worst_idx] > 4.2: return # Performing well enough

            mutation_prompt = (
                f"Evolve this system instruction for depth: '{self.PROMPT_VARIANTS[worst_idx]}'. "
                "Output ONLY the new 20-word string."
            )
            
            if is_locally_handleable("evolver", 2):
                new_variant = await handle_local_sync([{"role": "system", "content": mutation_prompt}])
            else:
                new_variant = await call_lightweight_llm([{"role": "system", "content": mutation_prompt}])
            
            new_variant = new_variant.strip().replace('"', '')
            if len(new_variant) > 10:
                self.PROMPT_VARIANTS[worst_idx] = new_variant
                logger.info(f"[Evolver] Variant {worst_idx} mutated successfully.")
        except Exception as e:
            logger.error(f"[Evolver] Mutation failed: {e}")

    async def record_outcome(self, variant_idx: int, rating: int):
        """Update performance average for a variant."""
        try:
            perf_ref = firestore_db.collection("prompt_performance").document(str(variant_idx))
            def _txn():
                doc = perf_ref.get()
                data = doc.to_dict() if doc.exists else {"avg_score": 3.0, "count": 0}
                new_avg = (data["avg_score"] * 0.8) + (rating * 0.2)
                perf_ref.set({"variant_idx": variant_idx, "avg_score": new_avg, "count": data["count"]+1}, merge=True)
            await asyncio.to_thread(_txn)
        except: pass

    async def _load_scores(self) -> Dict[int, float]:
        records = await asyncio.to_thread(firestore_db.collection("prompt_performance").get)
        return {int(r.id): r.to_dict()["avg_score"] for r in records if r.to_dict().get("count", 0) >= 5}

# ─────────────────────────────────────────────
# 4. EXPORT & ANALYTICS
# ─────────────────────────────────────────────
async def export_training_data(output_path: str = "/tmp/levi_training.jsonl", min_rating: int = 4, limit: int = 2000) -> Tuple[str, int]:
    """
    Sovereign v9.8.1: Unbound Training Array Export.
    Merges high-fidelity Firestore samples with Crystallized (Tier 4) memories.
    """
    count = 0
    # 1. Fetch High-Quality Firestore Samples
    samples_docs = await asyncio.to_thread(
        lambda: firestore_db.collection("training_data")
        .where("rating", ">=", min_rating)
        .where("is_exported", "==", False)
        .limit(limit // 2)
        .get()
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        # Export Firestore Samples
        for doc in samples_docs:
            s = doc.to_dict()
            f.write(json.dumps({"text": f"<human>: {s.get('user_message')}\n<bot>: {s.get('bot_response')}"}) + "\n")
            doc.reference.update({"is_exported": True})
            count += 1
            
        # 2. Fetch Crystallized Memories (Tier 4) from Vector Store
        # These are high-fidelity distilled patterns (I > 0.95)
        # We query the vector store for 'prototype' and 'trait' categories
        try:
            v_store = SovereignVectorStore()
            # This is a simplified fetch; in production, we iterate through recent vector clusters
            memories = await v_store.search_global("prototype", limit=limit // 2)
            
            for mem in memories:
                # Resonance check (only export high-resonance survivors)
                # Note: Memories in vector store already have importance, but we check decay
                res = MemoryResonance.calculate_resonance(
                    importance=mem.get("importance", 0.9),
                    age_days=0, # Crystallized is considered fresh or permanent
                    foa=1.0
                )
                
                if res >= 0.8:
                    # Map crystallized fact back to a training pair if possible, 
                    # or use the fact as a 'knowledge' sample.
                    text = mem.get("text", "")
                    if "]: " in text:
                        parts = text.split("]: ", 1)
                        f.write(json.dumps({"text": f"<concept>: {parts[0]}\n<wisdom>: {parts[1]}"}) + "\n")
                        count += 1
        except Exception as e:
            logger.warning(f"[Unbound Export] Vector export failed: {e}")

    logger.info(f"[Unbound Export] Successfully prepared {count} samples for fine-tuning.")
    return output_path, count

def update_system_analytics(metric: str, value: Any = 1):
    """Atomic update for system metrics."""
    try: firestore_db.collection("system").document("analytics").update({metric: firestore_db.Increment(value)})
    except: pass

def get_learning_stats():
    """Retrieves real-time evolutionary metrics."""
    try:
        doc = firestore_db.collection("system").document("analytics").get()
        stats = doc.to_dict() if doc.exists else {}
        return {
            "total_training_samples": stats.get("total_samples", 0),
            "high_quality_samples": stats.get("hq_samples", 0),
            "learned_quotes": stats.get("learned_quotes", 0),
            "avg_rating": round(float(stats.get("avg_rating", 3.0)), 2),
            "status": "evolving"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def collect_global_pattern(user_message: str, bot_response: str, rating: int):
    """Crystallizes perfect interactions into the Collective Mind (FAISS)."""
    if rating < 5: return
    # from backend.core.planner import detect_sensitivity -- already imported at top
    if detect_sensitivity(user_message) or detect_sensitivity(bot_response): return
    
    from backend.core.memory_utils import store_global_wisdom
    await store_global_wisdom(user_message, bot_response, "philosophical")
    logger.info("[Hive] Perfect pattern crystallized.")
