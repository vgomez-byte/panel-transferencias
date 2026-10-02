@echo off
REM Abre el panel de transferencias en el navegador (http://localhost:8501).
cd /d "%~dp0"
call venv\Scripts\activate
streamlit run src\panel_transferencias.py
pause
