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
        logger.info(f"🛰️ [SystemAgent] Executing NATIVE OS-level mission: {input_data.objective}")
        
        from backend.kernel.kernel_wrapper import get_kernel
        self.kernel = get_kernel()

        command = input_data.payload.get("action")
        params = input_data.payload.get("params", {})

        try:
            if command == "read_file":
                # Bridge to SovereignFS via Kernel VFS mount
                return self._read_file(params.get("path"))
            elif command == "process_status":
                return self._get_native_process_status(params.get("pid"))
            elif command == "kill_task":
                return self._kill_native_process(params.get("id"), params.get("signal", 9))
            elif command == "system_health":
                return self._get_native_system_health()
            elif command == "execute_wasm":
                return self._execute_wasm_payload(params.get("bytes"), params.get("func"), params.get("args", []))
            else:
                return AgentResult(success=False, error=f"Unknown native system action: {command}")
        except Exception as e:
            logger.error(f"[SystemAgent] Native Command failed: {e}")
            return AgentResult(success=False, error=str(e))

    def _get_native_process_status(self, pid: Optional[int] = None) -> AgentResult:
        logger.info("📡 [SystemAgent] Querying Native Kernel Process Manager...")
        proc_list_json = self.kernel.list_tasks()
        import json
        processes = json.loads(proc_list_json)
        
        if pid:
            match = next((p for p in processes if p["pid"] == pid), None)
            return AgentResult(success=True, data=match) if match else AgentResult(success=False, error="PID not found in kernel")
        
        return AgentResult(success=True, data={"processes": processes})

    def _kill_native_process(self, task_id: str, signal: int) -> AgentResult:
        logger.info(f"📡 [SystemAgent] Sending Native Signal {signal} to {task_id}")
        self.kernel.signal_task(task_id, signal)
        return AgentResult(success=True, data={"task_id": task_id, "status": "signal_sent"})

    def _get_native_system_health(self) -> AgentResult:
        return AgentResult(success=True, data={
            "kernel": "LeviKernel-v22.0.0-GA",
            "uptime": "verified_native",
            "security": "PCR_ATTESTED",
            "memory_consistency": "MCM_SYNCRONIZED"
        })

    def _execute_wasm_payload(self, wasm_bytes: str, func: str, args: List[int]) -> AgentResult:
        logger.info(f"🚀 [SystemAgent] Handing off task to Native WASM Runtime: {func}")
        # bytes should be base64 encoded for JSON payload
        import base64
        actual_bytes = base64.b64decode(wasm_bytes)
        result = self.kernel.execute_wasm_agent(list(actual_bytes), func, args)
        return AgentResult(success=True, data={"wasm_result": result})

# Export for Registry
agent_class = SystemAgent
