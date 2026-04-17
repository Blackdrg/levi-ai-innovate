"""
LEVI-AI Sovereign System Agent v16.3.0.
Handles OS-level control: File system, Process monitoring, and System resources.
"""

import os
import shutil
import psutil
import logging
from typing import Dict, Any, List, Optional
from backend.core.agent_base import AgentBase, AgentInput, AgentResult

logger = logging.getLogger(__name__)

class SystemAgent(AgentBase):
    """
    [Stage 3] System Control Agent.
    Gives LEVI the ability to interact with the host operating system.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capabilities = ["file_management", "process_monitoring", "sys_info"]

    async def _run(self, input_data: AgentInput) -> AgentResult:
        logger.info(f"🛰️ [SystemAgent] Executing OS-level mission: {input_data.objective}")
        
        command = input_data.payload.get("action")
        params = input_data.payload.get("params", {})

        try:
            if command == "read_file":
                return self._read_file(params.get("path"))
            elif command == "write_file":
                return self._write_file(params.get("path"), params.get("content"))
            elif command == "list_dir":
                return self._list_dir(params.get("path", "."))
            elif command == "process_status":
                return self._get_process_status(params.get("pid"))
            elif command == "system_health":
                return self._get_system_health()
            else:
                return AgentResult(success=False, error=f"Unknown system action: {command}")
        except Exception as e:
            logger.error(f"[SystemAgent] Command failed: {e}")
            return AgentResult(success=False, error=str(e))

    def _read_file(self, path: str) -> AgentResult:
        if not os.path.exists(path):
            return AgentResult(success=False, error="File not found")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return AgentResult(success=True, data={"content": content})

    def _write_file(self, path: str, content: str) -> AgentResult:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return AgentResult(success=True, data={"path": path, "status": "written"})

    def _list_dir(self, path: str) -> AgentResult:
        if not os.path.isdir(path):
            return AgentResult(success=False, error="Directory not found")
        items = os.listdir(path)
        return AgentResult(success=True, data={"items": items, "path": os.path.abspath(path)})

    def _get_process_status(self, pid: Optional[int] = None) -> AgentResult:
        if pid:
            try:
                proc = psutil.Process(pid)
                return AgentResult(success=True, data=proc.as_dict(attrs=['pid', 'name', 'status', 'cpu_percent', 'memory_info']))
            except psutil.NoSuchProcess:
                return AgentResult(success=False, error=f"Process {pid} not found")
        else:
            procs = [p.info for p in psutil.process_iter(attrs=['pid', 'name', 'status'])]
            return AgentResult(success=True, data={"processes": procs[:20]}) # Limit output

    def _get_system_health(self) -> AgentResult:
        health = {
            "cpu_usage": psutil.cpu_percent(interval=None),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "boot_time": psutil.boot_time()
        }
        return AgentResult(success=True, data=health)

# Export for Registry
agent_class = SystemAgent
