import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px  # <-- Nueva librería para gráficos hermosos

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="🚢", layout="wide", initial_sidebar_state="expanded")

# --- INYECCIÓN DE CSS PARA MEJORAR EL DISEÑO ---
st.markdown("""
<style>
    /* Ocultar el menú de Streamlit y el pie de página para que parezca una app nativa */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilo para las tarjetas de métricas */
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Estilo para los títulos de las pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 5px 5px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚓ Portal Central RBPE</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.2em;'>Sistema de Administración y Control Marítimo</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            with st.form("login_form"):
                st.markdown("### Acceso Restringido")
                usuario = st.text_input("👤 Usuario")
                clave = st.text_input("🔑 Contraseña", type="password")
                submit_button = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
                
                if submit_button:
                    if usuario == "admin" and clave == st.secrets["passwords"]["admin"]:
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas. Verifique e intente nuevamente.")
        return False
    return True

if not check_password():
    st.stop()


# ==========================================
# SISTEMA PRINCIPAL
# ==========================================

# 1. Configurar IA
genai.configure(api_key=st.secrets["api"]["gemini_key"])
modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')

# 2. Conexión a Google Sheets (REEMPLAZA TU ID)
SHEET_ID = "1ef0-OayCrHg4VeNJVkkM8w6t4j0rmBhT91nVfbJFibw" 

@st.cache_data(ttl=60)
def cargar_datos_sheets():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    return df

with st.spinner('Sincronizando con base de datos central...'):
    try:
        buques = cargar_datos_sheets()
    except Exception as e:
        st.error("⚠️ Error de conexión.")
        st.stop()

# --- ENCABEZADO ---
col_logo, col_titulo = st.columns([1, 8])
with col_titulo:
    st.title("🚢 Portal Central - Proyecto RBPE")
    st.markdown("**Módulo 1:** Control de Buques Extranjeros")
st.markdown("---")

# --- PESTAÑAS ---
tab_dashboard, tab_datos, tab_ia = st.tabs(["📊 Panel de Control", "🗄️ Directorio de Buques", "🤖 Analista IA"])

# --- PESTAÑA 1: DASHBOARD (Ahora con gráficos) ---
with tab_dashboard:
    st.markdown("### Resumen Operativo")
    
    # Tarjetas de métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Total de Registros", value=len(buques))
    
    if "Bandera" in buques.columns:
        col2.metric(label="Banderas Activas", value=buques["Bandera"].nunique())
    if "Tipo" in buques.columns:
        col3.metric(label="Tipos de Buque", value=buques["Tipo"].nunique())
    if "Buque de interes" in buques.columns:
        col4.metric(label="Buques de Interés", value=len(buques[buques["Buque de interes"] == "SI"]))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráficos de alta calidad
    if "Bandera" in buques.columns and "Tipo" in buques.columns:
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.markdown("**Distribución por Bandera**")
            # Gráfico de torta
            conteo_banderas = buques["Bandera"].value_counts().reset_index()
            conteo_banderas.columns = ["Bandera", "Cantidad"]
            fig_pie = px.pie(conteo_banderas, values='Cantidad', names='Bandera', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_graf2:
            st.markdown("**Tipos de Buque**")
            # Gráfico de barras
            conteo_tipos = buques["Tipo"].value_counts().reset_index()
            conteo_tipos.columns = ["Tipo", "Cantidad"]
            fig_bar = px.bar(conteo_tipos, x='Tipo', y='Cantidad', color='Tipo', text_auto=True)
            fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

# --- PESTAÑA 2: BASE DE DATOS ---
with tab_datos:
    st.markdown("### Buscador y Filtros Avanzados")
    
    # Menú de filtros elegante
    with st.expander("🔍 Desplegar Filtros de Búsqueda", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            if "Bandera" in buques.columns:
                lista_banderas = buques["Bandera"].dropna().unique()
                filtro_bandera = st.multiselect("Bandera:", lista_banderas)
        with col_f2:
            if "Tipo" in buques.columns:
                lista_tipos = buques["Tipo"].dropna().unique()
                filtro_tipo = st.multiselect("Tipo de Buque:", lista_tipos)
        with col_f3:
            if "Nombre" in buques.columns:
                busqueda_nombre = st.text_input("Buscar por Nombre:")

    # Aplicar filtros
    buques_filtrados = buques.copy()
    if "Bandera" in buques.columns and filtro_bandera:
        buques_filtrados = buques_filtrados[buques_filtrados["Bandera"].isin(filtro_bandera)]
    if "Tipo" in buques.columns and filtro_tipo:
        buques_filtrados = buques_filtrados[buques_filtrados["Tipo"].isin(filtro_tipo)]
    if "Nombre" in buques.columns and busqueda_nombre:
        # Filtro que ignora mayúsculas y minúsculas
        buques_filtrados = buques_filtrados[buques_filtrados["Nombre"].str.contains(busqueda_nombre, case=False, na=False)]

    st.dataframe(buques_filtrados, use_container_width=True, hide_index=True, height=500)

# --- PESTAÑA 3: AGENTE IA ---
with tab_ia:
    col_ia1, col_ia2 = st.columns([1, 2])
    with col_ia1:
        st.image("https://cdn-icons-png.flaticon.com/512/8649/8649603.png", width=150)
        st.markdown("### Asistente Virtual")
        st.caption("Conectado a Google Gemini IA")
        st.info("El agente analiza la base de datos en tiempo real. Puedes pedirle resúmenes, contar buques o buscar anomalías.")
        
    with col_ia2:
        columnas_clave = [col for col in ["Nombre", "MMSI", "Bandera", "Tipo", "Riesgo", "Buque de interes"] if col in buques.columns]
        datos_para_ia = buques[columnas_clave].to_csv(index=False)

        pregunta_usuario = st.text_area("¿Qué deseas saber sobre los buques registrados?", height=100, placeholder="Ejemplo: ¿Hay buques poteros de Corea del Sur que sean considerados 'de interés'?")
        
        if st.button("🧠 Procesar Consulta", type="primary"):
            if pregunta_usuario:
                with st.spinner("El agente está revisando los registros..."):
                    try:
                        prompt = f"""
                        Eres un analista experto en control marítimo. Tienes esta base de datos:
                        {datos_para_ia}
                        
                        Responde a esta consulta del usuario basándote SOLO en esos datos. Sé claro, profesional e incluye viñetas si es necesario:
                        Consulta: {pregunta_usuario}
                        """
                        respuesta = modelo_ia.generate_content(prompt)
                        st.success("Análisis completado")
                        st.markdown(f"> {respuesta.text}")
                    except Exception as e:
                        st.error(f"Error de comunicación con la IA: {e}")
            else:
                st.warning("Escribe una consulta para comenzar.")
