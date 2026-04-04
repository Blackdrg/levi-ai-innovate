import logging

logger = logging.getLogger(__name__)

class DataEngine:
    """
    Data Processing Engine (v8.15)
    Handles list operations, sorting, and basic statistics without LLM.
    """

    def run(self, task_input):
        """
        Processes a dict with 'data' key or a direct list.
        """
        try:
            logger.info("[DataEngine] Analyzing data input structure.")
            
            # Handle both direct list and dictionary-wrapped data
            data = task_input
            if isinstance(task_input, dict):
                data = task_input.get("data")

            if isinstance(data, list):
                # Check if all elements are numbers for math operations
                is_numeric = all(isinstance(x, (int, float)) for x in data)
                
                result = {
                    "sorted": sorted(data),
                    "length": len(data),
                    "sum": sum(data) if is_numeric else None,
                    "min": min(data) if data and (is_numeric or all(isinstance(x, str) for x in data)) else None,
                    "max": max(data) if data and (is_numeric or all(isinstance(x, str) for x in data)) else None
                }
                
                return {
                    "success": True,
                    "data": result,
                    "engine": "data",
                    "message": f"Data processed: {len(data)} items analyzed."
                }

            logger.warning("[DataEngine] Input is not a list.")
            return {"success": False, "error": "Input data must be a list."}
            
        except Exception as e:
            logger.error(f"[DataEngine] Failure: {e}")
            return {"success": False, "error": str(e), "engine": "data"}
