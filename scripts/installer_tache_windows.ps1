# Crée la tâche planifiée Windows qui lance Le Veilleur chaque matin.
# À exécuter une seule fois, dans PowerShell, depuis le dossier du projet :
#   powershell -ExecutionPolicy Bypass -File scripts\installer_tache_windows.ps1
#
# N'utiliser que si GitHub Actions n'est pas activé : deux lanceurs enverraient
# deux journaux et tiendraient deux mémoires différentes.

$projet = Split-Path -Parent $PSScriptRoot
$action = New-ScheduledTaskAction -Execute "$projet\scripts\lancer.bat" -WorkingDirectory $projet
$declencheur = New-ScheduledTaskTrigger -Daily -At 7:00

# StartWhenAvailable : si le PC était éteint à 7 h, l'édition part dès l'allumage.
# WakeToRun : sort le PC de la veille. Il ne peut pas l'allumer s'il est complètement arrêté.
$reglages = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

Register-ScheduledTask -TaskName "Le Veilleur" -Action $action -Trigger $declencheur `
    -Settings $reglages -Description "Journal de veille cyber quotidien" -Force

Write-Host "Tâche créée. Pour tester tout de suite : Start-ScheduledTask -TaskName 'Le Veilleur'"
