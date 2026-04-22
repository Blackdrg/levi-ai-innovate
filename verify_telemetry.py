import time
import os
import json
import redis
import threading
import asyncio
from backend.kernel.kernel_wrapper import kernel
from backend.serial_bridge import run_socket_bridge, KHTPParser

# Configuration for test
TEST_PORT = "localhost:5555"
os.environ["SERIAL_PORT"] = f"socket://{TEST_PORT}"
os.environ["REDIS_URL"] = "redis://localhost:6379/1" # Use celery DB for test isolation

def start_bridge():
    """Run the bridge server in a thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_socket_bridge())

def verify_end_to_end():
    print("🚀 Starting E2E Telemetry Path Verification...")
    
    # 1. Start Bridge
    bridge_thread = threading.Thread(target=start_bridge, daemon=True)
    bridge_thread.start()
    time.sleep(1) # Wait for bridge to bind
    
    # 2. Setup Redis connection to check stream
    r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    r.delete("kernel:telemetry") # Clear old data
    
    # 3. Emit Record
    event_id = 0xDEAF
    arg1 = 0x1234567890ABCDEF
    arg2 = 0xFEEDFACE
    
    print(f"📡 [Kernel] Emitting record: ID={hex(event_id)}")
    start_time = time.perf_counter()
    
    # If the Rust kernel is not loaded, _call will do nothing.
    # We should ensure the test can run even in fallback if we mock it,
    # but the task is to verify the path.
    # In a real environment, we'd have the .pyd/.so.
    kernel.write_record(event_id, arg1, arg2)
    
    # 4. Poll Redis for completion
    print("⏳ [Test] Polling Redis stream 'kernel:telemetry'...")
    found = False
    for _ in range(20):
        messages = r.xrange("kernel:telemetry", count=5)
        if messages:
            for mid, data in messages:
                payload = json.loads(data["payload"])
                if payload["event_id"] == event_id:
                    latency = (time.perf_counter() - start_time) * 1000
                    print(f"✅ [Test] MATCH FOUND in Redis!")
                    print(f"📊 [Test] E2E Latency: {latency:.2f}ms")
                    print(f"📦 [Test] Data: {payload}")
                    found = True
                    break
        if found: break
        time.sleep(0.5)
        
    if not found:
        print("❌ [Test] Telemetry delivery FAILED or TIMED OUT.")
        print("Note: This test requires a compiled 'levi_kernel' or a functional mock.")

if __name__ == "__main__":
    try:
        verify_end_to_end()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"💥 [Test] Crash: {e}")
