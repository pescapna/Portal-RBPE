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

# --- ESTILO MODERNO DARK ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0B0E14; color: #E2E8F0; }
    .stApp { background-color: #0B0E14; }
    .stChatMessage {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 15px !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    .charly-vessel-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border-left: 5px solid #3b82f6;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    }
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-top: 15px; }
    .stat-item { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }
    .stat-label { font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; }
    .stat-value { font-size: 1rem; font-weight: 600; color: #F8FAFC; display: block; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN (Reconoce al usuario) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.write("### Acceso al Sistema RBPE")
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            if st.button("Ingresar"):
                if usuario in st.secrets["passwords"] and clave == st.secrets["passwords"][usuario]:
                    st.session_state["password_correct"] = True
                    st.session_state["usuario_actual"] = usuario.capitalize()
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        return False
    return True

if not check_password():
    st.stop()

# --- CONEXIÓN DE DATOS ---
try:
    URL = st.secrets["supabase"]["url"]
    KEY = st.secrets["supabase"]["service_role_key"]
    supabase: Client = create_client(URL, KEY)
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- FUNCIONES DE CHARLY ---
@st.cache_data(ttl=60)
def cargar_datos_supabase():
    res = supabase.table("buques_identidad").select(
        "id_buque, nombre, mmsi, riesgo, buques_maestro(imo, eslora, arqueo_bruto, fecha_construccion), cat_banderas(nombre), cat_tipos_pesca(nombre)"
    ).execute()
    data = []
    for i in res.data:
        m = i.get("buques_maestro") or {}
        data.append({
            "id_buque": i["id_buque"], "Nombre": i["nombre"], "MMSI": i["mmsi"], "Riesgo": i["riesgo"],
            "IMO": m.get("imo", "-"), "Eslora": m.get("eslora", 0), "Arqueo": m.get("arqueo_bruto", 0),
            "Año": m.get("fecha_construccion", "-"), 
            "Bandera": i["cat_banderas"]["nombre"] if i.get("cat_banderas") else "-",
            "Tipo": i["cat_tipos_pesca"]["nombre"] if i.get("cat_tipos_pesca") else "-"
        })
    return pd.DataFrame(data)

def render_vessel(b):
    color = "#EF4444" if str(b['Riesgo']).lower() == "alto" else "#3B82F6"
    st.markdown(f"""
    <div class="charly-vessel-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h2 style="color: #60A5FA; margin:0;">🚢 {b['Nombre']}</h2>
            <div style="background: {color}; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold;">
                RIESGO {str(b['Riesgo']).upper()}
            </div>
        </div>
        <div class="stat-grid">
            <div class="stat-item"><span class="stat-label">ID BUQUE</span><span class="stat-value">{b['id_buque']}</span></div>
            <div class="stat-item"><span class="stat-label">MMSI</span><span class="stat-value">{b['MMSI']}</span></div>
            <div class="stat-item"><span class="stat-label">Bandera</span><span class="stat-value">{b['Bandera']}</span></div>
            <div class="stat-item"><span class="stat-label">Tipo</span><span class="stat-value">{b['Tipo']}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def ejecutar_comando_charly(texto, df):
    # 1. Actualización de Base de Datos
    updates = re.findall(r"\[UPDATE:\s*(.*?),\s*(.*?),\s*(.*?)\]", texto)
    for uid, field, val in updates:
        columna = field.strip().lower()
        if columna in ["riesgo", "nombre"]:
            supabase.table("buques_identidad").update({columna: val.strip()}).eq("id_buque", uid.strip()).execute()
            st.toast(f"✅ Sincronizado: {uid}")
            st.cache_data.clear()

    # 2. Perfiles Visuales
    fichas = re.findall(r"\[FICHA:\s*(.*?)\]", texto)
    for fid in fichas:
        v = df[df['id_buque'] == fid.strip()]
        if not v.empty: render_vessel(v.iloc[0])

    # 3. Gráficos (Línea 133 Corregida)
    texto_limpio = re.sub(r"\[.*?\]", "", texto)
    partes = re.split(r"```python\s*(.*?)\s*```", texto_limpio, flags=re.DOTALL)
    
    for i, p in enumerate(partes):
        if i % 2 == 1:
            try:
                scope = {"df": df, "px": px, "go": go, "pd": pd}
                exec(p, {}, scope)
                if "fig" in scope: st.plotly_chart(scope["fig"], use_container_width=True)
            except Exception as e:
                st.error(f"Error en gráfico: {e}")
        else:
            if p.strip(): st.markdown(p)

# --- INTERFAZ DE CHAT ---
st.title("⚓ Analista Charly")
usuario_actual = st.session_state.get("usuario_actual", "Operador")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Hola {usuario_actual}, soy Charly. Mi motor está listo para analizar y gestionar la base de datos RBPE. ¿Qué acción deseas realizar hoy?"}]

df_actual = cargar_datos_supabase()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        ejecutar_comando_charly(m["content"], df_actual)

if prompt := st.chat_input("Dime algo..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        cols = ", ".join(df_actual.columns.tolist())
        contexto = f"""Eres Charly, el asistente táctico de {usuario_actual}. Año: 2026.
        OBJETIVO: Ayudar al operador a gestionar la flota RBPE de forma segura.
        DATOS ACTUALES: [{cols}]
        
        REGLAS:
        1. Identifica siempre al usuario como {usuario_actual}.
        2. Explica qué vas a hacer antes de ejecutar un cambio o gráfico.
        3. Para mostrar un buque usa el tag: [FICHA: ID_DEL_BUQUE]
        4. Para editar en Supabase usa el tag: [UPDATE: ID_DEL_BUQUE, riesgo, VALOR]
        5. Los gráficos se crean en bloques ```python usando el dataframe 'df' y el objeto 'fig'.
        6. Guía al usuario paso a paso para evitar errores accidentales en la base de datos.
        """
        try:
            response = modelo_ia.generate_content(contexto + f"\n{usuario_actual}: " + prompt)
            ejecutar_comando_charly(response.text, df_actual)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            if "[UPDATE:" in response.text:
                st.rerun()
        except Exception as e:
            st.error(f"Error en Charly: {e}")
