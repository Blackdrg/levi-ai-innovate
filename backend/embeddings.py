# embeddings.py
import os
import logging
import asyncio
import json
from typing import List, Union, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Tier 1: Local ONNX (v15.0 Hardened)
BERT_MODEL_PATH = os.getenv("BERT_MODEL_PATH", "models/bert-base-uncased-quantized.onnx")
SOVEREIGN_MODE = os.getenv("SOVEREIGN_MODE", "true").lower() == "true"

class ONNXEmbedder:
    _session = None
    _tokenizer = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls):
        if cls._session is None:
            async with cls._lock:
                if cls._session is None:
                    try:
                        import onnxruntime as ort
                        from transformers import AutoTokenizer
                        
                        logger.info(f"[Embedder] Loading ONNX model from {BERT_MODEL_PATH}")
                        cls._session = ort.InferenceSession(
                            BERT_MODEL_PATH,
                            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
                        )
                        
                        sovereign = os.getenv("SOVEREIGN_MODE", "true").lower() == "true"
                        cls._tokenizer = AutoTokenizer.from_pretrained(
                            "bert-base-uncased",
                            local_files_only=SOVEREIGN_MODE
                        )
                    except Exception as e:
                        logger.error(f"[Embedder] Failed to load ONNX: {e}")
                        return None
        return cls._session, cls._tokenizer

async def embed(text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """
    Sovereign v15.0 Hierarchical Embedding Fallback:
    Tier 1: Local ONNX (Local-First, Fast)
    Tier 2: Ollama API (Local-First, Reliable)
    Tier 3: SentenceTransformers (Local-First, Accurate)
    """
    
    # 1. Tier 1: Local ONNX
    if os.getenv("BERT_PROVIDER", "onnx") == "onnx":
        try:
            session, tokenizer = await ONNXEmbedder.get_instance()
            if session:
                inputs = [text] if isinstance(text, str) else text
                results = []
                for t in inputs:
                    enc = tokenizer(t, return_tensors="np", padding=True, truncation=True)
                    ort_outs = await asyncio.to_thread(
                        lambda: session.run(None, {k: v for k, v in enc.items()})
                    )
                    # Mean pooling
                    emb = ort_outs[0].mean(axis=1).flatten().tolist()
                    results.append(emb)
                return results[0] if isinstance(text, str) else results
        except Exception as e:
            logger.warning(f"[Embedder] ONNX Tier 1 failure: {e}")

    # 2. Tier 2: Local Ollama
    if os.getenv("OLLAMA_EMBEDDING_ENABLED", "true").lower() == "true":
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            import httpx
            model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
            inputs = [text] if isinstance(text, str) else text
            
            async with httpx.AsyncClient() as client:
                embeddings = []
                for inp in inputs:
                    res = await client.post(f"{ollama_url}/api/embeddings", json={"model": model, "prompt": inp})
                    embeddings.append(res.json()["embedding"])
                
                return embeddings[0] if isinstance(text, str) else embeddings
        except Exception as e:
            logger.warning(f"[Embedder] Ollama Tier 2 failure: {e}")

    # 3. Tier 3: Local SentenceTransformers (Original Fallback)
    try:
        from sentence_transformers import SentenceTransformer
        # We'll use a local instance for simple fallback
        model_name = "nomic-ai/nomic-embed-text-v1.5"
        
        # v15.2: Sovereign Hardening
        sovereign = os.getenv("SOVEREIGN_MODE", "true").lower() == "true"
        model = await asyncio.to_thread(
            lambda: SentenceTransformer(
                model_name, 
                trust_remote_code=not sovereign, 
                local_files_only=sovereign
            )
        )
        
        embeddings = await asyncio.to_thread(
            lambda: model.encode(text, normalize_embeddings=True)
        )
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"[Embedder] All embedding tiers FAILED: {e}")
        raise RuntimeError("Failed to generate embeddings across all tiers.")

async def embed_text(text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """v13.0 Bridge: Shared alias for common Brain components."""
    return await embed(text)
