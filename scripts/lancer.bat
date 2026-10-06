@echo off
rem Lance une edition du Veilleur. Utilise par le Planificateur de taches Windows.
rem Les logs sont dans le dossier logs du projet.
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m veille.main
