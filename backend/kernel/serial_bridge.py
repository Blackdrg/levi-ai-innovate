import struct
import json
import asyncio
import logging
import os
from datetime import datetime, timezone
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger("serial-bridge")

# Magic number identifying the Sovereign Kernel Serial Protocol
LEVI_MAGIC = 0x4C455649 # "LEVI"

# Record Type Mapping
RECORD_TYPES = {
    0x01: "MEM_RESERVE",
    0x02: "WAVE_SPAWN",
    0x03: "BFT_SIGN",
    0x04: "PROC_KILL",
    0x05: "FS_WRITE",
    0x06: "FS_READ",
    0x07: "NET_PING",
    0x08: "DCN_PULSE",
    0x09: "SYS_WRITE",
    0xFE: "MISSION_OUTCOME",
    0xFF: "HEARTBEAT",
}

class SerialBridge:
    """
    Bridges the gap between the Bare-Metal HAL-0 Kernel and the Cognitive Soul (Python).
    Reads binary records from the serial port and broadcasts them via the Sovereign Event Bus.
    """
    def __init__(self):
        # Default to a local socket for QEMU testing, or a serial device
        self.port = os.getenv("KERNEL_SERIAL_PORT", "localhost:1234")
        self.is_running = False
        self._task = None

    async def start(self):
        if self._task:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("🛰️ [KernelBridge] Serial-to-WebSocket bridge activated.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self):
        while self.is_running:
            try:
                if ":" in self.port:
                    # QEMU -server -serial tcp:localhost:1234
                    host, port = self.port.split(":")
                    logger.info(f"🛰️ [KernelBridge] Connecting to QEMU serial socket at {host}:{port}...")
                    reader, writer = await asyncio.open_connection(host, int(port))
                    await self._read_loop(reader)
                else:
                    # Real Serial Device
                    await self._read_loop_serial()
            except Exception as e:
                logger.error(f"❌ [KernelBridge] Connection failed: {e}. Retrying in 5s...")
                await asyncio.sleep(5)

    async def _read_loop(self, reader):
        # Record format: [magic: u32][seq: u64][pid: u32][syscall_id: u8][ts: u32][fidelity: u8] = 22 bytes
        record_size = 22
        while self.is_running:
            try:
                data = await reader.readexactly(record_size)
                self._process_record(data)
            except asyncio.IncompleteReadError:
                logger.warning("⚠️ [KernelBridge] Serial stream interrupted.")
                break
            except Exception as e:
                logger.error(f"❌ [KernelBridge] Read error: {e}")
                break

    async def _read_loop_serial(self):
        try:
            import serial
            ser = serial.Serial(self.port, 115200, timeout=0.1)
            logger.info(f"🛰️ [KernelBridge] Opened serial port {self.port}")
            while self.is_running:
                if ser.in_waiting >= 22:
                    data = ser.read(22)
                    self._process_record(data)
                await asyncio.sleep(0.01)
        except ImportError:
            logger.error("❌ [KernelBridge] 'pyserial' not installed. Cannot use real serial port.")
            self.is_running = False
        except Exception as e:
            logger.error(f"❌ [KernelBridge] Serial error: {e}")
            await asyncio.sleep(5)

    def _process_record(self, data):
        try:
            # Struct: < (little endian), I (u32), Q (u64), I (u32), B (u8), I (u32), B (u8)
            magic, seq, pid, rtype, ts, fidelity = struct.unpack("<I Q I B I B", data)
            if magic != LEVI_MAGIC:
                return

            event_name = RECORD_TYPES.get(rtype, f"UNKNOWN_0x{rtype:02X}")
            
            # 1. Broadcaster (for Frontend WebSocket)
            SovereignBroadcaster.publish(
                "kernel_event",
                {
                    "type": "kernel_event",
                    "payload": {
                        "seq": seq,
                        "pid": pid,
                        "event": event_name,
                        "id": rtype,
                        "timestamp": ts,
                        "fidelity": fidelity,
                        "status": "EXECUTED"
                    }
                },
                user_id="system:pulse"
            )

            # 2. Logic hooks (MCM graduation)
            if rtype == 0xFE: # MISSION_OUTCOME (Fidelity Pulse)
                self._handle_mission_outcome(seq, pid, ts, fidelity)
                
            logger.debug(f"🔵 [KernelBridge] Recv: {event_name} (seq={seq}, pid={pid}, fidelity={fidelity})")
                
        except Exception as e:
            logger.error(f"❌ [KernelBridge] Parse error: {e}")

    def _handle_mission_outcome(self, seq, pid, ts, fidelity):
        """Triggers the MCM graduation logic based on kernel mission outcome."""
        try:
            from backend.services.mcm import mcm_service
            # Use real fidelity score from kernel (normalized to 0.0 - 1.0)
            f_score = fidelity / 255.0
            
            if hasattr(mcm_service, "graduate"):
                asyncio.create_task(mcm_service.graduate({
                    "source": "kernel",
                    "seq": seq,
                    "timestamp": ts,
                    "fidelity": f_score
                }))
        except Exception as e:
            logger.error(f"❌ [KernelBridge] MCM Hook failed: {e}")


# Global Instance
kernel_bridge = SerialBridge()
