import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_option_menu import option_menu

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTILO DARK PREMIUM (Imitando React) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Fondo principal */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Ocultar padding superior molesto de Streamlit */
    .block-container {
        padding-top: 2rem !important;
    }
    
    /* Estilizar la tabla (Dataframe) para modo oscuro */
    [data-testid="stDataFrame"] {
        background-color: #1E1E2E;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #30363D;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIÓN PARA TARJETAS KPI (HTML Personalizado) ---
def kpi_card(titulo, valor, color_borde):
    st.markdown(f"""
    <div style="background-color: #1E1E2E; padding: 20px; border-radius: 12px; border-left: 5px solid {color_borde}; border-top: 1px solid #30363D; border-right: 1px solid #30363D; border-bottom: 1px solid #30363D; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);">
        <p style="color: #94A3B8; margin: 0; font-size: 14px; font-weight: 600;">{titulo}</p>
        <h2 style="color: #F8FAFC; margin: 5px 0 0 0; font-size: 32px; font-weight: 700;">{valor}</h2>
    </div>
    """, unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("""
            <div style="background-color: #1E1E2E; padding: 40px; border-radius: 15px; border: 1px solid #30363D; text-align: center;">
                <h1 style="color: #3B82F6; margin-bottom: 5px;">⚓ Portal RBPE</h1>
                <p style="color: #94A3B8; margin-bottom: 30px;">Sistema de Administración y Control Marítimo</p>
            </div>
            """, unsafe_allow_html=True)
            with st.form("login_form"):
                usuario = st.text_input("👤 Usuario")
                clave = st.text_input("🔑 Contraseña", type="password")
                submit = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
                
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
try:
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
    SHEET_ID = st.secrets["api"]["sheet_id"]
except:
    st.error("Faltan configurar los secretos de Streamlit.")
    st.stop()

@st.cache_data(ttl=600) # ¡Cambiado a 10 minutos para mayor fluidez!
def cargar_datos():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    df = df.fillna("-") 
    return df

with st.spinner('Sincronizando con base de datos central...'):
    try:
        buques = cargar_datos()
    except Exception as e:
        st.error("⚠️ Error de conexión con Google Sheets.")
        st.stop()


# ==========================================
# VENTANA MODAL (FICHA TÉCNICA DARK)
# ==========================================
@st.dialog("Ficha de Identificación de Buque", width="large")
def abrir_modal_buque(b):
    # Encabezado Modal
    alerta_html = '<span style="background-color: rgba(239,68,68,0.2); color: #F87171; padding: 5px 15px; border-radius: 20px; border: 1px solid rgba(239,68,68,0.5); font-weight: bold; font-size: 12px;">🚨 ALERTA DE INTERÉS</span>' if str(b.get('Buque de interes', '')).upper() == "SI" else '<span style="background-color: rgba(16,185,129,0.2); color: #34D399; padding: 5px 15px; border-radius: 20px; border: 1px solid rgba(16,185,129,0.5); font-weight: bold; font-size: 12px;">✅ OPERACIÓN STANDARD</span>'
    
    st.markdown(f"""
    <div style="background-color: #161B22; padding: 20px; border-radius: 10px; border: 1px solid #30363D; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <h2 style="color: #60A5FA; margin: 0;">🚢 {b.get('Nombre', '-')}</h2>
            <p style="color: #94A3B8; margin: 5px 0 0 0;">Bandera: <span style="color: white;">{b.get('Bandera', '-')}</span> | Tipo: <span style="color: white;">{b.get('Tipo', '-')}</span></p>
        </div>
        <div>{alerta_html}</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background-color: #0E1117; padding: 15px; border-radius: 10px; border: 1px solid #30363D;">
            <h4 style="color: #94A3B8; border-bottom: 1px solid #30363D; padding-bottom: 10px; margin-top:0;">⚓ IDENTIFICACIÓN</h4>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:10px 0;"><span>MMSI</span> <strong style="color:white; font-family:monospace;">{b.get('MMSI', '-')}</strong></p>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:10px 0;"><span>IMO</span> <strong style="color:white; font-family:monospace;">{b.get('IMO', '-')}</strong></p>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:10px 0;"><span>Señal</span> <strong style="color:white; font-family:monospace;">{b.get('Indicativo de llamada', '-')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        riesgo_color = "#F87171" if str(b.get('Riesgo', '')) == "Alto" else "white"
        st.markdown(f"""
        <div style="background-color: #0E1117; padding: 15px; border-radius: 10px; border: 1px solid #30363D;">
            <h4 style="color: #94A3B8; border-bottom: 1px solid #30363D; padding-bottom: 10px; margin-top:0;">📊 CARACTERÍSTICAS</h4>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:10px 0;"><span>Eslora</span> <strong style="color:white;">{b.get('Eslora', '-')} m</strong></p>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:10px 0;"><span>Arqueo</span> <strong style="color:white;">{b.get('Arqueo bruto', '-')} GT</strong></p>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:10px 0;"><span>Riesgo</span> <strong style="color:{riesgo_color};">{b.get('Riesgo', '-')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Cerrar Ficha", use_container_width=True):
        st.rerun()

# ==========================================
# BARRA LATERAL (OPTION MENU)
# ==========================================
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:15px; margin-bottom:20px;">
        <div style="background-color:#2563EB; width:45px; height:45px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:24px;">⚓</div>
        <div>
            <h3 style="margin:0; color:white; line-height:1.2;">Portal <span style="color:#60A5FA;">RBPE</span></h3>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:10px; border-top:1px solid #30363D; border-bottom:1px solid #30363D; padding:15px 0; margin-bottom:10px;">
        <div style="background-color:#334155; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center;">👤</div>
        <div>
            <p style="margin:0; color:white; font-size:14px; font-weight:bold;">Operador: {st.session_state['usuario_actual'].capitalize()}</p>
            <p style="margin:0; color:#34D399; font-size:12px;">● En línea</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    menu = option_menu(
        menu_title=None,
        options=["Panel de Control", "Base de Datos", "Analista IA"],
        icons=["speedometer2", "database", "robot"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#60A5FA", "font-size": "20px"}, 
            "nav-link": {"color": "#94A3B8", "font-size": "15px", "text-align": "left", "margin":"5px 0", "border-radius":"8px"},
            "nav-link-selected": {"background-color": "#2563EB", "color": "white"},
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
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px;'>Panel de Inteligencia Marítima</h2>", unsafe_allow_html=True)
    
    # Cálculos
    total = len(buques)
    banderas = buques[buques["Bandera"] != "-"]["Bandera"].nunique() if "Bandera" in buques.columns else 0
    tipos = buques[buques["Tipo"] != "-"]["Tipo"].nunique() if "Tipo" in buques.columns else 0
    alertas = len(buques[buques["Buque de interes"].astype(str).str.upper() == "SI"]) if "Buque de interes" in buques.columns else 0

    # Tarjetas Personalizadas (Filas de KPIs)
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Registros", total, "#3B82F6") # Azul
    with c2: kpi_card("Banderas Activas", banderas, "#10B981") # Verde
    with c3: kpi_card("Tipos de Buque", tipos, "#8B5CF6") # Violeta
    with c4: kpi_card("Alertas (Interés)", alertas, "#EF4444") # Rojo
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráficos de Plotly Adaptados
    c_graf1, c_graf2 = st.columns([2, 1])
    
    with c_graf1:
        st.markdown("<h4 style='color: white;'>Volumen de Flota por Bandera (Top 15)</h4>", unsafe_allow_html=True)
        if "Bandera" in buques.columns:
            top = buques[buques["Bandera"] != "-"]["Bandera"].value_counts().head(15).reset_index()
            top.columns = ["Bandera", "Cantidad"]
            fig_bar = px.bar(top, x='Bandera', y='Cantidad', color='Cantidad', color_continuous_scale='Blues', text_auto=True)
            fig_bar.update_layout(template='plotly_dark', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#1E1E2E', margin=dict(t=20, l=10, r=10, b=40), coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    with c_graf2:
        st.markdown("<h4 style='color: white;'>Composición por Tipo</h4>", unsafe_allow_html=True)
        if "Tipo" in buques.columns:
            tipos_df = buques[buques["Tipo"] != "-"]["Tipo"].value_counts().reset_index()
            tipos_df.columns = ["Tipo", "Cantidad"]
            fig_pie = px.pie(tipos_df, values='Cantidad', names='Tipo', hole=0.5, color_discrete_sequence=px.colors.sequential.Ocean)
            fig_pie.update_layout(template='plotly_dark', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#1E1E2E', margin=dict(t=10, l=10, r=10, b=10), showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# MÓDULO 2: BASE DE DATOS INTERACTIVA
# ==========================================
elif menu == "Base de Datos":
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px;'>Directorio General de Buques</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background-color: #1E1E2E; padding: 15px; border-radius: 10px; border: 1px solid #30363D; margin-bottom: 20px;">
        <p style="color: #94A3B8; margin: 0 0 10px 0; font-size: 14px;">🔍 Búsqueda Inteligente (Nombre, MMSI, IMO, Bandera)</p>
    """, unsafe_allow_html=True)
    busqueda = st.text_input("", placeholder="Ejemplo: POTERO, China, 441879000...", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    
    b_filtrados = buques.copy()
    if busqueda:
        mask = b_filtrados.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        b_filtrados = b_filtrados[mask]
        
    st.caption(f"Mostrando {len(b_filtrados)} buques")

    cols_mostrar = [c for c in ["Nombre", "Bandera", "Tipo", "MMSI", "IMO", "Riesgo"] if c in b_filtrados.columns]
    
    # La tabla interactiva (Hover effects son nativos en modo dark)
    evento = st.dataframe(
        b_filtrados[cols_mostrar],
        use_container_width=True, hide_index=True, height=550,
        on_select="rerun", selection_mode="single-row"
    )
    
    if evento and len(evento.selection.rows) > 0:
        indice = evento.selection.rows[0]
        abrir_modal_buque(b_filtrados.iloc[indice])

# ==========================================
# MÓDULO 3: AGENTE IA
# ==========================================
elif menu == "Analista IA":
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px;'>Centro de Análisis Inteligente</h2>", unsafe_allow_html=True)
    
    col_ia1, col_ia2 = st.columns([1, 2.5])
    with col_ia1:
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <div style="background-color: rgba(37,99,235,0.2); width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px auto; border: 1px solid rgba(59,130,246,0.3);">
                <span style="font-size: 40px;">🤖</span>
            </div>
            <h3 style="color: white; margin: 0;">Agente RBPE</h3>
            <p style="color: #94A3B8; font-size: 14px;">Conectado a la base de datos central. Hazme cualquier pregunta.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_ia2:
        cols_clave = [c for c in ["Nombre", "MMSI", "Bandera", "Tipo", "Riesgo", "Buque de interes"] if c in buques.columns]
        datos_ia = buques[cols_clave].to_csv(index=False)

        st.markdown("""<div style="background-color: #1E1E2E; padding: 20px; border-radius: 12px; border: 1px solid #30363D;">""", unsafe_allow_html=True)
        pregunta = st.text_area("✍️ Ingresa tu consulta:", height=100, placeholder="Ejemplo: ¿Cuántos buques poteros hay con alerta de interés?")
        
        if st.button("🧠 Ejecutar Análisis IA", type="primary", use_container_width=True):
            if pregunta:
                with st.spinner("Procesando consulta en servidores seguros..."):
                    try:
                        prompt = f"Eres un analista naval. Base de datos:\n{datos_ia}\n\nConsulta: {pregunta}\nResponde SOLO basado en los datos, sé conciso y profesional."
                        respuesta = modelo_ia.generate_content(prompt)
                        st.markdown(f"""
                        <div style="background-color: #161B22; padding: 20px; border-radius: 10px; border-left: 4px solid #10B981; margin-top: 20px;">
                            <h4 style="color: #34D399; margin:0 0 10px 0;">Respuesta del Agente:</h4>
                            <p style="color: #E2E8F0; font-size: 15px; margin:0;">{respuesta.text}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error IA: {e}")
            else:
                st.warning("Escribe una consulta para comenzar.")
        st.markdown("</div>", unsafe_allow_html=True)
