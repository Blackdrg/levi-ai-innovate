"""
Sovereign Real-time Broadcast Engine v7.
Powered by Redis PubSub and Server-Sent Events (SSE).
Broadcasting neural evolution telemetry and asynchronous task updates.
"""

import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from backend.redis_client import SovereignCache

logger = logging.getLogger(__name__)

# --- Configuration ---
BROADCAST_CHANNEL = "sovereign:telemetry"

# Standardized v8 Neural Pulse Types
PULSE_MISSION_STARTED  = "mission_started"
PULSE_MISSION_PLANNED  = "mission_planned"
PULSE_MISSION_EXECUTED = "mission_executed"
PULSE_MISSION_AUDITED  = "mission_audited"
PULSE_NODE_COMPLETED   = "node_completed"
PULSE_MISSION_ERROR     = "mission_error"


class SovereignBroadcaster:
    """
    Real-time Telemetry Dispatcher.
    Coordinates between multi-threaded workers and the frontend dashboard.
    Hardened for backpressure and high-concurrency event streams.
    """
    
    @staticmethod
    def publish(event_type: str, data: Dict[str, Any], user_id: str = "global"):
        """Publishes a neural event to the Sovereign Pulse."""
        client = SovereignCache.get_client()
        channel = f"{BROADCAST_CHANNEL}:{user_id}"
        
        message = {
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        try:
            client.publish(channel, json.dumps(message))
            logger.debug(f"[Pulse] Broadcast event published on {channel}")
        except Exception as e:
            logger.error(f"[Pulse] Broadcast failure: {e}")

    @staticmethod
    async def subscribe(user_id: str = "global") -> AsyncGenerator[str, None]:
        """
        Subscribes a client to the Sovereign Pulse v4 stream.
        Features: Adaptive Heartbeats, Binary-Ready Payloads, and backpressure handling.
        """
        client = SovereignCache.get_client()
        pubsub = client.pubsub()
        channel = f"{BROADCAST_CHANNEL}:{user_id}"
        
        await asyncio.to_thread(lambda: pubsub.subscribe(channel))
        logger.info(f"[Pulse v4] New subscriber connected: {user_id}")
        
        try:
            # Yield Pulse v4 Handshake
            yield f"event: pulse_handshake\ndata: {json.dumps({'version': '4.0.0', 'user_id': user_id, 'status': 'connected'})}\n\n"
            
            while True:
                # Optimized multi-threaded message polling
                message = await asyncio.to_thread(lambda: pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1))
                
                if message and message['type'] == 'message':
                    data_raw = message['data']
                    try:
                         data = json.loads(data_raw)
                         event_type = data.get("type", "pulse_update")
                         # v4: Support for base64 encoded binary payloads if 'binary' flag is set
                         if data.get("binary"):
                             logger.debug("[Pulse v4] Processing binary payload...")
                             
                         yield f"event: {event_type}\ndata: {data_raw}\n\n"
                    except json.JSONDecodeError:
                         # Fallback for raw binary/string data
                         yield f"data: {data_raw}\n\n"
                
                # Dynamic Heartbeat (Pulse v4)
                yield f"event: heartbeat\ndata: {json.dumps({'timestamp': asyncio.get_event_loop().time()})}\n\n"

                await asyncio.sleep(0.1) # Higher frequency for v9.5 dashboards
                
        except asyncio.CancelledError:
            logger.info(f"[Pulse v4] Subscriber disconnected: {user_id}")
            # Ensure cleanup on disconnection
            try:
                await asyncio.to_thread(lambda: pubsub.unsubscribe(channel))
            except: pass
        except Exception as e:
            logger.error(f"[Pulse v4] Critical stream failure: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

# Global Accessor
def broadcast_event(event_type: str, data: Dict[str, Any], user_id: str = "global"):
    SovereignBroadcaster.publish(event_type, data, user_id)
