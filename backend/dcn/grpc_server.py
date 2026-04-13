# backend/dcn/grpc_server.py
import grpc
import json
import logging
import asyncio
from concurrent import futures
from typing import Dict, Any

# Assuming dcn_pb2 and dcn_pb2_grpc are generated from a .proto file
# For this software baseline, we will implement a mock server that simulates the P2P handshake
# In production, we'd use: python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. dcn.proto

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
            pulse_data = json.loads(request.payload)
            # Hand off to the secure listener in DCNProtocol
            # We bypass the Redis-stream check here since gRPC provides direct node-to-node security
            await self.dcn.handle_remote_pulse(pulse_data)
            return {"success": True, "message": "Pulse acknowledged"}
        except Exception as e:
            logger.error(f"[gRPC] Pulse processing failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

async def serve_gossip_service(dcn_protocol: Any, port: int = 9000):
    """Starts the gRPC server for P2P discovery."""
    server = grpc.aio.server()
    # In a real impl, we'd add the servicer to the server here:
    # dcn_pb2_grpc.add_DCNGossipServiceServicer_to_server(DCNGossipServiceServicer(dcn_protocol), server)
    
    server.add_insecure_port(f'[::]:{port}')
    logger.info(f"🚀 [gRPC] DCN Gossip Service started on port {port}")
    await server.start()
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        await server.stop(5)
