# scripts/kernel_bridge.py
import serial
import struct
import json
import time
import os
import redis
from typing import Dict, Any

# TelemetryRecord (32 bytes) - SYSC Format
#   magic: u32 (4)
#   seq_id: u64 (8)
#   pid: u32 (4)
#   syscall_id: u32 (4)
#   timestamp: u32 (4)
#   fidelity: u8 (1)
#   reserved: [u8; 7] (7)
RECORD_FORMAT = "<I Q I I I B 7s"
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)
LEVI_MAGIC = 0x4C455649

class KernelBridge:
    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.channel = "sovereign:telemetry:system:pulse"

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            print(f"[*] Connected to Kernel on {self.port} at {self.baud} baud.")
        except Exception as e:
            print(f"[!] Failed to open serial port {self.port}: {e}")
            print("[*] Continuing in MOCK mode...")

    def run(self):
        print("[*] Kernel Bridge active. Streaming to Redis channel: " + self.channel)
        while True:
            if self.ser and self.ser.in_waiting >= RECORD_SIZE:
                data = self.ser.read(RECORD_SIZE)
                self.process_packet(data)
            elif not self.ser:
                # Mock high-frequency telemetry for UI validation
                self.generate_mock_event()
                time.sleep(0.05) # 20 events per second
            else:
                time.sleep(0.01)

    def process_packet(self, data: bytes):
        try:
            magic, seq_id, pid, syscall_id, ts, fidelity, _ = struct.unpack(RECORD_FORMAT, data)
            if magic == LEVI_MAGIC:
                payload = {
                    "type": "kernel_event",
                    "data": {
                        "seq_id": seq_id,
                        "pid": pid,
                        "syscall_id": f"0x{syscall_id:02X}",
                        "timestamp": ts,
                        "fidelity": fidelity / 255.0,
                        "origin": "HAL-0"
                    }
                }
                self.broadcast(payload)
        except Exception as e:
            print(f"[!] Packet processing error: {e}")

    def generate_mock_event(self):
        import random
        syscalls = [1, 2, 3, 5, 6, 8, 0xFE, 0x99]
        sc = random.choice(syscalls)
        payload = {
            "type": "kernel_event",
            "data": {
                "seq_id": int(time.time() * 1000),
                "pid": random.randint(1, 16),
                "syscall_id": f"0x{sc:02X}",
                "timestamp": int(time.time()),
                "fidelity": random.uniform(0.85, 1.0),
                "origin": "HAL-0-MOCK"
            }
        }
        self.broadcast(payload)

    def broadcast(self, payload: Dict[str, Any]):
        try:
            # We wrap it in the format expected by SovereignBroadcaster.subscribe
            # event: kernel_event\ndata: {...}\n\n
            message = {
                "type": "kernel_event",
                "data": payload["data"],
                "timestamp": time.time()
            }
            self.redis_client.publish(self.channel, json.dumps(message))
            if payload["data"]["syscall_id"] == "0xFE":
                print(f"[🎓] GRADUATION PULSE: {payload['data']['fidelity']:.2f}")
            else:
                print(f"[>] SYSC {payload['data']['syscall_id']} | PID {payload['data']['pid']} | FID {payload['data']['fidelity']:.2f}")
        except Exception as e:
            print(f"[!] Redis broadcast failed: {e}")

if __name__ == "__main__":
    port = os.getenv("KERNEL_SERIAL_PORT", "COM3")
    bridge = KernelBridge(port)
    bridge.connect()
    bridge.run()
