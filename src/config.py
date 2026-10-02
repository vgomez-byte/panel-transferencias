import os
from dotenv import load_dotenv
from supabase import create_client

# Cargar variables de entorno (.env en la raíz del proyecto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Clave de LECTURA (anon). La usa el panel.
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# Clave de ESCRITURA (service_role). La usa solo el cargador. Opcional mientras no se active RLS.
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

TABLA = "transferencias_panel"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def cliente_escritura():
    """Cliente para cargar datos. Usa la clave de servicio si existe."""
    if SUPABASE_SERVICE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("⚠️  No hay SUPABASE_SERVICE_KEY en .env: se usará la clave de lectura (anon).")
    print("    Cuando se active la seguridad por filas (RLS), la carga dejará de funcionar sin esa clave.")
    return supabase


def test_connection():
    try:
        respuesta = supabase.table(TABLA).select("ppu").limit(1).execute()
        print("✅ Conexión exitosa a Supabase")
        print(respuesta.data)
    except Exception as e:
        print("❌ Error al conectar:", e)


if __name__ == "__main__":
    test_connection()
