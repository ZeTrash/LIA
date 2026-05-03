# Wrapper PowerShell pour la commande lia-sim
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
$env:PYTHONPATH = "$scriptPath\src;$env:PYTHONPATH"
& C:\Python313\python.exe -m simulation_service.cli $args



