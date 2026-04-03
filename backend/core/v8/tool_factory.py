"""
Sovereign Tool Factory v8.
Dynamic ingestion and wrapper generation for external OpenAPI/REST tools.
Enables LEVI to expand its capabilities autonomously by parsing external API contracts.
"""

import logging
import json
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ToolContract(BaseModel):
    name: str
    description: str
    base_url: str
    endpoints: List[Dict[str, Any]]
    auth_type: Optional[str] = None

class DynamicToolFactory:
    """
    Cognitive Factory for generating Python execution wrappers for unknown APIs.
    """
    
    @staticmethod
    async def ingest_openapi(url: str) -> ToolContract:
        """
        Parses an external OpenAPI JSON/YAML and returns a standardized LEVI Tool Contract.
        """
        logger.info(f"[ToolFactory] Ingesting OpenAPI from: {url}")
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            spec = res.json()
            
        # Basic parsing logic for V8 initialization
        contract = ToolContract(
            name=spec.get("info", {}).get("title", "unknown_tool"),
            description=spec.get("info", {}).get("description", ""),
            base_url=spec.get("servers", [{}])[0].get("url", ""),
            endpoints=[]
        )
        
        # Extract paths and methods
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                contract.endpoints.append({
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "params": details.get("parameters", [])
                })
                
        return contract

    @staticmethod
    def generate_wrapper_code(contract: ToolContract) -> str:
        """
        Generates a Python wrapper string that LEVI can execute via its internal PythonREPL or local_agent.
        """
        code = f'# Dynamic Wrapper for {contract.name}\n'
        code += f'# Base URL: {contract.base_url}\n\n'
        code += 'import httpx\n\n'
        code += f'async def execute_tool(endpoint_path, params=None):\n'
        code += f'    base_url = "{contract.base_url}"\n'
        code += f'    async with httpx.AsyncClient() as client:\n'
        code += f'        # V8 Dynamic Dispatch Logic\n'
        code += f'        url = f"{{base_url}}{{endpoint_path}}"\n'
        code += f'        # Logic to match method and inject params...\n'
        code += f'        return await client.get(url, params=params)\n'
        
        return code
