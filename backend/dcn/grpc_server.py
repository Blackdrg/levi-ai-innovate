# backend/dcn/grpc_server.py
import grpc
import json
import logging
import asyncio
from typing import Dict, Any

# We expect the dev to have run: python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. dcn.proto
# In the absence of generated files, we will use a dynamic approach or a known structure
try:
    from . import dcn_pb2
    from . import dcn_pb2_grpc
except ImportError:
    # Failback/Mock for initial discovery if protos aren't compiled yet
    dcn_pb2 = None
    dcn_pb2_grpc = None

logger = logging.getLogger(__name__)

class DCNGossipServiceServicer:
    """
    gRPC Servicer for the Distributed Cognitive Network.
    Handles incoming heartbeats and mission truth pulses from peers.
    """
    def __init__(self, dcn_protocol: Any):
        self.dcn = dcn_protocol

    async def PublishPulse(self, request, context):
        """Standard unary call for P2P gossip pulses."""
        try:
            # signature = request.signature
            payload_json = request.payload
            pulse_data = json.loads(payload_json)
            
            # Hand off to the secure listener in DCNProtocol
            # The DCNProtocol will verify the HMAC signature inside handle_remote_pulse
            await self.dcn.handle_remote_pulse(pulse_data)
            
            if dcn_pb2:
                return dcn_pb2.PulseResponse(success=True, message="Pulse acknowledged")
            return {"success": True, "message": "Pulse acknowledged"}
        except Exception as e:
            logger.error(f"[gRPC] Pulse processing failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

async def serve_gossip_service(dcn_protocol: Any, port: int = 9000):
    """Starts the gRPC server for P2P discovery."""
    if not dcn_pb2_grpc:
        logger.warning("⚠️ [gRPC] DCN Protos not compiled. Server starting in degraded/mock mode.")
    
    server = grpc.aio.server()
    
    if dcn_pb2_grpc:
        dcn_pb2_grpc.add_DCNGossipServiceServicer_to_server(
            DCNGossipServiceServicer(dcn_protocol), server
        )
    
    server.add_insecure_port(f'[::]:{port}')
    logger.info(f"🚀 [gRPC] DCN Gossip Service started on port {port}")
    await server.start()
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        await server.stop(5)
