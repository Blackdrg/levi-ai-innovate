"""
Sovereign Real-time Broadcast Engine v7.
Powered by Redis PubSub and Server-Sent Events (SSE).
Broadcasting neural evolution telemetry and asynchronous task updates.
"""

import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any
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

# v9.8.1: Swarm & Security Pulsar Types
PULSE_SWARM_CONSENSUS  = "swarm_consensus"
PULSE_SECURITY_SHIELD   = "security_shield" 
PULSE_FIDELITY_UPDATE   = "fidelity_update" # Live Swarm Confidence
PULSE_DREAM_PULSE       = "dream_pulse"     


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
    def broadcast(payload: Dict[str, Any], user_id: str = "global"):
        """
        Backward-compatible broadcast for dictionary payloads (v13.0.0).
        Extracts 'type' from payload and maps it to the publish protocol.
        """
        event_type = payload.get("type", "pulse_update")
        # Clean up data by removing internal 'type' field if present
        data = {k: v for k, v in payload.items() if k != "type"}
        SovereignBroadcaster.publish(event_type, data, user_id)

    @staticmethod
    async def subscribe(user_id: str = "global", profile: str = "desktop") -> AsyncGenerator[str, None]:
        """
        Sovereign Pulse v4.1: Adaptive Telemetry Stream.
        Features: Profile-based filtering and zlib compression for mobile resilience.
        """
        import zlib
        import base64
        
        client = SovereignCache.get_client()
        pubsub = client.pubsub()
        channel = f"{BROADCAST_CHANNEL}:{user_id}"
        
        await asyncio.to_thread(lambda: pubsub.subscribe(channel))
        logger.info(f"[Pulse v4.1] Subscriber connected: {user_id} (Profile: {profile})")
        
        try:
            # v4.1 Handshake with compression flag
            handshake = {"version": "4.1.0", "user_id": user_id, "profile": profile}
            yield f"event: pulse_handshake\ndata: {json.dumps(handshake)}\n\n"
            
            while True:
                message = await asyncio.to_thread(lambda: pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1))
                
                if message and message['type'] == 'message':
                    data_raw = message['data']
                    try:
                         data = json.loads(data_raw)
                         event_type = data.get("type", "pulse_update")
                         
                         # 1. Profile-Based Filtering (Sovereign v9.8.1)
                         if profile == "mobile":
                             # v13.0: 360 observability for mobile sovereignty
                             allowed = [
                                 "mission_start", "mission_started", "mission_complete", "mission_completed", 
                                 "mission_error", "mission_aborted", "perception", "activity", "graph", "results",
                                 "rule_promoted", "learning_feedback", "neural_synthesis",
                                 "MEMORY_DREAMING_START", "MEMORY_DREAMING_COMPLETE", "MEMORY_DREAMING_ERROR"
                             ]
                             if event_type not in allowed:
                                 continue
                         
                         # 2. Dynamic Compression for Mobile (Base64 Binary Pulse)
                         if profile == "mobile":
                             compressed = zlib.compress(data_raw.encode('utf-8'))
                             payload = base64.b64encode(compressed).decode('utf-8')
                             yield f"event: {event_type}\ndata: {payload}\n\n"
                         else:
                             yield f"event: {event_type}\ndata: {data_raw}\n\n"

                    except json.JSONDecodeError:
                         yield f"data: {data_raw}\n\n"
                
                # Dynamic Heartbeat
                yield f"event: heartbeat\ndata: {json.dumps({'timestamp': asyncio.get_event_loop().time()})}\n\n"

                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.info(f"[Pulse v4] Subscriber disconnected: {user_id}")
            # Ensure cleanup on disconnection
            try:
                await asyncio.to_thread(lambda: pubsub.unsubscribe(channel))
            except: pass
        except Exception as e:
            logger.error(f"[Pulse v4] Critical stream failure: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

# Global Accessors
def broadcast_event(event_type: str, data: Dict[str, Any], user_id: str = "global"):
    SovereignBroadcaster.publish(event_type, data, user_id)

def broadcast_fidelity(fidelity: float, mission_id: str, user_id: str = "global"):
    """Broadcasts a real-time fidelity score update."""
    SovereignBroadcaster.publish(PULSE_FIDELITY_UPDATE, {
        "mission_id": mission_id,
        "fidelity": round(fidelity, 4),
        "status": "stable" if fidelity > 0.8 else "fragile"
    }, user_id)
