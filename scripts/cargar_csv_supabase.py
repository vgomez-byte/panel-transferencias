"""
Carga la planilla "Seguimiento Transferencias y TAG" a Supabase.

Uso:
    python scripts/cargar_csv_supabase.py            -> carga real
    python scripts/cargar_csv_supabase.py --dry-run  -> solo revisa el archivo, no sube nada

Origen de los datos (en este orden):
  1) La planilla oficial en GERENCIA DVL (hoja BBDD), la misma que usa el chat.
     Se puede cambiar con la variable RUTA_EXCEL_TRANSFERENCIAS en el .env
  2) Si no se encuentra, el archivo .csv o .xlsx más reciente de la carpeta datos\\.
La carga es segura: primero inserta la versión nueva completa y solo después
borra la anterior. Si algo falla, se deshace lo insertado y el panel sigue
mostrando la versión anterior.
"""
import os
import sys
import glob
import time
import shutil
import tempfile
import warnings
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from config import TABLA, cliente_escritura  # noqa: E402

DRY_RUN = "--dry-run" in sys.argv
# Aviso inofensivo de openpyxl sobre validaciones de datos de la planilla
warnings.filterwarnings("ignore", message="Data Validation extension is not supported")

EXCEL_OFICIAL = os.getenv(
    "RUTA_EXCEL_TRANSFERENCIAS",
    os.path.join(
        os.path.expanduser("~"), "OneDrive - Macal", "GERENCIA DVL - Documentos",
        "Planillas", "Transferencias", "Seguimiento Transferencias y TAG 2025 2.0.xlsx",
    ),
)
HOJA_EXCEL = "BBDD"
TAMANO_LOTE = 500

# Correcciones de textos mal escritos en la planilla
CORRECCIONES_ESTADO = {
    "EN ESPERA DE TRANSFERNCIA": "EN ESPERA DE TRANSFERENCIA",
}


# ======================================================
# LECTURA DEL ARCHIVO
# ======================================================
def buscar_archivo():
    if os.path.exists(EXCEL_OFICIAL):
        return EXCEL_OFICIAL
    print(f"No se encontró la planilla oficial: {EXCEL_OFICIAL}")
    print("Se usará el archivo más reciente de la carpeta datos.")
    carpeta = os.path.join(BASE_DIR, "datos")
    archivos = [
        f for f in glob.glob(os.path.join(carpeta, "*"))
        if f.lower().endswith((".csv", ".xlsx")) and not os.path.basename(f).startswith("~$")
    ]
    if not archivos:
        raise Exception(f"No hay archivos .csv ni .xlsx en {carpeta}")
    return max(archivos, key=os.path.getmtime)


def fila_encabezado(muestra: pd.DataFrame) -> int:
    """Busca la fila que contiene la columna PPU (la planilla trae una fila de títulos arriba)."""
    for i, fila in muestra.iterrows():
        if "PPU" in [str(v).strip() for v in fila.values]:
            return i
    raise Exception("No se encontró la fila de encabezados (columna 'PPU') en el archivo")


class PlanillaBloqueada(Exception):
    pass


def copia_temporal(ruta: str) -> str:
    """
    Copia la planilla a una carpeta temporal y devuelve la ruta de la copia.
    Así se puede leer aunque alguien la tenga abierta en Excel o OneDrive la esté
    sincronizando. Reintenta unas veces porque esos bloqueos suelen ser pasajeros.
    """
    destino = os.path.join(tempfile.gettempdir(), "panel_transferencias_" + os.path.basename(ruta))
    for intento in range(1, 4):
        try:
            shutil.copy2(ruta, destino)
            return destino
        except PermissionError:
            if intento < 3:
                print(f"La planilla está bloqueada, reintentando en 10 segundos ({intento}/3)...")
                time.sleep(10)
    raise PlanillaBloqueada()


def leer_archivo(ruta: str) -> pd.DataFrame:
    if ruta.lower().endswith(".xlsx"):
        copia = copia_temporal(ruta)
        try:
            hojas = pd.ExcelFile(copia, engine="openpyxl").sheet_names
            hoja = HOJA_EXCEL if HOJA_EXCEL in hojas else 0
            muestra = pd.read_excel(copia, sheet_name=hoja, header=None, nrows=10, dtype=str)
            return pd.read_excel(copia, sheet_name=hoja, header=fila_encabezado(muestra), dtype=str)
        finally:
            try:
                os.remove(copia)
            except OSError:
                pass

    for encoding in ("utf-8-sig", "cp1252"):
        try:
            muestra = pd.read_csv(ruta, encoding=encoding, sep=";", header=None, nrows=10, dtype=str)
            return pd.read_csv(
                ruta, encoding=encoding, sep=";", header=fila_encabezado(muestra),
                dtype=str, low_memory=False,
            )
        except UnicodeDecodeError:
            continue
    raise Exception("No se pudo leer el CSV (codificación no reconocida)")


# ======================================================
# FUNCIONES DE LIMPIEZA
# ======================================================
def texto(valor):
    """Convierte valores vacíos en None y elimina espacios."""
    if pd.isna(valor):
        return None
    valor = str(valor).strip()
    if valor == "" or valor.upper() in ("#N/D", "#N/A", "NAN"):
        return None
    return valor


def id_texto(valor):
    """ID de remate como texto (soporta '583', '583.0' y 'M0017')."""
    valor = texto(valor)
    if valor and valor.endswith(".0") and valor[:-2].isdigit():
        valor = valor[:-2]
    return valor


