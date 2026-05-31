import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="🚢", layout="wide", initial_sidebar_state="expanded")

# --- INYECCIÓN DE CSS PARA DISEÑO MODERNO ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilo de Tarjetas de Métricas */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #1e3a8a;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Diseño del Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN MULTIUSUARIO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            with st.container(border=True):
                st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚓ Portal RBPE</h1>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center;'>Acceso Restringido - Nivel 1</p>", unsafe_allow_html=True)
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
# CONFIGURACIÓN DE IA Y BASE DE DATOS
# ==========================================

genai.configure(api_key=st.secrets["api"]["gemini_key"])
modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
SHEET_ID = st.secrets["api"]["sheet_id"]

@st.cache_data(ttl=60)
def cargar_datos_sheets():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    df = df.fillna("-") # Limpiamos celdas vacías
    return df

with st.spinner('Sincronizando con base de datos central...'):
    try:
        buques = cargar_datos_sheets()
    except Exception as e:
        st.error("⚠️ Error de conexión con la base central.")
        st.stop()


# ==========================================
# VENTANA MODAL (LA FICHA DEL BUQUE)
# ==========================================
@st.dialog("🪪 Ficha Técnica del Buque", width="large")
def abrir_modal_buque(datos_buque):
    col_encabezado1, col_encabezado2 = st.columns([3, 1])
    with col_encabezado1:
        st.markdown(f"<h2 style='color: #1e3a8a; margin-bottom: 0;'>{datos_buque.get('Nombre', '-')}</h2>", unsafe_allow_html=True)
        st.markdown(f"**Bandera:** {datos_buque.get('Bandera', '-')} | **Tipo:** {datos_buque.get('Tipo', '-')}")
    with col_encabezado2:
        if str(datos_buque.get('Buque de interes', '')).upper() == "SI":
            st.error("🚨 BUQUE DE INTERÉS")
        else:
            st.success("✅ Standard")
            
    st.divider()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 📡 Identificación")
        st.write(f"**MMSI:** {datos_buque.get('MMSI', '-')}")
        st.write(f"**IMO:** {datos_buque.get('IMO', '-')}")
        st.write(f"**Señal Distintiva:** {datos_buque.get('Indicativo de llamada', '-')}")
        
    with c2:
        st.markdown("#### 📏 Características")
        st.write(f"**Eslora:** {datos_buque.get('Eslora', '-')} m")
        st.write(f"**Arqueo Bruto:** {datos_buque.get('Arqueo bruto', '-')} GT")
        st.write(f"**Construcción:** {datos_buque.get('Fecha de construcción', '-')}")
        
    with c3:
        st.markdown("#### 🏢 Administración")
        st.write(f"**Propietario:** {datos_buque.get('Propietario_id', '-')}")
        st.write(f"**Nivel de Riesgo:** {datos_buque.get('Riesgo', '-')}")
        st.write(f"**Última Modif.:** {datos_buque.get('Fecha de modificación', '-')}")
    
    st.divider()
    if st.button("Cerrar Ficha", use_container_width=True):
        st.rerun()


# ==========================================
# BARRA LATERAL (MENU)
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Flag_of_Argentina.svg/1200px-Flag_of_Argentina.svg.png", width=80)
    st.markdown(f"Hola, **{st.session_state['usuario_actual'].capitalize()}**")
    st.markdown("---")
    menu = st.radio(
        "Navegación Principal",
        ["📊 Panel de Estadísticas", "📋 Directorio de Buques", "🤖 Agente IA"],
        index=0
    )
    st.markdown("---")
    if st.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()


# ==========================================
# MÓDULO 1: PANEL DE ESTADÍSTICAS
# ==========================================
if menu == "📊 Panel de Estadísticas":
    st.title("📊 Panel de Inteligencia Marítima")
    
    # Filtros exclusivos para los gráficos
    with st.expander("⚙️ Filtros para los Gráficos", expanded=False):
        f_bandera = st.multiselect("Filtrar por Bandera:", buques["Bandera"].unique() if "Bandera" in buques.columns else [])
    
    # Aplicar filtro a gráficos
    datos_graficos = buques.copy()
    if f_bandera:
        datos_graficos = datos_graficos[datos_graficos["Bandera"].isin(f_bandera)]

    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Buques en Vista", len(datos_graficos))
    if "Bandera" in datos_graficos.columns:
        col2.metric("Banderas Distintas", datos_graficos[datos_graficos["Bandera"] != "-"]["Bandera"].nunique())
    if "Tipo" in datos_graficos.columns:
        col3.metric("Tipos de Buque", datos_graficos[datos_graficos["Tipo"] != "-"]["Tipo"].nunique())
    if "Buque de interes" in datos_graficos.columns:
        col4.metric("Buques de Interés", len(datos_graficos[datos_graficos["Buque de interes"].astype(str).str.upper() == "SI"]))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráficos
    col_g1, col_g2 = st.columns([1, 1])
    
    with col_g1:
        st.markdown("**Jerarquía: Banderas y Tipos de Buque**")
        if "Bandera" in datos_graficos.columns and "Tipo" in datos_graficos.columns:
            # Gráfico Sunburst (Anillos) agrupando datos
            df_agrupado = datos_graficos[datos_graficos["Bandera"] != "-"].groupby(['Bandera', 'Tipo']).size().reset_index(name='Cantidad')
            fig_sun = px.sunburst(df_agrupado, path=['Bandera', 'Tipo'], values='Cantidad', color='Bandera')
            fig_sun.update_layout(margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)
            
    with col_g2:
        st.markdown("**Top 10 Banderas con Mayor Flota**")
        if "Bandera" in datos_graficos.columns:
            top_banderas = datos_graficos[datos_graficos["Bandera"] != "-"]["Bandera"].value_counts().head(10).reset_index()
            top_banderas.columns = ["Bandera", "Cantidad"]
            fig_bar = px.bar(top_banderas, x='Bandera', y='Cantidad', text_auto=True, color='Bandera')
            fig_bar.update_layout(margin=dict(t=10, l=10, r=10, b=10), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)


