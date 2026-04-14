import sys
import os
import asyncio
import time
import numpy as np
import logging
from typing import List

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.core.intent_classifier import HybridIntentClassifier

# Configure logging to be quiet
logging.basicConfig(level=logging.ERROR)

TEST_INTENTS = [
    "hello there",
    "generate an image of a cat in space",
    "write a python script for a rest api",
    "what is the price of ethereum?",
    "calculate the square root of 256",
    "summarize this legal document",
    "how is ai related to neural networks?",
    "help me with my homework",
    "create a logo for a tech startup",
    "fix the bug in my java code"
] * 10 # 100 intents

async def run_test():
    classifier = HybridIntentClassifier()
    latencies = []
    
    print(f"Starting Perception Engine Latency Test (100 iterations)...")
    
    # Warmup
    await classifier.classify("warmup")
    
    for i, intent in enumerate(TEST_INTENTS):
        start_time = time.perf_counter()
        await classifier.classify(intent)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)
        
        if (i + 1) % 20 == 0:
            print(f"Completed {i+1}/100...")

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    avg = np.mean(latencies)
    
    print("\n--- RESULTS ---")
    print(f"Average Latency: {avg:.2f}ms")
    print(f"P50 Latency:     {p50:.2f}ms")
    print(f"P95 Latency:     {p95:.2f}ms")
    print(f"P99 Latency:     {p99:.2f}ms")
    
    if p95 < 350:
        print("\nSUCCESS: P95 < 350ms")
    else:
        print("\nFAILURE: P95 >= 350ms")

if __name__ == "__main__":
    asyncio.run(run_test())
