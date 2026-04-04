import asyncio
import pytest
from backend.core.v8.brain import LeviBrainCoreController
from backend.core.v8.engines.deterministic_engine import DeterministicEngine
from backend.core.v8.engines.data_engine import DataEngine
from backend.core.v8.evolution_engine import EvolutionEngine

@pytest.mark.asyncio
async def test_deterministic_engine():
    engine = DeterministicEngine()
    result = engine.run("What is 15 * 5 + 10?")
    assert result["success"] is True
    assert result["data"] == 85

@pytest.mark.asyncio
async def test_data_engine():
    engine = DataEngine()
    # Test with numeric list
    result = engine.run({"data": [5, 2, 9, 1]})
    assert result["success"] is True
    assert result["data"]["sorted"] == [1, 2, 5, 9]
    assert result["data"]["sum"] == 17
    
    # Test with string list
    result = engine.run(["c", "a", "b"])
    assert result["success"] is True
    assert result["data"]["sorted"] == ["a", "b", "c"]

@pytest.mark.asyncio
async def test_evolution_engine():
    engine = EvolutionEngine()
    task = "test task evolution"
    result = "deterministic result 123"
    
    # Clean output if exists for testing
    if task in engine.rules:
        del engine.rules[task]
    
    # Learn 3 times to promote
    engine.learn(task, result)
    assert engine.apply(task) is None
    
    engine.learn(task, result)
    assert engine.apply(task) is None
    
    engine.learn(task, result)
    # Now it should be promoted
    assert engine.apply(task) == result
    assert engine.rules[engine._normalize(task)]["promoted"] is True

@pytest.mark.asyncio
async def test_brain_evolution_shortcut():
    brain = LeviBrainCoreController()
    task = "Calculate the circumference of 5"
    response = "The circumference is 31.41..."
    
    # Manually inject a promoted rule
    brain.evolution_engine.learn(task, response)
    brain.evolution_engine.learn(task, response)
    brain.evolution_engine.learn(task, response)
    
    # Run brain
    res = await brain.run(task, "test_user", "test_session")
    assert res["decision"] == "EVOLUTION"
    assert res["response"] == response

if __name__ == "__main__":
    asyncio.run(test_deterministic_engine())
    asyncio.run(test_data_engine())
    asyncio.run(test_evolution_engine())
    asyncio.run(test_brain_evolution_shortcut())
    print("All tests passed!")
