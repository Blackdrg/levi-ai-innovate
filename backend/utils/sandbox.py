import os
import logging
import subprocess
import uuid
import tempfile
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DockerSandbox:
    """
    Sovereign Code Sandbox v13.0.0.
    Executes arbitrary code in an isolated Docker container with strict resource limits.
    """
    
    IMAGE = "python:3.10-slim"
    CPU_LIMIT = "0.5" # 0.5 CPU core
    MEM_LIMIT = "256m" # 256MB RAM
    TIMEOUT = 10 # seconds

    @classmethod
    def execute(cls, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Runs code in an ephemeral container.
        """
        if language != "python":
            return {"success": False, "message": f"Language '{language}' not supported in v13.0."}

        # Create a temp file for the code
        with tempfile.NamedTemporary_File(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            tmp_path = f.name

        try:
            container_name = f"sovereign_sandbox_{uuid.uuid4().hex[:8]}"
            
            # Construct docker command
            # --rm: remove container after exit
            # --network none: no internet access
            # --cpus / --memory: resource limits
            cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                "--network", "none",
                "--cpus", cls.CPU_LIMIT,
                "--memory", cls.MEM_LIMIT,
                "-v", f"{tmp_path}:/app/script.py:ro",
                cls.IMAGE,
                "python", "/app/script.py"
            ]

            logger.info(f"[Sandbox] Launching container {container_name}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": result.stdout.strip(),
                    "data": {"stdout": result.stdout, "stderr": result.stderr}
                }
            else:
                return {
                    "success": False,
                    "message": f"Execution Error: {result.stderr.strip()}",
                    "data": {"stdout": result.stdout, "stderr": result.stderr}
                }

        except subprocess.TimeoutExpired:
            # Kill the container if it's still running
            subprocess.run(["docker", "kill", container_name], capture_output=True)
            return {"success": False, "message": f"Execution Timeout: Mission exceeded {cls.TIMEOUT}s limit."}
        except Exception as e:
            logger.error(f"[Sandbox] Critical Failure: {e}")
            return {"success": False, "message": f"Sandbox Flux: {str(e)}"}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
