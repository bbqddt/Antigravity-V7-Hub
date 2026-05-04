@echo off
CHCP 65001
title Antigravity Omega Control Center
echo [Antigravity] Starting Observation Tower (Port 8501)...
start /min streamlit run e:\享中\app.py --server.port 8501 --server.headless true

echo [Antigravity] Starting Sentinel V2...
start /min python e:\享中\skills\sentinel.py

echo [Antigravity] Starting Evolution Engine...
start /min python e:\享中\v7_evolved_engine.py

echo [Antigravity] All Systems Go. 049 Reality Locked.
pause
