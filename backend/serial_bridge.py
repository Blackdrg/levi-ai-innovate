import serial
import redis
import struct
import time
import json
import logging
import os
from typing import Optional

# Configuration
SERIAL_PORT = os.getenv("SERIAL_PORT", "socket://localhost:4444")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_NAME = "kernel:telemetry"
IS_SOCKET = SERIAL_PORT.startswith("socket://")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("serial_bridge")

def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT-FALSE implementation."""
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc

class KHTPParser:
    """
    Kernel Host Telemetry Protocol (KHTP) Parser.
    Frame: 32-byte fixed length.
    [0-4]: Magic 'KHTP'
    [4-12]: Timestamp (u64, little-endian)
    [12-16]: Event ID (u32, little-endian)
    [16-24]: Arg 1 (u64, little-endian)
    [24-28]: Arg 2 (u32, little-endian)
    [28-30]: Reserved (2 bytes)
    [30-32]: CRC16 (2 bytes, little-endian)
    """
    MAGIC = b'KHTP'
    FRAME_SIZE = 32

    def __init__(self, redis_client: redis.Redis):
        self.r = redis_client

    def parse_and_store(self, data: bytes):
        if len(data) != self.FRAME_SIZE:
            return False

        if data[:4] != self.MAGIC:
            return False

        # Validate CRC16 (everything except the last 2 bytes)
        claimed_crc = struct.unpack('<H', data[30:32])[0]
        actual_crc = crc16_ccitt(data[:30])
        
        if claimed_crc != actual_crc:
            logger.warning(f"CRC Mismatch: Expected {hex(actual_crc)}, got {hex(claimed_crc)}")
            return False

        # Unpack payload
        ts, event_id, arg1, arg2, reserved = struct.unpack('<QIQQH', data[4:30])
        # Wait, Q=8, I=4, Q=8, Q=8, H=2. 8+4+8+8+2 = 30. Correct.
        # Wait, the comment said Arg2 is u32 (I), but unpack used Q (u64).
        # Let's adjust to match the 32-byte total.
        # 4 (Magic) + 8 (ts) + 4 (id) + 8 (arg1) + 4 (arg2) + 2 (res) + 2 (crc) = 32.
        # Let's re-unpack:
        ts, event_id, arg1, arg2, reserved = struct.unpack('<QIQLH', data[4:30]) 
        # Q(8) + I(4) + Q(8) + L(4) + H(2) = 26 bytes. 
        # 4 (magic) + 26 (payload) + 2 (crc) = 32. Perfect.

        payload = {
            "ts": ts,
            "event_id": hex(event_id),
            "arg1": arg1,
            "arg2": arg2,
            "origin": "HAL-0",
            "ingested_at": time.time()
        }

        # XADD to Redis Stream
        try:
            self.r.xadd(STREAM_NAME, {"data": json.dumps(payload)}, maxlen=10000, approximate=True)
            logger.debug(f"Telemetry Ingested: {payload['event_id']}")
            return True
        except Exception as e:
            logger.error(f"Redis XADD failed: {e}")
            return False

def run_bridge():
    logger.info(f"🚀 KHTP Serial Bridge starting on {SERIAL_PORT}")
    
    r = redis.from_url(REDIS_URL, decode_responses=True)
    parser = KHTPParser(r)
    
    ser = None
    while True:
        try:
            if ser is None:
                ser = serial.serial_for_url(SERIAL_PORT, timeout=1)
                logger.info("Connected to serial port.")

            # Search for magic
            magic = ser.read(4)
            if not magic:
                continue
            
            if magic == KHTPParser.MAGIC:
                # Read the remaining 28 bytes
                remaining = ser.read(28)
                if len(remaining) == 28:
                    parser.parse_and_store(magic + remaining)
            else:
                # Aligning: skip until magic
                pass

        except Exception as e:
            logger.error(f"Bridge loop error: {e}")
            if ser:
                try: ser.close()
                except: pass
                ser = None
            time.sleep(2)

async def handle_client(reader, writer, parser):
    addr = writer.get_extra_info('peername')
    logger.info(f"Accepted connection from {addr}")
    last_heartbeat = time.time()
    
    try:
        while True:
            try:
                # Use wait_for to implement a heartbeat timeout
                magic = await asyncio.wait_for(reader.read(4), timeout=10.0)
                if not magic: break
                last_heartbeat = time.time()
                
                if magic == KHTPParser.MAGIC:
                    remaining = await reader.read(28)
                    if len(remaining) == 28:
                        parser.parse_and_store(magic + remaining)
            except asyncio.TimeoutError:
                logger.critical(f"🚨 [Watchdog] KHTP Heartbeat SILENT for 10s from {addr}. Degraded mode active.")
                # We stay in the loop to wait for recovery
                continue
    except Exception as e:
        logger.error(f"Client connection error {addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def run_socket_bridge():
    # socket://0.0.0.0:4444 -> host='0.0.0.0', port=4444
    url_part = SERIAL_PORT.replace("socket://", "")
    host, port = url_part.split(":")
    
    r = redis.from_url(REDIS_URL, decode_responses=True)
    parser = KHTPParser(r)
    
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, parser), 
        host, int(port)
    )
    
    addr = server.sockets[0].getsockname()
    logger.info(f"🚀 KHTP Socket Bridge serving on {addr}")
    
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    if IS_SOCKET:
        import asyncio
        try:
            asyncio.run(run_socket_bridge())
        except KeyboardInterrupt:
            pass
    else:
        run_bridge()
