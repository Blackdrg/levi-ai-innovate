import requests
import time
import random
import psutil
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SoakTest")

API_URL = "http://localhost:8000/api/v1/missions/spawn"
HEALTH_URL = "http://localhost:8000/readyz"
METRICS_URL = "http://localhost:8000/metrics"

MISSION_INPUTS = [
    "Analyze the current market trends in AI agents.",
    "Draft a research paper on sovereign OS architecture.",
    "Refine the cognitive planning logic for multi-agent swarms.",
    "Perform a thermal audit of the system.",
    "Calculate the graduation score for the past 24 hours.",
    "Search for cross-node latency anomalies.",
    "What is the status of the DCN consensus?",
    "Wipe all temporary mission data.",
    "Generate a forensic trail for the last interaction.",
    "Optimize VRAM allocation for neural inference."
]

def run_mission():
    payload = {
        "user_id": "soak_tester",
        "user_input": random.choice(MISSION_INPUTS),
        "session_id": "soak_test_session"
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Mission failed: {e}")
        return None

def get_memory_usage():
    """Returns the RSS memory of the current process and its children in MB."""
    process = psutil.Process()
    mem = process.memory_info().rss
    for child in process.children(recursive=True):
        try:
            mem += child.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return mem / (1024 * 1024) 

def check_metrics():
    try:
        resp = requests.get(METRICS_URL, timeout=5)
        return resp.status_code == 200
    except:
        return False

def run_loop(duration_hours=24, mission_limit=500):
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    
    missions_sent = 0
    start_memory = get_memory_usage()
    
    logger.info(f"🚀 Starting {duration_hours}-hour soak test...")
    logger.info(f"Target: {mission_limit} missions. Start memory: {start_memory:.2f} MB")
    
    mem_history = []
    
    while datetime.now() < end_time and missions_sent < mission_limit:
        run_mission()
        missions_sent += 1
        
        current_mem = get_memory_usage()
        mem_history.append(current_mem)
        
        if missions_sent % 10 == 0:
            elapsed = datetime.now() - start_time
            mem_growth = current_mem - start_memory
            growth_rate = mem_growth / (elapsed.total_seconds() / 3600) if elapsed.total_seconds() > 0 else 0
            
            logger.info(f"Progress: {missions_sent}/{mission_limit} missions. "
                        f"Memory: {current_mem:.2f} MB (+{mem_growth:.2f} MB). "
                        f"Growth Rate: {growth_rate:.2f} MB/hr")
            
            # Assertion: memory growth < 100MB/hr
            if growth_rate > 100:
                logger.error(f"❌ LEAK DETECTED: Memory growth rate {growth_rate:.2f} MB/hr exceeds 100MB/hr!")
            
            # Check for deadlocks / OOM (via health endpoint)
            try:
                h_resp = requests.get(HEALTH_URL, timeout=5)
                if h_resp.status_code != 200:
                    logger.critical(f"❌ SYSTEM UNHEALTHY: {h_resp.status_code}")
            except Exception as e:
                logger.critical(f"❌ SYSTEM UNRESPONSIVE: {e}")
        
        time.sleep(random.uniform(5, 15)) # Realistic traffic gap

    final_mem = get_memory_usage()
    logger.info(f"🏁 Soak test complete. Total missions: {missions_sent}. "
                f"Peak memory: {max(mem_history):.2f} MB. "
                f"Final growth: {final_mem - start_memory:.2f} MB.")

if __name__ == "__main__":
    import sys
    duration = 24
    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    run_loop(duration_hours=duration)
