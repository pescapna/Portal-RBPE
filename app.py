import streamlit as st
import pandas as pd

st.set_page_config(page_title="Portal RBPE", page_icon="🚢", layout="wide")

st.title("🚢 Portal Central - Proyecto RBPE")
st.subheader("Módulo de Administración: Buques Extranjeros en Vivo")
st.markdown("---")

# === CONEXIÓN A GOOGLE SHEETS ===
# REEMPLAZA ESTO por el ID de tu documento de Google Sheets (la cadena larga de letras y números)
SHEET_ID = "1ef0-OayCrHg4VeNJVkkM8w6t4j0rmBhT91nVfbJFibw" 

@st.cache_data(ttl=60)
def cargar_datos_sheets():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    return df

try:
    with st.spinner('Conectando con la base de datos central...'):
        buques = cargar_datos_sheets()
    
    st.success("✅ Conexión a Google Sheets establecida con éxito.")

    # --- MENÚ LATERAL ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Flag_of_Argentina.svg/1200px-Flag_of_Argentina.svg.png", width=100)
    st.sidebar.header("Filtros de Búsqueda")
    
    if "Bandera" in buques.columns:
        lista_banderas = buques["Bandera"].dropna().unique()
        bandera_seleccionada = st.sidebar.multiselect("Filtrar por Bandera:", lista_banderas)
        
        if bandera_seleccionada:
            buques = buques[buques["Bandera"].isin(bandera_seleccionada)]

    # --- MÉTRICAS ---
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total de Buques", value=len(buques))
    if "Bandera" in buques.columns:
        col2.metric(label="Banderas", value=buques["Bandera"].nunique())
    if "Buque de interes" in buques.columns:
        col3.metric(label="Buques de Interés", value=len(buques[buques["Buque de interes"] == "SI"]))
    
    st.markdown("---")
    st.write("### Base de Datos en Tiempo Real")
    st.dataframe(buques, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("⚠️ Error al conectar con Google Sheets.")
    st.error(f"Detalle: {e}")
