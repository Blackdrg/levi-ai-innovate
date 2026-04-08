import os
import logging
import subprocess
import uuid
import tempfile
import shutil
from typing import Dict, Any

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
    PIDS_LIMIT = "64"

    @classmethod
    def execute(cls, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Runs code in an ephemeral container.
        """
        if language != "python":
            return {"success": False, "message": f"Language '{language}' not supported in v13.0."}

        # Create a temp file for the code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name

        try:
            container_name = f"sovereign_sandbox_{uuid.uuid4().hex[:8]}"
            runtime = os.getenv("SANDBOX_RUNTIME", "").strip()
            seccomp_profile = os.getenv("SANDBOX_SECCOMP_PROFILE", "").strip()
            docker_bin = shutil.which("docker") or "docker"
            
            cmd = [
                docker_bin, "run", "--rm",
                "--name", container_name,
                "--network", "none",
                "--cpus", cls.CPU_LIMIT,
                "--memory", cls.MEM_LIMIT,
                "--pids-limit", cls.PIDS_LIMIT,
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "-v", f"{tmp_path}:/app/script.py:ro",
                cls.IMAGE,
                "python", "/app/script.py"
            ]
            if runtime:
                cmd[2:2] = ["--runtime", runtime]
            if seccomp_profile:
                cmd[2:2] = ["--security-opt", f"seccomp={seccomp_profile}"]

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
            subprocess.run([docker_bin, "kill", container_name], capture_output=True)
            return {"success": False, "message": f"Execution Timeout: Mission exceeded {cls.TIMEOUT}s limit."}
        except Exception as e:
            logger.error(f"[Sandbox] Critical Failure: {e}")
            return {"success": False, "message": f"Sandbox Flux: {str(e)}"}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
