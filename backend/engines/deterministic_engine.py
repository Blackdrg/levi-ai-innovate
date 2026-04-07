import logging
import statistics
from typing import Dict, Any
from backend.engines.base import EngineBase

logger = logging.getLogger(__name__)

class DeterministicEngine(EngineBase):
    """
    LeviBrain v8.12: Hardened Deterministic Engine.
    Handles arithmetic, comparisons, boolean logic, conditionals, 
    sorting/filtering, string transforms, and basic statistics.
    """
    
    def __init__(self):
        super().__init__("Deterministic")

    async def _run(self, op: str, params: Dict[str, Any], **kwargs) -> Any:
        """
        Main execution logic for deterministic operations.
        """
        self.logger.info(f"Executing Deterministic Operation: {op}")
        
        try:
            if op == "math":
                return self._handle_math(params)
            elif op == "stats":
                return self._handle_stats(params)
            elif op == "transform":
                return self._handle_transform(params)
            elif op == "logic":
                return self._handle_logic(params)
            elif op == "filter_sort":
                return self._handle_filter_sort(params)
            else:
                return {"status": "error", "message": f"Unsupported operation: {op}"}
        except Exception as e:
            self.logger.error(f"Deterministic Operation Error: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_math(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simple math operations."""
        expr = params.get("expression")
        if not expr: return {"error": "Missing expression"}
        
        # Use safe eval for simple arithmetic
        allowed = set("0123456789+-*/%(). ")
        if not all(c in allowed for c in str(expr)):
            return {"error": "Expression contains invalid characters"}
            
        try:
            result = eval(str(expr))
            return {"result": result, "status": "success"}
        except ZeroDivisionError:
             return {"error": "Division by zero", "status": "error"}

    def _handle_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Basic stats (sum, avg, min, max, count)."""
        data = params.get("data")
        if not data: return {"error": "Missing data list"}
        
        try:
            vals = [float(v) for v in data]
            return {
                "sum": sum(vals),
                "avg": statistics.mean(vals),
                "min": min(vals),
                "max": max(vals),
                "count": len(vals),
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "error"}

    def _handle_transform(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """String transformations."""
        text = params.get("text", "")
        mode = params.get("mode", "upper")
        
        if mode == "upper": result = text.upper()
        elif mode == "lower": result = text.lower()
        elif mode == "capitalize": result = text.capitalize()
        elif mode == "title": result = text.title()
        elif mode == "strip": result = text.strip()
        else: result = text
        
        return {"result": result, "status": "success"}

    def _handle_logic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Boolean logic & Comparisons."""
        a = params.get("a")
        b = params.get("b")
        op = params.get("logic_op", "==")
        
        if op == "==": result = a == b
        elif op == "!=": result = a != b
        elif op == ">": result = a > b
        elif op == "<": result = a < b
        elif op == ">=": result = a >= b
        elif op == "<=": result = a <= b
        elif op == "and": result = bool(a) and bool(b)
        elif op == "or": result = bool(a) or bool(b)
        elif op == "not": result = not bool(a)
        else: return {"error": f"Unsupported logic op: {op}"}
        
        return {"result": result, "status": "success"}

    def _handle_filter_sort(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sorting & Filtering."""
        data = params.get("data", [])
        sort_key = params.get("sort_key")
        reverse = params.get("reverse", False)
        filter_query = params.get("filter_query")
        
        res = list(data)
        
        # Filtering
        if filter_query:
            # Simple substring filter for demonstration
            res = [item for item in res if filter_query in str(item)]
            
        # Sorting
        if sort_key:
            res.sort(key=lambda x: x.get(sort_key) if isinstance(x, dict) else x, reverse=reverse)
        else:
            res.sort(reverse=reverse)
            
        return {"result": res, "status": "success"}
