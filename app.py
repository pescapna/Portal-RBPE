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
st.set_page_config(page_title="Marcelo-AI: Inteligencia Naval", page_icon="⚓", layout="wide")

# --- CONEXIÓN DE DATOS ---
try:
    URL = st.secrets["supabase"]["url"]
    KEY = st.secrets["supabase"]["service_role_key"]
    supabase: Client = create_client(URL, KEY)
    
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    # Usamos el modelo estable. Si prefieres 'gemini-1.5-flash', cámbialo aquí.
    modelo_ia = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"⚠️ Error de configuración: {e}")
    st.stop()

# --- CSS: DARK PREMIUM TACTICAL ---
st.markdown("""
<style>
    .stApp { background-color: #0B0E14; color: #F1F5F9; }
    .stChatMessage { background-color: #121620 !important; border: 1px solid #21262D !important; border-radius: 12px !important; }
    
    /* Ficha Estilizada de Buque */
    .vessel-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #3b82f6; border-radius: 15px; padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6); margin: 20px 0;
    }
    .grid-ficha { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px; }
    .stat-item { background: rgba(22, 27, 34, 0.8); padding: 12px; border-radius: 10px; border: 1px solid #30363D; text-align: center; }
    .stat-val { color: #F8FAFC; font-size: 1.3rem; font-weight: 700; display: block; }
    .stat-lab { color: #94A3B8; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_todo():
    # Traemos buques + datos maestros + catálogos en un solo join
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

def render_ficha(b):
    """Genera la ficha visual tipo sistema militar"""
    riesgo_color = "#EF4444" if str(b['Riesgo']).lower() == "alto" else "#3B82F6"
    st.markdown(f"""
    <div class="vessel-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: #60A5FA; margin:0; font-family: monospace;">🚢 {b['Nombre']}</h1>
                <small style="color: #64748B;">ID: {b['id_buque']}</small>
            </div>
            <div style="background: {riesgo_color}; padding: 8px 20px; border-radius: 30px; font-weight: 900; color: white;">
                RIESGO {str(b['Riesgo']).upper()}
            </div>
        </div>
        <div class="grid-ficha">
            <div class="stat-item"><span class="stat-lab">Bandera</span><span class="stat-val">{b['Bandera']}</span></div>
            <div class="stat-item"><span class="stat-lab">MMSI</span><span class="stat-val">{b['MMSI']}</span></div>
            <div class="stat-item"><span class="stat-lab">IMO</span><span class="stat-val">{b['IMO']}</span></div>
            <div class="stat-item"><span class="stat-lab">Tipo</span><span class="stat-val">{b['Tipo']}</span></div>
            <div class="stat-item"><span class="stat-lab">Eslora</span><span class="stat-val">{b['Eslora']}m</span></div>
            <div class="stat-item"><span class="stat-lab">Arqueo</span><span class="stat-val">{b['Arqueo']}GT</span></div>
            <div class="stat-item"><span class="stat-lab">Construcción</span><span class="stat-val">{b['Año']}</span></div>
            <div class="stat-item"><span class="stat-lab">Estatus</span><span class="stat-val" style="color:#10B981;">ACTIVO</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- CEREBRO DEL SÚPER AGENTE ---
def brain(prompt, df_master, df_file=None):
    contexto_archivo = f"\nARCHIVO EXTERNO SUBIDO:\n{df_file.to_csv(index=False)}" if df_file is not None else ""
    
    sys_prompt = f"""
    Eres Marcelo-AI, Súper Agente de Inteligencia Naval RBPE. 
    ESTRUCTURA DE DATOS DISPONIBLE:
    {df_master.to_csv(index=False)}
    {contexto_archivo}
    
    CAPACIDADES TÁCTICAS:
    1. Si te piden datos de un barco, usa: [FICHA: ID_BUQUE]
    2. Si quieres graficar, genera código python con Plotly (usa 'df' y 'fig'): ```python ... ```
    3. Si piden cambiar el riesgo de un barco, usa: [UPDATE: ID_BUQUE, Riesgo, Valor]
    4. El año actual es 2026. Calcula antigüedades basándote en eso.
    5. Puedes recibir y comparar archivos externos con la base de datos de Supabase.
    """
    
    try:
        response = modelo_ia.generate_content(sys_prompt + "\nComando Usuario: " + prompt)
        return response.text
    except Exception as e:
        return f"❌ Error de Inteligencia: {str(e)}"

def parse_response(text, df):
    # 1. Ejecutar Actualizaciones en DB
    upd_matches = re.findall(r"\[UPDATE:\s*(.*?),\s*(.*?),\s*(.*?)\]", text)
    for uid, field, val in upd_matches:
        supabase.table("buques_identidad").update({field.strip().lower(): val.strip()}).eq("id_buque", uid.strip()).execute()
        st.success(f"Sincronización Exitosa: Buque {uid} actualizado.")
        st.cache_data.clear()

    # 2. Renderizar Fichas
    fichas = re.findall(r"\[FICHA:\s*(.*?)\]", text)
    for fid in fichas:
        v_data = df[df['id_buque'] == fid.strip()]
        if not v_data.empty: render_ficha(v_data.iloc[0])

    # 3. Gráficos y Texto
    clean_text = re.sub(r"\[.*?\]", "", text)
    parts = re.split(r"```python\s*(.*?)\s*```", clean_text, flags=re.DOTALL)
    
    for i, p in enumerate(parts):
        if i % 2 == 1:
            try:
                scope = {"df": df, "px": px, "go": go, "pd": pd}
                exec(p, {}, scope)
                if "fig" in scope: st.plotly_chart(scope["fig"], use_container_width=True)
            except Exception as e: st.error(f"Error gráfico: {e}")
        else:
            if p.strip(): st.markdown(p)

# --- INTERFAZ ---
st.session_state.df = cargar_todo()

with st.sidebar:
    st.markdown("<h1 style='text-align:center;'>⚓ RBPE COMMAND</h1>", unsafe_allow_html=True)
    menu = option_menu(None, ["Súper Agente", "Dashboard"], icons=["cpu-fill", "bar-chart-fill"], default_index=0)
    st.markdown("---")
    ext_file = st.file_uploader("📁 Subir Reporte Externo", type=["csv", "xlsx"])
    df_ext = None
    if ext_file:
        df_ext = pd.read_csv(ext_file) if ext_file.name.endswith('csv') else pd.read_excel(ext_file)
        st.info("Archivo externo cargado para análisis comparativo.")

if menu == "Súper Agente":
    st.title("🤖 Analista Táctico Marcelo-AI")
    
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": "Sistema listo, Marcelo. ¿Qué buque o flota analizamos hoy?"}]

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            parse_response(m["content"], st.session_state.df)

    if prompt := st.chat_input("Escriba su comando táctico..."):
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            res = brain(prompt, st.session_state.df, df_ext)
            parse_response(res, st.session_state.df)
            st.session_state.chat.append({"role": "assistant", "content": res})
