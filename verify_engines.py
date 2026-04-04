import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core.v8.engine_registry import EngineRegistry
from backend.core.v8.engines.deterministic_engine import DeterministicEngine
from backend.core.v8.engines.code_engine import CodeEngine

async def test_engines():
    print("--- Testing Deterministic Engine ---")
    de = DeterministicEngine()
    math_res = de.run("what is 15 * 1.5?")
    print(f"Math Result: {math_res}")
    assert math_res["success"] == True
    assert math_res["data"] == 22.5
    
    print("\n--- Testing Code Engine ---")
    ce = CodeEngine()
    code = "x = 10\ny = 20\nresult = x + y"
    code_res = ce.run(code)
    print(f"Code Result: {code_res}")
    assert code_res["success"] == True
    assert code_res["data"]["result"] == 30
    
    print("\n--- Testing Engine Registry ---")
    registry = EngineRegistry()
    registry.register("deterministic", de)
    registry.register("code", ce)
    
    reg_math = await registry.execute("deterministic", "solve 2**8")
    print(f"Registry Math Result: {reg_math}")
    assert reg_math["success"] == True
    assert reg_math["data"] == 256
    
    print("\nAll engine tests passed!")

if __name__ == "__main__":
    asyncio.run(test_engines())
