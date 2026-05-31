import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import re
from io import StringIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTILO DARK PREMIUM COMPACTO Y ULTRA-RESPONSIVO ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Configuración del fondo y tipografía */
    .stApp {
        background-color: #0B0E14;
        color: #F1F5F9;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }
    
    /* Estilización de Inputs nativos */
    .stTextInput input, .stTextArea textarea {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        color: #F1F5F9 !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
    }

    /* Estilización avanzada y pulida de la Tabla (Dataframe) */
    [data-testid="stDataFrame"] {
        background-color: #121620 !important;
        border-radius: 12px !important;
        padding: 8px !important;
        border: 1px solid #21262D !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
    }

    /* Ocultar bordes innecesarios de botones nativos */
    .stButton button {
        border-radius: 8px !important;
    }

    /* Tarjeta de login centrada con brillo de neón sutil */
    .login-container {
        background-color: #121620;
        padding: 3rem;
        border-radius: 16px;
        border: 1px solid #21262D;
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.15);
        text-align: center;
        margin-top: 2rem;
    }

    /* Contenedores de gráficos idénticos, transparentes y alineados */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(18, 22, 32, 0.45) !important;
        border: 1px solid #21262D !important;
        border-radius: 12px !important;
        padding: 18px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5) !important;
    }

    /* Ajustes Chatbot nativo de Streamlit */
    .stChatMessage {
        background-color: rgba(18, 22, 32, 0.3) !important;
        border: 1px solid #21262D !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        padding: 1rem !important;
    }
    [data-testid="chatAvatarIcon-user"] {
        background-color: #2563EB !important;
    }
    [data-testid="chatAvatarIcon-assistant"] {
        background-color: #10B981 !important;
    }
    .stChatInputContainer {
        border-color: #21262D !important;
        border-radius: 12px !important;
        background-color: #121620 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIÓN PARA TARJETAS KPI (HTML Premium) ---
def kpi_card(titulo, valor, color_borde):
    st.markdown(f"""
    <div style="background-color: #121620; padding: 1.2rem; border-radius: 12px; border-left: 5px solid {color_borde}; border-top: 1px solid #21262D; border-right: 1px solid #21262D; border-bottom: 1px solid #21262D; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4); width: 100%;">
        <p style="color: #8E9CAE; margin: 0; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px;">{titulo}</p>
        <h2 style="color: #F8FAFC; margin: 6px 0 0 0; font-size: 2.1rem; font-weight: 700; font-family: system-ui, sans-serif;">{valor}</h2>
    </div>
    """, unsafe_allow_html=True)

# --- SISTEMA DE LOGIN MEJORADO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            st.markdown("""
            <div class="login-container">
                <div style="text-align: center; margin-bottom: 1.5rem;">
                    <span style="font-size: 3rem;">⚓</span>
                    <h2 style="color: #F8FAFC; margin: 10px 0 0 0; font-weight: 700;">ACCESO PORTAL RBPE</h2>
                    <p style="color: #8E9CAE; font-size: 0.9rem; margin-top: 5px;">Sistema Táctico de Control Marítimo</p>
                </div>
            """, unsafe_allow_html=True)
            with st.form("login_form"):
                usuario = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
                clave = st.text_input("🔑 Contraseña", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
                
                if submit:
                    if usuario in st.secrets["passwords"] and clave == st.secrets["passwords"][usuario]:
                        st.session_state["password_correct"] = True
                        st.session_state["usuario_actual"] = usuario
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas.")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True

if not check_password():
    st.stop()


# ==========================================
# IA Y CONEXIÓN DE DATOS (CON PARSER ROBUSTO)
# ==========================================
try:
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
    SHEET_ID = st.secrets["api"]["sheet_id"]
except:
    st.error("Error: Faltan configurar credenciales en los secretos.")
    st.stop()

# Función inteligente para evitar KeyError: 'Tipo' o similares en hojas externas
def normalizar_columnas(df):
    df.columns = df.columns.str.strip()
    mapeo = {
        'nombre': 'Nombre',
        'bandera': 'Bandera',
        'tipo': 'Tipo', 'tipo de pesca': 'Tipo', 'tipo_pesca': 'Tipo', 'arte de pesca': 'Tipo',
        'mmsi': 'MMSI', 'mmsi_2': 'MMSI_2',
        'imo': 'IMO',
        'indicativo de llamada': 'Indicativo de llamada', 'senal': 'Indicativo de llamada', 'señal': 'Indicativo de llamada',
        'eslora': 'Eslora',
        'arqueo bruto': 'Arqueo bruto', 'arqueo': 'Arqueo bruto',
        'riesgo': 'Riesgo',
        'buque de interes': 'Buque de interes', 'buque de interés': 'Buque de interes', 'interes': 'Buque de interes'
    }
    nuevos_nombres = {}
    for col in df.columns:
        col_min = col.lower()
        if col_min in mapeo:
            nuevos_nombres[col] = mapeo[col_min]
    df = df.rename(columns=nuevos_nombres)
    return df

@st.cache_data(ttl=600)
def cargar_datos():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    df = df.fillna("-") 
    df = normalizar_columnas(df) # Normalizamos de forma proactiva
    return df

with st.spinner('Actualizando base de datos táctica...'):
    try:
        buques = cargar_datos()
    except Exception as e:
        st.error("⚠️ Error de conexión con el repositorio de datos.")
        st.stop()


# ==========================================
# VENTANA MODAL (FICHA TÉCNICA GLASS)
# ==========================================
@st.dialog("Ficha de Identificación de Buque", width="large")
def abrir_modal_buque(b):
    alerta_html = '<span style="background-color: rgba(239,68,68,0.15); color: #F87171; padding: 6px 16px; border-radius: 20px; border: 1px solid rgba(239,68,68,0.4); font-weight: bold; font-size: 11px; letter-spacing: 0.5px;">🚨 ALERTA DE INTERÉS</span>' if str(b.get('Buque de interes', '')).upper() == "SI" else '<span style="background-color: rgba(16,185,129,0.15); color: #34D399; padding: 6px 16px; border-radius: 20px; border: 1px solid rgba(16,185,129,0.4); font-weight: bold; font-size: 11px; letter-spacing: 0.5px;">✅ OPERACIÓN STANDARD</span>'
    
    st.markdown(f"""
    <div style="background-color: #121620; padding: 20px; border-radius: 12px; border: 1px solid #21262D; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <div>
            <h2 style="color: #60A5FA; margin: 0; font-weight: 700;">🚢 {b.get('Nombre', '-')}</h2>
            <p style="color: #8E9CAE; margin: 5px 0 0 0; font-size: 0.9rem;">Bandera: <span style="color: white; font-weight: 600;">{b.get('Bandera', '-')}</span> &nbsp;|&nbsp; Tipo: <span style="color: white; font-weight: 600;">{b.get('Tipo', '-')}</span></p>
        </div>
        <div>{alerta_html}</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background-color: #0B0E14; padding: 18px; border-radius: 10px; border: 1px solid #21262D; height: 100%;">
            <h4 style="color: #8E9CAE; border-bottom: 1px solid #21262D; padding-bottom: 10px; margin-top:0; font-size: 0.9rem; font-weight: 700; letter-spacing: 0.5px;">⚓ IDENTIFICACIÓN</h4>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE; margin:12px 0; font-size: 0.9rem;"><span>MMSI</span> <strong style="color:white; font-family:monospace;">{b.get('MMSI', '-')}</strong></p>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE; margin:12px 0; font-size: 0.9rem;"><span>IMO</span> <strong style="color:white; font-family:monospace;">{b.get('IMO', '-')}</strong></p>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE; margin:12px 0; font-size: 0.9rem;"><span>Señal</span> <strong style="color:white; font-family:monospace;">{b.get('Indicativo de llamada', '-')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        riesgo_color = "#F87171" if str(b.get('Riesgo', '')) == "Alto" else "white"
        st.markdown(f"""
        <div style="background-color: #0B0E14; padding: 18px; border-radius: 10px; border: 1px solid #21262D; height: 100%;">
            <h4 style="color: #8E9CAE; border-bottom: 1px solid #21262D; padding-bottom: 10px; margin-top:0; font-size: 0.9rem; font-weight: 700; letter-spacing: 0.5px;">📊 CARACTERÍSTICAS</h4>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE; margin:12px 0; font-size: 0.9rem;"><span>Eslora</span> <strong style="color:white;">{b.get('Eslora', '-')} m</strong></p>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE; margin:12px 0; font-size: 0.9rem;"><span>Arqueo</span> <strong style="color:white;">{b.get('Arqueo bruto', '-')} GT</strong></p>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE; margin:12px 0; font-size: 0.9rem;"><span>Riesgo</span> <strong style="color:{riesgo_color};">{b.get('Riesgo', '-')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Cerrar Ficha", use_container_width=True):
        st.rerun()


# ==========================================
# BARRA LATERAL (SIDEBAR REDISEÑADO CON UX PREMIUM)
# ==========================================
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    # Escudo Nacional / Logotipo
    col_esc, col_title = st.columns([1, 3.2])
    with col_esc:
        st.markdown("""
        <div style="background-color:#1E3A8A; width:45px; height:45px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:22px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">⚓</div>
        """, unsafe_allow_html=True)
    with col_title:
        st.markdown("""
        <h3 style="margin:0; color:white; line-height:1.2; font-weight: 700; font-size: 1.3rem;">Portal <span style="color:#3B82F6;">RBPE</span></h3>
        <span style="color: #8E9CAE; font-size: 0.72rem; letter-spacing: 0.5px;">CONTROL MARÍTIMO</span>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Perfil Operador
    st.markdown(f"""
    <div style="background-color: #121620; border: 1px solid #21262D; border-radius: 12px; padding: 12px 15px; display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
        <div style="background-color: #21262D; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; font-size: 18px;">👤</div>
        <div>
            <p style="margin:0; color:white; font-size:0.85rem; font-weight:700; text-transform: capitalize;">{st.session_state['usuario_actual']}</p>
            <div style="display: flex; align-items: center; gap: 6px; margin-top: 2px;">
                <span style="background-color: #10B981; width: 8px; height: 8px; border-radius: 50%; display: inline-block; box-shadow: 0 0 6px #10B981;"></span>
                <span style="color: #10B981; font-size: 0.75rem; font-weight: 600;">Online</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Menú
    menu = option_menu(
        menu_title=None,
        options=["Panel de Control", "Base de Datos", "Analista IA"],
        icons=["grid-fill", "server", "cpu-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#60A5FA", "font-size": "18px"}, 
            "nav-link": {"color": "#8E9CAE", "font-size": "14px", "text-align": "left", "margin": "8px 0", "border-radius": "8px", "padding": "10px 15px"},
            "nav-link-selected": {"background-color": "#2563EB", "color": "white", "font-weight": "700"},
        }
    )
    
    # Espaciado dinámico UX para empujar el botón de cierre a la zona inferior de forma fluida
    st.markdown("<div style='height: 18vh;'></div>", unsafe_allow_html=True)
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ==========================================
# MÓDULO 1: PANEL DE CONTROL (DASHBOARD EQUILIBRADO)
# ==========================================
if menu == "Panel de Control":
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px; font-weight: 700;'>Panel de Inteligencia Marítima</h2>", unsafe_allow_html=True)
    
    # Filtrado exclusivo de pesqueros requeridos
    tipos_pesqueros = ["ARRASTRERO", "POTERO", "PALANGRERO", "POLIVALENTE"]
    pesqueros_filtrados = buques[buques["Tipo"].astype(str).str.upper().str.strip().isin(tipos_pesqueros)]
    
    # Cálculos
    total_gral = len(buques)
    total_pesqueros = len(pesqueros_filtrados)
    banderas_activas = pesqueros_filtrados["Bandera"].nunique() if not pesqueros_filtrados.empty else 0
    alertas_activas = len(pesqueros_filtrados[pesqueros_filtrados["Buque de interes"].astype(str).str.upper() == "SI"])

    # Tarjetas KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Flota General", total_gral, "#3B82F6")
    with c2: kpi_card("Buques Pesqueros", total_pesqueros, "#8B5CF6")
    with c3: kpi_card("Banderas Pesqueras", banderas_activas, "#10B981")
    with c4: kpi_card("Alertas de Pesca", alertas_activas, "#EF4444")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráficos de Alta Calidad, Transparentes y Alineación Simétrica
    col_graf1, col_graf2 = st.columns([1, 1])
    
    with col_graf1:
        # Contenedor con borde nativo estilizado por CSS a semi-transparente
        with st.container(border=True):
            st.markdown("<h4 style='color: #E2E8F0; margin: 0 0 10px 0; font-weight: 600; font-size: 1.1rem; border-bottom: 1px solid #21262D; padding-bottom: 8px;'>Flota Pesquera por Bandera</h4>", unsafe_allow_html=True)
            if not pesqueros_filtrados.empty:
                conteo_banderas = pesqueros_filtrados["Bandera"].value_counts().reset_index()
                conteo_banderas.columns = ["Bandera", "Cantidad"]
                
                fig_bar = px.bar(
                    conteo_banderas, x='Bandera', y='Cantidad', 
                    color='Cantidad', color_continuous_scale='Blues', text_auto=True
                )
                fig_bar.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)', # Transparente para respetar el Glassmorphic
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=15, l=15, r=15, b=20),
                    height=330,
                    coloraxis_showscale=False,
                    xaxis_title="",
                    yaxis_title="Cantidad",
                    font=dict(color='#8E9CAE')
                )
                fig_bar.update_traces(marker_line_color='#21262D', marker_line_width=1, textposition="outside", cliponaxis=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Sin datos para procesar.")

    with col_graf2:
        with st.container(border=True):
            st.markdown("<h4 style='color: #E2E8F0; margin: 0 0 10px 0; font-weight: 600; font-size: 1.1rem; border-bottom: 1px solid #21262D; padding-bottom: 8px;'>Distribución por Tipo de Pesquero</h4>", unsafe_allow_html=True)
            if not pesqueros_filtrados.empty:
                conteo_tipos = pesqueros_filtrados["Tipo"].value_counts().reset_index()
                conteo_tipos.columns = ["Tipo", "Cantidad"]
                
                fig_pie = px.pie(
                    conteo_tipos, values='Cantidad', names='Tipo', hole=0.6,
                    color_discrete_sequence=px.colors.sequential.Cyan_r
                )
                fig_pie.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)', # Transparente para respetar el Glassmorphic
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=15, l=15, r=15, b=15),
                    height=330,
                    font=dict(color='#8E9CAE'),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
                )
                fig_pie.update_traces(marker=dict(line=dict(color='#21262D', width=1.5)))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Sin datos para procesar.")


# ==========================================
# MÓDULO 2: BASE DE DATOS INTERACTIVA (ESTILIZADA SIN COLUMNAS SQUISHED)
# ==========================================
elif menu == "Base de Datos":
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px; font-weight: 700;'>Directorio General de Buques</h2>", unsafe_allow_html=True)
    
    # Campo de búsqueda directa y limpia de ancho completo (Sin contenedor innecesario de lupa)
    busqueda = st.text_input("🔍 Buscar Buque", placeholder="Escriba un Nombre, MMSI, IMO, Bandera o Tipo de pesquero...", label_visibility="collapsed")
    
    b_filtrados = buques.copy()
    if busqueda:
        mask = b_filtrados.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        b_filtrados = b_filtrados[mask]
        
    st.markdown(f"<p style='color: #8E9CAE; font-size: 0.9rem; margin-bottom: 10px;'>Mostrando {len(b_filtrados)} registros encontrados en la base central.</p>", unsafe_allow_html=True)

    # Columnas que se mostrarán en la tabla principal de manera limpia
    cols_mostrar = [c for c in ["Nombre", "Bandera", "Tipo", "MMSI", "IMO", "Riesgo"] if c in b_filtrados.columns]
    
    # DEFINICIÓN DE CONFIGURACIÓN DE COLUMNAS (Evita que queden aplastadas o feas)
    col_config = {
        "Nombre": st.column_config.TextColumn(
            "Nombre del Buque",
            help="Nombre identificador del navío extranjero",
            width="large",
            required=True
        ),
        "Bandera": st.column_config.TextColumn(
            "Bandera",
            help="País de bandera registrada",
            width="medium"
        ),
        "Tipo": st.column_config.TextColumn(
            "Tipo de Pesca",
            help="Clasificación del arte de pesca autorizado",
            width="medium"
        ),
        "MMSI": st.column_config.TextColumn(
            "MMSI",
            help="Maritime Mobile Service Identity",
            width="medium"
        ),
        "IMO": st.column_config.TextColumn(
            "IMO",
            help="Número de la Organización Marítima Internacional",
            width="medium"
        ),
        "Riesgo": st.column_config.TextColumn(
            "Nivel Riesgo",
            help="Evaluación del riesgo estratégico táctico",
            width="small"
        )
    }

    evento = st.dataframe(
        b_filtrados[cols_mostrar],
        use_container_width=True, 
        hide_index=True, 
        height=520,
        on_select="rerun", 
        selection_mode="single-row",
        column_config=col_config  # <-- ¡Aquí se aplica la magia de estructuración visual!
    )
    
    if evento and len(evento.selection.rows) > 0:
        indice = evento.selection.rows[0]
        abrir_modal_buque(b_filtrados.iloc[indice])


# ==========================================
# MÓDULO 3: AGENTE IA (CHATBOT MODERNO E INTERACTIVO)
# ==========================================
elif menu == "Analista IA":
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Saludos, Operador. He analizado la base táctica de buques extranjeros. Estoy a su disposición para cruzar datos, generar reportes de inteligencia y armar gráficos interactivos. Pruebe pidiéndome: *'Grafica la flota de pesqueros por bandera'* o *'Dame una tabla de los buques de interés'*."}
        ]

    # Encabezado del Chat Premium
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #21262D;">
        <div style="background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 0 10px rgba(16, 185, 129, 0.1);">🤖</div>
        <div>
            <h2 style="color: #F8FAFC; margin: 0; font-size: 1.4rem; font-weight: 700;">Agente Analista RBPE</h2>
            <div style="display: flex; align-items: center; gap: 6px; margin-top: 2px;">
                <span style="background-color: #10B981; width: 6px; height: 6px; border-radius: 50%; display: inline-block;"></span>
                <span style="color: #10B981; font-size: 0.75rem; font-weight: 600;">Servicio de IA Activo</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Contexto reducido
    cols_clave = [c for c in ["Nombre", "MMSI", "Bandera", "Tipo", "Riesgo", "Buque de interes"] if c in buques.columns]
    datos_ia = buques[cols_clave].to_csv(index=False)
    
    # Función inteligente para analizar el output de la IA y pintar gráficos/tablas interactivas descargables
    def renderizar_respuesta_inteligente(texto_crudo, df_base):
        # Separar bloques de código de Python para gráficos Plotly
        patron_python = r"```python\s*(.*?)\s*```"
        # Separar bloques de código CSV para tablas st.dataframe descargables
        patron_csv = r"```csv\s*(.*?)\s*```"
        
        partes_python = re.split(patron_python, texto_crudo, flags=re.DOTALL)
        
        for idx, parte in enumerate(partes_python):
            if idx % 2 == 1:  # Es un bloque de código Python para graficar
                try:
                    # Entorno de ejecución seguro con las librerías necesarias
                    variables_locales = {"df": df_base, "px": px, "go": go, "pd": pd}
                    exec(parte, {}, variables_locales)
                    fig = variables_locales.get("fig")
                    if fig is not None:
                        # Estilizar el gráfico dinámico para que combine con el dashboard oscurecido
                        fig.update_layout(
                            template='plotly_dark',
                            paper_bgcolor='rgba(18, 22, 32, 0.45)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            margin=dict(t=30, l=15, r=15, b=20),
                            font=dict(color='#8E9CAE')
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("⚠️ El agente generó código, pero no devolvió la figura 'fig'.")
                except Exception as e:
                    st.error(f"Error al procesar el gráfico interactivo: {e}")
                    with st.expander("Ver código de depuración"):
                        st.code(parte, language="python")
            else:
                # Procesar bloques de CSV para transformarlos en tablas de alta gama descargables
                partes_csv = re.split(patron_csv, parte, flags=re.DOTALL)
                for csv_idx, csv_parte in enumerate(partes_csv):
                    if csv_idx % 2 == 1:  # Es una tabla en CSV
                        try:
                            df_tabla = pd.read_csv(StringIO(csv_parte.strip()))
                            # Renderizamos st.dataframe (Streamlit ofrece descarga y copiado nativo en la esquina superior derecha)
                            st.dataframe(df_tabla, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error al estructurar la tabla interactiva: {e}")
                            st.code(csv_parte, language="csv")
                    else:
                        # Es texto Markdown común
                        if csv_parte.strip():
                            st.markdown(csv_parte)

    # Renderizar el historial de conversación en el Chat container
    chat_container = st.container()
    with chat_container:
        for mensaje in st.session_state.chat_history:
            with st.chat_message(mensaje["role"]):
                renderizar_respuesta_inteligente(mensaje["content"], buques)

    # Entrada de mensajes nativa
    if prompt := st.chat_input("Escriba su consulta analítica..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Procesando datos y estructurando respuesta..."):
                try:
                    # Instrucciones estrictas para que Gemini use el parser inteligente de frontend
                    contexto_oculto = f"""
                    Eres un analista naval e ingeniero de datos tácticos para el Portal RBPE.
                    Responde al operador utilizando estrictamente estos datos de buques en formato CSV:
                    
                    {datos_ia}
                    
                    REGLAS CRÍTICAS DE SALIDA:
                    1. Si el usuario te pide un gráfico (ej. "gráfica", "haz un gráfico", "comparativa visual", "gráfico de barras", etc.), DEBES incluir en tu respuesta un bloque de código python estructurado EXACTAMENTE de la siguiente manera:
                       ```python
                       # Genera un objeto de Plotly llamado 'fig' utilizando exclusivamente el DataFrame 'df' provisto
                       # df contiene columnas: Nombre, MMSI, Bandera, Tipo, Riesgo, Buque de interes
                       conteo = df['Bandera'].value_counts().reset_index().head(10)
                       conteo.columns = ['Bandera', 'Cantidad']
                       fig = px.bar(conteo, x='Bandera', y='Cantidad', color='Cantidad', color_continuous_scale='Blues')
                       ```
                       NO utilices st.plotly_chart ni muestres la figura. Define únicamente la variable 'fig'.
                       
                    2. Si el usuario te pide una lista estructurada, resumen de registros, o tabla de datos, DEBES presentar los datos estructurados dentro de un bloque CSV EXACTAMENTE de la siguiente manera:
                       ```csv
                       Nombre,Bandera,Tipo,MMSI
                       101 HAERANG,Corea del Sur,POTERO,441879000
                       FONG TAI NO. 21,Vanuatu,POTERO,577101000
                       ```
                       Esto permitirá que nuestro sistema lo convierta de forma transparente en una tabla interactiva que el operador podrá COPIAR, FILTRAR y DESCARGAR en formato CSV.

                    3. Mantén un tono formal, técnico y conciso. Evita introducciones innecesarias si la consulta es directa.
                    
                    Pregunta del Operador: {prompt}
                    """
                    respuesta = modelo_ia.generate_content(contexto_oculto)
                    renderizar_respuesta_inteligente(respuesta.text, buques)
                    st.session_state.chat_history.append({"role": "assistant", "content": respuesta.text})
                except Exception as e:
                    st.error(f"Error de comunicación con el nodo de IA: {e}")
