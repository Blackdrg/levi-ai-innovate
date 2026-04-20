import serial
import redis
import struct
import time
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("serial_bridge")

def run_bridge():
    r = redis.Redis()
    logger.info("Starting serial bridge on socket://localhost:4444...")
    try:
        ser = serial.Serial('socket://localhost:4444', timeout=1)
    except Exception as e:
        logger.error(f"Failed to connect to QEMU serial port: {e}")
        # Not exiting so it can retry or just serve as a stub.
        # In a real daemon, we might want to retry loop here.
        while True:
            try:
                ser = serial.Serial('socket://localhost:4444', timeout=1)
                break
            except Exception:
                time.sleep(2)
    
    MAGIC = b'SYSC'
    while True:
        try:
            data = ser.read(32)
            if len(data) == 32 and data[:4] == MAGIC:
                ts, syscall_id, arg1, arg2 = struct.unpack('<QIQQ', data[4:])
                payload = json.dumps({
                    'ts': ts, 'syscall': hex(syscall_id),
                    'arg1': arg1, 'arg2': arg2
                })
                r.publish('kernel:telemetry', payload)
        except Exception as e:
            logger.error(f"Error reading serial: {e}")
            time.sleep(1)

if __name__ == '__main__':
    run_bridge()
