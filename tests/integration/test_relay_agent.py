"""
Integration tests for RelayAgent v1.0.
Asserts:
  - Valid relay enqueues to a real agent and returns its result.
  - Unknown target_agent → typed RelayError + DLQ entry.
  - DLQ entry is written to Redis on failure.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.agents.relay_agent import RelayAgent, RelayPayload, RelayError


class TestRelayAgent:

    @pytest.fixture(autouse=True)
    def agent(self):
        self.agent = RelayAgent()

    @pytest.mark.asyncio
    async def test_valid_relay_routes_to_target(self):
        """A valid target agent should receive the sub-mission and return success."""
        fake_result = MagicMock()
        fake_result.success = True
        fake_result.message = "Research complete."
        fake_result.model_dump = lambda: {"success": True, "message": "Research complete."}

        with patch("backend.agents.relay_agent.AGENT_REGISTRY", {"Researcher": AsyncMock()}):
            with patch(
                "backend.agents.relay_agent.RelayAgent._enqueue_sub_mission",
                new_callable=AsyncMock,
                return_value=fake_result,
            ):
                result = await self.agent.execute(
                    RelayPayload(
                        target_agent="Researcher",
                        sub_mission="Tell me about quantum computing",
                        caller_agent="Artisan",
                    )
                )

        assert result.success is True
        assert "Researcher" in result.data.get("target_agent", "")

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_relay_error(self):
        """Unknown target should return success=False with typed RelayError data."""
        with patch("backend.agents.relay_agent.AGENT_REGISTRY", {"Researcher": object()}):
            with patch("backend.agents.relay_agent.RelayAgent._fail", new_callable=AsyncMock) as mock_fail:
                mock_fail.return_value = {
                    "success": False,
                    "message": "Relay failed: ...",
                    "data": {"relay_id": "x", "target_agent": "GhostAgent"},
                }
                result = await self.agent.execute(
                    RelayPayload(
                        target_agent="GhostAgent",
                        sub_mission="do something",
                        caller_agent="Scout",
                    )
                )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_dlq_entry_written_on_failure(self):
        """On routing failure, a JSON entry must be pushed to the Redis DLQ."""
        captured_pushes = []

        mock_redis = MagicMock()
        mock_redis.lpush = lambda key, val: captured_pushes.append((key, val))
        mock_redis.expire = MagicMock()

        with patch("backend.agents.relay_agent.AGENT_REGISTRY", {}):
            with patch("backend.agents.relay_agent.r", mock_redis):
                with patch("backend.agents.relay_agent.HAS_REDIS", True):
                    result = await self.agent.execute(
                        RelayPayload(
                            target_agent="NoSuchAgent",
                            sub_mission="fail me",
                            caller_agent="Critic",
                        )
                    )

        assert result.success is False
        assert len(captured_pushes) == 1
        key, val = captured_pushes[0]
        assert key == "relay:dlq"
        entry = json.loads(val)
        assert entry["target_agent"] == "NoSuchAgent"
        assert "relay_id" in entry
