# pyright: reportMissingImports=false
"""
Tests for the Structured Memory Graph features added in learning.py:
  - _extract_memory_insights (using mocked Groq)
  - update_memory_graph
  - UserPreferenceModel.build_system_prompt incorporating structured_memory
"""
import sys
import os
import pytest  # type: ignore
from unittest.mock import patch, MagicMock
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

class TestMemoryGraph:
    db: Any
    mock_memory: Any

    @pytest.fixture(autouse=True)
    def _setup_db(self):
        """Mock out get_db / Session."""
        self.db = MagicMock()
        try:
             from backend.models import UserMemory  # type: ignore
        except ImportError:
             from models import UserMemory  # type: ignore
             
        self.mock_memory = UserMemory(
            user_id=1,
            structured_memory={"entities": {"interests": ["stoicism"], "goals": [], "facts": []}}
        )
        self.db.query().filter().first.return_value = self.mock_memory

    def test_extract_memory_insights_mock(self):
        try:
            from backend.learning import _extract_memory_insights  # type: ignore
        except ImportError:
            from learning import _extract_memory_insights  # type: ignore

        # Mock Groq response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"entities": {"interests": ["coffee", "AI"], "goals": ["launch app"], "facts": ["Lives in SF"]}}'

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_groq.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response

            with patch.dict(os.environ, {"GROQ_API_KEY": "fake_key"}):
                 res = _extract_memory_insights("I want to launch my AI app soon over coffee in SF.")

        assert "entities" in res
        assert "interests" in res["entities"]
        assert "coffee" in res["entities"]["interests"]

    def test_update_memory_graph(self):
        try:
            from backend.learning import update_memory_graph  # type: ignore
        except ImportError:
            from learning import update_memory_graph  # type: ignore

        extract_mock_val = {
            "entities": {
                "interests": ["meditation"],
                "goals": ["run a marathon"],
                "facts": ["Wakes up early"]
            }
        }

        with patch("backend.learning._extract_memory_insights", return_value=extract_mock_val):
            update_memory_graph(1, "I want to run a marathon and medidate.", self.db)

        # Verify merge logic was applied: "stoicism" was existing, "meditation" added
        current_mem = self.mock_memory.structured_memory
        assert "entities" in current_mem
        entities = current_mem["entities"]
        assert "stoicism" in entities["interests"]
        assert "meditation" in entities["interests"]
        assert "run a marathon" in entities["goals"]

    def test_system_prompt_injection(self):
        try:
            from backend.learning import UserPreferenceModel  # type: ignore
        except ImportError:
            from learning import UserPreferenceModel  # type: ignore

        # Force get_profile to mock load profile so we can explicitly test prompt building
        model = UserPreferenceModel(self.db, user_id=1)
        mock_profile = {
            "preferred_moods": ["philosophical"],
            "response_style": "concise",
            "top_topics": [],
            "avg_rating": 4.0,
            "structured_memory": {
                "entities": {
                    "interests": ["Machine learning", "Quantum mechanics"],
                    "goals": ["Travel to space"]
                }
            }
        }
        model._profile = mock_profile

        prompt = model.build_system_prompt("Answer wisely.", "stoic")
        
        # Verify both items were injected into prompt
        assert "User interests: Machine learning, Quantum mechanics" in prompt
        assert "User goals: Travel to space" in prompt
