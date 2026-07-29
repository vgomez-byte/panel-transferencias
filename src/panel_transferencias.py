import streamlit as st
import pandas as pd
from config import supabase
import io

# CONFIGURACIÓN BÁSICA
st.set_page_config(page_title="Panel de Transferencias", layout="wide")

# Carga de Base SQL
#@st.cache_data
def cargar_datos():
    """Carga los datos desde Supabase."""
    todos = []
    inicio = 0
    tamano = 1000
    while True:
        respuesta = (
            supabase
            .table("transferencias_panel")
            .select("*")
            .range(inicio, inicio + tamano - 1)
            .execute()
        )
        if not respuesta.data:
            break
        todos.extend(respuesta.data)
        if len(respuesta.data) < tamano:
            break
        inicio += tamano
    df = pd.DataFrame(todos)
    if df.empty:
        return df
    
    # ===== Renombrar columnas para que el resto del código no cambie =====
    df.rename(columns={
        "id_rte": "ID_remate",
        "fecha_remate": "fecha_subasta",
        "ppu": "PPU",
        "mandante_comercial": "mandante_comercial",
        "mandante_cav": "mandante_cav",
        "unidad_negocio": "unidad_negocio",
        "estado_lote": "estado_lote",
        "estado_transferencia": "estado_transferencia",
        "mandato": "mandato",
        "compra_directa": "compra_directa",
        "observacion": "comentario",
        "ingreso_proveedor": "fecha_ingreso_a_proveedor",
        "solicitud_transferencia": "fecha_solicitud_transferencia",
        "solicitud_alzamiento": "fecha_solicitud_alzamiento",
        "rechazo": "fecha_rechazo",
        "reingreso": "fecha_reingreso",
        "transferido": "fecha_transferencia",
        "enviado_banco": "fecha_enviado_banco",
        "recibido_banco": "fecha_recibido_banco",
        "enviado_mandante": "fecha_enviado_mandante",
        "recibido_mandante": "fecha_recibido_mandante",
        "enviado_legalizar": "fecha_enviado_notaria",
        "recibido_legalizacion": "fecha_recibido_notaria",
        "fecha_st_si": "fecha_ST_a_SI",
        "fecha_transferido_si": "fecha_transferido_a_SI",
        "fecha_actualizacion": "last_update"
    }, inplace=True)
    return df

def obtener_fecha_actualizacion():
    respuesta = (
        supabase
        .table("transferencias_panel")
        .select("fecha_actualizacion")
        .order("fecha_actualizacion", desc=True)
        .limit(1)
        .execute()
    )
    if not respuesta.data:
        return None
    return pd.to_datetime(
        respuesta.data[0]["fecha_actualizacion"]
    )

# Función auxiliar de cálculo estado de cierres, dias totales y dias en etapa actual
def calcular_dias(df):
    """Agrega columnas de cálculo: Cerrado, Días Totales, Días Etapa Actual."""
    hoy = pd.Timestamp.now().normalize()

    # Parseo seguro de fechas
    fecha_cols = [
        "fecha_subasta", "fecha_transferencia", "fecha_enviado_banco", "fecha_recibido_banco",
        "fecha_enviado_mandante", "fecha_recibido_mandante", "fecha_enviado_notaria",
        "fecha_recibido_notaria", "fecha_ST_a_SI", "fecha_transferido_a_SI",
        "fecha_ingreso_a_proveedor", "fecha_solicitud_transferencia",
        "fecha_solicitud_alzamiento", "fecha_rechazo", "fecha_reingreso"
    ]
    for col in fecha_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Cierre automático por estado_lote para cada LOTE
    cerrado_estado_lote = (
        df["estado_transferencia"]
        .astype(str)
        .str.strip()
        .str.upper()
        .isin(["NO APLICA", "NO CONTRATA"])
    )

    df["Cerrado"] = (
        (df["fecha_transferencia"].notna()) | (cerrado_estado_lote)
    ).map({True: "Sí", False: "No"})

    # Días totales
    dias = (
        df["fecha_transferencia"].fillna(hoy) - df["fecha_subasta"]
    ).dt.days
    df["Días Totales"] = dias.clip(lower=0)

    # Días en etapa actual
    fechas_hitos = [
        "fecha_subasta", "fecha_enviado_banco", "fecha_recibido_banco", "fecha_enviado_mandante",
        "fecha_recibido_mandante", "fecha_enviado_notaria", "fecha_recibido_notaria",
        "fecha_ST_a_SI", "fecha_transferido_a_SI", "fecha_ingreso_a_proveedor",
        "fecha_solicitud_transferencia", "fecha_solicitud_alzamiento",
        "fecha_rechazo", "fecha_reingreso", "fecha_transferencia"
    ]
    df["última_fecha"] = (
        df[fechas_hitos]
        .apply(lambda fila: fila.dropna().max(), axis=1)
    )
    dias_etapa = (
        hoy - df["última_fecha"]
    ).dt.days
    df["Días en etapa actual"] = dias_etapa.clip(lower=0)
    df.drop(columns=["última_fecha"], inplace=True)
    return df

