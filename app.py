import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import re
from supabase import create_client, Client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Portal RBPE - Súper Agente", page_icon="⚓", layout="wide")

# --- CONEXIÓN DE DATOS ---
try:
    # Captura de Secrets
    URL = st.secrets["supabase"]["url"]
    KEY = st.secrets["supabase"]["service_role_key"]
    supabase: Client = create_client(URL, KEY)
    
    # Configuración de IA (Usando el modelo flash más estable)
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    # Cambiamos a 'gemini-1.5-flash' (sin variaciones extrañas)
    modelo_ia = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"⚠️ Error en Configuración de Secrets: {e}")
    st.stop()

# --- ESTILO TÁCTICO PREMIUM ---
st.markdown("""
<style>
    .stApp { background-color: #0B0E14; color: #F1F5F9; }
    .vessel-profile { 
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
        border: 2px solid #3b82f6; border-radius: 15px; padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6); margin: 20px 0;
    }
    .stat-card { background: #161B22; padding: 12px; border-radius: 10px; border: 1px solid #30363D; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def get_data():
    res = supabase.table("buques_identidad").select(
        "id_buque, nombre, mmsi, riesgo, buques_maestro(imo, eslora, arqueo_bruto, fecha_construccion), cat_banderas(nombre), cat_tipos_pesca(nombre)"
    ).execute()
    data = []
    for i in res.data:
        m = i.get("buques_maestro") or {}
        data.append({
            "id_buque": i["id_buque"], "Nombre": i["nombre"], "MMSI": i["mmsi"], "Riesgo": i["riesgo"],
            "IMO": m.get("imo"), "Eslora": m.get("eslora"), "Arqueo": m.get("arqueo_bruto"),
            "Construccion": m.get("fecha_construccion"), 
            "Bandera": i["cat_banderas"]["nombre"] if i.get("cat_banderas") else "-",
            "Tipo": i["cat_tipos_pesca"]["nombre"] if i.get("cat_tipos_pesca") else "-"
        })
    return pd.DataFrame(data)

def draw_vessel(b):
    """Ficha visual de alta gama"""
    color = "#EF4444" if str(b['Riesgo']).lower() == "alto" else "#3B82F6"
    st.markdown(f"""
    <div class="vessel-profile">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1 style="color: #60A5FA; margin:0;">🚢 {b['Nombre']}</h1>
            <div style="background: {color}; padding: 8px 20px; border-radius: 30px; font-weight: bold; color: white;">
                RIESGO {str(b['Riesgo']).upper()}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px;">
            <div class="stat-card"><small style="color:#94A3B8;">BANDERA</small><br><strong>{b['Bandera']}</strong></div>
            <div class="stat-card"><small style="color:#94A3B8;">MMSI</small><br><strong>{b['MMSI']}</strong></div>
            <div class="stat-card"><small style="color:#94A3B8;">IMO</small><br><strong>{b['IMO']}</strong></div>
            <div class="stat-card"><small style="color:#94A3B8;">ESLORA</small><br><strong>{b['Eslora']} m</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- CEREBRO DEL AGENTE ---
def ask_agent(prompt, df):
    sys_msg = f"""
    Eres Marcelo-AI, Analista Táctico Naval. 
    BASE DE DATOS: {df.to_csv(index=False)}
    COMANDOS:
    - Para mostrar un buque: [FICHA: ID_BUQUE]
    - Para actualizar riesgo: [UPDATE: ID_BUQUE, Riesgo, Valor]
    - Para gráficos: Usa bloques ```python e incluye 'fig'
    - Año actual: 2026.
    """
    try:
        response = modelo_ia.generate_content(sys_msg + "\nComando: " + prompt)
        return response.text
    except Exception as e:
        return f"❌ Error de conexión con Gemini: {str(e)}"

def process_response(text, df):
    # Actualizaciones DB
    upd = re.findall(r"\[UPDATE:\s*(.*?),\s*(.*?),\s*(.*?)\]", text)
    for uid, field, val in upd:
        supabase.table("buques_identidad").update({field.strip().lower(): val.strip()}).eq("id_buque", uid.strip()).execute()
        st.success(f"Sincronizado: {uid} actualizado.")
        st.cache_data.clear()

    # Fichas
    fichas = re.findall(r"\[FICHA:\s*(.*?)\]", text)
    for fid in fichas:
        v = df[df['id_buque'] == fid.strip()]
        if not v.empty: draw_vessel(v.iloc[0])

    # Texto y Gráficos
    clean = re.sub(r"\[.*?\]", "", text)
    parts = re.split(r"```python\s*(.*?)\s*```", clean, flags=re.DOTALL)
    for i, p in enumerate(parts):
        if i % 2 == 1:
            try:
                scope = {"df": df, "px": px, "go": go, "pd": pd}
                exec(p, {}, scope)
                if "fig" in scope: st.plotly_chart(scope["fig"], use_container_width=True)
            except: st.error("Error al generar gráfico dinámico.")
        else:
            if p.strip(): st.markdown(p)

# --- UI ---
st.session_state.df = get_data()

with st.sidebar:
    menu = option_menu("RBPE TACTICAL", ["Súper Agente", "Dashboard"], icons=["cpu", "bar-chart"], default_index=0)

if menu == "Súper Agente":
    st.title("🤖 Analista Táctico Marcelo-AI")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Sistema operativo. ¿Qué buque desea analizar?"}]

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            process_response(m["content"], st.session_state.df)

    if p := st.chat_input("Mensaje..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        with st.chat_message("assistant"):
            r = ask_agent(p, st.session_state.df)
            process_response(r, st.session_state.df)
            st.session_state.messages.append({"role": "assistant", "content": r})
