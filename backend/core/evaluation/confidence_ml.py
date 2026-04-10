import numpy as np
import logging
from typing import Dict, Any, List, Optional
from sklearn.linear_model import LinearRegression
import joblib
import os

logger = logging.getLogger(__name__)

class AdaptiveConfidenceModel:
    """
    LEVI-AI v14.1 Adaptive Confidence Model.
    Replaces static formula with a calibrated ML model.
    Features: DAG Depth, Node Count, Dependency Complexity, Historical Success, Complexity Score.
    """
    
    MODEL_PATH = "data/models/confidence_regressor.joblib"
    
    def __init__(self):
        self.model = LinearRegression()
        self._is_trained = False
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.MODEL_PATH):
            try:
                self.model = joblib.load(self.MODEL_PATH)
                self._is_trained = True
                logger.info("[ConfidenceML] Pre-trained model loaded.")
            except Exception as e:
                logger.warning(f"[ConfidenceML] Failed to load model: {e}")

    def predict(self, features: Dict[str, float]) -> float:
        """
        Predicts confidence score (0.0 - 1.0).
        Fallback to heuristic if model is not trained.
        """
        # Baseline Feature Order
        # 1. Depth, 2. Node Count, 3. Dependencies, 4. Hist. Success, 5. Complexity
        X = np.array([[
            features.get("depth", 1.0),
            features.get("node_count", 1.0),
            features.get("dependencies", 0.0),
            features.get("historical_success", 0.8),
            features.get("complexity", 0.5)
        ]])

        if not self._is_trained:
            # Fallback to calibrated heuristic (v14.1 baseline)
            return self._heuristic_fallback(features)

        try:
            prediction = self.model.predict(X)[0]
            return float(max(0.05, min(0.99, round(prediction, 3))))
        except Exception as e:
            logger.error(f"[ConfidenceML] Prediction failed: {e}")
            return self._heuristic_fallback(features)

    def _heuristic_fallback(self, f: Dict[str, float]) -> float:
        """Calibrated v14.1 heuristic baseline."""
        score = 0.95
        score -= 0.05 * (f.get("depth", 1) - 1)
        score -= 0.02 * f.get("node_count", 1)
        score -= 0.03 * f.get("dependencies", 0)
        score += 0.1 * (f.get("historical_success", 0.8) - 0.8)
        score -= 0.1 * f.get("complexity", 0.5)
        return max(0.05, min(0.99, round(score, 3)))

    def train(self, X_train: List[List[float]], y_train: List[float]):
        """Online/Batch training for the regressor."""
        if not X_train or not y_train:
            return
        
        try:
            self.model.fit(X_train, y_train)
            self._is_trained = True
            os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
            joblib.dump(self.model, self.MODEL_PATH)
            logger.info("[ConfidenceML] Model trained and persisted.")
        except Exception as e:
            logger.error(f"[ConfidenceML] Training failed: {e}")

# Global instance
confidence_model = AdaptiveConfidenceModel()
