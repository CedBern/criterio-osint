@echo off
title NEXOME OSINT Terminal
color 0A
echo.
echo  ============================================
echo   NEXOME OSINT TERMINAL - DEMARRAGE
echo  ============================================
echo.

cd /d "%~dp0"

echo [*] Installation des dependances...
pip install -r requirements.txt --quiet

echo [*] Lancement du serveur FastAPI sur http://127.0.0.1:8080
echo [*] Appuyez sur Ctrl+C pour arreter.
echo.
echo [!] RAPPEL: Lancez 'tor' dans un autre terminal pour activer l'anonymat.
echo.

python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload
pause
