@echo off
setlocal
cd /d "%~dp0"

:: 1. Configuration environnement
:: On pointe vers le python portable et on ajoute le dossier bin au PATH
set "PY_EXE=%~dp0python_env\python.exe"
set "PATH=%~dp0app\bin;%PATH%"
set "PYTHONDONTWRITEBYTECODE=1"

:: 2. Lancement
:: On lance directement le script. Plus besoin de redirections > vers error.log ici,
:: car PathManager et logging.basicConfig s'en occupent en interne.
"%PY_EXE%" -c "import sys; sys.path.insert(0, 'app'); import main; main.main()"

:: 3. Analyse post-exécution
:: Si le programme crash avant d'initialiser le logging Python
if %errorlevel% neq 0 (
    echo [ERREUR] Le programme s'est arrete brutalement.
    pause
)
