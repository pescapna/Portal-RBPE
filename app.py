import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
import re
from io import StringIO
from supabase import create_client, Client

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Charly - Inteligencia Naval", page_icon="⚓", layout="centered")

# --- ESTILO DARK PROFESIONAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0B0E14; color: #E2E8F0; }
    .stApp { background-color: #0B0E14; }
    .stChatMessage { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 12px !important; }
    .vessel-card { background: linear-gradient(145deg, #1e293b, #0f172a); border-radius: 12px; padding: 20px; border-left: 5px solid #3b82f6; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- LOGIN DINÁMICO ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align:center;'>⚓ Acceso RBPE</h2>", unsafe_allow_html=True)
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if user_input in st.secrets["passwords"] and pass_input == st.secrets["passwords"][user_input]:
                st.session_state["password_correct"] = True
                st.session_state["user"] = user_input.capitalize()
                st.rerun()
            else: st.error("Acceso denegado.")
    st.stop()

# --- CONEXIÓN ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])

supabase = init_connection()
genai.configure(api_key=st.secrets["api"]["gemini_key"])
model = genai.GenerativeModel('gemini-3.1-flash-lite')

# --- CARGA MASIVA DE DATOS (EL CEREBRO) ---
@st.cache_data(ttl=600)
def load_all_data():
    # 1. Identidad
    r1 = supabase.table("buques_identidad").select("*, buques_maestro(*), cat_banderas(nombre), cat_tipos_pesca(nombre)").execute()
    df_id = pd.DataFrame(r1.data)
    # 2. Operaciones
    r2 = supabase.table("operaciones").select("*").execute()
    df_ops = pd.DataFrame(r2.data)
    # 3. ZEEA
    r3 = supabase.table("navegaciones_zeea").select("*").execute()
    df_zeea = pd.DataFrame(r3.data)
    
    return df_id, df_ops, df_zeea

df_id, df_ops, df_zeea = load_all_data()

# --- MOTOR DE EJECUCIÓN DEL AGENTE ---
def execute_agent_logic(response_text):
    """Detecta y ejecuta las herramientas que Charly decide usar"""
    # 1. Ejecutar código Python (Análisis, Gráficos, Filtros)
    python_blocks = re.findall(r"```python\s*(.*?)\s*```", response_text, flags=re.DOTALL)
    for code in python_blocks:
        try:
            # Charly opera sobre los dataframes cargados
            local_vars = {"df_id": df_id, "df_ops": df_ops, "df_zeea": df_zeea, "px": px, "go": go, "pd": pd}
            exec(code, {}, local_vars)
            if "fig" in local_vars: st.plotly_chart(local_vars["fig"], use_container_width=True)
            if "result_df" in local_vars: st.dataframe(local_vars["result_df"], use_container_width=True)
        except Exception as e:
            st.error(f"Error de ejecución: {e}")

    # 2. Actualizaciones en Supabase
    updates = re.findall(r"\[UPDATE:\s*(.*?),\s*(.*?),\s*(.*?)\]", response_text)
    for uid, col, val in updates:
        supabase.table("buques_identidad").update({col.strip(): val.strip()}).eq("id_buque", uid.strip()).execute()
        st.toast(f"Dato actualizado en Supabase: {uid}")

    # 3. Texto plano (Limpiar comandos para mostrar solo la respuesta)
    clean_text = re.sub(r"\[.*?\]", "", response_text)
    clean_text = re.sub(r"```python.*?```", "", clean_text, flags=re.DOTALL)
    if clean_text.strip():
        st.markdown(clean_text)

# --- INTERFAZ DE CHAT ---
current_user = st.session_state["user"]
st.title(f"⚓ Analista Charly")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Hola {current_user}. Estoy conectado a las tablas de Identidad, Operaciones y ZEEA. Tengo autonomía total para cruzar datos y generar informes. ¿Qué misión tenemos?"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant":
            execute_agent_logic(m["content"])
        else:
            st.markdown(m["content"])

if prompt := st.chat_input("Órdenes para Charly..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # EL PROMPT DEFINITIVO: Charly es el dueño del código
        agent_instruction = f"""
        Eres Charly, el Agente Autónomo de Inteligencia Naval para el operador {current_user}.
        Tu entorno de trabajo tiene 3 DataFrames de Pandas cargados:
        1. 'df_id': Identidad, banderas, tipos de pesca y riesgo.
        2. 'df_ops': Historial de operaciones, áreas (adyacente, Malvinas, etc.) y temporadas.
        3. 'df_zeea': Registros de entrada y salida de la ZEEA.

        REGLAS DE ORO:
        - NO ADIVINES. Si necesitas saber algo, escribe código Python para filtrar los dataframes.
        - Para mostrar resultados tabulares, guarda el filtro en una variable llamada 'result_df'.
        - Para gráficos, usa Plotly y guarda el objeto en 'fig'.
        - Si el usuario pide cambiar un dato, usa: [UPDATE: ID_BUQUE, columna, valor].
        - Eres un agente de ALTA PRECISIÓN. Si no hay datos tras ejecutar el filtro, informa que no hay registros.
        - El año actual es 2026.
        """
        
        try:
            response = model.generate_content(agent_instruction + "\nComando del Operador: " + prompt)
            execute_agent_logic(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Falla en el motor de IA: {e}")
