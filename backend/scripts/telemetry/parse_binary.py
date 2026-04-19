import struct
import time
from typing import Dict, Any

# Magic: 0x53595343 (SYSC)
MAGIC = 0x53595343

def parse_syscall_packet(data: bytes) -> Dict[str, Any]:
    """
    Parses a 32-byte binary telemetry packet from HAL-0.
    Format:
    [4B Magic] [8B Timestamp] [4B Syscall ID] [8B Arg1] [8B Arg2]
    """
    if len(data) != 32:
        raise ValueError(f"Invalid packet size: {len(data)} bytes (expected 32)")

    magic, timestamp, syscall_id, arg1, arg2 = struct.unpack("<I Q I Q Q", data)

    if magic != MAGIC:
        raise ValueError(f"Invalid magic: 0x{magic:08X}")

    return {
        "magic": hex(magic),
        "timestamp": timestamp,
        "syscall_id": syscall_id,
        "args": [arg1, arg2],
        "readable_time": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp / 1000.0))
    }

if __name__ == "__main__":
    # Test packet
    test_packet = struct.pack("<I Q I Q Q", MAGIC, int(time.time() * 1000), 0x05, 1024, 2048)
    try:
        parsed = parse_syscall_packet(test_packet)
        print(f"Parsed Syscall: {parsed}")
    except Exception as e:
        print(f"Parse Error: {e}")