# ==========================================
# MÓDULO 2: DIRECTORIO DE BUQUES
# ==========================================
elif menu == "📋 Directorio de Buques":
    st.title("📋 Directorio General de Buques")
    st.info("💡 **Instrucción:** Haz clic en la casilla a la izquierda de cualquier buque para abrir su ficha completa.")
    
    # Buscador Global (Busca en TODAS las columnas)
    busqueda_global = st.text_input("🔍 Buscador Global (Escriba un Nombre, IMO, MMSI, Bandera, etc.):", placeholder="Ej: LU RONG YUAN, 412331182, POTERO...")
    
    b_filtrados = buques.copy()
    
    if busqueda_global:
        # Crea una máscara que busca el texto en toda la base de datos convertida a texto
        mask = b_filtrados.astype(str).apply(lambda x: x.str.contains(busqueda_global, case=False, na=False)).any(axis=1)
        b_filtrados = b_filtrados[mask]
        
    st.caption(f"Mostrando {len(b_filtrados)} resultados.")

    # La Tabla con selección interactiva (Esta es la nueva magia de Streamlit)
    columnas_mostrar = [col for col in ["Nombre", "Bandera", "Tipo", "MMSI", "IMO", "Riesgo"] if col in b_filtrados.columns]
    
    evento_seleccion = st.dataframe(
        b_filtrados[columnas_mostrar],
        use_container_width=True,
        hide_index=True,
        height=500,
        on_select="rerun", # Esto recarga la app al hacer clic
        selection_mode="single-row" # Solo permite seleccionar uno a la vez
    )
    
    # Si el usuario seleccionó una fila de la tabla, se abre la ventana modal
    if evento_seleccion and len(evento_seleccion.selection.rows) > 0:
        indice_fila = evento_seleccion.selection.rows[0]
        # Recuperamos todos los datos de ese buque (incluyendo las columnas ocultas)
        buque_seleccionado = b_filtrados.iloc[indice_fila]
        abrir_modal_buque(buque_seleccionado)


# ==========================================
# MÓDULO 3: AGENTE IA
# ==========================================
elif menu == "🤖 Agente IA":
    st.title("🤖 Centro de Análisis IA")
    
    col_ia1, col_ia2 = st.columns([1, 2.5])
    with col_ia1:
        st.image("https://cdn-icons-png.flaticon.com/512/8649/8649603.png", width=150)
        st.markdown("### Asistente Virtual")
        st.info("Conectado a la base de datos central en tiempo real.")
        
    with col_ia2:
        columnas_clave = [col for col in ["Nombre", "MMSI", "Bandera", "Tipo", "Riesgo", "Buque de interes"] if col in buques.columns]
        datos_para_ia = buques[columnas_clave].to_csv(index=False)

        with st.container(border=True):
            pregunta_usuario = st.text_area("¿Qué deseas investigar?", height=120, placeholder="Ejemplo: Resume la cantidad de buques por bandera y dime si hay algún buque de interés.")
            
            if st.button("🧠 Ejecutar Análisis", type="primary", use_container_width=True):
                if pregunta_usuario:
                    with st.spinner("El agente está analizando los registros..."):
                        try:
                            prompt = f"Eres un analista de control marítimo. Base de datos:\n{datos_para_ia}\n\nConsulta: {pregunta_usuario}\nResponde SOLO basado en los datos de forma profesional."
                            respuesta = modelo_ia.generate_content(prompt)
                            st.success("Análisis completado")
                            st.markdown(f"**Resultado:**\n\n> {respuesta.text}")
                        except Exception as e:
                            st.error(f"Error IA: {e}")
                else:
                    st.warning("Por favor, escribe una consulta.")
