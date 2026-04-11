"""
Sovereign Health & DCN Topology API v14.1.0.
Provides surgical health probes and cognitive network visualization.
"""

import logging
import os
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from backend.utils.health import probe_dependencies
from backend.utils.metrics import MetricsHub
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC

router = APIRouter(prefix="", tags=["Health & DCN"])
logger = logging.getLogger(__name__)

@router.get("/graph")
async def get_health_graph():
    """
    Returns a graph representation of the DCN nodes and their health links.
    Used for Cybernetic UI visualization.
    """
    nodes = []
    links = []
    
    if HAS_REDIS_ASYNC and redis_client:
        try:
            raw_nodes = await redis_client.hgetall("dcn:swarm:nodes")
            for nid, data_json in raw_nodes.items():
                import json
                n_data = json.loads(data_json)
                nodes.append({
                    "id": nid,
                    "type": n_data.get("node_role", "worker"),
                    "health": n_data.get("health_score", 1.0),
                    "load": n_data.get("cpu_percent", 0),
                    "status": "online" if n_data.get("is_active", True) else "offline"
                })
                # Simulated links based on gossip proximity
                # In prod, this would pull from the actual Raft topology
                if n_data.get("peer_id"):
                    links.append({"source": nid, "target": n_data["peer_id"], "strength": 0.95})
        except Exception as e:
            logger.error(f"[Health] Graph retrieval failed: {e}")

    # Fallback to standalone node if no swarm detected
    if not nodes:
        nodes.append({"id": "node-alpha", "type": "leader", "health": 1.0, "load": 5, "status": "online"})

    return {
        "nodes": nodes,
        "links": links,
        "metrics": MetricsHub.get_latest_metrics() if hasattr(MetricsHub, "get_latest_metrics") else {}
    }

@router.get("/readiness")
async def get_root_healthz():
    """Root /ready probe for K8s/Docker."""
    probe = await probe_dependencies()
    return {
        "status": probe["status"],
        "timestamp": os.getenv("START_TIME", "0"),
        "resonance": "STABLE"
    }

@router.post("/rollback")
async def trigger_emergency_rollback():
    """
    Sovereign v15.0: Emergency Rollback Trigger.
    Emits a GitHub Repository Dispatch to revert the cluster state.
    Requires: ROLLBACK_TOKEN (PAT with repo scope).
    """
    import aiohttp
    
    token = os.getenv("ROLLBACK_TOKEN")
    repo = os.getenv("GITHUB_REPO") # e.g., "Blackdrg/levi-ai-innovate"
    
    if not token or not repo:
        logger.error("[Rollback] FAILED: Missing ROLLBACK_TOKEN or GITHUB_REPO in env.")
        return {"status": "error", "message": "Rollback capability not configured."}

    url = f"https://api.github.com/repos/{repo}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    payload = {"event_type": "trigger-rollback"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status in [201, 204]:
                    logger.warning(f"[Rollback] CRITICAL: Emergency rollback triggered via GitHub Dispatch for {repo}.")
                    return {"status": "triggered", "message": "Rollback workflow initiated."}
                
                txt = await response.text()
                logger.error(f"[Rollback] GitHub API rejected request: {response.status} - {txt}")
                return {"status": "failed", "http_code": response.status}
    except Exception as e:
        logger.exception(f"[Rollback] Unexpected error during dispatch: {e}")
        return {"status": "error", "message": str(e)}
