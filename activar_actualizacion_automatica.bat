@echo off
REM Crea una tarea de Windows que revisa cada 10 minutos si cambio la planilla y actualiza el panel.
cd /d "%~dp0"
schtasks /Create /F /TN "Panel Transferencias - Actualizacion" /SC MINUTE /MO 10 /TR "\"%~dp0venv\Scripts\pythonw.exe\" \"%~dp0scripts\auto_actualizar.py\""
if errorlevel 1 (echo No se pudo crear la tarea.) else (echo Listo: el panel se actualizara solo cada 10 minutos mientras el PC este encendido.)
"%~dp0venv\Scripts\pythonw.exe" "%~dp0scripts\auto_actualizar.py"
echo Primera revision ejecutada. Revise logs\actualizacion_auto.log
pause
