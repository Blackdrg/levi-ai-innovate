import asyncio
import sys
import os
import json

# Add backend and project root to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend"))
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_path)
sys.path.append(project_root)

from engines.brain.orchestrator import BrainOrchestrator

async def test_brain():
    print("Initializing Brain Orchestrator...")
    brain = BrainOrchestrator()
    
    test_queries = [
        "Hello, how are you?",  # Chat
        "Explain the theory of relativity.",  # Knowledge
        "Extract the main topic from the uploaded document.", # RAG/Document
        "Calculate the logical deduction of a train leaving at 5pm." # Reasoning
    ]

    for query in test_queries:
        print(f"\n--- Testing Query: '{query}' ---")
        state = await brain.process_request("test_user_1", query)
        
        print(f"Detected Intent: {state.intent}")
        print("Execution Plan:")
        print(json.dumps(state.plan, indent=2))
        print(f"Final Response: {state.final_response}")
        print(f"Error: {state.error}")

if __name__ == "__main__":
    asyncio.run(test_brain())
