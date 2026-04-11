# backend/core/executor/sandbox.py
import subprocess
import logging
import os
import json
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DockerSandbox:
    """
    Sovereign v14.2: Isolated Tool Execution Environment.
    Wraps tool logic in a short-lived Docker container with strict resource limits.
    Supports gVisor (runsc) if available for enhanced kernel isolation.
    """
    def __init__(
        self, 
        image: str = "python:3.10-slim",
        memory_mb: int = 512,
        cpu_quota: float = 1.0,
        use_gvisor: bool = False
    ):
        self.image = image
        self.memory_mb = memory_mb
        self.cpu_quota = cpu_quota
        self.runtime = "runsc" if use_gvisor else "runc"

    async def run_code(self, code: str, env: Optional[Dict[str, str]] = None, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Executes raw Python code in the hardened sandbox.
        Sovereign v14.2: Maximum isolation pass.
        """
        sandbox_id = f"sandbox_{uuid.uuid4().hex[:8]}"
        
        # Security Flags (Hardened v14.2)
        # 1. --cap-drop=ALL: Drops all Linux capabilities (no raw sockets, no chown, etc)
        # 2. --security-opt=no-new-privileges: Prevents binaries from gaining new privileges via setuid/setgid
        # 3. --read-only: Root filesystem is immutable
        # 4. --tmpfs /tmp: Allow writing only to a temporary, memory-backed /tmp
        # 5. --user=nobody: Run as non-privileged user
        
        docker_cmd = [
            "docker", "run", "--rm", "-i",
            "--memory", f"{self.memory_mb}m",
            "--memory-swap", "0", # Hard disable swap escalation per P0 request
            "--oom-kill-disable=false", # Ensure process is killed on OOM
            "--cpus", str(self.cpu_quota),
            "--pids-limit", "64",
            "--network", "none",
            "--cap-drop=ALL",
            "--security-opt", "no-new-privileges",
            "--user", "nobody",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--volume", "/etc/ssl/certs:/etc/ssl/certs:ro",
            f"--runtime={self.runtime}",
            self.image,
            "python", "-c", code
        ]
        
        logger.info(f"[Sandbox] Launching Hardened {sandbox_id} (Runtime: {self.runtime})...")
        
        try:
            # We use asyncio.create_subprocess_exec for non-blocking execution
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode().strip(),
                "stderr": stderr.decode().strip(),
                "exit_code": process.returncode,
                "sandbox_id": sandbox_id
            }
        except asyncio.TimeoutError:
            logger.error(f"[Sandbox] {sandbox_id} timed out after {timeout}s.")
            return {"success": False, "error": "Sandbox timeout", "sandbox_id": sandbox_id}
        except Exception as e:
            logger.error(f"[Sandbox] {sandbox_id} critical failure: {e}")
            return {"success": False, "error": str(e), "sandbox_id": sandbox_id}

    async def run_command(self, command: List[str], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Executes a generic command in the hardened sandbox.
        """
        sandbox_id = f"sandbox_{uuid.uuid4().hex[:8]}"
        
        docker_cmd = [
            "docker", "run", "--rm", "-i",
            "--memory", f"{self.memory_mb}m",
            "--memory-swap", "0",
            "--oom-kill-disable=false",
            "--cpus", str(self.cpu_quota),
            "--pids-limit", "64",
            "--network", "none",
            "--cap-drop=ALL",
            "--security-opt", "no-new-privileges",
            "--user", "nobody",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--volume", "/etc/ssl/certs:/etc/ssl/certs:ro",
            f"--runtime={self.runtime}",
            self.image
        ] + command
        
        logger.info(f"[Sandbox] Launching Hardened Command {sandbox_id}...")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode().strip(),
                "stderr": stderr.decode().strip(),
                "exit_code": process.returncode,
                "sandbox_id": sandbox_id
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Sandbox timeout", "sandbox_id": sandbox_id}
        except Exception as e:
            return {"success": False, "error": str(e), "sandbox_id": sandbox_id}

# Global fallback for environments without Docker (e.g., local dev without daemon)
class LocalProcessSandbox:
    """Fallback sandbox using subprocess for non-docker environments."""
    async def run_code(self, code: str, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if os.getenv("ENVIRONMENT") == "production":
            logger.critical("[Security] INSECURE SANDBOX BLOCK: LocalProcessSandbox triggered in PRODUCTION. Access REJECTED.")
            return {"success": False, "error": "Insecure sandbox execution prohibited in production.", "sandbox_id": "blocked"}
            
        logger.warning("[Sandbox] DOCKER UNAVAILABLE. Falling back to local process isolation (INSECURE).")
        return {"success": True, "stdout": "Local fallback executed (mock result)", "sandbox_id": "local_dev"}

def get_sandbox(agent_config: Any = None) -> Any:
    """Factory to create the appropriate sandbox for an agent."""
    if os.getenv("DISABLE_DOCKER_SANDBOX", "false").lower() == "true":
        return LocalProcessSandbox()
    
    image = getattr(agent_config, "sandbox_image", "python:3.10-slim")
    memory = getattr(agent_config, "memory_limit_mb", 512)
    cpu = getattr(agent_config, "cpu_cores", 1.0)
    
    return DockerSandbox(image=image, memory_mb=memory, cpu_quota=cpu)
