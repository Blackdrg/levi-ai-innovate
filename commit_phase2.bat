@echo off
echo ============================================================
echo  LEVI AI - Phase 2 Commit: Test Fix + Chat Enhancements
echo ============================================================
cd /d "C:\Users\mehta\Desktop\New folder\LEVI-AI"

git add tests/test_orchestrator.py
git add backend/services/chat/router.py
git add frontend/js/chat.js

git commit -m "feat(chat): route badge, fix Dict import, test fix

- tests: fix check_allowance patch target to engine namespace (42/42 pass)
- chat router: add missing Dict, Any imports (prevented server startup)
- chat.js: add _buildRouteBadge() — color-coded engine indicator
  Green=Local (zero API), Yellow=Tool (agent), Red=AI (Groq LLM)
- chat.js: add loadChatHistory + displayWelcomeMessage stubs
- Frontend now shows intent + engine route on every LEVI response"

git push origin master:main
echo.
echo Done! All changes pushed.
pause
