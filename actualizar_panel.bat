@echo off
REM Sube la planilla oficial (GERENCIA DVL, hoja BBDD) al panel de transferencias.
cd /d "%~dp0"
call venv\Scripts\activate
python scripts\cargar_csv_supabase.py
pause
