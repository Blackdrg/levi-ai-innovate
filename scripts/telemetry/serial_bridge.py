import serial
import redis
import json
import time
import os
from parse_binary import parse_syscall_packet, MAGIC

# Configuration
SERIAL_PATH = os.getenv("LEVI_SERIAL_PATH", "socket://localhost:4444")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_CHANNEL = "kernel:telemetry"

def run_bridge():
    print(f"[*] Starting LEVI-AI Serial Bridge (Reality Hardening Phase 1)")
    print(f"[*] Connecting to Serial: {SERIAL_PATH}")
    print(f"[*] Connecting to Redis: {REDIS_HOST}:{REDIS_PORT}")

    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        # Test connection
        r.ping()
    except Exception as e:
        print(f"[!] Redis Connection Error: {e}")
        return

    try:
        # Connect to QEMU serial socket
        ser = serial.Serial(SERIAL_PATH, timeout=None)
    except Exception as e:
        print(f"[!] Serial Connection Error: {e}")
        return

    print(f"[*] Bridge Operational. Awaiting packets...")

    buffer = b""
    while True:
        try:
            # Read in chunks
            new_data = ser.read(1)
            if not new_data:
                continue
            
            buffer += new_data
            
            # Look for Magic
            magic_idx = buffer.find(struct.pack("<I", MAGIC))
            if magic_idx != -1:
                # Trim buffer to start of packet
                buffer = buffer[magic_idx:]
                
                if len(buffer) >= 32:
                    packet_data = buffer[:32]
                    buffer = buffer[32:]
                    
                    try:
                        parsed = parse_syscall_packet(packet_data)
                        print(f"[TELEMETRY] Syscall: {hex(parsed['syscall_id'])} Args: {parsed['args']}")
                        
                        # Publish to Redis
                        r.publish(REDIS_CHANNEL, json.dumps(parsed))
                    except Exception as e:
                        print(f"[!] Packet Parse Error: {e}")
            
            # Prevent buffer bloat if no magic found
            if len(buffer) > 1024:
                buffer = buffer[-32:]

        except KeyboardInterrupt:
            print("\n[*] Shutting down bridge.")
            break
        except Exception as e:
            print(f"[!] Runtime Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    import struct # Required for magic search
    run_bridge()
