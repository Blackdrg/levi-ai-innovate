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
    @pytest.fixture(autouse=True)
    def _setup_mocks(self):
        """Mock Firestore and internal learning components."""
        self.user_id = "user_123"
        self.mock_memory_data = {
            "user_id": self.user_id,
            "structured_memory": {"entities": {"interests": ["stoicism"], "goals": [], "facts": []}}
        }

    def test_extract_memory_insights_mock(self):
        from backend.services.learning.logic import _extract_memory_insights

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
        from backend.services.learning.logic import update_memory_graph
        
        extract_mock_val = {
            "entities": {
                "interests": ["meditation"],
                "goals": ["run a marathon"],
                "facts": ["Wakes up early"]
            }
        }

        # Mock Firestore db call
        with patch("backend.learning.firestore_db") as mock_firestore:
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = self.mock_memory_data
            mock_firestore.collection().document().get.return_value = mock_doc
            
            with patch("backend.learning._extract_memory_insights", return_value=extract_mock_val):
                update_memory_graph(self.user_id, "I want to run a marathon and medidate.")

            # Verify firestore update was called
            mock_firestore.collection().document().update.assert_called()

    def test_system_prompt_injection(self):
        from backend.services.learning.logic import UserPreferenceModel

        # Mock Firestore and Redis for get_profile
        with patch("backend.learning.firestore_db") as mock_firestore:
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = self.mock_memory_data
            mock_firestore.collection().document().get.return_value = mock_doc
            mock_firestore.collection().where().order_by().limit().get.return_value = [] # no rated samples

            model = UserPreferenceModel(user_id=self.user_id)
            
            # Explicitly set structured memory in mock profile to test injection
            mock_profile = {
                "preferred_moods": ["philosophical"],
                "response_style": "concise",
                "top_topics": ["Machine Learning", "Stoicism"],
                "avg_rating": 4.5,
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
