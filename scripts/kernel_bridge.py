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
        print("[*] Kernel Bridge active (Sliding Window Sync). Streaming to: " + self.channel)
        buffer = b""
        while True:
            if self.ser:
                if self.ser.in_waiting > 0:
                    buffer += self.ser.read(self.ser.in_waiting)
                    
                    while len(buffer) >= RECORD_SIZE:
                        # Search for LEVI_MAGIC (0x4C455649 -> b'IVE L' in little-endian)
                        # Actually, LEVI_MAGIC is 0x4C455649. struct.pack("<I", 0x4C455649) is b'IVE L'
                        # Wait, 0x49 is I, 0x56 is V, 0x45 is E, 0x4C is L.
                        # So b'IVEL'? No, b'I V E L'. Let's check:
                        magic_bytes = struct.pack("<I", LEVI_MAGIC)
                        
                        idx = buffer.find(magic_bytes)
                        if idx == -1:
                            # Not found, keep the last RECORD_SIZE - 1 bytes in case magic is split
                            if len(buffer) > RECORD_SIZE:
                                buffer = buffer[-(RECORD_SIZE - 1):]
                            break
                        elif idx > 0:
                            # Discard bytes before magic
                            print(f"[!] Discarding {idx} bytes of noise.")
                            buffer = buffer[idx:]
                            continue
                        
                        # We have magic at the start
                        if len(buffer) < RECORD_SIZE:
                            break
                            
                        chunk = buffer[:RECORD_SIZE]
                        self.process_packet(chunk)
                        buffer = buffer[RECORD_SIZE:]
                else:
                    time.sleep(0.01)
            else:
                # Mock high-frequency telemetry
                self.generate_mock_event()
                time.sleep(0.05)

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
            sc = payload["data"]["syscall_id"]
            if sc == "0xFE":
                print(f"[🎓] GRADUATION PULSE: {payload['data']['fidelity']:.2f}")
            elif sc == "0x04":
                print(f"[🌐] NET_SEND: Outbound packet emitted via HAL-0.")
            elif sc == "0x06":
                print(f"[💾] MCM_GRADUATE: Fact CRYSTALLIZED to Tier 3 hardware.")
            elif sc == "0x0C":
                print(f"[📖] MCM_READ: Fact RETRIEVED from Tier 3 hardware.")
            else:
                print(f"[>] SYSC {sc} | PID {payload['data']['pid']} | FID {payload['data']['fidelity']:.2f}")
        except Exception as e:
            print(f"[!] Redis broadcast failed: {e}")

if __name__ == "__main__":
    port = os.getenv("KERNEL_SERIAL_PORT", "COM3")
    bridge = KernelBridge(port)
    bridge.connect()
    bridge.run()
