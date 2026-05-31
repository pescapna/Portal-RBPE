import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_option_menu import option_menu

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
        padding: 2.5rem;
        border-radius: 16px;
        border: 1px solid #1F2937;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.15);
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
# IA Y CONEXIÓN DE DATOS
# ==========================================
try:
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
    SHEET_ID = st.secrets["api"]["sheet_id"]
except:
    st.error("Error: Faltan configurar credenciales en los secretos.")
    st.stop()

@st.cache_data(ttl=600)
def cargar_datos():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    df = df.fillna("-") 
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
# BARRA LATERAL (SIDEBAR REDISEÑADO)
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
        <h3 style="margin:0; color:white; line-height:1.2; font-weight: 700; font-size: 1.4rem;">Portal <span style="color:#3B82F6;">RBPE</span></h3>
        <span style="color: #8E9CAE; font-size: 0.75rem; letter-spacing: 0.5px;">CONTROL MARÍTIMO</span>
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
            "nav-link": {"color": "#8E9CAE", "font-size": "14px", "text-align": "left", "margin": "4px 0", "border-radius": "8px", "padding": "10px 15px"},
            "nav-link-selected": {"background-color": "#2563EB", "color": "white", "font-weight": "700"},
        }
    )
    
    st.markdown("<br><br>", unsafe_allow_html=True)
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
        st.markdown("<h4 style='color: #E2E8F0; margin-bottom: 15px; font-weight: 600;'>Flota Pesquera por Bandera</h4>", unsafe_allow_html=True)
        if not pesqueros_filtrados.empty:
            conteo_banderas = pesqueros_filtrados["Bandera"].value_counts().reset_index()
            conteo_banderas.columns = ["Bandera", "Cantidad"]
            
            fig_bar = px.bar(
                conteo_banderas, x='Bandera', y='Cantidad', 
                color='Cantidad', color_continuous_scale='Blues', text_auto=True
            )
            fig_bar.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(18, 22, 32, 0.4)',  # Glassmorphic semi-transparente
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=15, l=15, r=15, b=20),
                height=380,
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
        st.markdown("<h4 style='color: #E2E8F0; margin-bottom: 15px; font-weight: 600;'>Distribución por Tipo de Pesquero</h4>", unsafe_allow_html=True)
        if not pesqueros_filtrados.empty:
            conteo_tipos = pesqueros_filtrados["Tipo"].value_counts().reset_index()
            conteo_tipos.columns = ["Tipo", "Cantidad"]
            
            fig_pie = px.pie(
                conteo_tipos, values='Cantidad', names='Tipo', hole=0.6,
                color_discrete_sequence=px.colors.sequential.Cyan_r
            )
            fig_pie.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(18, 22, 32, 0.4)',  # Glassmorphic semi-transparente
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=15, l=15, r=15, b=15),
                height=380,
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
    
    # Campo de búsqueda directa y limpia de ancho completo
    busqueda = st.text_input("🔍 Buscador Táctico", placeholder="Escriba un Nombre, MMSI, IMO, Bandera o Tipo de pesquero...", label_visibility="collapsed")
    
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
# MÓDULO 3: AGENTE IA (CHATBOT MODERNO)
# ==========================================
elif menu == "Analista IA":
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Saludos, Operador. He analizado la base táctica de buques extranjeros. Estoy a su disposición para cruzar datos y generar informes tácticos. ¿Cuál es su consulta?"}
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
    
    chat_container = st.container()
    
    with chat_container:
        for mensaje in st.session_state.chat_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

    # Chat Input nativo moderno
    if prompt := st.chat_input("Escriba su consulta analítica..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Procesando datos y estructurando respuesta..."):
                try:
                    contexto_oculto = f"""
                    Eres un analista naval de nivel corporativo para la plataforma RBPE.
                    Usa de forma estricta los siguientes datos en CSV para responder:
                    
                    {datos_ia}
                    
                    Pregunta: {prompt}
                    
                    Responde de forma concisa, objetiva y estructurada utilizando viñetas o tablas markdown si es oportuno.
                    """
                    respuesta = modelo_ia.generate_content(contexto_oculto)
                    st.markdown(respuesta.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": respuesta.text})
                except Exception as e:
                    st.error(f"Error de comunicación con el nodo de IA: {e}")
