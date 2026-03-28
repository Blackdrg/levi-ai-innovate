# pyright: reportMissingImports=false
import pytest
from unittest.mock import patch, AsyncMock
from backend.generation import generate_council_response

@pytest.mark.asyncio
async def test_council_selection_logic():
    """Verify that the council selects the most 'profound' response."""
    # Mock responses: 1 simple, 1 cliché, 1 deep/long
    mock_responses = [
        "It's just life.", # Simple
        "The tapestry of existence is grand.", # Cliché
        "Consider why the shadow is as real as the light that casts it? What is the weight of an unasked question?" # Deep/Long
    ]
    
    with patch('backend.generation._async_call_groq_api', side_effect=mock_responses):
        winner = await generate_council_response("test prompt", history=[], mood="philosophical")
        # should pick the 3rd one based on scoring logic
        assert "?" in winner
        assert len(winner) > 50
        assert "tapestry" not in winner

@pytest.mark.asyncio
async def test_council_fallback_on_silence():
    """Verify fallback if all models fail."""
    with patch('backend.generation._async_call_groq_api', return_value=None):
        winner = await generate_council_response("test prompt")
        assert "council is silent" in winner.lower()

@pytest.mark.asyncio
async def test_council_partial_failure():
    """Verify council still works if 1 model fails."""
    mock_responses = [None, "Success from model 2", None]
    with patch('backend.generation._async_call_groq_api', side_effect=mock_responses):
        winner = await generate_council_response("test prompt")
        assert winner == "Success from model 2"
