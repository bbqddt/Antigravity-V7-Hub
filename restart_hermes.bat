@echo off
echo Killing old hermes...
wmic process where "commandline like '%%cloud_hermes.py%%'" call terminate
timeout /t 2 /nobreak >nul
echo Starting new hermes...
start "" "e:\享中\.venv\Scripts\python.exe" "e:\享中\skills\cloud_hermes.py"
echo Done.
