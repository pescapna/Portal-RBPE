import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
from streamlit_option_menu import option_menu

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTILO DARK PREMIUM Y RESPONSIVO ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Fondo principal y espaciado fluido */
    .stApp {
        background-color: #0E1117;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important; /* Full responsive */
    }
    
    /* Estilizar la tabla (Dataframe) */
    [data-testid="stDataFrame"] {
        background-color: #1E1E2E;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #30363D;
    }

    /* Ajustes Chatbot nativo de Streamlit */
    .stChatMessage {
        background-color: transparent !important;
        padding: 1rem 0 !important;
    }
    [data-testid="chatAvatarIcon-user"] {
        background-color: #3B82F6 !important;
    }
    [data-testid="chatAvatarIcon-assistant"] {
        background-color: #10B981 !important;
    }
    .stChatInputContainer {
        border-color: #30363D !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIÓN PARA TARJETAS KPI (HTML Personalizado Responsive) ---
def kpi_card(titulo, valor, color_borde):
    st.markdown(f"""
    <div style="background-color: #1E1E2E; padding: 1.2rem; border-radius: 12px; border-left: 5px solid {color_borde}; border-top: 1px solid #30363D; border-right: 1px solid #30363D; border-bottom: 1px solid #30363D; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5); width: 100%;">
        <p style="color: #94A3B8; margin: 0; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">{titulo}</p>
        <h2 style="color: #F8FAFC; margin: 8px 0 0 0; font-size: 2.2rem; font-weight: 700;">{valor}</h2>
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
                <p style="color: #94A3B8; margin-bottom: 30px;">Sistema Avanzado de Control Marítimo</p>
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
    st.error("Faltan configurar los secretos de Streamlit (API Key / Sheet ID).")
    st.stop()

@st.cache_data(ttl=600) # 10 minutos de caché
def cargar_datos():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    df = df.fillna("-") 
    return df

with st.spinner('Sincronizando con satélites y base central...'):
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
    alerta_html = '<span style="background-color: rgba(239,68,68,0.2); color: #F87171; padding: 5px 15px; border-radius: 20px; border: 1px solid rgba(239,68,68,0.5); font-weight: bold; font-size: 12px;">🚨 ALERTA DE INTERÉS</span>' if str(b.get('Buque de interes', '')).upper() == "SI" else '<span style="background-color: rgba(16,185,129,0.2); color: #34D399; padding: 5px 15px; border-radius: 20px; border: 1px solid rgba(16,185,129,0.5); font-weight: bold; font-size: 12px;">✅ OPERACIÓN STANDARD</span>'
    
    st.markdown(f"""
    <div style="background-color: #161B22; padding: 20px; border-radius: 10px; border: 1px solid #30363D; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
        <div>
            <h2 style="color: #60A5FA; margin: 0;">🚢 {b.get('Nombre', '-')}</h2>
            <p style="color: #94A3B8; margin: 5px 0 0 0;">Bandera: <span style="color: white; font-weight: bold;">{b.get('Bandera', '-')}</span> &nbsp;|&nbsp; Tipo: <span style="color: white; font-weight: bold;">{b.get('Tipo', '-')}</span></p>
        </div>
        <div>{alerta_html}</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background-color: #0E1117; padding: 15px; border-radius: 10px; border: 1px solid #30363D; height: 100%;">
            <h4 style="color: #94A3B8; border-bottom: 1px solid #30363D; padding-bottom: 10px; margin-top:0;">⚓ IDENTIFICACIÓN</h4>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:12px 0;"><span>MMSI</span> <strong style="color:white; font-family:monospace;">{b.get('MMSI', '-')}</strong></p>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:12px 0;"><span>IMO</span> <strong style="color:white; font-family:monospace;">{b.get('IMO', '-')}</strong></p>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:12px 0;"><span>Señal</span> <strong style="color:white; font-family:monospace;">{b.get('Indicativo de llamada', '-')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        riesgo_color = "#F87171" if str(b.get('Riesgo', '')) == "Alto" else "white"
        st.markdown(f"""
        <div style="background-color: #0E1117; padding: 15px; border-radius: 10px; border: 1px solid #30363D; height: 100%;">
            <h4 style="color: #94A3B8; border-bottom: 1px solid #30363D; padding-bottom: 10px; margin-top:0;">📊 CARACTERÍSTICAS</h4>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:12px 0;"><span>Eslora</span> <strong style="color:white;">{b.get('Eslora', '-')} m</strong></p>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:12px 0;"><span>Arqueo</span> <strong style="color:white;">{b.get('Arqueo bruto', '-')} GT</strong></p>
            <p style="display:flex; justify-content:space-between; color:#94A3B8; margin:12px 0;"><span>Riesgo</span> <strong style="color:{riesgo_color};">{b.get('Riesgo', '-')}</strong></p>
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
            <p style="margin:0; color:#34D399; font-size:12px;">● Online</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    menu = option_menu(
        menu_title=None,
        options=["Panel de Control", "Base de Datos", "Analista IA"],
        icons=["grid", "server", "robot"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#60A5FA", "font-size": "20px"}, 
            "nav-link": {"color": "#94A3B8", "font-size": "15px", "text-align": "left", "margin":"5px 0", "border-radius":"8px"},
            "nav-link-selected": {"background-color": "#2563EB", "color": "white", "font-weight": "bold"},
        }
    )
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# MÓDULO 1: PANEL DE CONTROL
# ==========================================
if menu == "Panel de Control":
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px; font-weight: 600;'>Panel de Inteligencia Marítima</h2>", unsafe_allow_html=True)
    
    # Cálculos
    total = len(buques)
    banderas = buques[buques["Bandera"] != "-"]["Bandera"].nunique() if "Bandera" in buques.columns else 0
    tipos = buques[buques["Tipo"] != "-"]["Tipo"].nunique() if "Tipo" in buques.columns else 0
    alertas = len(buques[buques["Buque de interes"].astype(str).str.upper() == "SI"]) if "Buque de interes" in buques.columns else 0

    # Tarjetas Personalizadas (Responsivas con st.columns)
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Flota", total, "#3B82F6") # Azul
    with c2: kpi_card("Banderas", banderas, "#10B981") # Verde
    with c3: kpi_card("Clasificaciones", tipos, "#8B5CF6") # Violeta
    with c4: kpi_card("Alertas Activas", alertas, "#EF4444") # Rojo
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- GRÁFICOS NIVEL EMPRESARIAL ---
    
    # Fila 1 de Gráficos: Flota General y Composición
    c_graf1, c_graf2 = st.columns([2, 1.2])
    
    with c_graf1:
        st.markdown("<h4 style='color: #E2E8F0; margin-bottom: 10px;'>Volumen de Flota por Bandera (Top 15)</h4>", unsafe_allow_html=True)
        if "Bandera" in buques.columns:
            top = buques[buques["Bandera"] != "-"]["Bandera"].value_counts().head(15).reset_index()
            top.columns = ["Bandera", "Cantidad"]
            fig_bar = px.bar(top, x='Bandera', y='Cantidad', color='Cantidad', color_continuous_scale='Blues', text_auto=True)
            fig_bar.update_layout(
                template='plotly_dark', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#1E1E2E', 
                margin=dict(t=10, l=10, r=10, b=40), coloraxis_showscale=False,
                xaxis_title="", yaxis_title="Cantidad de Buques"
            )
            fig_bar.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    with c_graf2:
        st.markdown("<h4 style='color: #E2E8F0; margin-bottom: 10px;'>Composición General por Tipo</h4>", unsafe_allow_html=True)
        if "Tipo" in buques.columns:
            tipos_df = buques[buques["Tipo"] != "-"]["Tipo"].value_counts().reset_index()
            tipos_df.columns = ["Tipo", "Cantidad"]
            fig_pie = px.pie(tipos_df, values='Cantidad', names='Tipo', hole=0.6, color_discrete_sequence=px.colors.sequential.Teal)
            fig_pie.update_layout(
                template='plotly_dark', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#1E1E2E', 
                margin=dict(t=10, l=10, r=10, b=10), showlegend=True, 
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Fila 2 de Gráficos: NUEVO GRÁFICO ESPECÍFICO DE PESQUEROS (ARRASTRERO, POTERO, ETC)
    c_graf3, c_graf4 = st.columns([2.2, 1])
    
    with c_graf3:
        st.markdown("<h4 style='color: #E2E8F0; margin-bottom: 10px;'>Distribución de Pesqueros por Tipo y Bandera</h4>", unsafe_allow_html=True)
        if "Tipo" in buques.columns and "Bandera" in buques.columns:
            # Filtrar solo los tipos pesqueros solicitados
            tipos_pesqueros = ["ARRASTRERO", "POTERO", "PALANGRERO", "POLIVALENTE"]
            df_pesc = buques[buques["Tipo"].astype(str).str.upper().isin(tipos_pesqueros)]
            
            if not df_pesc.empty:
                # Agrupar por Tipo y Bandera
                df_group = df_pesc.groupby(['Tipo', 'Bandera']).size().reset_index(name='Cantidad')
                # Ordenar para que las banderas con más buques aparezcan primero
                df_group = df_group.sort_values('Cantidad', ascending=False)
                
                # Crear gráfico de barras apiladas (Stacked Bar)
                fig_pesqueros = px.bar(
                    df_group, x='Tipo', y='Cantidad', color='Bandera',
                    text='Cantidad', barmode='stack',
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_pesqueros.update_layout(
                    template='plotly_dark', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#1E1E2E',
                    margin=dict(t=10, l=10, r=10, b=10),
                    xaxis_title="", yaxis_title="Cantidad Operativa",
                    legend_title="Banderas"
                )
                fig_pesqueros.update_traces(textposition='inside', textfont=dict(color='white'))
                st.plotly_chart(fig_pesqueros, use_container_width=True)
            else:
                st.info("No hay registros de buques pesqueros para mostrar.")

    with c_graf4:
        st.markdown("<h4 style='color: #F87171; margin-bottom: 10px;'>🚨 Alertas Críticas</h4>", unsafe_allow_html=True)
        if "Buque de interes" in buques.columns:
            buques_alerta = buques[buques["Buque de interes"].astype(str).str.upper() == "SI"]
            if not buques_alerta.empty:
                cols_alerta = [c for c in ["Nombre", "Bandera"] if c in buques.columns]
                # Envolvemos la tabla en un div estilizado
                st.markdown('<div style="border-radius: 10px; overflow: hidden; border: 1px solid #30363D;">', unsafe_allow_html=True)
                st.dataframe(buques_alerta[cols_alerta], use_container_width=True, hide_index=True, height=380)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("No hay buques marcados como de interés.")

# ==========================================
# MÓDULO 2: BASE DE DATOS INTERACTIVA
# ==========================================
elif menu == "Base de Datos":
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px; font-weight: 600;'>Directorio General de Buques</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background-color: #1E1E2E; padding: 15px 20px; border-radius: 10px; border: 1px solid #30363D; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 20px;">🔍</span>
        <div style="flex-grow: 1;">
    """, unsafe_allow_html=True)
    busqueda = st.text_input("", placeholder="Búsqueda Inteligente: Escribe Nombre, MMSI, IMO, Bandera o Tipo de pesquero...", label_visibility="collapsed")
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    b_filtrados = buques.copy()
    if busqueda:
        mask = b_filtrados.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        b_filtrados = b_filtrados[mask]
        
    st.caption(f"Mostrando {len(b_filtrados)} buques")

    cols_mostrar = [c for c in ["Nombre", "Bandera", "Tipo", "MMSI", "IMO", "Riesgo"] if c in b_filtrados.columns]
    
    evento = st.dataframe(
        b_filtrados[cols_mostrar],
        use_container_width=True, hide_index=True, height=550,
        on_select="rerun", selection_mode="single-row"
    )
    
    if evento and len(evento.selection.rows) > 0:
        indice = evento.selection.rows[0]
        abrir_modal_buque(b_filtrados.iloc[indice])

# ==========================================
# MÓDULO 3: AGENTE IA (CHATBOT MODERNO)
# ==========================================
elif menu == "Analista IA":
    # Inicializar el historial del chat en memoria si no existe
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Saludos, Operador. Soy el Agente IA de la plataforma RBPE. Estoy conectado a la base de datos central. ¿Qué análisis necesitas realizar hoy?"}
        ]

    # Diseño del encabezado del Chat
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 30px; padding-bottom: 15px; border-bottom: 1px solid #30363D;">
        <div style="background-color: rgba(16, 185, 129, 0.2); border: 1px solid #10B981; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; font-size: 24px;">🤖</div>
        <div>
            <h2 style="color: #F8FAFC; margin: 0; font-size: 24px;">Analista Táctico RBPE</h2>
            <p style="color: #10B981; margin: 0; font-size: 14px;">● Sistema Activo y Conectado</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Preparar el contexto oculto (para que la IA sepa de qué hablamos)
    cols_clave = [c for c in ["Nombre", "MMSI", "Bandera", "Tipo", "Riesgo", "Buque de interes"] if c in buques.columns]
    datos_ia = buques[cols_clave].to_csv(index=False)
    
    # Contenedor para los mensajes (esto permite scroll en pantallas pequeñas)
    chat_container = st.container()
    
    with chat_container:
        # Dibujar todos los mensajes del historial
        for mensaje in st.session_state.chat_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

    # Entrada de texto del usuario (Interfaz nativa de Chat)
    if prompt := st.chat_input("Escribe tu consulta aquí (Ej: ¿Cuántos buques poteros hay de Vanuatu?)..."):
        # 1. Guardar y mostrar el mensaje del usuario
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Generar y mostrar la respuesta de la IA
        with st.chat_message("assistant"):
            with st.spinner("Procesando datos y redactando informe..."):
                try:
                    # El "Prompt del Sistema" oculto para la IA
                    contexto_oculto = f"""
                    Eres el analista táctico de una plataforma marítima. 
                    Responde al usuario usando de forma exclusiva esta base de datos en formato CSV:
                    
                    {datos_ia}
                    
                    Pregunta del usuario: {prompt}
                    
                    Instrucciones: Responde de manera altamente profesional, utiliza viñetas o tablas markdown si es necesario clasificar datos. No saludes repetidamente.
                    """
                    
                    # Llamada a la API
                    respuesta = modelo_ia.generate_content(contexto_oculto)
                    
                    # Mostramos la respuesta con efecto nativo
                    st.markdown(respuesta.text)
                    
                    # Guardamos la respuesta en el historial
                    st.session_state.chat_history.append({"role": "assistant", "content": respuesta.text})
                    
                except Exception as e:
                    st.error(f"Error de comunicación con el nodo de IA: {e}")
