# Script de test pour vérifier que le CLI fonctionne
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
$env:PYTHONPATH = "$scriptPath\src;$env:PYTHONPATH"

Write-Host "Test de l'import du module..."
& C:\Python313\python.exe -c "import simulation_service; print('✅ Module simulation_service importé avec succès')"

Write-Host "`nTest de la commande CLI --help..."
& C:\Python313\python.exe -m simulation_service.cli --help



