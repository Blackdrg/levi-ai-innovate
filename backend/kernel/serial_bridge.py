# backend/kernel/serial_bridge.py
import serial
import redis
import struct
import json
import time
import logging
import asyncio
import os

from backend.utils.circuit_breaker import bridge_breaker
import structlog
logger = structlog.get_logger("SerialBridge")

class SerialTelemetryBridge:
    """
    Sovereign v22.1: Kernel-to-Host Telemetry Bridge.
    Stabilization Plan Fix: Implements the 32-byte SYSC binary packet format.
    """
    MAGIC = b'SYSC'
    
    def __init__(self):
        self.port = os.getenv("SERIAL_PORT", "socket://localhost:4444")
        self.baud = int(os.getenv("SERIAL_BAUD", "115200"))
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0
        )
        self._running = False
        self._task = None

    async def start(self):
        if self._running: return
        self._running = True
        self._task = asyncio.create_task(self._bridge_loop())
        self._watchdog = asyncio.create_task(self._watchdog_loop())
        logger.info(f"🛰️ [SerialBridge] Listening on {self.port}...")

    async def _watchdog_loop(self):
        """Monitors last_pulse and switch to fallback if kernel is silent > 10s."""
        while self._running:
            try:
                last_pulse = self.redis_client.get("system:last_pulse")
                if last_pulse:
                    data = json.loads(last_pulse)
                    last_ts = data.get("arrival_ts", 0)
                    if time.time() - last_ts > 10:
                        logger.warning("🚨 [Watchdog] Kernel SILENT for > 10s. Degrading telemetry...")
                        self.redis_client.set("system:telemetry_status", "degraded")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"[Watchdog] Error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
        logger.info("🛑 [SerialBridge] Stopped.")

    async def _bridge_loop(self):
        """
        Binary Packet Format (32 bytes):
        [4] MAGIC ('SYSC')
        [8] Timestamp (u64)
        [4] Syscall ID (u32)
        [8] Arg 1 (u64)
        [8] Arg 2 (u64)
        """
        try:
            # Using loop.run_in_executor for blocking serial reads
            loop = asyncio.get_event_loop()
            ser = await loop.run_in_executor(None, lambda: serial.serial_for_url(self.port, timeout=1))
            
            async def _read_serial():
                return await loop.run_in_executor(None, lambda: ser.read(32))
            
            while self._running:
                try:
                    data = await bridge_breaker.call(_read_serial)
                except Exception as e:
                    logger.warning(f"Serial read suppressed by circuit breaker: {e}")
                    await asyncio.sleep(1)
                    continue
                
                if not data: continue
                
                if len(data) == 32 and data[:4] == self.MAGIC:
                    try:
                        ts, syscall_id, arg1, arg2 = struct.unpack('<QIQQ', data[4:])
                        payload = {
                            'type': 'kernel_telemetry',
                            'timestamp': ts,
                            'arrival_ts': time.time(),
                            'syscall': hex(syscall_id),
                            'arg1': arg1,
                            'arg2': arg2,
                            'origin': 'HAL-0'
                        }
                        # Publish to internal telemetry stream
                        self.redis_client.publish('system:telemetry', json.dumps(payload))
                        self.redis_client.set("system:last_pulse", json.dumps(payload))
                        logger.debug(f" [SYSC] {hex(syscall_id)} ({arg1}, {arg2})")
                    except Exception as e:
                        logger.error(f"Failed to unpack telemetry: {e}")
                else:
                    # Alignment search
                    if self.MAGIC in data:
                        idx = data.index(self.MAGIC)
                        # Re-align next read
                        await loop.run_in_executor(None, lambda: ser.read(idx))

        except Exception as e:
            logger.error(f"Serial Bridge fatal error: {e}")
            self._running = False

kernel_bridge = SerialTelemetryBridge()
