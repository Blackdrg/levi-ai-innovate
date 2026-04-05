@echo off
echo ============================================
echo  LEVI AI Brain - Orchestrator v1.0 Commit
echo ============================================
cd /d "D:\LEVI-AI"

echo.
echo [1/3] Staging files...
git add backend/services/orchestrator/engine.py
git add backend/services/orchestrator/planner.py
git add backend/services/orchestrator/local_engine.py
git add backend/services/orchestrator/memory_manager.py
git add backend/services/orchestrator/router.py
git add backend/services/orchestrator/orchestrator_types.py
git add backend/services/orchestrator/__init__.py
git add tests/test_orchestrator.py

echo.
echo [2/3] Committing...
git commit -m "feat(brain): implement LeviOrchestrator v1.0

- Add LeviOrchestrator class with clean handle() interface
- Implement 8-stage pipeline: sanitize/memory/intent/decide/execute/validate/store/output
- Add 3-route decision engine: LOCAL (greeting/simple_query), TOOL (image/code/search), API (complex)
- Add local_engine.py: zero-API handler for greetings and FAQ (50%%+ cost reduction)
- Fix store_memory sync bug: now async def with asyncio.to_thread
- Fix router double-wrap bug: returns full result dict
- Add BackgroundTasks passthrough to router
- Expand intent taxonomy: greeting, simple_query, tool_request, unknown
- Add validate_response() with 3-tier fallback chain (never returns empty)
- Add DecisionLog structured logging at every routing decision
- Add 30-test suite covering all 5 required execution paths"

echo.
echo [3/3] Pushing to GitHub...
git push origin main

echo.
echo ============================================
echo  Done! Check output above for any errors.
echo ============================================
pause
