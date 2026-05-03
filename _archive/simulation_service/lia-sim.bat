@echo off
REM Wrapper pour la commande lia-sim
cd /d "%~dp0"
set PYTHONPATH=%~dp0src;%PYTHONPATH%
C:\Python313\python.exe -m simulation_service.cli %*



