@echo off
setlocal enabledelayedexpansion

echo [Sovereign Refactor] Phase 1: Preparation
mkdir frontend_legacy
mkdir backend_new
mkdir backend_new\api
mkdir backend_new\core
mkdir backend_new\engines
mkdir backend_new\engines\chat
mkdir backend_new\engines\memory
mkdir backend_new\engines\document
mkdir backend_new\engines\search
mkdir backend_new\models
mkdir backend_new\services
mkdir backend_new\utils
mkdir backend_new\config
mkdir backend_new\data
mkdir backend_new\tests
mkdir shared
mkdir configs
mkdir docs

echo [Sovereign Refactor] Phase 2: Frontend Migration
xcopy /E /I /Y frontend frontend_legacy
xcopy /E /I /Y frontend_react\* frontend\
rd /S /Q frontend_react

echo [Sovereign Refactor] Phase 3: Backend Initial Migration
copy backend\main.py backend_new\api\
copy backend\config.py backend_new\config\
xcopy /E /I /Y backend\api backend_new\api\
xcopy /E /I /Y backend\services backend_new\core\
xcopy /E /I /Y backend\utils backend_new\utils\
xcopy /E /I /Y backend\data backend_new\data\
xcopy /E /I /Y backend\tests backend_new\tests\

echo [Sovereign Refactor] Phase 4: Engine Extraction
move backend_new\core\services\orchestrator\memory_manager.py backend_new\engines\memory\
move backend_new\core\services\orchestrator\fusion_engine.py backend_new\engines\chat\
move backend\generation.py backend_new\engines\chat\
move backend\embeddings.py backend_new\engines\document\
move backend\image_gen.py backend_new\services\
move backend\video_gen.py backend_new\services\
move backend\payments.py backend_new\services\
move backend\email_service.py backend_new\services\
move backend\models.py backend_new\models\
move backend\orchestrator_types.py backend_new\models\

echo [Sovereign Refactor] Phase 5: Root Cleanup
move *.md docs\
move docker-compose.yml configs\
move nginx.conf configs\

echo [Sovereign Refactor] Completed Initial Restructuring.
echo [WARNING] Manual import updates required.
