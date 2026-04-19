@echo off
title LEVI-AI 3-Node Cluster Launcher
echo Starting Sovereign DCN Cluster (3 Nodes)...

:: Node 0 (Leader/Primary)
echo Starting HAL-0 (Port 8001)...
set NODE_ID=HAL-0-PRIMARY
set PORT=8001
start cmd /k "title HAL-0 PRIMARY && cd /d backend\levi_runtime && cargo run --release"

:: Node 1 (Follower)
echo Starting HAL-1 (Port 8002)...
set NODE_ID=HAL-1-FOLLOWER
set PORT=8002
start cmd /k "title HAL-1 FOLLOWER && cd /d backend\levi_runtime && cargo run --release"

:: Node 2 (Follower)
echo Starting HAL-2 (Port 8003)...
set NODE_ID=HAL-2-FOLLOWER
set PORT=8003
start cmd /k "title HAL-2 FOLLOWER && cd /d backend\levi_runtime && cargo run --release"

echo Cluster is initializing. Peer discovery in progress...
pause
