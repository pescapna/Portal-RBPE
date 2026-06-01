import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM ---
st.set_page_config(page_title="Charly - Comando Táctico", page_icon="⚓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #07090E; color: #E2E8F0; }
    .stApp { background-color: #07090E; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .stChatMessage {
        background: rgba(22, 27, 34, 0.6) !important;
        border: 1px solid rgba(48, 54, 61, 0.8) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.2rem !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SISTEMA DE LOGIN ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><h2 style='text-align:center; color: #F8FAFC; font-weight: 800; letter-spacing: 1px;'>⚓ COMANDO RBPE</h2>", unsafe_allow_html=True)
        user_input = st.text_input("Identificación de Operador")
        pass_input = st.text_input("Código de Acceso", type="password")
        if st.button("INICIAR SESIÓN TÁCTICA", use_container_width=True):
            # Verifica en los secrets de Streamlit
            if user_input in st.secrets["passwords"] and pass_input == st.secrets["passwords"][user_input]:
                st.session_state["password_correct"] = True
                st.session_state["user"] = user_input.capitalize()
                st.rerun()
            else: 
                st.error("Acceso denegado.")
    st.stop()

operador = st.session_state["user"]

# --- 3. CONEXIÓN DE INFRAESTRUCTURA ---
@st.cache_resource
def init_connections():
    supa = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    return supa

supabase = init_connections()

# --- 4. HERRAMIENTAS TÁCTICAS (FUNCIONES PARA LA IA) ---
def buscar_perfil_buque(identificador: str) -> dict:
    """
    Busca información detallada de un buque por su nombre o número MMSI.
    Devuelve datos de identidad, bandera, tipo de pesca y empresa.
    """
    try:
        res = supabase.table("buques_identidad").select(
            "id_buque, nombre, mmsi, riesgo, indicativo_llamada, "
            "cat_banderas(nombre), cat_tipos_pesca(nombre), cat_empresas(nombre)"
        ).or_(f"nombre.ilike.%{identificador}%,mmsi.eq.{identificador}").execute()
        
        if not res.data:
            return {"status": "error", "mensaje": f"No se encontró el buque: {identificador}"}
        
        id_buque = res.data[0]['id_buque']
        res_maestro = supabase.table("buques_maestro").select(
            "eslora, arqueo_bruto, fecha_construccion, imo"
        ).eq("id_buque", id_buque).execute()

        return {
            "status": "success", 
            "identidad": res.data, 
            "datos_fisicos": res_maestro.data if res_maestro.data else "No disponibles"
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def consultar_ultimas_operaciones(identificador: str, limite: int = 5) -> dict:
    """
    Obtiene el historial de las últimas operaciones registradas de un buque (puertos, fechas).
    Requiere el nombre o MMSI del buque.
    """
    try:
        res_id = supabase.table("buques_identidad").select("id_buque").or_(f"nombre.ilike.%{identificador}%,mmsi.eq.{identificador}").execute()
        if not res_id.data:
             return {"status": "error", "mensaje": "Buque no encontrado para buscar operaciones."}
             
        id_buque = res_id.data[0]['id_buque']
        res_ops = supabase.table("operaciones").select(
            "puerto_origen, fecha_zarpada, area_ingreso, fecha_ingreso_area, opero_en_zeea, puerto_amarre"
        ).eq("id_buque", id_buque).limit(limite).execute()
        
        return {"status": "success", "operaciones": res_ops.data}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

herramientas_charly = [buscar_perfil_buque, consultar_ultimas_operaciones]

# --- 5. CONFIGURACIÓN DEL AGENTE ---
MODELO_ACTIVO = 'gemini-3.1-flash-lite' # <-- Cambia esto a 'gemini-2.0-flash' si vuelve a dar error 404

model = genai.GenerativeModel(
    model_name=MODELO_ACTIVO, 
    tools=herramientas_charly,
    system_instruction=f"""
    Eres Charly, analista naval táctico. Asistes al Operador {operador}.
    - Usa ESTRICTAMENTE las herramientas proporcionadas para consultar la base de datos.
    - Si la herramienta devuelve un error, infórmalo con claridad militar.
    - NUNCA inventes información.
    - Responde de forma estructurada (usa viñetas o negritas).
    """
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Sistema Táctico en línea.** Operador **{operador}** reconocido. Conexión segura con Supabase establecida. ¿Cuáles son sus órdenes?"}]

# --- 6. INTERFAZ DE CHAT (FRONTEND) ---
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Analista Naval <span style='color: #3B82F6;'>Charly</span></h1>", unsafe_allow_html=True)

for msg in st.session_state.mensajes_ui:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Introduzca comando (ej: 'Dame el perfil del buque ALFA')..."):
    st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando base de datos táctica..."):
            try:
                respuesta = st.session_state.chat.send_message(prompt)
                st.markdown(respuesta.text)
                st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
            except Exception as api_e:
                st.error(f"Error de enlace de comunicaciones: {api_e}")
