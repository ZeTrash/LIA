@echo off
REM Script pour démarrer le serveur de simulation
cd /d "%~dp0"
set PYTHONPATH=%~dp0src;%PYTHONPATH%
C:\Python313\python.exe -m simulation_service.main



