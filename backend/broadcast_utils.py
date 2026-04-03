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
        """Subscribes a client to the Sovereign Pulse stream."""
        client = SovereignCache.get_client()
        pubsub = client.pubsub()
        channel = f"{BROADCAST_CHANNEL}:{user_id}"
        
        await asyncio.to_thread(lambda: pubsub.subscribe(channel))
        logger.info(f"[Pulse] New subscriber connected to {channel}")
        
        try:
            # Yield initial connection event
            yield f"event: pulse_connected\ndata: {json.dumps({'status': 'listening', 'user_id': user_id})}\n\n"

            
            while True:
                # We use a non-blocking check for messages in a thread
                message = await asyncio.to_thread(lambda: pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0))
                
                if message and message['type'] == 'message':
                    data_raw = message['data']
                    data = json.loads(data_raw)
                    event_type = data.get("type", "pulse_update")
                    # Forward as a structured SSE event
                    yield f"event: {event_type}\ndata: {data_raw}\n\n"
                
                # Keep-alive heartbeat
                yield ": heartbeat\n\n"

                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            logger.info(f"[Pulse] Subscriber disconnected from {channel}")
            await asyncio.to_thread(lambda: pubsub.unsubscribe(channel))
        except Exception as e:
            logger.error(f"[Pulse] Subscription failure: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"

# Global Accessor
def broadcast_event(event_type: str, data: Dict[str, Any], user_id: str = "global"):
    SovereignBroadcaster.publish(event_type, data, user_id)
