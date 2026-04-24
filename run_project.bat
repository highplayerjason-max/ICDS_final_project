@echo off
cd /d "%~dp0"
start "ICDS Chat Server" cmd /k python server.py
timeout /t 2 /nobreak > nul
start "ICDS Chat Client" cmd /k python gui_client.py