# Definición de tabla de seguimiento por Subasta / Mandante / Mandato
def preparar_tabla(df):
    columnas = [
        "Días Totales","PPU","estado_transferencia","Días en etapa actual","comentario",
        "estado_lote","mandato","compra_directa","lote",
        "mandante_cav","mandante_comercial","unidad_negocio",
        "fecha_enviado_banco","fecha_recibido_banco",
        "fecha_enviado_mandante","fecha_recibido_mandante",
        "fecha_enviado_notaria","fecha_recibido_notaria",
        "fecha_ST_a_SI","fecha_transferido_a_SI",
        "fecha_ingreso_a_proveedor","fecha_solicitud_transferencia",
        "fecha_solicitud_alzamiento","fecha_rechazo",
        "fecha_reingreso","fecha_transferencia",
        "Cerrado","ID_remate","fecha_subasta", "last_update"
    ]

    columnas_existentes = [c for c in columnas if c in df.columns]
    df = df[columnas_existentes].copy()

    for c in ["lote","ID_remate"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    # Formato de fechas para mostrar
    fecha_cols = [c for c in df.columns if c.startswith("fecha_")] + ["last_update"]
    for col in fecha_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["Subasta"] = df.apply(
    lambda x:
        f"{x['ID_remate']} - {x['fecha_subasta'].strftime('%d-%m-%Y')}"
        if pd.notna(x["fecha_subasta"])
        else f"{x['ID_remate']} - Sin fecha",
    axis=1
    )

    df.rename(columns={
        "mandante_comercial":"Mandante","mandante_cav":"Mandante CAV",
        "unidad_negocio":"Unidad negocio","estado_lote":"Estado lote",
        "estado_transferencia":"Estado transferencia","comentario":"Observación",
        "mandato":"Mandato","compra_directa":"Compra directa", "last_update":"Última actualización"
    }, inplace=True)
    return df

# Condiciones de color para celdas de días
def aplicar_color(dias):
    if pd.isna(dias):
        return "white"
    if dias <= 30:
        return "#c6efce"
    elif dias <= 60:
        return "#fff2cc"
    else:
        return "#f4cccc"

# Cacheo de tabla para evitar descarga repetitiva de base SQL
#@st.cache_data
def preparar_datos(df):
    """Aplica los cálculos base de columnas derivadas."""
    df = calcular_dias(df)
    df = preparar_tabla(df)
    return df

# ======================================================
# INTERFAZ PRINCIPAL
# ======================================================
fecha_update = obtener_fecha_actualizacion()

if pd.notna(fecha_update):
    st.caption(f"Actualizado por última vez el {fecha_update:%d-%m-%Y %H:%M}")
else:
    st.caption("Actualizado por última vez: sin información disponible")

st.title("📋 Panel de Seguimiento de Transferencias")

try:
    df = preparar_datos(cargar_datos())
except Exception as e:
    st.error(f"❌ Error al cargar datos: {e}")
    st.stop()

# ======================================================
# FILTROS
# ======================================================
st.sidebar.header("🔍 Filtros")
mandantes = sorted(df["Mandante"].dropna().unique().tolist())
mandatos = sorted(df["Mandato"].dropna().unique().tolist())
estados_lote = sorted(df["Estado lote"].dropna().unique().tolist())
estados_transf = sorted(df["Estado transferencia"].dropna().unique().tolist())
cerrados = ["Sí","No"]
subastas = sorted([str(s) for s in df["Subasta"].dropna().unique().tolist()])

sel_mandantes = st.sidebar.multiselect("Mandante", mandantes)
sel_mandatos = st.sidebar.multiselect("Mandato", mandatos)
sel_est_lote = st.sidebar.multiselect("Estado lote", estados_lote)
sel_est_transf = st.sidebar.multiselect("Estado transferencia", estados_transf)
sel_subastas = st.sidebar.multiselect("Subasta", subastas)
sel_cerrado = st.sidebar.multiselect("Cerrado", cerrados, default=["No"])
sel_ppu = st.sidebar.text_input("Buscar PPU")
excluir_liq = st.sidebar.checkbox("Excluir mandatos LIQ", value=True)
excluir_no_transferibles = st.sidebar.checkbox("Excluir no transferibles", value =True)

if st.sidebar.button("Limpiar filtros"):
    sel_mandantes=sel_mandatos=sel_est_lote=sel_est_transf=sel_subastas=[]
    sel_ppu=""; sel_cerrado=[]; excluir_liq=False; excluir_no_transferibles=False

# ======================================================
# APLICAR FILTROS
# ======================================================
df_filtrado = df.copy()

if excluir_liq and "Mandato" in df_filtrado.columns:
    df_filtrado = df_filtrado[~df_filtrado["Mandato"].astype(str).str.strip().str.upper().eq("LIQ")]
if excluir_no_transferibles and "Estado transferencia" in df_filtrado.columns:
    df_filtrado = df_filtrado[~df_filtrado["Estado transferencia"].astype(str).str.strip().str.upper().eq("NO TRANSFERIBLE")]
if sel_mandantes:
    df_filtrado = df_filtrado[df_filtrado["Mandante"].isin(sel_mandantes)]
if sel_mandatos:
    df_filtrado = df_filtrado[df_filtrado["Mandato"].isin(sel_mandatos)]
if sel_est_lote:
    df_filtrado = df_filtrado[df_filtrado["Estado lote"].isin(sel_est_lote)]
if sel_est_transf:
    df_filtrado = df_filtrado[df_filtrado["Estado transferencia"].isin(sel_est_transf)]
if sel_subastas:
    df_filtrado = df_filtrado[df_filtrado["Subasta"].isin(sel_subastas)]
if sel_ppu:
    df_filtrado = df_filtrado[df_filtrado["PPU"].str.contains(sel_ppu, case=False, na=False)]

# ======================================================
# ESTADOS DE CIERRE JERÁRQUICOS PARA SUBASTA, MANDANTE Y MANDATO
# ======================================================
# Nivel Subasta / Mandante / Mandato
mandato_estado = (
    df_filtrado.groupby(["ID_remate","Mandante","Mandato"], dropna=False)["Cerrado"]
    .apply(lambda x: "Sí" if all(x == "Sí") else "No")
    .reset_index()
    .rename(columns={"Cerrado": "Mandato Cerrado"})
)

df_filtrado = df_filtrado.merge(mandato_estado, on=["ID_remate","Mandante","Mandato"], how="left")

# Nivel Mandante (dentro de la Subasta)
mandante_estado = (
    mandato_estado.groupby(["ID_remate","Mandante"])["Mandato Cerrado"]
    .apply(lambda x: "Sí" if all(x == "Sí") else "No")
    .reset_index()
    .rename(columns={"Mandato Cerrado": "Mandante Cerrado"})
)
df_filtrado = df_filtrado.merge(mandante_estado, on=["ID_remate","Mandante"], how="left")

# Nivel Subasta (general)
subasta_estado = (
    mandante_estado.groupby("ID_remate")["Mandante Cerrado"]
    .apply(lambda x: "Sí" if all(x == "Sí") else "No")
    .reset_index()
    .rename(columns={"Mandante Cerrado": "Subasta Cerrado"})
)
df_filtrado = df_filtrado.merge(subasta_estado, on="ID_remate", how="left")

# Aplicar filtro de cerrado
if sel_cerrado:
    df_filtrado = df_filtrado[df_filtrado["Cerrado"].isin(sel_cerrado)]

# ======================================================
# KPI PRINCIPAL
# ======================================================
hoy = pd.Timestamp.now()
hace_6_meses = hoy - pd.DateOffset(months=6)
df_tmp = df.copy()

# Filtrado de cerradas en últimos 6 meses (excluye mandatos LIQ)
filtro_cerradas = (
    (df_tmp["Cerrado"] == "Sí") &
    (~df_tmp["Mandato"].astype(str).str.upper().eq("LIQ")) &
    (df_tmp["fecha_subasta"] >= hace_6_meses)
)
df_cerradas = df_tmp[filtro_cerradas]

# Si hay filtro de mandato, calcula el promedio solo para esos mandatos
if sel_mandatos:
    df_cerradas = df_cerradas[df_cerradas["Mandato"].isin(sel_mandatos)]
    mandato_label = ", ".join(sel_mandatos)
else:
    mandato_label = "Global"

promedio_6m = df_cerradas["Días Totales"].mean().round(1) if not df_cerradas.empty else 0

col1, col2, col3 = st.columns([1,1,2])
col1.metric("Total registros", len(df_filtrado))
col2.metric("Cerrados", (df_filtrado["Cerrado"] == "Sí").sum())
col3.metric(f"Promedio últimos 180 días ({mandato_label})", f"{promedio_6m:.1f}")

# ======================================================
# RESUMEN POR SUBASTA / MANDANTE / MANDATO
# ======================================================

hoy = pd.Timestamp.now().normalize()
df_aux = df_filtrado.copy()

# Días desde subasta
def dias_desde_subasta(r):
    if pd.isna(r["fecha_subasta"]):
        return None
    if r["Cerrado"] == "Sí" and pd.notna(r["fecha_transferencia"]):
        return max((r["fecha_transferencia"] - r["fecha_subasta"]).days, 0)
    return max((hoy - r["fecha_subasta"]).days, 0)

df_aux["Días desde subasta"] = df_aux.apply(dias_desde_subasta, axis=1)

# === Cálculo de cierre por Subasta/Mandante/Mandato ===
resumen = (
    df_aux.groupby(["ID_remate", "fecha_subasta", "Mandante", "Mandato"], dropna=False)
    .agg(
        PPUs=("PPU", "count"),
        Cerrado=("Cerrado", lambda x: "Sí" if (x == "Sí").all() else "No"),
        DiasDesde=("Días desde subasta", "mean")
    )
    .reset_index()
    .sort_values(["ID_remate", "Mandante"], kind="stable")
    .reset_index(drop=True)
)

resumen.rename(columns={"ID_remate": "ID Subasta"}, inplace=True)
resumen.rename(columns={"fecha_subasta": "Fecha Subasta"}, inplace=True)
resumen["DiasDesde"] = resumen["DiasDesde"].fillna(0).round(0).astype(int)
resumen.rename(columns={"DiasDesde": "Días desde subasta"}, inplace=True)
resumen["Fecha Subasta"] = resumen["Fecha Subasta"].dt.strftime("%d-%m-%Y")

# Estilos
def color_dias(v, cerrado):
    if cerrado == "Sí" or pd.isna(v):
        return ""
    if v <= 30:
        return "background-color: #c6efce"
    elif v <= 60:
        return "background-color: #fff2cc"
    else:
        return "background-color: #f4cccc"

def color_fila(row):
    return [
        color_dias(row["Días desde subasta"], row["Cerrado"])
        if col == "Días desde subasta"
        else ""
        for col in row.index
    ]

st.markdown("### 📋 Resumen por **Subasta, Mandante y Mandato**")
styled = (
    resumen.style
    .apply(color_fila, axis=1)
    .map(lambda v: "background-color: #d9ead3" if v == "Sí" else "", subset=["Cerrado"])
)
st.dataframe(
    styled, 
    width="stretch", 
    column_config={"Mandato": st.column_config.TextColumn(width="small"),} 
    )

st.divider()

# ======================================================
# DETALLE AGRUPADO
# ======================================================

# Filtrado para excel descargable con la misma información de pantalla
df_export = df_filtrado.copy()
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    df_export.to_excel(writer, index=False, sheet_name="Detalle")
buffer.seek(0)

t1 , t2 = st.columns([0.82, 0.18])
with t1:
    st.markdown("### 📦 Detalle por Subasta y Mandante")
with t2:
    st.download_button(
        label="⬇️ Descargar a Excel",
        data=buffer,
        file_name="detalle_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("&nbsp;")

for subasta, df_sub in df_filtrado.groupby("ID_remate", dropna=False):
    fecha_sub = df_sub["fecha_subasta"].iloc[0]
    fecha_fmt = fecha_sub.strftime("%d-%m-%Y") if pd.notna(fecha_sub) else "—"
    dias_transcurridos = (pd.Timestamp.now().normalize() - fecha_sub).days if pd.notna(fecha_sub) else 0
    total_ppus = len(df_sub)
    estado_sub = df_sub["Subasta Cerrado"].iloc[0]

    # --- Encabezado de subasta ---
    c1, c2 = st.columns([0.92, 0.08])
    with c1:
        st.markdown(
            f"📅 **SUBASTA {subasta}** del {fecha_fmt} | {total_ppus} PPUs | {dias_transcurridos} días desde subasta"
        )
    with c2:
        if estado_sub == "Sí":
            st.badge("Cerrado", icon=":material/check:", color="green")
        else:
            st.badge("Abierto", icon=":material/hourglass_empty:", color="red")

    for mandante, df_man in df_sub.groupby("Mandante", dropna=False):
        total_ppus_man = len(df_man)
        estado_man = df_man["Mandante Cerrado"].iloc[0]

        # --- Encabezado de mandante ---
        cm1, cm2 = st.columns([0.92, 0.08])
        with cm1:
            st.markdown(
                f"{mandante if pd.notna(mandante) else 'Sin mandante'} | {total_ppus_man} PPUs"
            )
        with cm2:
            if estado_man == "Sí":
                st.badge("Cerrado", icon=":material/check:", color="green")
            else:
                st.badge("Abierto", icon=":material/hourglass_empty:", color="red")

        # --- Tabla de detalle ---
        df_mostrar = df_man.copy()
        for col in df_mostrar.select_dtypes(include=["float", "int"]).columns:
            df_mostrar[col] = pd.to_numeric(df_mostrar[col], errors="coerce").astype("Int64")

        styled = (df_mostrar.style
            .map(lambda v: f"background-color: {aplicar_color(v)}", subset=["Días Totales"])
        )
        
        st.dataframe(
            styled,
            width="stretch",
            column_config={
            "Días Totales": st.column_config.TextColumn(width=80),
            "PPU": st.column_config.TextColumn(width=60),
            "Estado transferencia": st.column_config.TextColumn(width=200),
            "Días en etapa actual": st.column_config.TextColumn(width=80),
            "Observación": st.column_config.TextColumn(width=350),
            "Estado lote": st.column_config.TextColumn(width=100),
            "Mandato": st.column_config.TextColumn(width=100),
            "Compra directa": st.column_config.TextColumn(width=80),
            }
        )
    st.markdown("<hr style='border:none;border-top:1px solid #ddd;margin:25px 0;'>",unsafe_allow_html=True)
