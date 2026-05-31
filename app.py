import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_option_menu import option_menu # <-- La nueva estrella del menú

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="🚢", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTILO DARK PREMIUM ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Fondo principal y textos */
    .stApp {
        background-color: #0E1117;
        color: #E2E8F0;
    }
    
    /* Fondo de la barra lateral */
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #30363D;
    }
    
    /* Tarjetas de Métricas (KPIs) Modo Oscuro */
    div[data-testid="metric-container"] {
        background-color: #1E1E2E;
        border-left: 5px solid #3B82F6;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 2px 4px 15px rgba(59, 130, 246, 0.2);
    }
    
    /* Asegurar que los números de las métricas sean blancos */
    div[data-testid="metric-container"] label, 
    div[data-testid="metric-container"] div {
        color: #F8FAFC !important;
    }
    
    /* Ajustes para encabezados */
    h1, h2, h3, h4 {
        color: #F8FAFC !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            with st.container(border=True):
                st.markdown("<h2 style='text-align: center; color: #60A5FA !important;'>⚓ Acceso RBPE</h2>", unsafe_allow_html=True)
                st.divider()
                with st.form("login_form"):
                    usuario = st.text_input("👤 Usuario")
                    clave = st.text_input("🔑 Contraseña", type="password")
                    submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
                    
                    if submit:
                        if usuario in st.secrets["passwords"] and clave == st.secrets["passwords"][usuario]:
                            st.session_state["password_correct"] = True
                            st.session_state["usuario_actual"] = usuario
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas.")
        return False
    return True

if not check_password():
    st.stop()

# ==========================================
# IA Y BASE DE DATOS
# ==========================================
genai.configure(api_key=st.secrets["api"]["gemini_key"])
modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
SHEET_ID = st.secrets["api"]["sheet_id"]

@st.cache_data(ttl=60)
def cargar_datos():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    df = df.fillna("-") 
    return df

with st.spinner('Sincronizando base de datos central...'):
    try:
        buques = cargar_datos()
    except Exception as e:
        st.error("⚠️ Error de conexión.")
        st.stop()

# ==========================================
# VENTANA MODAL (FICHA TÉCNICA DARK)
# ==========================================
@st.dialog("🪪 Ficha Técnica del Buque", width="large")
def abrir_modal_buque(datos_buque):
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"<h3 style='color: #60A5FA !important; margin-bottom: 0;'>{datos_buque.get('Nombre', '-')}</h3>", unsafe_allow_html=True)
        st.caption(f"Bandera: {datos_buque.get('Bandera', '-')} | Tipo: {datos_buque.get('Tipo', '-')}")
    with c2:
        if str(datos_buque.get('Buque de interes', '')).upper() == "SI":
            st.error("🚨 ALERTA")
        else:
            st.success("✅ OK")
            
    st.divider()
    
    col_id, col_tec = st.columns(2)
    with col_id:
        st.write(f"**MMSI:** {datos_buque.get('MMSI', '-')}")
        st.write(f"**IMO:** {datos_buque.get('IMO', '-')}")
        st.write(f"**Señal Distintiva:** {datos_buque.get('Indicativo de llamada', '-')}")
    with col_tec:
        st.write(f"**Eslora:** {datos_buque.get('Eslora', '-')} m")
        st.write(f"**Arqueo Bruto:** {datos_buque.get('Arqueo bruto', '-')} GT")
        st.write(f"**Riesgo:** {datos_buque.get('Riesgo', '-')}")
    
    st.divider()
    if st.button("Cerrar Ficha", use_container_width=True):
        st.rerun()

