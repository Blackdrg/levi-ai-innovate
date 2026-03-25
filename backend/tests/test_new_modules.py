# pyright: reportMissingImports=false
"""
Tests for the new custom AI module features added in this iteration:
  - sd_engine:       new style presets, generate_image() alias
  - content_engine:  new content types, language param, batch_generate()
  - API routes:      /api/content/types, /api/content/tones, /api/image/styles
"""
import sys
import os
import pytest  # type: ignore  # Pyre2: not in its search roots but present at runtime
from unittest.mock import patch, MagicMock
from typing import Any

# ---------------------------------------------------------------------------
# Ensure the backend package is importable when running from project root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ===========================================================================
# sd_engine tests
# ===========================================================================

class TestSDEngineStyles:
    def test_new_styles_present(self):
        """New style presets should be registered in STYLE_PRESETS."""
        try:
            from backend.sd_engine import STYLE_PRESETS, get_available_styles  # type: ignore
        except ImportError:
            from sd_engine import STYLE_PRESETS, get_available_styles  # type: ignore

        new_styles = ["watercolor", "surrealism", "minimal_line_art"]
        for style in new_styles:
            assert style in STYLE_PRESETS, f"Style '{style}' missing from STYLE_PRESETS"

    def test_get_available_styles_includes_new(self):
        try:
            from backend.sd_engine import get_available_styles  # type: ignore
        except ImportError:
            from sd_engine import get_available_styles  # type: ignore

        styles = get_available_styles()
        assert "watercolor" in styles
        assert "surrealism" in styles
        assert "minimal_line_art" in styles
        # default should NOT be in the public list
        assert "default" not in styles

    def test_generate_image_alias_exists(self):
        """generate_image() public alias should be importable."""
        try:
            from backend.sd_engine import generate_image  # type: ignore
        except ImportError:
            from sd_engine import generate_image  # type: ignore
        assert callable(generate_image)

    def test_sd_model_id_env_override(self, monkeypatch):
        """SD_MODEL_ID env var should be read at module level."""
        monkeypatch.setenv("SD_MODEL_ID", "stabilityai/stable-diffusion-2-1")
        # Re-import to pick up the env var (module-level read)
        import importlib
        try:
            import backend.sd_engine as sd_engine  # type: ignore
        except ImportError:
            import sd_engine  # type: ignore
        importlib.reload(sd_engine)
        assert sd_engine._SD_MODEL_ID == "stabilityai/stable-diffusion-2-1"


# ===========================================================================
# content_engine tests
# ===========================================================================

class TestContentEngineNewTypes:
    def _import_engine(self):
        try:
            import backend.content_engine as ce  # type: ignore
        except ImportError:
            import content_engine as ce  # type: ignore
        return ce

    def test_new_content_types_registered(self):
        ce = self._import_engine()
        for t in ("poem", "newsletter", "readme"):
            assert t in ce.CONTENT_TEMPLATES, f"Content type '{t}' not in CONTENT_TEMPLATES"

    def test_get_available_types_includes_new(self):
        ce = self._import_engine()
        types = ce.get_available_types()
        for t in ("poem", "newsletter", "readme"):
            assert t in types

    def test_all_original_types_still_present(self):
        ce = self._import_engine()
        original = ["quote", "essay", "story", "script", "philosophy", "caption", "thread", "blog"]
        types = ce.get_available_types()
        for t in original:
            assert t in types, f"Original type '{t}' was removed unexpectedly"

    def test_generate_content_language_param_accepted(self):
        """generate_content should accept a language argument without error."""
        ce = self._import_engine()
        # Patch the internal Groq call so no real API call is made
        with patch.object(ce, "_generate_via_groq", return_value="Test content."):
            result = ce.generate_content("quote", "freedom", language="Spanish")
        assert result["language"] == "Spanish"
        assert result["streaming"] is False

    def test_generate_content_streaming_key_present(self):
        ce = self._import_engine()
        with patch.object(ce, "_generate_via_groq", return_value="Some content here."):
            result = ce.generate_content("quote", "resilience")
        assert "streaming" in result
        assert result["streaming"] is False

    def test_batch_generate(self):
        ce = self._import_engine()
        requests = [
            {"content_type": "quote", "topic": "resilience"},
            {"content_type": "poem", "topic": "the ocean", "tone": "calm"},
        ]
        with patch.object(ce, "_generate_via_groq", return_value="Generated text."):
            results = ce.batch_generate(requests)
        assert len(results) == 2
        assert results[0]["type"] == "quote"
        assert results[1]["type"] == "poem"
        assert results[1]["tone"] == "calm"

    def test_batch_generate_empty_list(self):
        ce = self._import_engine()
        results = ce.batch_generate([])
        assert results == []

    def test_generate_content_unknown_type_returns_error(self):
        ce = self._import_engine()
        result = ce.generate_content("nonexistent_type", "test")
        assert "error" in result

    def test_language_injected_into_non_english_prompt(self):
        """Non-English language should be appended to the system prompt."""
        ce = self._import_engine()
        captured = {}

        def mock_groq(*args, **kwargs):
            system_prompt = kwargs.get("system_prompt")
            if not system_prompt and args:
                system_prompt = args[0]
            captured["system"] = system_prompt
            return "Contenido en español."

        with patch.object(ce, "_generate_via_groq", side_effect=mock_groq):
            ce.generate_content("quote", "life", language="Spanish")

        assert "Spanish" in (captured.get("system") or ""), f"Language not found in system prompt: {captured.get('system')}"


# ===========================================================================
# API route tests (using FastAPI TestClient — no real services required)
# ===========================================================================

class TestAPIRoutes:
    client: Any  # Declared for Pyre2; set by the autouse fixture at runtime

    @pytest.fixture(autouse=True)
    def _setup_client(self):
        """
        Import TestClient and app with all DB / Redis dependencies mocked out.
        Skips gracefully if the app cannot be imported in the test environment.
        """
        try:
            from fastapi.testclient import TestClient  # type: ignore
            # Patch heavy startup dependencies
            with (
                patch("backend.db.get_db"),
                patch("backend.redis_client.HAS_REDIS", False),
            ):
                try:
                    from backend.main import app  # type: ignore
                except Exception:
                    from main import app  # type: ignore
                self.client = TestClient(app, raise_server_exceptions=False)
        except Exception as e:
            pytest.skip(f"Could not import app for route tests: {e}")

    def test_get_content_types(self):
        resp = self.client.get("/api/content/types")
        assert resp.status_code == 200
        data = resp.json()
        assert "types" in data
        assert "poem" in data["types"]
        assert "newsletter" in data["types"]
        assert "readme" in data["types"]

    def test_get_content_tones(self):
        resp = self.client.get("/api/content/tones")
        assert resp.status_code == 200
        data = resp.json()
        assert "tones" in data
        assert "inspiring" in data["tones"]

    def test_get_image_styles(self):
        resp = self.client.get("/api/image/styles")
        assert resp.status_code == 200
        data = resp.json()
        assert "styles" in data
        assert "watercolor" in data["styles"]
        assert "surrealism" in data["styles"]
        assert "minimal_line_art" in data["styles"]

    def test_content_generate_requires_auth(self):
        """POST /api/content/generate should return 401 without a token."""
        resp = self.client.post(
            "/api/content/generate",
            json={"content_type": "quote", "topic": "courage"},
        )
        assert resp.status_code in (401, 403)
