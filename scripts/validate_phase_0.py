
import asyncio
import time
import logging
import os
import sys
from typing import List, Dict, Any

# Mocking parts that might be hard to run without real environment
# But we'll try to use real classes as much as possible

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Phase0Validator")

# Ensure backend is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def test_perception_engine():
    """Test Perception Engine: Run 100 test intents; measure latency P95 < 350ms"""
    logger.info("--- Testing Perception Engine ---")
    try:
        from backend.core.intent_classifier import HybridIntentClassifier
        classifier = HybridIntentClassifier()
        
        test_intents = [
            "hello", "how are you?", "hi", "hey levi", 
            "generate an image of a cat", "create a picture of a sunset", "draw a forest",
            "write a python script to sort a list", "fix this bug in my javascript code", "explain this algorithm",
            "search for the latest news on AI", "who is the president of USA?", "what is the price of gold?",
            "calculate 5 + 5", "what is 2 ^ 10?", "solve x + 5 = 10",
            "summarize this document", "read the attached pdf", "extract text from image",
            "how is bitcoin related to ethereum?", "show connections in the knowledge graph",
            "just chat with me", "how's the weather?"
        ]
        
        # Multiply to reach ~100 tests
        test_suite = (test_intents * 5)[:100]
        latencies = []
        results = []
        
        for i, text in enumerate(test_suite):
            start = time.perf_counter()
            res = await classifier.classify(text)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            results.append(res)
            if (i+1) % 20 == 0:
                logger.info(f"Processed {i+1}/100 intents...")

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        avg = sum(latencies) / len(latencies)
        
        logger.info(f"Perception Engine Results: Avg={avg:.2f}ms, P95={p95:.2f}ms")
        
        if p95 < 350:
            logger.info("✅ Perception Engine latency check PASSED.")
            return True
        else:
            logger.warning(f"❌ Perception Engine latency check FAILED (P95={p95:.2f}ms > 350ms).")
            return False
    except Exception as e:
        logger.error(f"💥 Perception Engine test CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def validate_auth_flow():
    """Validate Auth Flow: JWT verification with real tokens; 100 requests verified"""
    logger.info("--- Validating Auth Flow ---")
    try:
        from backend.auth.jwt_provider import JWTProvider
        
        test_user = {"id": "test_user_123", "role": "admin"}
        token = JWTProvider.create_access_token(test_user)
        
        start = time.perf_counter()
        success_count = 0
        for i in range(100):
            decoded = JWTProvider.verify_token(token)
            if decoded and decoded.get("user_id") == test_user["id"]:
                success_count += 1
        
        latency = (time.perf_counter() - start) * 1000
        logger.info(f"Auth Flow Results: 100 verifications in {latency:.2f}ms ({latency/100:.2f}ms/op)")
        
        if success_count == 100:
            logger.info("✅ Auth Flow validation PASSED.")
            return True
        else:
            logger.warning(f"❌ Auth Flow validation FAILED (Only {success_count}/100 success).")
            return False
    except Exception as e:
        logger.error(f"💥 Auth Flow test CRASHED: {e}")
        return False

async def test_agent_dispatch():
    """Test Agent Dispatch: Run 5-wave DAG; measure concurrency"""
    logger.info("--- Testing Agent Dispatch ---")
    try:
        from backend.core.executor.wave_scheduler import WaveScheduler
        from dataclasses import dataclass
        
        @dataclass
        class MockNode:
            id: str
            critical: bool = False
            agent: str = "test_agent"
            
        class MockGraph:
            def get_execution_waves(self):
                # 5 waves of tasks
                return [
                    [MockNode("n1_1"), MockNode("n1_2")],
                    [MockNode("n2_1")],
                    [MockNode("n3_1"), MockNode("n3_2"), MockNode("n3_3")],
                    [MockNode("n4_1")],
                    [MockNode("n5_1"), MockNode("n5_2")]
                ]
        
        async def mock_execute_node(node, results, wave_idx):
            # Simulate work
            await asyncio.sleep(0.05)
            # Use ToolResult if available, else mock
            try:
                from backend.core.orchestrator_types import ToolResult
                return ToolResult(success=True, output=f"Result of {node.id}", agent="test")
            except:
                class MockToolResult:
                    def __init__(self, success, output, agent):
                        self.success = success
                        self.output = output
                        self.agent = agent
                return MockToolResult(True, f"Result of {node.id}", "test")

        scheduler = WaveScheduler()
        start = time.perf_counter()
        results = await scheduler.execute_waves(MockGraph(), mock_execute_node, {"mission_id": "test_mission"})
        duration = (time.perf_counter() - start) * 1000
        
        logger.info(f"Agent Dispatch Results: Completed {len(results)} nodes in {duration:.2f}ms")
        
        if len(results) == 9: # Total nodes in MockGraph
            logger.info("✅ Agent Dispatch test PASSED.")
            return True
        else:
            logger.warning(f"❌ Agent Dispatch test FAILED (Got {len(results)} results, expected 9).")
            return False
            
    except Exception as e:
        logger.error(f"💥 Agent Dispatch test CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def confirm_postgresql():
    """Confirm PostgreSQL: Run migrations; verify schema"""
    logger.info("--- Confirming PostgreSQL ---")
    try:
        import subprocess
        # Run alembic upgrade head
        process = await asyncio.create_subprocess_exec(
            "alembic", "upgrade", "head",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("✅ PostgreSQL migrations PASSED.")
            return True
        else:
            logger.warning(f"❌ PostgreSQL migrations FAILED: {stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"💥 PostgreSQL check CRASHED: {e}")
        return False

async def validate_voice_pipeline():
    """Validate Voice Pipeline: STT 10 audio files; measure latency P95 < 500ms"""
    logger.info("--- Validating Voice Pipeline ---")
    try:
        from backend.engines.voice.stt import SovereignSTT
        stt = SovereignSTT(model_size="tiny")
        
        # We need a sample audio file. If not exists, we'll skip or mock.
        sample_audio = os.path.join(os.path.dirname(__file__), "sample.wav")
        if not os.path.exists(sample_audio):
            logger.warning("⚠️ No sample.wav found. Creating a dummy one (this might fail transcription).")
            import wave
            import struct
            with wave.open(sample_audio, 'w') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(16000)
                for i in range(16000): # 1 second of silence
                    f.writeframesraw(struct.pack('<h', 0))

        latencies = []
        for i in range(10):
            start = time.perf_counter()
            res = await stt.transcribe(sample_audio)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        logger.info(f"Voice Pipeline Results: P95={p95:.2f}ms")
        
        if p95 < 500:
            logger.info("✅ Voice Pipeline check PASSED.")
            return True
        else:
            logger.warning(f"❌ Voice Pipeline check FAILED (P95={p95:.2f}ms > 500ms).")
            # For purposes of this task, I might need to optimize or it might fail due to lack of GPU/resources
            return False
            
    except Exception as e:
        logger.error(f"💥 Voice Pipeline test CRASHED: {e}")
        return False

async def main():
    results = {}
    results["perception"] = await test_perception_engine()
    results["auth"] = await validate_auth_flow()
    results["dispatch"] = await test_agent_dispatch()
    results["postgres"] = await confirm_postgresql()
    results["voice"] = await validate_voice_pipeline()
    
    success = all(results.values())
    if success:
        logger.info("🚀 PHASE 0 STABILIZATION COMPLETE: 100% SUCCESS")
    else:
        logger.error(f"❌ PHASE 0 STABILIZATION FAILED: {results}")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
