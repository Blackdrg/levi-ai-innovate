import math
import operator
import re
import logging

logger = logging.getLogger(__name__)

class DeterministicEngine:
    """
    Advanced Deterministic Engine (v8.15)
    Solves math, logic, and calculations without LLM.
    """

    def run(self, task: str):
        try:
            logger.info(f"[DeterministicEngine] Processing task: {task}")
            # extract math expression: find the longest valid sequence of math chars
            expressions = re.findall(r'[\d\+\-\*/\.\%\(\) ]+', task)
            if not expressions:
                return {"success": False, "error": "No mathematical expression detected"}
            
            # Use the longest match to avoid fragments
            expr = max(expressions, key=len).strip()
            
            # Clean up: remove trailing operators
            expr = re.sub(r'[\+\-\*/\%\.]+$', '', expr)
            
            logger.debug(f"[DeterministicEngine] Evaluating expr: {expr}")
            
            # Strict safety: No builtins, only math module
            result = eval(expr, {"__builtins__": None}, {"math": math})
            
            return {
                "success": True, 
                "data": result,
                "engine": "deterministic",
                "message": f"Deterministic result: {result}"
            }
        except Exception as e:
            logger.error(f"[DeterministicEngine] Failure: {e}")
            return {"success": False, "error": str(e)}
