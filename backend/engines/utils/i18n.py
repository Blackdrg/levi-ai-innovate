import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SovereignI18n:
    """
    Handles multi-language prompt templates and UI strings for Global-Ready engines.
    """
    
    _PROMPTS = {
        "en": {
            "system_brain": "You are LEVI-AI Sovereign OS, a high-fidelity autonomous intelligence.",
            "intent_classification": "Analyze the query and determine the logical engine route: RAG, KNOWLEDGE, REASONING, or CHAT.",
            "rag_synthesis": "Synthesize a response based on the following retrieved context: {context}",
            "error_fallback": "System anomaly detected. Causal link severed."
        },
        "es": {
            "system_brain": "Eres LEVI-AI Sovereign OS, una inteligencia autónoma de alta fidelidad.",
            "intent_classification": "Analiza la consulta y determina la ruta lógica: RAG, CONOCIMIENTO, RAZONAMIENTO o CHAT.",
            "rag_synthesis": "Sintetiza una respuesta basada en el siguiente contexto: {context}",
            "error_fallback": "Anomalía del sistema detectada. Vínculo causal roto."
        },
        "fr": {
            "system_brain": "Vous êtes LEVI-AI Sovereign OS, une intelligence autonome haute fidélité.",
            "intent_classification": "Analysez la requête et déterminez l'itinéraire logique : RAG, CONNAISSANCE, RAISONNEMENT ou CHAT.",
            "rag_synthesis": "Synthétisez une réponse basée sur le contexte suivant : {context}",
            "error_fallback": "Anomalie système détectée. Lien causal rompu."
        }
    }

    @classmethod
    def get_prompt(cls, key: str, lang: str = "en", **kwargs) -> str:
        """Retrieves and formats a prompt template for a specific language."""
        lang_bundle = cls._PROMPTS.get(lang, cls._PROMPTS["en"])
        template = lang_bundle.get(key, cls._PROMPTS["en"].get(key, ""))
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing key in i18n formatting for {key}: {e}")
            return template
