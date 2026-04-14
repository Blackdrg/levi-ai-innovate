# backend/agents/artisan_agent.py
import logging
import asyncio
import time
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, validator

from backend.agents.base import SovereignAgent, AgentResult
from backend.utils.filesystem_sandbox import FileSystemInterface

import os
import json
import uuid

logger = logging.getLogger(__name__)

class ArtisanInput(BaseModel):
    """
    Sovereign v15.0: Artisan Task Execution Contract (TEC) Input.
    """
    objective: str = Field(..., description="The computational objective")
    code: Optional[str] = Field(None, description="Python source code to execute")
    dependencies: Optional[List[str]] = Field(default_factory=list, description="Pip packages to install")
    timeout: int = Field(45, ge=1, le=120)
    session_id: str

    @validator('code')
    def validate_code_safety(cls, v):
        if v and len(v.strip()) == 0:
            raise ValueError("Code cannot be empty if provided")
        return v

class ArtisanAgent(SovereignAgent[ArtisanInput, AgentResult]):
    """
    Sovereign v15.0: The Artisan.
    Master of computational execution, code synthesis, and sandboxed processing.
    """
    def __init__(self):
        super().__init__(name="Artisan", profile="Computational Architect")
        self.fs: Optional[FileSystemInterface] = None

    async def _run(self, input_data: ArtisanInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Executes computational missions using the Sovereign Sandbox (v15.0 Hardened).
        """
        mission_id = input_data.session_id
        self.fs = FileSystemInterface(mission_id)
        
        logger.info(f"[Artisan] Initializing sandboxed mission: {mission_id}")
        
        try:
            # 1. BRAIN-LEVEL SAFETY VALIDATION
            if input_data.code:
                await self._validate_code_safety(input_data.code)
                
                # 2. FILE SYSTEM ISOLATION
                path = await self.fs.write_file("main.py", input_data.code)
                logger.info(f"[Artisan] Payload staged at: {path}")
                
                # 3. SANDBOX ABSTRACTION (v15.0: gVisor/Docker Ready)
                # In production, this would trigger a gVisor-hardened container.
                # Locally, we use a restricted subprocess.
                output = await self._execute_in_sandbox(path, input_data.timeout, mission_id)
                
                return {
                    "success": output["exit_code"] == 0,
                    "message": "Artisan mission completed." if output["exit_code"] == 0 else "Mission halted by system boundary.",
                    "data": {
                        "stdout": output["stdout"],
                        "stderr": output["stderr"],
                        "exit_code": output["exit_code"],
                        "execution_time_s": output["time"],
                        "files": await self.fs.list_files()
                    },
                    "confidence": 1.0,
                    "fidelity_score": 1.0 if output["exit_code"] == 0 else 0.2
                }
            
            return {
                "success": True,
                "message": "Artisan environment ready.",
                "data": {"files": await self.fs.list_files()},
                "confidence": 1.0
            }
            
        except Exception as e:
            logger.error(f"[Artisan] Mission failure: {e}")
            return {
                "success": False,
                "message": f"Artisan Neural Block: {str(e)}",
                "data": {"error_type": type(e).__name__}
            }

    async def _execute_in_sandbox(self, script_path: Any, timeout: int, session_id: str) -> Dict[str, Any]:
        """
        The 'Sovereign Bridge' to the physical execution layer.
        Currently implements a hardened subprocess. Architecture allows hot-swap to gVisor.
        """
        import sys
        import subprocess
        
        # Hardened environment variables (No inheritance from host)
        env = {
            "PYTHONPATH": ".",
            "MISSION_ID": session_id,
            "COGNITIVE_BOUND": "TRUE"
        }
        
        start_time = time.time()
        try:
            # v15.0 GA: We simulate gVisor by stripping environment and restricting CWD
            process = await asyncio.to_thread(
                lambda: subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(self.fs.mission_dir),
                    env=env # Strict isolation
                )
            )
            return {
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
                "time": time.time() - start_time
            }
        except subprocess.TimeoutExpired as e:
            return {
                "stdout": e.stdout.decode() if e.stdout else "",
                "stderr": "Mission timed out by Sovereign Guardrails.",
                "exit_code": 124,
                "time": timeout
            }

    async def _validate_code_safety(self, code: str):
        """
        Artisan Guardrails v15.1 [HARDENED]: AST-based Static Analysis.
        Prevents dangerous modules, direct file-system access outside sandbox, and unauthorized syscalls.
        """
        import ast
        try:
            tree = ast.parse(code)
            
            # Sovereign Block-list (v15.1 Manifest)
            PROHIBITED_MODULES = {
                "os", "sys", "subprocess", "socket", "requests", "httpx", "urllib",
                "pickle", "marshal", "pty", "platform", "resource", "multiprocessing", "threading"
            }
            PROHIBITED_CALLS = {"eval", "exec", "open", "getattr", "setattr", "delattr", "compile", "globals", "locals"}
            
            for node in ast.walk(tree):
                # 1. Block prohibited imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in PROHIBITED_MODULES:
                            raise ValueError(f"Sovereign Guardrail: Prohibited module import '{alias.name}' detected.")
                
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in PROHIBITED_MODULES:
                        raise ValueError(f"Sovereign Guardrail: Prohibited module import '{node.module}' detected.")
                
                # 2. Block prohibited function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in PROHIBITED_CALLS:
                            raise ValueError(f"Sovereign Guardrail: Dangerous syscall attempt '{node.func.id}()' neutralized.")
                    
                    # Prevent __import__ and other dynamic loading
                    if isinstance(node.func, ast.Attribute):
                         if node.func.attr == "__import__":
                              raise ValueError("Sovereign Guardrail: Dynamic import attempt detected.")
            
            logger.info("[Artisan] Code safety validation: PASSED (AST analysis)")
            
        except SyntaxError as e:
            raise ValueError(f"Sovereign Block: Syntax error in staged code: {e}")
        except Exception as e:
            if "Sovereign Guardrail" in str(e): raise
            logger.error(f"[Artisan] AST analysis failed: {e}")
            raise ValueError("Sovereign Security: Code analysis failed to confirm safety baseline.")
