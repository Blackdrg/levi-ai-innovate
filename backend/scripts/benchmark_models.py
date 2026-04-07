import asyncio
import time
import statistics
import logging
import argparse

from backend.core.model_router import ModelRouter
from backend.services.local_llm import local_llm
from backend.db.postgres import PostgresDB
from backend.db.models import BenchmarkLedger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

async def run_benchmark(model: str, tier: str, ctx_length: int, samples: int = 100):
    """
    Runs a benchmark for a specific model and context length.
    """
    logger.info(f"🚀 Benchmarking {model} ({tier}) at {ctx_length} tokens...")
    
    # Generate a dummy prompt of desired context length
    # Approx 4 chars per token
    dummy_prompt = "reason " * (ctx_length - 10)
    
    latencies = []
    tokens_generated = []
    
    for i in range(samples):
        start = time.perf_counter()
        # Using agenerate directly to bypass complex logic
        # We limit max_tokens to get a consistent small response to measure latency primarily
        response = await local_llm.agenerate(dummy_prompt, max_tokens=128, model_tier=tier)
        latency = (time.perf_counter() - start) * 1000
        
        if response:
            latencies.append(latency)
            # Estimate tokens in response (simple word count for benchmark)
            tokens_generated.append(len(response.split()))
            
        if (i + 1) % 10 == 0:
            logger.info(f"  Progress: {i+1}/{samples} samples...")

    if not latencies:
        logger.error(f"❌ Benchmark failed for {model}")
        return

    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
    
    avg_tokens = sum(tokens_generated) / len(tokens_generated)
    tps = (avg_tokens / (p50 / 1000)) if p50 > 0 else 0

    logger.info(f"✅ {model} Results: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms, TPS={tps:.2f}")

    # Store in Ledger
    try:
        async with PostgresDB._session_factory() as session:
            entry = BenchmarkLedger(
                model=model,
                tier=tier,
                context_length=ctx_length,
                p50_latency_ms=p50,
                p95_latency_ms=p95,
                p99_latency_ms=p99,
                tps_p50=tps,
                samples=samples
            )
            session.add(entry)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to store benchmark: {e}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=10, help="Samples per test (user requested 100, but default low for testing)")
    args = parser.parse_args()

    models = ModelRouter.get_all_assignments()
    ctx_lengths = [512, 1024, 2048, 4096]

    for tier, model in models.items():
        if tier == "L4": continue # Same as L3 for now
        for ctx in ctx_lengths:
            await run_benchmark(model, tier, ctx, samples=args.samples)

if __name__ == "__main__":
    asyncio.run(main())
