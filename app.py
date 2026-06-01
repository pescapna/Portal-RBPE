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

# --- ESTILO DARK ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0B0E14; color: #E2E8F0; }
    .stApp { background-color: #0B0E14; }
    .stChatMessage { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 12px !important; margin-bottom: 1rem !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
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

# --- CARGA Y CRUCE DE DATOS (RELACIONAL) ---
@st.cache_data(ttl=600)
def load_master_view():
    # 1. Traer Identidad con sus relaciones (JOIN de SQL)
    # Esto une buques_identidad con cat_banderas, cat_tipos_pesca y buques_maestro
    r = supabase.table("buques_identidad").select(
        "*, buques_maestro(*), cat_banderas(nombre), cat_tipos_pesca(nombre)"
    ).execute()
    
    flat_data = []
    for i in r.data:
        m = i.get("buques_maestro") or {}
        flat_data.append({
            "ID_Buque": i["id_buque"],
            "Nombre": i["nombre"],
            "MMSI": i["mmsi"],
            "Riesgo": i["riesgo"],
            "Bandera": i["cat_banderas"]["nombre"] if i.get("cat_banderas") else "S/D",
            "Tipo_Pesca": i["cat_tipos_pesca"]["nombre"] if i.get("cat_tipos_pesca") else "S/D",
            "IMO": m.get("imo", "-"),
            "Eslora": m.get("eslora", 0),
            "Arqueo": m.get("arqueo_bruto", 0),
            "Año_Construccion": m.get("fecha_construccion", "-")
        })
    df_id = pd.DataFrame(flat_data)

    # 2. Operaciones
    r_ops = supabase.table("operaciones").select("*").execute()
    df_ops = pd.DataFrame(r_ops.data)

    # 3. ZEEA
    r_zeea = supabase.table("navegaciones_zeea").select("*").execute()
    df_zeea = pd.DataFrame(r_zeea.data)
    
    return df_id, df_ops, df_zeea

df_id, df_ops, df_zeea = load_master_view()

# --- MOTOR DE EJECUCIÓN ---
def execute_agent_logic(response_text):
    python_blocks = re.findall(r"```python\s*(.*?)\s*```", response_text, flags=re.DOTALL)
    for code in python_blocks:
        try:
            local_vars = {"df": df_id, "df_ops": df_ops, "df_zeea": df_zeea, "px": px, "go": go, "pd": pd}
            exec(code, {}, local_vars)
            
            if "fig" in local_vars: 
                st.plotly_chart(local_vars["fig"], use_container_width=True)
            
            if "resultado" in local_vars:
                res = local_vars["resultado"]
                if isinstance(res, pd.DataFrame): st.dataframe(res, use_container_width=True)
                else: st.markdown(f"**Resultado del Análisis:** {res}")
        except Exception as e:
            st.error(f"Error en ejecución táctica: {e}")

    # Limpiar tags y mostrar texto
    clean_text = re.sub(r"\[.*?\]", "", response_text)
    clean_text = re.sub(r"```python.*?```", "", clean_text, flags=re.DOTALL)
    if clean_text.strip():
        st.markdown(clean_text)

# --- CHAT ---
operador = st.session_state["user"]
st.title(f"⚓ Analista Charly")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Hola {operador}. Base de datos relacional RBPE cargada y sincronizada. ¿Qué análisis de flota ejecutamos hoy?"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant": execute_agent_logic(m["content"])
        else: st.markdown(m["content"])

if prompt := st.chat_input("Dime qué buscar o analizar..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # EL PROMPT QUE DEFINE EL CONOCIMIENTO DE LAS TABLAS DE LA IMAGEN
        contexto = f"""Eres Charly, analista naval de {operador}. 
        Tienes acceso a la base de datos RBPE (Supabase) mapeada en 3 DataFrames:

        1. 'df' (Vista Maestra): Es la unión de buques_identidad, buques_maestro, cat_banderas y cat_tipos_pesca.
           Columnas: {df_id.columns.tolist()}
        
        2. 'df_ops' (Operaciones): Historial de movimientos en áreas.
           Columnas: {df_ops.columns.tolist()}
        
        3. 'df_zeea' (Navegaciones ZEEA): Entradas y salidas de la ZEEA.
           Columnas: {df_zeea.columns.tolist()}

        REGLAS PARA CHARLY:
        - Si te preguntan por banderas, usa 'df' y la columna 'Bandera'.
        - Si te preguntan por áreas o temporadas, usa 'df_ops'.
        - Para relacionar un buque con su operación, usa 'ID_Buque' en 'df' y 'id_buque' en 'df_ops'.
        - Para mostrar resultados usa: ```python resultado = ... ```
        - Para gráficos usa: ```python fig = ... ```
        - NO alucines. Si el código devuelve vacío, informa que no hay registros.
        - Año: 2026.
        """
        try:
            response = model.generate_content(contexto + "\nConsulta del Operador: " + prompt)
            execute_agent_logic(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Error de motor: {e}")