def fecha(valor):
    """Devuelve la fecha en formato YYYY-MM-DD o None."""
    if isinstance(valor, pd.Timestamp):
        return None if pd.isna(valor) else valor.strftime("%Y-%m-%d")
    valor = texto(valor)
    if valor is None:
        return None
    for formato in ("%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        f = pd.to_datetime(valor, format=formato, errors="coerce")
        if pd.notna(f):
            return f.strftime("%Y-%m-%d")
    return None


# ======================================================
# PROCESO
# ======================================================
print("=" * 60)
print("IMPORTADOR SUPABASE" + ("  (MODO PRUEBA, NO SE SUBE NADA)" if DRY_RUN else ""))
print("=" * 60)

ruta = buscar_archivo()
print(f"Leyendo archivo: {os.path.basename(ruta)}" + (f" (hoja {HOJA_EXCEL})" if ruta == EXCEL_OFICIAL else ""))
try:
    df = leer_archivo(ruta)
except PlanillaBloqueada:
    print()
    print("❌ No se pudo leer la planilla: Windows la tiene bloqueada.")
    print("   Normalmente es porque alguien la tiene abierta en Excel de escritorio")
    print("   (abrirla en Excel en el navegador no la bloquea) o porque OneDrive")
    print("   la está sincronizando. Ciérrela o espere un momento y vuelva a intentar.")
    print("   No se modificó nada en el panel.")
    sys.exit(2)
df.columns = df.columns.astype(str).str.strip()
print(f"Registros encontrados: {len(df)}")

# Eliminar filas sin patente y normalizar PPU
df["PPU"] = df["PPU"].astype(str).str.strip().str.upper()
df = df[~df["PPU"].isin(["", "NAN", "NONE"])]
df["ID Rte"] = df["ID Rte"].map(id_texto)

# Una fila por remate + patente (se conserva la última que aparece en la planilla).
# Así se mantiene el historial cuando un vehículo se remata más de una vez.
antes = len(df)
df = df.drop_duplicates(subset=["ID Rte", "PPU"], keep="last")
if antes != len(df):
    print(f"Duplicados remate+patente eliminados: {antes - len(df)}")
print(f"Registros válidos: {len(df)}")

# Marca única de esta carga (misma para todas las filas)
CARGA = pd.Timestamp.now().floor("s").isoformat()

print("Preparando registros...")
registros = []
for _, fila in df.iterrows():
    estado_transf = texto(fila["Estado de transferencia"])
    if estado_transf:
        estado_transf = CORRECCIONES_ESTADO.get(estado_transf.upper(), estado_transf)
    registros.append({
        "id_rte": id_texto(fila["ID Rte"]),
        "fecha_remate": fecha(fila["Fecha Remate"]),
        "lote": texto(fila["Lote"]),
        "ppu": texto(fila["PPU"]),
        "estado_lote": texto(fila["Estado Lote"]),
        "estado_transferencia": estado_transf,
        "mandante_comercial": texto(fila["MANDANTE COMERCIAL"]),
        "mandante_cav": texto(fila["Mandante CAV"]),
        "unidad_negocio": texto(fila["Unidad Negocio"]),
        "mandato": texto(fila["Mandato"]),
        "compra_directa": texto(fila["Compra directa"]),
        "observacion": texto(fila["Observación"]),
        "ingreso_proveedor": fecha(fila["Ingreso Proveedor"]),
        "solicitud_transferencia": fecha(fila["Solicitud transferencia"]),
        "solicitud_alzamiento": fecha(fila["Solicitud Alzamiento"]),
        "rechazo": fecha(fila["Rechazo"]),
        "reingreso": fecha(fila["Reingreso"]),
        "transferido": fecha(fila["Transferido"]),
        "enviado_banco": fecha(fila["Enviado Banco"]),
        "recibido_banco": fecha(fila["Recibido Banco"]),
        "enviado_mandante": fecha(fila["Enviado Mandante"]),
        "recibido_mandante": fecha(fila["Recibido Mandante"]),
        "enviado_legalizar": fecha(fila["Enviado a Legalizar"]),
        "recibido_legalizacion": fecha(fila["Recibida Legalización"]),
        "fecha_st_si": fecha(fila["Solo T a S.I. Fecha ST"]),
        "fecha_transferido_si": fecha(fila["Solo T a S.I. Transferido"]),
        "fecha_actualizacion": CARGA,
    })
total = len(registros)
print(f"Registros preparados: {total}")

if DRY_RUN:
    print()
    print("Modo prueba: el archivo se leyó correctamente. No se modificó Supabase.")
    sys.exit(0)

supabase = cliente_escritura()

# 1) Insertar la versión nueva completa
print("Subiendo registros a Supabase...")
try:
    for inicio in range(0, total, TAMANO_LOTE):
        fin = min(inicio + TAMANO_LOTE, total)
        supabase.table(TABLA).insert(registros[inicio:fin]).execute()
        print(f"✔ Registros {inicio + 1} - {fin} cargados.")
except Exception as e:
    print(f"❌ Error al subir registros: {e}")
    print("Deshaciendo la carga parcial (el panel sigue mostrando la versión anterior)...")
    supabase.table(TABLA).delete().eq("fecha_actualizacion", CARGA).execute()
    raise

# 2) Recién ahora borrar la versión anterior
print("Eliminando la versión anterior...")
supabase.table(TABLA).delete().neq("fecha_actualizacion", CARGA).execute()
supabase.table(TABLA).delete().is_("fecha_actualizacion", "null").execute()

print()
print("=" * 60)
print("IMPORTACIÓN TERMINADA")
print("=" * 60)
print(f"Total registros : {total}")
print("=" * 60)
