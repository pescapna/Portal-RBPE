import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import re
from io import StringIO
from supabase import create_client, Client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="⚓", layout="wide", initial_sidebar_state="expanded")

# --- CONEXIÓN DE DATOS (SUPABASE & GEMINI) ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["service_role_key"] # Usamos service_role para permitir escritura desde la IA
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
except Exception as e:
    st.error(f"Error: Configura las credenciales de Supabase y Gemini en tus secretos. Detalle: {e}")
    st.stop()

# --- CSS: ESTILO DARK PREMIUM INTACTO ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0B0E14; color: #F1F5F9; }
    .block-container { padding: 1.5rem 2rem !important; max-width: 100% !important; }
    .stTextInput input, .stTextArea textarea {
        background-color: #161B22 !important; border: 1px solid #30363D !important;
        color: #F1F5F9 !important; border-radius: 8px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3B82F6 !important; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
    }
    .stButton button { border-radius: 8px !important; }
    .login-container {
        background-color: #121620; padding: 3rem; border-radius: 16px;
        border: 1px solid #21262D; box-shadow: 0 8px 32px rgba(59, 130, 246, 0.15);
        text-align: center; margin-top: 2rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #121620 !important; border: 1px solid #21262D !important;
        border-radius: 12px !important; padding: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4) !important;
    }
    .buque-card {
        background-color: #121620; border: 1px solid #21262D; border-radius: 12px;
        padding: 1.25rem; box-shadow: 0 4px 12px rgba(0,0,0,0.35); margin-bottom: 1.2rem;
        transition: transform 0.2s, border-color 0.2s;
    }
    .buque-card:hover { transform: translateY(-3px); border-color: #3B82F6; }
    
    .buque-card-interes {
        background-color: #121620; border: 1.5px solid #EF4444; border-radius: 12px;
        padding: 1.25rem; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.15); margin-bottom: 1.2rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .buque-card-interes:hover { transform: translateY(-3px); box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3); }
    .stChatMessage { background-color: rgba(18, 22, 32, 0.3) !important; border: 1px solid #21262D !important; border-radius: 12px !important; margin-bottom: 12px !important; padding: 1rem !important; }
    [data-testid="chatAvatarIcon-user"] { background-color: #2563EB !important; }
    [data-testid="chatAvatarIcon-assistant"] { background-color: #10B981 !important; }
    .stChatInputContainer { border-color: #21262D !important; border-radius: 12px !important; background-color: #121620 !important; }
    .sidebar-content { display: flex; flex-direction: column; justify-content: space-between; height: 85vh; }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN INTACTO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            st.markdown('<div class="login-container"><div style="text-align: center; margin-bottom: 1.5rem;"><span style="font-size: 3rem;">⚓</span><h2 style="color: #F8FAFC; margin: 10px 0 0 0; font-weight: 700;">ACCESO PORTAL RBPE</h2><p style="color: #8E9CAE; font-size: 0.9rem; margin-top: 5px;">Sistema Táctico de Control Marítimo</p></div>', unsafe_allow_html=True)
            with st.form("login_form"):
                usuario = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
                clave = st.text_input("🔑 Contraseña", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
                if submit:
                    if usuario in st.secrets["passwords"] and clave == st.secrets["passwords"][usuario]:
                        st.session_state["password_correct"] = True
                        st.session_state["usuario_actual"] = usuario
                        st.rerun()
                    else: st.error("❌ Credenciales incorrectas.")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True

if not check_password(): st.stop()

# --- CARGAR DATOS DESDE SUPABASE ---
@st.cache_data(ttl=60)
def cargar_datos_vessel_view():
    # Cruzamos la tabla identidad con los datos físicos del maestro y los catálogos en una sola consulta limpia
    query = supabase.table("buques_identidad").select(
        "id_buque, nombre, mmsi, mmsi_2, indicativo_llamada, riesgo, id_propietario, "
        "buques_maestro(imo, eslora, arqueo_bruto, fecha_construccion), "
        "cat_banderas(nombre), cat_tipos_pesca(nombre)"
    ).execute()
    
    registros = []
    for item in query.data:
        maestro = item.get("buques_maestro") or {}
        bandera_obj = item.get("cat_banderas") or {}
        tipo_obj = item.get("cat_tipos_pesca") or {}
        
        registros.append({
            "id_buque": item.get("id_buque"),
            "Nombre": item.get("nombre"),
            "MMSI": item.get("mmsi"),
            "MMSI_2": item.get("mmsi_2"),
            "Indicativo de llamada": item.get("indicativo_llamada"),
            "Riesgo": item.get("riesgo"),
            "Propietario_id": item.get("id_propietario"),
            "Bandera": bandera_obj.get("nombre", "-"),
            "Tipo": tipo_obj.get("nombre", "-"),
            "IMO": maestro.get("imo", "-"),
            "Eslora": maestro.get("eslora", "-"),
            "Arqueo bruto": maestro.get("arqueo_bruto", "-"),
            "Fecha de construccion": maestro.get("fecha_construccion", "-")
        })
    return pd.DataFrame(registros)

if "buques_df" not in st.session_state:
    st.session_state.buques_df = cargar_datos_vessel_view()

buques = st.session_state.buques_df

# --- TARJETAS KPI ---
def kpi_card(titulo, valor, color_borde):
    st.markdown(f"""
    <div style="background-color: #121620; padding: 1.2rem; border-radius: 12px; border-left: 5px solid {color_borde}; border-top: 1px solid #21262D; border-right: 1px solid #21262D; border-bottom: 1px solid #21262D; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4); width: 100%;">
        <p style="color: #8E9CAE; margin: 0; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px;">{titulo}</p>
        <h2 style="color: #F8FAFC; margin: 6px 0 0 0; font-size: 2.1rem; font-weight: 700;">{valor}</h2>
    </div>
    """, unsafe_allow_html=True)

# --- VENTANA MODAL ENLAZADA A HISTORIALES REALES ---
@st.dialog("Ficha de Identificación de Buque", width="large")
def abrir_modal_buque(b):
    es_alto_riesgo = str(b.get('Riesgo', '')).lower() == "alto"
    alerta_html = '<span style="background-color: rgba(239,68,68,0.15); color: #F87171; padding: 6px 16px; border-radius: 20px; border: 1px solid rgba(239,68,68,0.4); font-weight: bold; font-size: 11px;">🚨 ALERTA DE INTERÉS</span>' if es_alto_riesgo else '<span style="background-color: rgba(16,185,129,0.15); color: #34D399; padding: 6px 16px; border-radius: 20px; border: 1px solid rgba(16,185,129,0.4); font-weight: bold; font-size: 11px;">✅ OPERACIÓN STANDARD</span>'
    
    st.markdown(f"""
    <div style="background-color: #121620; padding: 20px; border-radius: 12px; border: 1px solid #21262D; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <h2 style="color: #60A5FA; margin: 0;">🚢 {b.get('Nombre', '-')}</h2>
            <p style="color: #8E9CAE; margin: 5px 0 0 0;">Bandera: <span style="color: white; font-weight: 600;">{b.get('Bandera', '-')}</span> &nbsp;|&nbsp; Tipo: <span style="color: white; font-weight: 600;">{b.get('Tipo', '-')}</span></p>
        </div>
        <div>{alerta_html}</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background-color: #0B0E14; padding: 18px; border-radius: 10px; border: 1px solid #21262D;">
            <h4 style="color: #8E9CAE; border-bottom: 1px solid #21262D; padding-bottom: 10px; margin-top:0;">⚓ IDENTIFICACIÓN</h4>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE;"><span>MMSI</span> <strong style="color:white; font-family:monospace;">{b.get('MMSI', '-')}</strong></p>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE;"><span>IMO</span> <strong style="color:white; font-family:monospace;">{b.get('IMO', '-')}</strong></p>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE;"><span>Señal</span> <strong style="color:white; font-family:monospace;">{b.get('Indicativo de llamada', '-')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="background-color: #0B0E14; padding: 18px; border-radius: 10px; border: 1px solid #21262D;">
            <h4 style="color: #8E9CAE; border-bottom: 1px solid #21262D; padding-bottom: 10px; margin-top:0;">📊 CARACTERÍSTICAS</h4>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE;"><span>Eslora</span> <strong style="color:white;">{b.get('Eslora', '-')} m</strong></p>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE;"><span>Arqueo</span> <strong style="color:white;">{b.get('Arqueo bruto', '-')} GT</strong></p>
            <p style="display:flex; justify-content:space-between; color:#8E9CAE;"><span>Riesgo</span> <strong style="color:white;">{b.get('Riesgo', '-')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("### 📋 Historial de Operaciones Cruzado")
    # CONSULTA REAL DEL HISTORIAL OPERATIVO
    ops_query = supabase.table("operaciones").select("*").eq("id_buque", b.get("id_buque")).execute()
    if ops_query.data:
        st.dataframe(pd.DataFrame(ops_query.data)[["fecha_zarpada", "puerto_origen", "area_ingreso", "fecha_egreso"]], use_container_width=True)
    else:
        st.info("Sin registros operativos en la base de datos.")

    if st.button("Cerrar Ficha", use_container_width=True):
        st.session_state.selected_buque = None
        st.rerun()

if "selected_buque" in st.session_state and st.session_state.selected_buque is not None:
    abrir_modal_buque(st.session_state.selected_buque)

# --- SIDEBAR REDISEÑADO ---
with st.sidebar:
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    with st.container():
        st.markdown("<br>", unsafe_allow_html=True)
        col_esc, col_title = st.columns([1, 3.2])
        with col_esc: st.markdown('<div style="background-color:#1E3A8A; width:45px; height:45px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:22px;">⚓</div>', unsafe_allow_html=True)
        with col_title: st.markdown('<h3 style="margin:0; color:white; line-height:1.2; font-weight: 700; font-size: 1.3rem;">Portal <span style="color:#3B82F6;">RBPE</span></h3><span style="color: #8E9CAE; font-size: 0.72rem;">CONTROL MARÍTIMO</span>', unsafe_allow_html=True)
        
        st.markdown(f'<div style="background-color: #121620; border: 1px solid #21262D; border-radius: 12px; padding: 12px 15px; display: flex; align-items: center; gap: 12px; margin-top: 15px;"><div style="background-color: #21262D; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;">👤</div><div><p style="margin:0; color:white; font-size:0.85rem; font-weight:700;">{st.session_state["usuario_actual"]}</p><div style="display: flex; align-items: center; gap: 6px;"><span style="background-color: #10B981; width: 8px; height: 8px; border-radius: 50%; display: inline-block;"></span><span style="color: #10B981; font-size: 0.75rem;">Online</span></div></div></div>', unsafe_allow_html=True)
        
        menu = option_menu(menu_title=None, options=["Panel de Control", "Base de Datos", "Analista IA"], icons=["grid-fill", "server", "cpu-fill"], default_index=0,
            styles={"container": {"padding": "0!important", "background-color": "transparent"}, "icon": {"color": "#60A5FA", "font-size": "18px"}, "nav-link": {"color": "#8E9CAE", "font-size": "14px", "text-align": "left", "margin": "8px 0", "border-radius": "8px"}, "nav-link-selected": {"background-color": "#2563EB"}})
            
    with st.container():
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MÓDULO 1: PANEL DE CONTROL
# ==========================================
if menu == "Panel de Control":
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px; font-weight: 700;'>Panel de Inteligencia Marítima</h2>", unsafe_allow_html=True)
    
    total_gral = len(buques)
    total_pesqueros = len(buques[buques["Tipo"].str.upper().isin(["ARRASTRERO", "POTERO", "PALANGRERO", "POLIVALENTE"])])
    banderas_activas = buques["Bandera"].nunique()
    alertas_activas = len(buques[buques["Riesgo"].str.lower() == "alto"])

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Flota General", total_gral, "#3B82F6")
    with c2: kpi_card("Buques Pesqueros", total_pesqueros, "#8B5CF6")
    with c3: kpi_card("Banderas Pesqueras", banderas_activas, "#10B981")
    with c4: kpi_card("Alertas de Riesgo", alertas_activas, "#EF4444")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        with st.container(border=True):
            st.markdown("<h4 style='color: #E2E8F0; margin-bottom: 10px;'>Flota Pesquera por Bandera</h4>", unsafe_allow_html=True)
            if not buques.empty:
                conteo_banderas = buques["Bandera"].value_counts().reset_index()
                conteo_banderas.columns = ["Bandera", "Cantidad"]
                fig_bar = px.bar(conteo_banderas.head(10), x='Bandera', y='Cantidad', color='Cantidad', color_continuous_scale=["#00e5ff", "#2563eb"], text_auto=True)
                fig_bar.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, coloraxis_showscale=False)
                st.plotly_chart(fig_bar, use_container_width=True)
    with col_graf2:
        with st.container(border=True):
            st.markdown("<h4 style='color: #E2E8F0; margin-bottom: 10px;'>Distribución por Tipo de Pesquero</h4>", unsafe_allow_html=True)
            if not buques.empty:
                conteo_tipos = buques["Tipo"].value_counts().reset_index()
                conteo_tipos.columns = ["Tipo", "Cantidad"]
                fig_pie = px.pie(conteo_tipos, values='Cantidad', names='Tipo', hole=0.6, color_discrete_sequence=["#22d3ee", "#0891b2", "#155e75"])
                fig_pie.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
                st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# MÓDULO 2: BASE DE DATOS
# ==========================================
elif menu == "Base de Datos":
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 15px;'>Directorio General Táctico</h2>", unsafe_allow_html=True)
    busqueda = st.text_input("🔍 Buscador Táctico Real", placeholder="Filtre por Nombre, MMSI, IMO, Bandera...")
    
    b_filtrados = buques.copy()
    if busqueda:
        mask = b_filtrados.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        b_filtrados = b_filtrados[mask]

    total_resultados = len(b_filtrados)
    st.markdown(f"<p style='color: #3B82F6;'>{total_resultados} Buques Activos en Supabase</p>", unsafe_allow_html=True)

    cartas_por_pagina = 12
    paginas_totales = max(1, (total_resultados + cartas_por_pagina - 1) // cartas_por_pagina)
    pagina_actual = st.number_input(f"Página (1 de {paginas_totales})", min_value=1, max_value=paginas_totales, value=1)
    
    inicio_idx = (pagina_actual - 1) * cartas_por_pagina
    b_pagina = b_filtrados.iloc[inicio_idx:inicio_idx + cartas_por_pagina]

    num_columnas = 3
    rows = [b_pagina.iloc[i:i + num_columnas] for i in range(0, len(b_pagina), num_columnas)]

    for row_df in rows:
        cols_grid = st.columns(num_columnas)
        for i, (_, b) in enumerate(row_df.iterrows()):
            with cols_grid[i]:
                es_interes = str(b.get('Riesgo', '')).lower() == "alto"
                card_class = "buque-card-interes" if es_interes else "buque-card"
                badge_html = '<span style="background-color: rgba(239, 68, 68, 0.2); color: #F87171; padding: 2.5px 10px; border-radius: 12px; font-size: 10px; font-weight: 700;">ALTO RIESGO</span>' if es_interes else '<span style="background-color: rgba(16, 185, 129, 0.15); color: #34D399; padding: 2.5px 10px; border-radius: 12px; font-size: 10px; font-weight: 700;">STANDARD</span>'
                
                st.markdown(f"""
                <div class="{card_class}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4 style="color: #60A5FA; margin: 0; font-family: monospace;">🚢 {b.get('Nombre', '-')}</h4>
                        {badge_html}
                    </div>
                    <div style="font-size: 0.85rem; color: #8E9CAE; line-height: 1.5; margin-bottom: 12px;">
                        <strong>Bandera:</strong> {b.get('Bandera', '-')}<br>
                        <strong>Tipo:</strong> {b.get('Tipo', '-')}<br>
                        <strong>ID Buque:</strong> {b.get('id_buque', '-')}
                    </div>
                    <div style="border-top: 1px solid #21262D; padding-top: 10px; font-size: 0.78rem; font-family: monospace; color: #64748B;">
                        MMSI: {b.get('MMSI', '-')} &nbsp;|&nbsp; IMO: {b.get('IMO', '-')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🔎 Ver Ficha - {b.get('Nombre')}", key=f"btn_{b.get('id_buque')}", use_container_width=True):
                    st.session_state.selected_buque = b
                    st.rerun()

# ==========================================
# MÓDULO 3: AGENTE IA CON ESCRITURA REAL EN SUPABASE
# ==========================================
elif menu == "Analista IA":
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role": "assistant", "content": "Saludos, Operador Marcelo. Estoy conectado a Supabase en tiempo real. Ahora puedo ejecutar órdenes reales de actualización sobre la flota."}]

    st.markdown("<h3 style='color: white;'>🤖 Agente Analista Táctico Real</h3>", unsafe_allow_html=True)

    def renderizar_respuesta_inteligente(texto_crudo, df_base):
        # PARSEAR ACCIONES DE ESCRITURA REAL EN SUPABASE
        patron_accion = r"\[DB_ACTION:\s*UPDATE\s*KEY=\"(.*?)\"\s*FIELD=\"(.*?)\"\s*VALUE=\"(.*?)\"\]"
        acciones = re.findall(patron_accion, texto_crudo)
        
        for id_buque, campo, nuevo_valor in acciones:
            campo_db = "riesgo" if campo == "Riesgo" else campo
            try:
                # ¡MAGIA! Escritura real en Supabase
                supabase.table("buques_identidad").update({campo_db: nuevo_valor}).eq("id_buque", id_buque).execute()
                st.toast(f"💾 [SUPABASE REAL] ¡Id {id_buque} actualizado con {campo_db}='{nuevo_valor}'!")
            except Exception as db_err:
                st.error(f"Error escribiendo en base de datos: {db_err}")
        
        texto_limpio = re.sub(r"\[DB_ACTION:.*?\]", "", texto_crudo)
        
        # Renderizado de bloques Python/Charts nativos
        partes_python = re.split(r"```python\s*(.*?)\s*
```", texto_limpio, flags=re.DOTALL)
        for idx, parte in enumerate(partes_python):
            if idx % 2 == 1:
                try:
                    v_locales = {"df": df_base, "px": px, "go": go, "pd": pd}
                    exec(parte, {}, v_locales)
                    fig = v_locales.get("fig")
                    if fig is not None: st.plotly_chart(fig, use_container_width=True)
                except Exception as e: st.error(f"Error de gráfico: {e}")
            else:
                st.markdown(parte)

    for mensaje in st.session_state.chat_history:
        with st.chat_message(mensaje["role"]):
            renderizar_respuesta_inteligente(mensaje["content"], buques)

    if prompt := st.chat_input("Escriba un comando (ej: 'Cambia el riesgo a Alto del buque con ID XXXXXXX')..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando nodo central..."):
                datos_ia = buques.to_csv(index=False)
                contexto_oculto = f"""
                Eres un analista naval corporativo militar. Tienes acceso a esta base de datos en CSV:
                {datos_ia}
                
                Instrucciones:
                1. El año actual es 2026.
                2. Si te piden cambiar o modificar el riesgo de un buque, genera al final de tu respuesta de éxito la etiqueta estricta:
                   [DB_ACTION: UPDATE KEY="id_buque_valor" FIELD="Riesgo" VALUE="Alto" o "Bajo" o "Medio"]
                Pregunta: {prompt}
                """
                respuesta = modelo_ia.generate_content(contexto_oculto)
                renderizar_respuesta_inteligente(respuesta.text, buques)
                st.session_state.chat_history.append({"role": "assistant", "content": respuesta.text})
                if "[DB_ACTION:" in respuesta.text:
                    st.cache_data.clear() # Limpiamos caché para forzar recarga de Supabase
                    st.session_state.buques_df = cargar_datos_vessel_view()
                    st.rerun()
