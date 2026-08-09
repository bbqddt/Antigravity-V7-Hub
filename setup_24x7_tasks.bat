@echo off
REM Antigravity 7x24 守护进程计划任务创建脚本
REM 以管理员身份运行

set BASE=E:\享中.worktrees\agents-invisible-pelican
set PYTHON=%BASE%\.venv\Scripts\python.exe
set LOG_DIR=%BASE%\logs

echo ============================================
echo   Antigravity 7x24 Daemon Tasks Setup (schtasks)
echo ============================================

REM 删除旧任务
schtasks /Delete /TN "Antigravity_CloudDaemon_24x7" /F 2>nul
schtasks /Delete /TN "Antigravity_ResearchDaemon_24x7" /F 2>nul
schtasks /Delete /TN "Antigravity_24x7_HealthCheck" /F 2>nul

REM Cloud Daemon - 开机启动
schtasks /Create /TN "Antigravity_CloudDaemon_24x7" ^
    /TR "\"%PYTHON%\" \"%BASE%\cloud_daemon_24x7.py\"" ^
    /SC ONSTART /RU SYSTEM /RL HIGHEST /F

REM Cloud Daemon - 每日 03:00 重启
schtasks /Create /TN "Antigravity_CloudDaemon_24x7_DailyRestart" ^
    /TR "\"%PYTHON%\" \"%BASE%\cloud_daemon_24x7.py\"" ^
    /SC DAILY /ST 03:00 /RU SYSTEM /RL HIGHEST /F

REM Research Daemon - 开机启动
schtasks /Create /TN "Antigravity_ResearchDaemon_24x7" ^
    /TR "\"%PYTHON%\" \"%BASE%\research_daemon_24x7.py\"" ^
    /SC ONSTART /RU SYSTEM /RL HIGHEST /F

REM Research Daemon - 每日 03:00 重启
schtasks /Create /TN "Antigravity_ResearchDaemon_24x7_DailyRestart" ^
    /TR "\"%PYTHON%\" \"%BASE%\research_daemon_24x7.py\"" ^
    /SC DAILY /ST 03:00 /RU SYSTEM /RL HIGHEST /F

REM Health Check - 每小时
schtasks /Create /TN "Antigravity_24x7_HealthCheck" ^
    /TR "cmd /c echo [HEALTH] %%date%% %%time%% CloudDaemon=%%^tasklist /FI \"IMAGENAME eq python.exe\" /FO CSV 2^>nul ^| findstr /I cloud_daemon_24x7 ^|^| echo STOPPED%% ResearchDaemon=%%^tasklist /FI \"IMAGENAME eq python.exe\" /FO CSV 2^>nul ^| findstr /I research_daemon_24x7 ^|^| echo STOPPED%% >> \"%LOG_DIR%\health_24x7.log\" 2^>^&1" ^
    /SC HOURLY /ST 00:00 /RU SYSTEM /RL HIGHEST /F

echo.
echo ============================================
echo   SETUP COMPLETE!
echo ============================================
echo.
echo Created tasks:
echo   - Antigravity_CloudDaemon_24x7 (ONSTART)
echo   - Antigravity_CloudDaemon_24x7_DailyRestart (DAILY 03:00)
echo   - Antigravity_ResearchDaemon_24x7 (ONSTART)
echo   - Antigravity_ResearchDaemon_24x7_DailyRestart (DAILY 03:00)
echo   - Antigravity_24x7_HealthCheck (HOURLY)
echo.
echo Verify: schtasks /Query /TN "Antigravity_*" /FO LIST /V
echo Start now: schtasks /Run /TN "Antigravity_CloudDaemon_24x7"
echo Logs: %LOG_DIR%\cloud_daemon_*.log, %LOG_DIR%\research_daemon_*.log
pause