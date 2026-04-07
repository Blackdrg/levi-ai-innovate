"""
Sovereign Tool Discovery v14.0.
Provides semantic search and dynamic recommendation for the autonomous Agent Ecosystem.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from backend.core.tool_registry import list_tools, get_tool
from backend.embeddings import embed_text
import numpy as np

logger = logging.getLogger(__name__)

class ToolDiscoveryService:
    _index: List[Dict[str, Any]] = []
    _embeddings: Optional[np.ndarray] = None
    _lock = asyncio.Lock()

    @classmethod
    async def refresh_index(cls):
        """Re-indexes all available tools from the registry and generates embeddings."""
        async with cls._lock:
            logger.info("[Discovery] Refreshing Tool Index...")
            tools = list_tools()
            new_index = []
            texts_to_embed = []
            
            for name, description in tools.items():
                agent = get_tool(name)
                # Capabilities extraction
                caps = getattr(agent, "__capabilities__", ["general"])
                
                entry = {
                    "name": name,
                    "description": description,
                    "capabilities": caps,
                    "search_text": f"{name}: {description} | caps: {', '.join(caps)}"
                }
                new_index.append(entry)
                texts_to_embed.append(entry["search_text"])
            
            if texts_to_embed:
                # Generate embeddings for the entire index
                embeddings = await embed_text(texts_to_embed)
                cls._embeddings = np.array(embeddings)
                cls._index = new_index
                logger.info(f"[Discovery] Indexed {len(new_index)} tools successfully.")

    @classmethod
    async def discover_tools(cls, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Semantic search for tools matching the query."""
        if not cls._index:
            await cls.refresh_index()
            
        if cls._embeddings is None or len(cls._embeddings) == 0:
            return []

        query_embedding = await embed_text(query)
        # Cosine similarity
        similarities = np.dot(cls._embeddings, np.array(query_embedding))
        top_indices = np.argsort(similarities)[::-1][:limit]
        
        results = []
        for idx in top_indices:
            tool = cls._index[idx]
            results.append({
                "name": tool["name"],
                "description": tool["description"],
                "capabilities": tool["capabilities"],
                "score": float(similarities[idx])
            })
            
        return results

    @classmethod
    async def get_recommended_for_agent(cls, agent_name: str, task: str) -> List[str]:
        """Recommends specific tools based on agent type and current task."""
        # Simple heuristic: filter out the agent itself and find best matches
        all_tools = await cls.discover_tools(task, limit=5)
        return [t["name"] for t in all_tools if t["name"] != agent_name][:3]

# Global Accessor
async def find_relevant_tools(query: str, limit: int = 3):
    return await ToolDiscoveryService.discover_tools(query, limit)
