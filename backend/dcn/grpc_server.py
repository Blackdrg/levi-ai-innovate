# backend/dcn/grpc_server.py
import grpc
import json
import logging
import asyncio
from typing import Dict, Any, Optional

from backend.utils.ssl_manager import SSLManager

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

    async def PulseStream(self, request_iterator, context):
        """Bidirectional stream for continuous pulse propagation."""
        logger.info(f"🛰️ [gRPC] Bidirectional PulseStream opened (Phase 2.3)")
        async for request in request_iterator:
            try:
                pulse_data = json.loads(request.payload)
                await self.dcn.handle_remote_pulse(pulse_data)
                
                if dcn_pb2:
                    yield dcn_pb2.PulseResponse(success=True)
                else:
                    yield {"success": True}
                    
            except Exception as e:
                logger.error(f"[gRPC-Stream] Processing error: {e}")
                continue

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

    async def PullArtifact(self, request, context):
        """Phase 2.3: Chunked Artifact Transfer. Streams a file in 1MB chunks."""
        artifact_id = request.artifact_id
        logger.info(f"📤 [gRPC-P2P] Incoming PullArtifact request: {artifact_id}")
        
        try:
            from backend.db.postgres import PostgresDB
            from backend.db.models import Artifact
            from sqlalchemy import select
            
            async with PostgresDB._session_factory() as session:
                stmt = select(Artifact).where(Artifact.id == int(artifact_id))
                result = await session.execute(stmt)
                artifact = result.scalar_one_or_none()
                
            if not artifact or not os.path.exists(artifact.file_path):
                logger.error(f"[gRPC-P2P] Artifact {artifact_id} not found on local storage.")
                context.abort(grpc.StatusCode.NOT_FOUND, "Artifact not found")
                return

            # Read and stream in chunks
            chunk_size = 1014 * 1024 # 1MB
            with open(artifact.file_path, "rb") as f:
                f.seek(request.start_offset)
                chunk_idx = 0
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    
                    is_final = len(data) < chunk_size
                    yield dcn_pb2.ArtifactChunk(
                        data=data,
                        chunk_index=chunk_idx,
                        is_final=is_final,
                        checksum=artifact.checksum
                    )
                    chunk_idx += 1
                    if is_final: break
                
        except Exception as e:
            logger.error(f"[gRPC-P2P] Artifact transfer failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

async def serve_gossip_service(dcn_protocol: Any, port: int = 9000):
    """Starts the gRPC server for P2P discovery with mTLS reinforcement."""
    if not dcn_pb2_grpc:
        logger.warning("⚠️ [gRPC] DCN Protos not compiled. Server starting in degraded/mock mode.")
    
    server = grpc.aio.server()
    
    if dcn_pb2_grpc:
        dcn_pb2_grpc.add_DCNGossipServiceServicer_to_server(
            DCNGossipServiceServicer(dcn_protocol), server
        )
    
    # --- mTLS SECURE PORT LOGIC ---
    creds = SSLManager.get_server_credentials()
    if creds:
        private_key, certificate_chain, root_certificates = creds
        server_creds = grpc.ssl_server_credentials(
            [(private_key, certificate_chain)],
            root_certificates=root_certificates,
            require_client_auth=True # ENFORCE mTLS
        )
        server.add_secure_port(f'[::]:{port}', server_creds)
        logger.info(f"🛡️ [gRPC] DCN Hive Secure (mTLS) Service active on port {port}")
    else:
        server.add_insecure_port(f'[::]:{port}')
        logger.warning(f"⚠️ [gRPC] DCN Gossip Service started in INSECURE mode on port {port}")
    # ------------------------------

    await server.start()
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        await server.stop(5)
