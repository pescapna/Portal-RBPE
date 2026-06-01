import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
import re
from io import StringIO
from supabase import create_client, Client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Charly - Analista Naval", page_icon="⚓", layout="centered")

# --- ESTILO DARK MODERNO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0B0E14; color: #E2E8F0; }
    .stApp { background-color: #0B0E14; }
    .stChatMessage { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 15px !important; margin-bottom: 1rem !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align:center;'>⚓ Acceso RBPE</h2>", unsafe_allow_html=True)
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if user in st.secrets["passwords"] and pw == st.secrets["passwords"][user]:
                st.session_state["password_correct"] = True
                st.session_state["usuario_actual"] = user.capitalize()
                st.rerun()
    st.stop()

# --- CONEXIÓN ---
try:
    URL = st.secrets["supabase"]["url"]
    KEY = st.secrets["supabase"]["service_role_key"]
    supabase = create_client(URL, KEY)
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
except Exception as e:
    st.error(f"Error de sistema: {e}")
    st.stop()

# --- DICCIONARIO DE DATOS PARA CHARLY (AYUDA MEMORIA) ---
DICCIONARIO_TECNICO = """
MAPA DE LA BASE DE DATOS:
1. Tabla 'Identidad': Contiene Nombre, MMSI, IMO, Bandera, Tipo de Pesca y Nivel de Riesgo.
2. Tabla 'Operaciones': Registro de viajes. 
   - Columnas clave: 'temporada', 'fecha_zarpada', 'area_ingreso', 'fecha_egreso'.
   - Columnas de zona (SI/NO): 'operó_en_zeea', 'operó_en_adyacente' (Área Adyacente a la ZEEA), 'operó_en_malvinas', 'operó_en_antartida'.
3. Tabla 'ZEEA': Registros específicos de entrada/salida de la Zona Económica Exclusiva Argentina.
"""

# --- CARGA DE DATOS OPTIMIZADA ---
@st.cache_data(ttl=300) # Caché de 5 minutos para velocidad
def cargar_inteligencia_total():
    # Traemos Identidad y Maestro
    id_res = supabase.table("buques_identidad").select("*, buques_maestro(*), cat_banderas(nombre), cat_tipos_pesca(nombre)").execute()
    df_id = pd.DataFrame(id_res.data)
    
    # Traemos Operaciones (Solo lo necesario para no saturar memoria)
    ops_res = supabase.table("operaciones").select("*").execute()
    df_ops = pd.DataFrame(ops_res.data)
    
    return df_id, df_ops

def ejecutar_acciones(text, df_id, df_ops):
    # Detección de Fichas
    fichas = re.findall(r"\[FICHA:\s*(.*?)\]", text)
    for fid in fichas:
        v = df_id[df_id['id_buque'] == fid.strip()].iloc[0]
        st.info(f"🚢 **Buque:** {v['nombre']} | **Bandera:** {v['cat_banderas']['nombre']} | **Riesgo:** {v['riesgo']}")
        st.write(v.to_dict())

    # Detección de Gráficos/Tablas
    clean_text = re.sub(r"\[.*?\]", "", text)
    partes = re.split(r"```python\s*(.*?)\s*```", clean_text, flags=re.DOTALL)
    for i, p in enumerate(partes):
        if i % 2 == 1:
            try:
                scope = {"df": df_id, "df_ops": df_ops, "px": px, "go": go, "pd": pd}
                exec(p, {}, scope)
                if "fig" in scope: st.plotly_chart(scope["fig"], use_container_width=True)
            except Exception as e: st.error(f"Error visual: {e}")
        else:
            # Procesar tablas CSV que genere Charly
            csv_parts = re.split(r"```csv\s*(.*?)\s*```", p, flags=re.DOTALL)
            for j, csv_p in enumerate(csv_parts):
                if j % 2 == 1:
                    st.dataframe(pd.read_csv(StringIO(csv_p.strip())), use_container_width=True)
                else:
                    if csv_p.strip(): st.markdown(csv_p)

# --- INTERFAZ DE CHAT ---
user_name = st.session_state.get("usuario_actual", "Operador")
st.title(f"⚓ Analista Charly")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Hola {user_name}. Mi motor ha procesado las tablas de identidad y operaciones. Estoy listo para el análisis táctico sin alucinaciones."}]

df_id, df_ops = cargar_inteligencia_total()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        ejecutar_acciones(m["content"], df_id, df_ops)

if prompt := st.chat_input("Consulta a la base de datos..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # Reducimos los datos que enviamos a la IA para ganar velocidad
        # Solo enviamos el resumen de lo que el usuario busca
        relevant_data = ""
        if any(word in prompt.lower() for word in ["tanzania", "kenia", "china", "bandera"]):
            relevant_data = df_id.head(200).to_csv() # Ejemplo de los primeros 200
        else:
            # Si es por operaciones, enviamos resumen de áreas
            relevant_data = df_ops.head(100).to_csv()

        contexto_charly = f"""{DICCIONARIO_TECNICO}
        Instrucciones para Charly:
        - Usuario actual: {user_name}. Año actual: 2026.
        - Tienes prohibido alucinar. Si un dato no está en el CSV adjunto, di: 'No dispongo de esa información'.
        - Para mostrar un buque: [FICHA: ID_BUQUE].
        - Para gráficos: ```python e incluye 'fig'.
        - Para tablas de datos: ```csv.
        
        DATOS RELEVANTES DE LA BASE:
        {relevant_data}
        """
        try:
            res = modelo_ia.generate_content(contexto_charly + f"\nPregunta: " + prompt)
            ejecutar_acciones(res.text, df_id, df_ops)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
        except Exception as e:
            st.error(f"Error de comunicación: {e}")
