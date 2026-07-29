import os
from dotenv import load_dotenv
from supabase import create_client

# Cargar variables de entorno
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)
def test_connection():
    try:
        respuesta = (
            supabase
            .table("transferencias")
            .select("ppu")
            .limit(1)
            .execute()
        )
        print("✅ Conexión exitosa a Supabase")
        print(respuesta.data)
    except Exception as e:
        print("❌ Error al conectar:", e)

if __name__ == "__main__":
    test_connection()