"""
Sovereign Real-time Broadcast Engine v8.
Powered by Redis PubSub and Server-Sent Events (SSE).
Refactored for Tiered Sovereign Architecture.
"""

import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from backend.db.redis import get_redis_client

logger = logging.getLogger(__name__)

# --- Configuration ---
BROADCAST_CHANNEL = "sovereign:telemetry"

class SovereignBroadcaster:
    """
    Real-time Telemetry Dispatcher.
    Coordinates between autonomous waves and the frontend dashboard.
    """
    
    @staticmethod
    def publish(event_type: str, data: Dict[str, Any], user_id: str = "global"):
        """Publishes a neural pulse to the Sovereign Stream."""
        client = get_redis_client()
        if not client: return

        channel = f"{BROADCAST_CHANNEL}:{user_id}"
        message = {
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        try:
            client.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"[Broadcaster] Pulse failure: {e}")

    @staticmethod
    async def subscribe(user_id: str = "global") -> AsyncGenerator[str, None]:
        """Subscribes an SSE client to the specific user's telemetry pulse."""
        client = get_redis_client()
        if not client:
            yield "event: error\ndata: {\"error\": \"Redis Pulse Offline\"}\n\n"
            return

        pubsub = client.pubsub()
        channel = f"{BROADCAST_CHANNEL}:{user_id}"
        
        await asyncio.to_thread(pubsub.subscribe, channel)
        logger.info(f"[Broadcaster] New subscriber linked to {channel}")
        
        try:
            yield f"event: pulse_connected\ndata: {json.dumps({'status': 'online'})}\n\n"
            
            while True:
                message = await asyncio.to_thread(pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    yield f"event: pulse_update\ndata: {message['data']}\n\n"
                
                # Keep-alive
                yield ": heartbeat\n\n"
                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            await asyncio.to_thread(pubsub.unsubscribe, channel)
        except Exception as e:
            logger.error(f"[Broadcaster] Stream anomaly: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

def broadcast_event(event_type: str, data: Dict[str, Any], user_id: str = "global"):
    """Global accessor for background tasks."""
    SovereignBroadcaster.publish(event_type, data, user_id)
