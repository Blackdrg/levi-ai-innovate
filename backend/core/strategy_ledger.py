"""
Sovereign Strategy Ledger v14.1.0.
Central repository for high-fidelity DAG templates and cognitive strategies.
"""

import logging
import json
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class StrategyLedger:
    """
    The Strategy Ledger stores validated 'winning' DAG templates 
    indexed by intent and domain complexity.
    """
    LEDGER_PATH = "backend/data/strategy_templates.json"

    @classmethod
    def get_best_template(cls, intent_type: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the highest fidelity DAG template for the given intent.
        Returns None if no optimized strategy exists (triggering default heuristic).
        """
        if not os.path.exists(cls.LEDGER_PATH):
            return None
            
        try:
            with open(cls.LEDGER_PATH, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            
            strategy = ledger.get(intent_type)
            if not strategy:
                return None
            
            # Calibration: Ensure fidelity is still high enough
            # Strategies with < 0.7 fidelity are considered 'stale'
            if strategy.get("avg_fidelity", 1.0) < 0.7:
                logger.warning(f"[Ledger] Strategy for {intent_type} is stale (F={strategy['avg_fidelity']}).")
                return None
            
            logger.info(f"[Ledger] Optimized strategy match for {intent_type} (F={strategy.get('avg_fidelity')})")
            return strategy.get("graph_template")
            
        except Exception as e:
            logger.error(f"[Ledger] Template retrieval failure: {e}")
            return None

    @classmethod
    def update_strategy(cls, intent_type: str, template: Dict[str, Any], fidelity: float):
        """Updates the ledger with a new winning strategy."""
        os.makedirs(os.path.dirname(cls.LEDGER_PATH), exist_ok=True)
        
        ledger = {}
        if os.path.exists(cls.LEDGER_PATH):
            try:
                with open(cls.LEDGER_PATH, "r") as f:
                    ledger = json.load(f)
            except: pass
            
        current = ledger.get(intent_type, {})
        if fidelity >= current.get("avg_fidelity", 0.0):
            ledger[intent_type] = {
                "graph_template": template,
                "avg_fidelity": fidelity,
                "last_updated": os.getenv("START_TIME", "0")
            }
            with open(cls.LEDGER_PATH, "w") as f:
                json.dump(ledger, f, indent=2)
