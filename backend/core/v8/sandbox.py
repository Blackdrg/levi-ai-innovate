"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
Logic Sandbox: Secure code execution and resource-constrained simulation.
"""

import sys
import io
import logging
import concurrent.futures
from typing import Any, Dict, Optional
from backend.utils.audit import AuditLogger

# Resource limiting is Unix-only, fallback for Windows
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

logger = logging.getLogger(__name__)

class SovereignSandbox:
    """
    Sovereign OS v13.0: Secure Execution Sandbox.
    Handles tool execution with strict resource constraints and restricted environments.
    """
    
    @staticmethod
    def _limit_resources_production():
        """Unix-specific resource hardening."""
        if HAS_RESOURCE:
            # CPU time: 5s, Memory: 512MB
            resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        
    @classmethod
    def execute(cls, code: str, context: Optional[Dict[str, Any]] = None, timeout: int = 5) -> Dict[str, Any]:
        """
        Executes logic in a hardened environment.
        - Restricted Builtins (no os, sys, eval)
        - CPU/Memory limits (Production)
        - Thread-based timeout (Cross-platform)
        """
        stdout = io.StringIO()
        stderr = io.StringIO()
        
        # 1. Restricted Builtins (No os, sys, eval, open, input, etc.)
        safe_builtins = {
            'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool, 'chr': chr,
            'dict': dict, 'divmod': divmod, 'enumerate': enumerate, 'filter': filter,
            'float': float, 'format': format, 'frozenset': frozenset, 
            'int': int, 'isinstance': isinstance,
            'iter': iter, 'len': len, 'list': list, 'map': map, 'max': max, 'min': min,
            'next': next, 'object': object, 'oct': oct, 'ord': ord, 'pow': pow, 
            'print': print, 'range': range, 'repr': repr, 'reversed': reversed,
            'round': round, 'set': set, 'sorted': sorted, 'str': str, 'sum': sum, 
            'tuple': tuple, 'type': type, 'zip': zip,
            'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
            '__name__': '__main__', '__doc__': None,
        }
        
        # 2. Local Namespace
        loc = context or {}
        
        # 3. Execution Wrap
        def run_code():
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = stdout, stderr
            try:
                if HAS_RESOURCE: cls._limit_resources_production()
                exec(code, {"__builtins__": safe_builtins}, loc)
                return True
            except Exception as e:
                stderr.write(f"Sovereign Sandbox Fault: {str(e)}")
                return False
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

        # 4. Global Timeout Enforcement
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_code)
            try:
                success = future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                success = False
                stderr.write(f"Sovereign Sandbox Fault: Execution timed out after {timeout}s.")
            except Exception as e:
                success = False
                stderr.write(f"Sovereign Sandbox Fault: Internal system error - {str(e)}")

        # 🛡️ Graduation Audit: Record Execution Attempt
        loop = asyncio.get_event_loop()
        if loop.is_running():
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(AuditLogger.log_event(
                event_type="SECURITY",
                action="REPL EXEC",
                status="success" if success else "failed",
                metadata={"code_len": len(code), "success": success}
            ), name="sandbox-audit-log")

        return {
            "success": success,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
            "locals": {k: v for k, v in loc.items() if not k.startswith("__")}
        }
