"""
LEVI-AI Latency Benchmark v16.1.
Validates system performance on H100/A100 hardware.
Measures: ONNX Embeddings, DistilBERT Intent, Ollama Inference.
"""

import asyncio
import time
import logging
import numpy as np
from statistics import mean, stdev

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("benchmark")

async def benchmark_embeddings(iterations=100):
    from backend.embeddings import embed_text
    times = []
    text = "Deploying the sovereign cognitive network across distributed nodes."
    
    # Warmup
    await embed_text(text)
    
    for _ in range(iterations):
        start = time.perf_counter()
        await embed_text(text)
        times.append((time.perf_counter() - start) * 1000)
    
    return mean(times), stdev(times)

async def benchmark_intent(iterations=50):
    from backend.core.intent_classifier import HybridIntentClassifier
    classifier = HybridIntentClassifier()
    times = []
    text = "Can you help me refactor this python script and draw a diagram?"
    
    # Warmup
    await classifier.classify(text)
    
    for _ in range(iterations):
        start = time.perf_counter()
        await classifier.classify(text)
        times.append((time.perf_counter() - start) * 1000)
    
    return mean(times), stdev(times)

async def benchmark_inference(iterations=10):
    from backend.services.brain_service import BrainService
    service = BrainService()
    times = []
    text = "Write a hello world in Rust."
    
    # Warmup
    await service.call_local_llm(text)
    
    for _ in range(iterations):
        start = time.perf_counter()
        await service.call_local_llm(text)
        times.append((time.perf_counter() - start) * 1000)
    
    return mean(times), stdev(times)

async def run_suite():
    print("🚀 [Benchmark] Initiating Sovereignty Performance Audit...")
    
    # 1. Embeddings (ONNX)
    e_mean, e_std = await benchmark_embeddings()
    print(f"📊 [Embeddings] Avg: {e_mean:.2f}ms (Std: {e_std:.2f}ms) - Target: < 15ms")

    # 2. Intent (Hybrid - DistilBERT)
    i_mean, i_std = await benchmark_intent()
    print(f"📊 [Intent]     Avg: {i_mean:.2f}ms (Std: {i_std:.2f}ms) - Target: < 50ms")

    # 3. Inference (Ollama - Llama 3)
    l_mean, l_std = await benchmark_inference()
    print(f"📊 [Inference]  Avg: {l_mean:.2f}ms (Std: {l_std:.2f}ms) - Target: < 1000ms")

    total_path = e_mean + i_mean
    print(f"🏁 [Total Path] Perception + Intent: {total_path:.2f}ms")
    
    if total_path < 65:
        print("✅ PERFORMANCE STATUS: GRADUATED (H100 Ready)")
    else:
        print("⚠️ PERFORMANCE STATUS: DEGRADED (Check GPU Bindings)")

if __name__ == "__main__":
    asyncio.run(run_suite())
