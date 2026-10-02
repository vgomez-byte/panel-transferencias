"""
Actualización automática del panel (la ejecuta el Programador de tareas de Windows).

Si la planilla oficial "Seguimiento Transferencias y TAG 2025 2.0" cambió -> la sube a Supabase.
Si no cambió, no hace nada. Todo queda registrado en logs\\actualizacion_auto.log
"""
import os
import sys
import json
import datetime
import subprocess

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

EXCEL_FILE = os.getenv(
    "RUTA_EXCEL_TRANSFERENCIAS",
    os.path.join(os.path.expanduser("~"), "OneDrive - Macal", "GERENCIA DVL - Documentos",
                 "Planillas", "Transferencias", "Seguimiento Transferencias y TAG 2025 2.0.xlsx"),
)
ESTADO = os.path.join(BASE_DIR, "logs", "estado_auto.json")
LOG = os.path.join(BASE_DIR, "logs", "actualizacion_auto.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")


def ejecutar_carga():
    python = sys.executable
    if python.lower().endswith("pythonw.exe"):
        python = python[:-5] + ".exe"  # python.exe, sin ventana gracias a CREATE_NO_WINDOW
    flags = 0x08000000 if os.name == "nt" else 0
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    r = subprocess.run(
        [python, os.path.join(BASE_DIR, "scripts", "cargar_csv_supabase.py")],
        cwd=BASE_DIR, capture_output=True, text=True, env=entorno,
        encoding="utf-8", errors="replace", creationflags=flags,
    )
    resumen = [l for l in r.stdout.splitlines() if "✔" not in l and l.strip() and "=====" not in l]
    if r.returncode != 2:
        for l in resumen[-6:]:
            log("   " + l)
    if r.returncode not in (0, 2):
        log("   ERROR: " + (r.stderr.strip().splitlines() or ["desconocido"])[-1])
    return r.returncode


def main():
    try:
        with open(ESTADO, encoding="utf-8") as f:
            estado = json.load(f)
    except Exception:
        estado = {}

    if not os.path.exists(EXCEL_FILE):
        log(f"No se encontró la planilla: {EXCEL_FILE}")
        return

    mtime = str(int(os.path.getmtime(EXCEL_FILE)))
    if estado.get("excel") == mtime:
        return  # sin cambios

    resultado = ejecutar_carga()
    if resultado == 0:
        log("Planilla modificada -> panel actualizado")
        estado["excel"] = mtime
    elif resultado == 2:
        # Bloqueada: se reintenta en la próxima revisión (avisa una sola vez por versión)
        if estado.get("aviso_excel") != mtime:
            log("Planilla con cambios, pero está bloqueada (abierta en Excel): se sube cuando se libere")
            estado["aviso_excel"] = mtime

    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR inesperado: {e}")
