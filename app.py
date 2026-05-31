import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="🚢", layout="wide", initial_sidebar_state="collapsed")

# --- INYECCIÓN DE CSS PARA DISEÑO MODERNO ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    div[data-testid="metric-container"] {
        background-color: #f8fafc;
        border-left: 5px solid #1e3a8a;
        border-radius: 5px;
        padding: 15px;
        box-shadow: 1px 1px 4px rgba(0,0,0,0.1);
    }
    
    /* Estilo de la Tarjeta del Buque */
    .tarjeta-buque {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
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
                usuario = st.text_input("👤 Usuario")
                clave = st.text_input("🔑 Contraseña", type="password")
                submit_button = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
                
                if submit_button:
                    if usuario == "admin" and clave == st.secrets["passwords"]["admin"]:
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas.")
        return False
    return True

if not check_password():
    st.stop()


# ==========================================
# SISTEMA PRINCIPAL
# ==========================================

genai.configure(api_key=st.secrets["api"]["gemini_key"])
modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')

# REEMPLAZA TU ID AQUÍ
SHEET_ID = "1ef0-OayCrHg4VeNJVkkM8w6t4j0rmBhT91nVfbJFibw" 

@st.cache_data(ttl=60)
def cargar_datos_sheets():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    # Llenar valores vacíos para evitar errores visuales
    df = df.fillna("-")
    return df

with st.spinner('Sincronizando con base de datos central...'):
    try:
        buques = cargar_datos_sheets()
    except Exception as e:
        st.error("⚠️ Error de conexión.")
        st.stop()

# --- ENCABEZADO ---
st.title("🚢 Portal Central - Proyecto RBPE")
st.markdown("**Módulo 1:** Control de Buques Extranjeros")
st.markdown("---")

# --- PESTAÑAS ---
tab_dashboard, tab_datos, tab_ia = st.tabs(["📊 Panel de Control", "🗂️ Directorio de Buques", "🤖 Analista IA"])

# --- PESTAÑA 1: DASHBOARD ---
with tab_dashboard:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Total de Registros", value=len(buques))
    if "Bandera" in buques.columns:
        col2.metric(label="Banderas Activas", value=buques[buques["Bandera"] != "-"]["Bandera"].nunique())
    if "Tipo" in buques.columns:
        col3.metric(label="Tipos de Buque", value=buques[buques["Tipo"] != "-"]["Tipo"].nunique())
    if "Buque de interes" in buques.columns:
        col4.metric(label="Buques de Interés", value=len(buques[buques["Buque de interes"].astype(str).str.upper() == "SI"]))
    
    st.markdown("<br>", unsafe_allow_html=True)
    if "Bandera" in buques.columns and "Tipo" in buques.columns:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("**Distribución por Bandera**")
            conteo_banderas = buques[buques["Bandera"] != "-"]["Bandera"].value_counts().reset_index()
            conteo_banderas.columns = ["Bandera", "Cantidad"]
            fig_pie = px.pie(conteo_banderas, values='Cantidad', names='Bandera', hole=0.4)
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_g2:
            st.markdown("**Tipos de Buque**")
            conteo_tipos = buques[buques["Tipo"] != "-"]["Tipo"].value_counts().reset_index()
            conteo_tipos.columns = ["Tipo", "Cantidad"]
            fig_bar = px.bar(conteo_tipos, x='Tipo', y='Cantidad', color='Tipo')
            fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

# --- PESTAÑA 2: BASE DE DATOS (NUEVO DISEÑO MAESTRO-DETALLE) ---
with tab_datos:
    # Dividimos la pantalla: 60% para lista/filtros, 40% para la tarjeta
    col_lista, col_tarjeta = st.columns([1.5, 1], gap="large")
    
    with col_lista:
        st.markdown("### 📋 Filtros y Lista")
        
        # Filtros compactos
        f1, f2, f3 = st.columns(3)
        with f1:
            lista_banderas = buques["Bandera"].unique() if "Bandera" in buques.columns else []
            filtro_b = st.multiselect("Bandera:", [b for b in lista_banderas if b != "-"])
        with f2:
            lista_tipos = buques["Tipo"].unique() if "Tipo" in buques.columns else []
            filtro_t = st.multiselect("Tipo:", [t for t in lista_tipos if t != "-"])
        with f3:
            busqueda = st.text_input("🔍 Buscar Nombre o MMSI:")
            
        # Lógica de filtrado
        b_filtrados = buques.copy()
        if filtro_b: b_filtrados = b_filtrados[b_filtrados["Bandera"].isin(filtro_b)]
        if filtro_t: b_filtrados = b_filtrados[b_filtrados["Tipo"].isin(filtro_t)]
        if busqueda:
            b_filtrados = b_filtrados[
                b_filtrados["Nombre"].astype(str).str.contains(busqueda, case=False) | 
                b_filtrados["MMSI"].astype(str).str.contains(busqueda, case=False)
            ]
            
        st.caption(f"Mostrando {len(b_filtrados)} buques")
        
        # Mostramos una tabla resumida (solo lo esencial)
        columnas_resumen = [col for col in ["Nombre", "Bandera", "Tipo", "MMSI"] if col in b_filtrados.columns]
        st.dataframe(b_filtrados[columnas_resumen], use_container_width=True, hide_index=True, height=400)

    with col_tarjeta:
        st.markdown("### 🪪 Perfil del Buque")
        
        if len(b_filtrados) > 0:
            # Selector vinculado a la lista filtrada
            nombres_disponibles = b_filtrados["Nombre"].tolist()
            buque_seleccionado = st.selectbox("Seleccione un buque para ver su ficha:", nombres_disponibles)
            
            if buque_seleccionado:
                # Obtenemos todos los datos de ese buque específico
                datos_buque = b_filtrados[b_filtrados["Nombre"] == buque_seleccionado].iloc[0]
                
                # Construimos la "Tarjeta" visual usando un contenedor con borde
                with st.container(border=True):
                    st.markdown(f"<h2 style='color: #1e3a8a; margin-bottom: 0;'>{datos_buque.get('Nombre', '-')}</h2>", unsafe_allow_html=True)
                    st.markdown(f"**Bandera:** {datos_buque.get('Bandera', '-')} | **Tipo:** {datos_buque.get('Tipo', '-')}")
                    
                    if str(datos_buque.get('Buque de interes', '')).upper() == "SI":
                        st.error("🚨 **ALERTA: BUQUE DE INTERÉS**")
                    else:
                        st.success("✅ Operación Standard")
                        
                    st.divider()
                    
                    c_info1, c_info2 = st.columns(2)
                    with c_info1:
                        st.caption("IDENTIFICACIÓN")
                        st.write(f"**MMSI:** {datos_buque.get('MMSI', '-')}")
                        st.write(f"**MMSI Sec:** {datos_buque.get('MMSI_2', '-')}")
                        st.write(f"**IMO:** {datos_buque.get('IMO', '-')}")
                        st.write(f"**Señal Dist.:** {datos_buque.get('Indicativo de llamada', '-')}")
                    
                    with c_info2:
                        st.caption("CARACTERÍSTICAS")
                        st.write(f"**Eslora:** {datos_buque.get('Eslora', '-')} m")
                        st.write(f"**Arqueo:** {datos_buque.get('Arqueo bruto', '-')} GT")
                        st.write(f"**Construcción:** {datos_buque.get('Fecha de construcción', '-')}")
                        st.write(f"**Riesgo:** {datos_buque.get('Riesgo', '-')}")
        else:
            st.info("No hay buques que coincidan con los filtros.")

# --- PESTAÑA 3: AGENTE IA ---
with tab_ia:
    col_ia1, col_ia2 = st.columns([1, 2])
    with col_ia1:
        st.image("https://cdn-icons-png.flaticon.com/512/8649/8649603.png", width=150)
        st.markdown("### Asistente Virtual")
        st.info("El agente analiza la base de datos en tiempo real.")
        
    with col_ia2:
        columnas_clave = [col for col in ["Nombre", "MMSI", "Bandera", "Tipo", "Riesgo", "Buque de interes"] if col in buques.columns]
        datos_para_ia = buques[columnas_clave].to_csv(index=False)

        pregunta_usuario = st.text_area("¿Qué deseas saber sobre los buques registrados?", height=100)
        
        if st.button("🧠 Procesar Consulta", type="primary"):
            if pregunta_usuario:
                with st.spinner("Analizando..."):
                    try:
                        prompt = f"Eres un analista experto en control marítimo. Base de datos:\n{datos_para_ia}\n\nConsulta: {pregunta_usuario}\nResponde SOLO basado en los datos."
                        respuesta = modelo_ia.generate_content(prompt)
                        st.success("Análisis completado")
                        st.markdown(f"> {respuesta.text}")
                    except Exception as e:
                        st.error(f"Error IA: {e}")
            else:
                st.warning("Escribe una consulta.")
