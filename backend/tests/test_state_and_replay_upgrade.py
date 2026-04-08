import importlib
import json
import sys
import types


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def rpush(self, key, value):
        self.store.setdefault(key, [])
        self.store[key].append(value)
        return len(self.store[key])


def _load_modules():
    fake_redis = _FakeRedis()
    sys.modules["backend.core.engine"] = types.SimpleNamespace(run_orchestrator=None, LeviOrchestrator=None)
    sys.modules["backend.db.redis"] = types.SimpleNamespace(r=fake_redis, HAS_REDIS=True)
    execution_state = importlib.reload(importlib.import_module("backend.core.execution_state"))
    replay_engine = importlib.reload(importlib.import_module("backend.core.replay_engine"))
    return fake_redis, execution_state, replay_engine


def test_execution_state_claims_idempotency_and_stores_replay():
    fake_redis, execution_state, _ = _load_modules()

    sm = execution_state.CentralExecutionState("mission-1", trace_id="mission-1", user_id="user-1")
    sm.initialize()
    assert execution_state.CentralExecutionState.claim_idempotency("user-1", "key-1", "mission-1") is True
    assert execution_state.CentralExecutionState.claim_idempotency("user-1", "key-1", "mission-2") is False
    assert fake_redis.get("mission:key-1:lock") == "mission-1"

    sm.attach_replay_payload({"user_input": "hello", "reasoning": {"confidence": 0.9}})
    state = json.loads(fake_redis.get("mission:state:mission-1"))
    assert state["replay"]["user_input"] == "hello"
    assert state["replay"]["reasoning"]["confidence"] == 0.9


def test_replay_engine_returns_deterministic_payload():
    fake_redis, execution_state, replay_engine = _load_modules()

    sm = execution_state.CentralExecutionState("mission-2", trace_id="mission-2", user_id="user-2")
    sm.initialize()
    sm.attach_replay_payload(
        {
            "user_input": "research batteries",
            "reasoning": {"strategy": {"safe_mode": False}},
            "task_graph": [{"node_id": "t1", "agent": "search_agent"}],
        }
    )
    fake_redis.setex(
        "trace:mission-2",
        3600,
        json.dumps(
            {
                "request_id": "mission-2",
                "steps": [
                    {
                        "step": "node_complete",
                        "data": {"node_id": "t1", "agent": "search_agent", "latency_ms": 42},
                    }
                ],
            }
        ),
    )

    result = __import__("asyncio").run(replay_engine.ReplayEngine.replay_mission("mission-2"))
    assert result["deterministic"] is True
    assert result["input"] == "research batteries"
    assert result["graph"][0]["node_id"] == "t1"


def test_replay_engine_validates_memory_state_checksums():
    _, _, replay_engine = _load_modules()

    outcome = replay_engine.ReplayEngine.validate_replay_consistency(
        {"memory_events": [{"id": "m1", "version": 1}]},
        {"memory_events": [{"id": "m1", "version": 1}]},
    )
    assert outcome["deterministic"] is True
