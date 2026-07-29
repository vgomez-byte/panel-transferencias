# Funciones reutilizables de conexión y consultas a servidor SQL

import pandas as pd
from sqlalchemy import text
from config import engine

# ======================================================
# Funciones genéricas de conexión a SQL Server
# ======================================================

def leer_tabla(nombre_tabla: str, limit: int | None = None) -> pd.DataFrame:
    """
    Lee una tabla completa o parcial desde SQL Server y la devuelve como DataFrame.
    
    Parámetros:
        nombre_tabla (str): Nombre de la tabla a consultar (por ejemplo 'TRANSFERENCIAS_vehiculos_actual').
        limit (int, opcional): Número de filas a limitar (por ejemplo 100 para prueba).
    
    Retorna:
        pd.DataFrame con el resultado de la consulta.
    """
    if limit:
        query = f"SELECT TOP {limit} * FROM {nombre_tabla}"
    else:
        query = f"SELECT * FROM {nombre_tabla}"
    
    try:
        with engine.begin() as conn:
            df = pd.read_sql(text(query), conn)
        print(f"✅ Consulta ejecutada correctamente: {nombre_tabla} ({len(df)} filas)")
        return df
    except Exception as e:
        print("❌ Error al leer tabla:", e)
        return pd.DataFrame()


def insertar_dataframe(df: pd.DataFrame, tabla_destino: str, if_exists: str = "append"):
    """
    Inserta un DataFrame en una tabla de SQL Server.

    Parámetros:
        df (pd.DataFrame): DataFrame a insertar.
        tabla_destino (str): Nombre de la tabla destino.
        if_exists (str): Qué hacer si la tabla existe ('append', 'replace', 'fail').
    """
    if df.empty:
        print("⚠️ El DataFrame está vacío. No se insertaron registros.")
        return
    
    try:
        df.to_sql(tabla_destino, engine, if_exists=if_exists, index=False)
        print(f"✅ {len(df)} registros insertados en {tabla_destino}.")
    except Exception as e:
        print("❌ Error al insertar DataFrame:", e)


def ejecutar_sql(query: str):
    """
    Ejecuta una consulta SQL arbitraria (INSERT, UPDATE, DELETE, etc.)
    
    Parámetros:
        query (str): Consulta SQL a ejecutar.
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(query))
        print("✅ Consulta ejecutada correctamente.")
    except Exception as e:
        print("❌ Error al ejecutar consulta:", e)