# ==========================================
# BARRA LATERAL AVANZADA (OPTION MENU)
# ==========================================
with st.sidebar:
    col_img, col_txt = st.columns([1, 3])
    with col_img:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Flag_of_Argentina.svg/1200px-Flag_of_Argentina.svg.png", width=50)
    with col_txt:
        st.markdown(f"**Operador:**<br>{st.session_state['usuario_actual'].capitalize()}", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # EL NUEVO MENÚ INTERACTIVO
    menu = option_menu(
        menu_title="Navegación",  # Título del menú
        options=["Panel de Control", "Base de Datos", "Analista IA"], # Opciones
        icons=["speedometer2", "database", "robot"], # Iconos de Bootstrap
        menu_icon="cast", # Icono principal
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#60A5FA", "font-size": "18px"}, 
            "nav-link": {"color": "#E2E8F0", "font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#21262d"},
            "nav-link-selected": {"background-color": "#3B82F6", "color": "white"},
        }
    )
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# ==========================================
# MÓDULO 1: PANEL DE CONTROL
# ==========================================
if menu == "Panel de Control":
    st.markdown("<h2>📊 Panel de Inteligencia Marítima</h2>", unsafe_allow_html=True)
    
    # --- FILA 1: KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Buques Registrados", len(buques))
    if "Bandera" in buques.columns:
        col2.metric("Banderas Operativas", buques[buques["Bandera"] != "-"]["Bandera"].nunique())
    if "Tipo" in buques.columns:
        col3.metric("Clasificaciones (Tipos)", buques[buques["Tipo"] != "-"]["Tipo"].nunique())
    if "Buque de interes" in buques.columns:
        col4.metric("Buques de Interés (SI)", len(buques[buques["Buque de interes"].astype(str).str.upper() == "SI"]))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- FILA 2: GRÁFICO PRINCIPAL ANCHO ---
    if "Bandera" in buques.columns:
        st.markdown("#### Volumen de Flota por Bandera (Top 15)")
        top_banderas = buques[buques["Bandera"] != "-"]["Bandera"].value_counts().head(15).reset_index()
        top_banderas.columns = ["Bandera", "Cantidad"]
        
        fig_bar = px.bar(
            top_banderas, x='Bandera', y='Cantidad', 
            color='Cantidad', color_continuous_scale='Blues', text_auto=True
        )
        # Adaptación del gráfico al Modo Oscuro
        fig_bar.update_layout(
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=20, l=10, r=10, b=40),
            coloraxis_showscale=False,
            xaxis_title="", yaxis_title="Cantidad de Buques"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- FILA 3: GRAFICOS SECUNDARIOS ---
    col_pie, col_tabla = st.columns([1.2, 1])
    
    with col_pie:
        if "Tipo" in buques.columns:
            st.markdown("#### Composición por Tipo de Buque")
            conteo_tipos = buques[buques["Tipo"] != "-"]["Tipo"].value_counts().reset_index()
            conteo_tipos.columns = ["Tipo", "Cantidad"]
            
            fig_pie = px.pie(
                conteo_tipos, values='Cantidad', names='Tipo', hole=0.5, 
                color_discrete_sequence=px.colors.sequential.Teal
            )
            # Adaptación al Modo Oscuro
            fig_pie.update_layout(
                template='plotly_dark',
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, l=0, r=0, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
    with col_tabla:
        if "Buque de interes" in buques.columns:
            st.markdown("#### 🚨 Alerta: Buques de Interés")
            buques_alerta = buques[buques["Buque de interes"].astype(str).str.upper() == "SI"]
            if not buques_alerta.empty:
                cols_alerta = [c for c in ["Nombre", "Bandera", "MMSI"] if c in buques.columns]
                st.dataframe(buques_alerta[cols_alerta], use_container_width=True, hide_index=True, height=350)
            else:
                st.success("No hay buques marcados como de interés actualmente.")

# ==========================================
# MÓDULO 2: BASE DE DATOS INTERACTIVA
# ==========================================
elif menu == "Base de Datos":
    st.markdown("<h2>📋 Directorio General de Buques</h2>", unsafe_allow_html=True)
    
    busqueda = st.text_input("🔍 Buscar en toda la base de datos (Nombre, IMO, Señal, etc.):")
    b_filtrados = buques.copy()
    
    if busqueda:
        mask = b_filtrados.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        b_filtrados = b_filtrados[mask]
        
    st.caption(f"Registros encontrados: {len(b_filtrados)}")

    cols_mostrar = [c for c in ["Nombre", "Bandera", "Tipo", "MMSI", "IMO", "Riesgo"] if c in b_filtrados.columns]
    
    evento = st.dataframe(
        b_filtrados[cols_mostrar],
        use_container_width=True, hide_index=True, height=500,
        on_select="rerun", selection_mode="single-row"
    )
    
    if evento and len(evento.selection.rows) > 0:
        indice = evento.selection.rows[0]
        abrir_modal_buque(b_filtrados.iloc[indice])

# ==========================================
# MÓDULO 3: AGENTE IA
# ==========================================
elif menu == "Analista IA":
    st.markdown("<h2>🤖 Centro de Análisis IA</h2>", unsafe_allow_html=True)
    
    col_ia1, col_ia2 = st.columns([1, 2.5])
    with col_ia1:
        st.image("https://cdn-icons-png.flaticon.com/512/8649/8649603.png", width=120)
        st.info("Pregúntale al agente sobre tendencias, resúmenes o cruce de datos de los buques.")
        
    with col_ia2:
        cols_clave = [c for c in ["Nombre", "MMSI", "Bandera", "Tipo", "Riesgo", "Buque de interes"] if c in buques.columns]
        datos_ia = buques[cols_clave].to_csv(index=False)

        pregunta = st.text_area("¿Qué deseas investigar?", height=100)
        
        if st.button("🧠 Ejecutar Análisis", type="primary", use_container_width=True):
            if pregunta:
                with st.spinner("Procesando en servidores seguros..."):
                    try:
                        prompt = f"Eres un analista naval. Base de datos:\n{datos_ia}\n\nConsulta: {pregunta}\nResponde SOLO basado en los datos, sé conciso y profesional."
                        respuesta = modelo_ia.generate_content(prompt)
                        st.success("Análisis completado")
                        st.markdown(f"**Resultado:**\n\n> {respuesta.text}")
                    except Exception as e:
                        st.error(f"Error IA: {e}")
            else:
                st.warning("Escribe una consulta.")
