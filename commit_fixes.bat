@echo off
echo Committing orchestrator stability fixes...
cd /d "C:\Users\mehta\Desktop\New folder\LEVI-AI"
git add backend/services/orchestrator/planner.py backend/services/orchestrator/memory_manager.py
git commit -m "fix(brain): harden detect_intent and prune_task against LLM/async failures

- detect_intent: wrap LLM stage in try/except, always returns valid IntentResult
- memory_manager: guard asyncio.create_task(prune_old_facts) with RuntimeError catch"
git push origin master:main
echo Done!
pause
