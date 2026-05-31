import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE", page_icon="🚢", layout="wide")

# --- SISTEMA DE LOGIN ---
def check_password():
    """Devuelve True si el usuario ingresó la contraseña correcta."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<h1 style='text-align: center;'>⚓ Acceso Restringido</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Ingrese sus credenciales del Proyecto RBPE</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                usuario = st.text_input("Usuario")
                clave = st.text_input("Contraseña", type="password")
                submit_button = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
                
                if submit_button:
                    # Verifica contra los secretos de Streamlit
                    if usuario == "admin" and clave == st.secrets["passwords"]["admin"]:
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
        return False
    return True

# Si el login no es correcto, detenemos la ejecución del resto del código
if not check_password():
    st.stop()


# ==========================================
# A PARTIR DE AQUÍ: EL SISTEMA PRINCIPAL
# ==========================================

# 1. Configurar la IA de Gemini
genai.configure(api_key=st.secrets["api"]["gemini_key"])
modelo_ia = genai.GenerativeModel('gemini-pro')

# 2. Conexión a Google Sheets (REEMPLAZA TU ID AQUÍ)
SHEET_ID = "1ef0-OayCrHg4VeNJVkkM8w6t4j0rmBhT91nVfbJFibw" 

@st.cache_data(ttl=60)
def cargar_datos_sheets():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    return df

# Cargar datos
try:
    buques = cargar_datos_sheets()
except Exception as e:
    st.error("⚠️ Error de conexión con la base de datos.")
    st.stop()

# --- DISEÑO VISUAL MEJORADO ---
st.title("🚢 Portal Central - Proyecto RBPE")
st.markdown("*Sistema de Administración y Control Marítimo*")
st.markdown("---")

# Creamos Pestañas de Navegación
tab_dashboard, tab_datos, tab_ia = st.tabs(["📊 Dashboard", "🗄️ Base de Datos", "🤖 Agente IA (Analista)"])

# --- PESTAÑA 1: DASHBOARD ---
with tab_dashboard:
    st.subheader("Métricas Generales")
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total de Buques Extranjeros", value=len(buques))
    if "Bandera" in buques.columns:
        col2.metric(label="Banderas Distintas", value=buques["Bandera"].nunique())
    if "Buque de interes" in buques.columns:
        col3.metric(label="Buques de Interés (SI)", value=len(buques[buques["Buque de interes"] == "SI"]))
    
    st.info("💡 Aquí a futuro agregaremos gráficos de torta y mapas de posicionamiento en vivo.")

# --- PESTAÑA 2: BASE DE DATOS INTERACTIVA ---
with tab_datos:
    st.subheader("Directorio de Buques")
    
    # Filtros visuales en columnas (no en el menú lateral)
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        if "Bandera" in buques.columns:
            lista_banderas = buques["Bandera"].dropna().unique()
            filtro_bandera = st.multiselect("Filtrar por Bandera:", lista_banderas)
    with col_f2:
        if "Tipo" in buques.columns:
            lista_tipos = buques["Tipo"].dropna().unique()
            filtro_tipo = st.multiselect("Filtrar por Tipo de Buque:", lista_tipos)

    # Aplicar filtros
    buques_filtrados = buques.copy()
    if filtro_bandera:
        buques_filtrados = buques_filtrados[buques_filtrados["Bandera"].isin(filtro_bandera)]
    if filtro_tipo:
        buques_filtrados = buques_filtrados[buques_filtrados["Tipo"].isin(filtro_tipo)]

    st.dataframe(buques_filtrados, use_container_width=True, hide_index=True)

# --- PESTAÑA 3: AGENTE IA (El Cerebro) ---
with tab_ia:
    st.subheader("🤖 Agente Analista RBPE")
    st.write("Hazme preguntas sobre la base de datos de buques actuales.")
    
    # Preparamos los datos para que la IA los pueda "leer" (convertimos la tabla a texto)
    # Solo le enviamos un resumen de columnas importantes para no saturar la memoria
    columnas_clave = [col for col in ["Nombre", "MMSI", "Bandera", "Tipo", "Riesgo", "Buque de interes"] if col in buques.columns]
    datos_para_ia = buques[columnas_clave].to_csv(index=False)

    # Chatbox
    pregunta_usuario = st.text_input("Escribe tu consulta (Ej: ¿Cuántos buques poteros hay de bandera China?):")
    
    if st.button("Consultar IA"):
        if pregunta_usuario:
            with st.spinner("Analizando registros..."):
                try:
                    # Le damos el contexto (los datos) y la pregunta a la IA
                    prompt = f"""
                    Eres un analista experto en control marítimo de la Prefectura/Autoridad Pesquera.
                    Aquí tienes la base de datos actual de buques extranjeros en formato CSV:
                    
                    {datos_para_ia}
                    
                    Por favor, responde a esta pregunta del usuario basándote ÚNICAMENTE en estos datos. Sé profesional, claro y conciso:
                    Pregunta: {pregunta_usuario}
                    """
                    
                    respuesta = modelo_ia.generate_content(prompt)
                    st.success("Análisis completado:")
                    st.write(respuesta.text)
                except Exception as e:
                    st.error(f"Error al conectar con la IA: {e}")
        else:
            st.warning("Por favor, escribe una pregunta primero.")
