import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
import json

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Charly - Comando Táctico", page_icon="⚓", layout="wide")

@st.cache_resource
def init_connections():
    supa = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    return supa

supabase = init_connections()

# --- 2. HERRAMIENTAS TÁCTICAS (FUNCIONES PARA LA IA) ---

def buscar_perfil_buque(identificador: str) -> dict:
    """
    Busca información detallada de un buque por su nombre o número MMSI.
    Usa esta función cuando el usuario pregunte por un barco en específico.
    Devuelve datos de identidad, bandera, tipo de pesca y empresa.
    """
    try:
        # Hacemos los JOINs con la nueva estructura
        res = supabase.table("buques_identidad").select(
            "id_buque, nombre, mmsi, riesgo, indicativo_llamada, "
            "cat_banderas(nombre), cat_tipos_pesca(nombre), cat_empresas(nombre)"
        ).or_(f"nombre.ilike.%{identificador}%,mmsi.eq.{identificador}").execute()
        
        if not res.data:
            return {"status": "error", "mensaje": f"No se encontró el buque: {identificador}"}
        
        # Si encuentra el buque, buscamos sus datos físicos en buques_maestro
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
    Obtiene el historial de las últimas operaciones registradas de un buque (puertos, fechas, zonas ZEEA).
    Requiere el nombre o MMSI del buque.
    """
    try:
        # Primero obtenemos el id_buque
        res_id = supabase.table("buques_identidad").select("id_buque").or_(f"nombre.ilike.%{identificador}%,mmsi.eq.{identificador}").execute()
        if not res_id.data:
             return {"status": "error", "mensaje": "Buque no encontrado para buscar operaciones."}
             
        id_buque = res_id.data[0]['id_buque']
        
        # Buscamos en la tabla operaciones
        res_ops = supabase.table("operaciones").select(
            "puerto_origen, fecha_zarpada, area_ingreso, fecha_ingreso_area, opero_en_zeea, puerto_amarre"
        ).eq("id_buque", id_buque).limit(limite).execute()
        
        return {"status": "success", "operaciones": res_ops.data}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

# Lista de herramientas que le daremos a Gemini
herramientas_charly = [buscar_perfil_buque, consultar_ultimas_operaciones]

# --- 3. CONFIGURACIÓN DEL AGENTE ---
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash', 
    tools=herramientas_charly,
    system_instruction="""
    Eres Charly, analista naval del Comando RBPE. 
    Tu trabajo es asistir al operador usando estrictamente las herramientas proporcionadas.
    - Si te preguntan por un buque, usa `buscar_perfil_buque`.
    - Si te preguntan qué hizo o dónde operó, usa `consultar_ultimas_operaciones`.
    - Si la herramienta devuelve un error o no encuentra datos, infórmalo con claridad militar.
    - NUNCA inventes información. Si no tienes la herramienta, di que no estás autorizado/capacitado para esa tarea.
    - Responde de forma concisa, estructurada (usa viñetas o negritas) y con tono táctico/naval.
    """
)

if "chat" not in st.session_state:
    # enable_automatic_function_calling=True hace que Gemini ejecute el código Python por detrás automáticamente
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": "⚓ **Sistema Táctico en línea.** Conexión segura con Supabase establecida. ¿Cuáles son sus órdenes?"}]

# --- 4. INTERFAZ DE CHAT (FRONTEND) ---
# Aquí puedes mantener tu CSS personalizado que me mostraste al principio

st.markdown("<h1 style='color: #F8FAFC;'>⚓ Analista Naval <span style='color: #3B82F6;'>Charly</span></h1>", unsafe_allow_html=True)

# Renderizar historial
for msg in st.session_state.mensajes_ui:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Capturar input
if prompt := st.chat_input("Introduzca comando (ej: 'Dame el perfil del buque ALFA' o '¿Dónde operó el MMSI 123456789?')..."):
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
