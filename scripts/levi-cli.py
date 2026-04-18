import argparse
import sys
import json
import requests
import os

# LEVI-AI Sovereign CLI v1.0
# The official developer tool for hardware-governed cognitive orchestration.

BASE_URL = os.getenv("LEVI_API_URL", "http://localhost:8000/api/v1")

def main():
    parser = argparse.ArgumentParser(description="LEVI-AI Sovereign CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sovereign commands")

    # 1. System Pulse
    subparsers.add_parser("pulse", help="Get global hardware heartbeat")

    # 2. Mission Dispatch
    mission_parser = subparsers.add_parser("mission", help="Dispatch a cognitive mission wave")
    mission_parser.add_argument("objective", type=str, help="Mission objective title")
    mission_parser.add_argument("--priority", type=float, default=1.0, help="Mission priority (0-1)")

    # 3. Kernel Status
    subparsers.add_parser("kernel", help="Inspect HAL-0 kernel drivers and resource gauges")

    # 4. Forensic Audit
    audit_parser = subparsers.add_parser("audit", help="Verify the integrity of a mission pulse")
    audit_parser.add_argument("mission_id", type=str, help="ID of the mission to verify")

    args = parser.parse_args()

    if args.command == "pulse":
        get_pulse()
    elif args.command == "mission":
        dispatch_mission(args.objective, args.priority)
    elif args.command == "kernel":
        get_kernel_status()
    elif args.command == "audit":
        verify_audit(args.mission_id)
    else:
        parser.print_help()

def get_pulse():
    try:
        r = requests.get(f"{BASE_URL}/system/pulse")
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

def dispatch_mission(objective, priority):
    try:
        payload = {"objective": objective, "priority": priority}
        r = requests.post(f"{BASE_URL}/orchestrator/dispatch", json=payload)
        print(f"🚀 Mission Dispatched. ID: {r.json().get('mission_id')}")
    except Exception as e:
        print(f"Error: {e}")

def get_kernel_status():
    try:
        r = requests.get(f"{BASE_URL}/system/backpressure")
        print(f"🧠 HAL-0 Status: {r.json().get('status')}")
        print(f"🔋 VRAM Usage: {r.json().get('vram_usage_pct')}%")
    except Exception as e:
        print(f"Error: {e}")

def verify_audit(mission_id):
    try:
        r = requests.get(f"{BASE_URL}/shield/audit/{mission_id}")
        if r.json().get("verified"):
            print(f"✅ Mission {mission_id}: BFT SIGNATURE VERIFIED. TRUTH CONFIRMED.")
        else:
            print(f"❌ Mission {mission_id}: INTEGRITY BREACH DETECTED. DO NOT TRUST.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
