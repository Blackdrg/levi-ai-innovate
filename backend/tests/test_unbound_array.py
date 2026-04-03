import pytest
import asyncio
from unittest.mock import MagicMock, patch
from backend.services.learning.scraper import scraper
from backend.services.learning.unbound import unbound_engine

@pytest.mark.asyncio
async def test_scraper_arxiv_mock():
    """Verifies that the Arxiv scraper can be called (mocked)."""
    with patch("arxiv.Client.results") as mock_results:
        # Mock a result object
        mock_result = MagicMock()
        mock_result.title = "Sovereign AGI"
        mock_result.download_pdf.return_value = "dummy.pdf"
        mock_result.entry_id = "123.456"
        mock_result.published.isoformat.return_value = "2024-01-01"
        mock_result.authors = [MagicMock(name="Zenon")]
        mock_result.summary = "A paper about sovereignty."
        
        mock_results.return_value = [mock_result]
        
        with patch.object(scraper, "_extract_text_from_pdf", return_value="Wisdom content."):
            with patch("os.remove"):
                results = await scraper.scrape_arxiv(["Sovereign"], max_results=1)
                assert len(results) == 1
                assert results[0]["title"] == "Sovereign AGI"
                assert results[0]["content"] == "Wisdom content."

@pytest.mark.asyncio
async def test_unbound_filtering():
    """Verifies the Unbound Engine filtering logic."""
    with patch.object(unbound_engine, "calculate_wisdom_density", return_value=0.9):
        score = await unbound_engine.calculate_wisdom_density("Test", "High depth content.")
        assert score >= 0.8

@pytest.mark.asyncio
async def test_dataset_generation():
    """Verifies JSONL generation format."""
    content = "The soul is dyed by its thoughts."
    pair = unbound_engine.generate_instruction_pair(content)
    assert "messages" in pair
    assert len(pair["messages"]) == 3
    assert "role" in pair["messages"][0]
    assert "LEVI" in pair["messages"][0]["content"]

if __name__ == "__main__":
    asyncio.run(test_scraper_arxiv_mock())
    print("Tests passed locally.")
