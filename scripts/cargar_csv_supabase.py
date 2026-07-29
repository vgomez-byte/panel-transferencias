import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# CONFIGURACIÓN
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL:
    raise Exception("No existe SUPABASE_URL en .env")
if not SUPABASE_KEY:
    raise Exception("No existe SUPABASE_KEY en .env")
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# CSV
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CSV_FILE = os.path.join(
    BASE_DIR,
    "datos",
    "Seguimiento Transferencias y TAG 2025 2.0.csv"
)
print("=" * 60)
print("IMPORTADOR SUPABASE")
print("=" * 60)
print("Leyendo CSV...")

try:
    df = pd.read_csv(
    CSV_FILE,
    encoding="utf-8-sig",
    sep=";",
    low_memory=False
)
except UnicodeDecodeError:
    print("CSV detectado...")
    df = pd.read_csv(
        CSV_FILE,
        encoding="cp1252",
        sep=";",
        header=1,
        low_memory=False
    )
print(f"Registros encontrados: {len(df)}")
df.columns = df.columns.str.strip()

# Eliminar filas sin patente
df = df[df["PPU"].notna()]
df = df[df["PPU"].astype(str).str.strip() != ""]

# Normalizar PPU
df["PPU"] = (
    df["PPU"]
    .astype(str)
    .str.strip()
    .str.upper()
)
df = df[df["PPU"] != ""]

# Conservar el registro más reciente de cada patente
df["Fecha Remate Orden"] = pd.to_datetime(
    df["Fecha Remate"],
    format="%d-%m-%Y",
    errors="coerce"
)
df = (
    df.sort_values("Fecha Remate Orden")
      .drop_duplicates(subset=["PPU"], keep="last")
)
df.drop(columns=["Fecha Remate Orden"], inplace=True)

print(f"Registros válidos: {len(df)}")

# FUNCIONES
def texto(valor):
    """
    Convierte valores vacíos en None y elimina espacios.
    """
    if pd.isna(valor):
        return None
    valor = str(valor).strip()
    if valor == "":
        return None
    return valor
def fecha(valor):
    if pd.isna(valor):
        return None
    valor = str(valor).strip()
    if valor == "":
        return None
    # Formato del CSV: DD-MM-YYYY
    fecha = pd.to_datetime(
        valor,
        format="%d-%m-%Y",
        errors="coerce"
    )
    # Si por algún motivo viene en otro formato ISO
    if pd.isna(fecha):
        fecha = pd.to_datetime(
            valor,
            format="%Y-%m-%d",
            errors="coerce"
        )
    if pd.isna(fecha):
        return None
    return fecha.strftime("%Y-%m-%d")
print("Preparando registros...")
registros = []

# CONSTRUIR REGISTROS
for _, fila in df.iterrows():
    registro = {
        "id_rte": texto(fila["ID Rte"]),
        "fecha_remate": fecha(fila["Fecha Remate"]),
        "lote": texto(fila["Lote"]),
        "ppu": texto(fila["PPU"]),
        "estado_lote": texto(fila["Estado Lote"]),
        "estado_transferencia": texto(fila["Estado de transferencia"]),
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
        "fecha_actualizacion": pd.Timestamp.now().isoformat()
    }
    registros.append(registro)
print(f"Registros preparados: {len(registros)}")

print("Limpiando tabla...")
supabase.table("transferencias_panel")\
    .delete()\
    .neq("id", 0)\
    .execute()

# CARGAR A SUPABASE
print("Subiendo registros a Supabase...")
TAMANO_LOTE = 500
total = len(registros)
for inicio in range(0, total, TAMANO_LOTE):
    fin = min(inicio + TAMANO_LOTE, total)
    lote = registros[inicio:fin]
    try:
        supabase.table("transferencias_panel").insert(
            lote
        ).execute()
        print(
            f"✔ Registros {inicio + 1} - {fin} cargados."
        )
    except Exception as e:
        print(
            f"❌ Error entre {inicio + 1} y {fin}"
        )
        print(e)
        raise
print()
print("=" * 60)
print("IMPORTACIÓN TERMINADA")
print("=" * 60)
print(f"Total registros : {total}")
print("=" * 60)

if __name__ == "__main__":
    print()

    print("Proceso finalizado correctamente.")