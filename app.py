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
st.set_page_config(page_title="Portal RBPE - Súper Agente", page_icon="⚓", layout="wide")

# --- CONEXIÓN DE DATOS ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["service_role_key"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de Configuración (Secrets): {e}")
    st.stop()

# --- CSS: ESTILO DARK TÁCTICO ---
st.markdown("""
<style>
    .stApp { background-color: #0B0E14; color: #F1F5F9; }
    .stChatMessage { background-color: #121620 !important; border: 1px solid #21262D !important; border-radius: 12px !important; }
    .vessel-profile { 
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
        border: 2px solid #3b82f6; border-radius: 15px; padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6); margin: 20px 0;
    }
    .kpi-box { background: #161B22; padding: 12px; border-radius: 10px; border: 1px solid #30363D; text-align: center; }
    .kpi-val { color: #F8FAFC; font-size: 1.4rem; font-weight: 700; display: block; }
    .kpi-lab { color: #94A3B8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS OPTIMIZADA ---
@st.cache_data(ttl=60)
def fetch_master_data():
    query = supabase.table("buques_identidad").select(
        "id_buque, nombre, mmsi, riesgo, buques_maestro(imo, eslora, arqueo_bruto, fecha_construccion), cat_banderas(nombre), cat_tipos_pesca(nombre)"
    ).execute()
    flat_data = []
    for i in query.data:
        m = i.get("buques_maestro") or {}
        flat_data.append({
            "id_buque": i["id_buque"], "Nombre": i["nombre"], "MMSI": i["mmsi"], "Riesgo": i["riesgo"],
            "IMO": m.get("imo"), "Eslora": m.get("eslora"), "Arqueo": m.get("arqueo_bruto"),
            "Construccion": m.get("fecha_construccion"), 
            "Bandera": i["cat_banderas"]["nombre"] if i.get("cat_banderas") else "Desconocida",
            "Tipo": i["cat_tipos_pesca"]["nombre"] if i.get("cat_tipos_pesca") else "Otros"
        })
    return pd.DataFrame(flat_data)

def display_styled_profile(b):
    """Renderiza una ficha técnica de buque de nivel militar"""
    riesgo_color = "#EF4444" if str(b['Riesgo']).lower() == "alto" else "#3B82F6"
    st.markdown(f"""
    <div class="vessel-profile">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1 style="color: #60A5FA; margin:0; font-family: 'Courier New', monospace;">🚢 {b['Nombre']}</h1>
            <div style="background: {riesgo_color}; padding: 8px 20px; border-radius: 30px; font-weight: 800; color: white; letter-spacing: 1px;">
                RIESGO {str(b['Riesgo']).upper()}
            </div>
        </div>
        <p style="color: #64748B; margin-top: 5px;">Identificador de Sistema: {b['id_buque']}</p>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px;">
            <div class="kpi-box"><span class="kpi-lab">Bandera</span><span class="kpi-val">{b['Bandera']}</span></div>
            <div class="kpi-box"><span class="kpi-lab">Tipo</span><span class="kpi-val">{b['Tipo']}</span></div>
            <div class="kpi-box"><span class="kpi-lab">MMSI</span><span class="kpi-val">{b['MMSI']}</span></div>
            <div class="kpi-box"><span class="kpi-lab">IMO</span><span class="kpi-val">{b['IMO']}</span></div>
            <div class="kpi-box"><span class="kpi-lab">Eslora</span><span class="kpi-val">{b['Eslora']} m</span></div>
            <div class="kpi-box"><span class="kpi-lab">Arqueo</span><span class="kpi-val">{b['Arqueo']} GT</span></div>
            <div class="kpi-box"><span class="kpi-lab">Año</span><span class="kpi-val">{b['Construccion']}</span></div>
            <div class="kpi-box"><span class="kpi-lab">Estado</span><span class="kpi-val" style="color: #10B981;">OPERATIVO</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- LÓGICA DEL SÚPER AGENTE ---
def agent_brain(prompt, df_main, df_extra=None):
    contexto_extra = f"\nARCHIVO SUBIDO:\n{df_extra.head(50).to_csv(index=False)}" if df_extra is not None else ""
    
    sys_prompt = f"""
    Eres el Súper Agente RBPE 'Marcelo-AI', un Analista Naval de nivel Corporativo Militar.
    DATOS MAESTROS SUPABASE:
    {df_main.to_csv(index=False)}
    {contexto_extra}
    
    CAPACIDADES:
    1. Perfil de Buque: Si mencionas un buque o el usuario lo pide, usa: [PROFILE: ID_BUQUE]
    2. Actualización DB: Si ordenan cambiar el riesgo, usa: [UPDATE: ID_BUQUE, Campo, Valor] (Campos: Riesgo, Nombre)
    3. Gráficos: Genera bloques de código python con Plotly usando 'df' y 'fig': ```python ... ```
    4. Informes: Genera tablas en Markdown y análisis detallado.
    
    REGLA: El año actual es 2026. Responde de forma táctica y concisa.
    """
    response = modelo_ia.generate_content(sys_prompt + "\nComando Usuario: " + prompt)
    return response.text

def parse_agent_response(text, df):
    # 1. Ejecutar Actualizaciones en Supabase
    updates = re.findall(r"\[UPDATE:\s*(.*?),\s*(.*?),\s*(.*?)\]", text)
    for uid, field, val in updates:
        try:
            field_name = field.strip().lower()
            supabase.table("buques_identidad").update({field_name: val.strip()}).eq("id_buque", uid.strip()).execute()
            st.success(f"⚡ Base de Datos Sincronizada: {uid} -> {field}={val}")
            st.cache_data.clear()
        except Exception as e: st.error(f"Falla en escritura: {e}")

    # 2. Renderizar Fichas Estilizadas
    profiles = re.findall(r"\[PROFILE:\s*(.*?)\]", text)
    for pid in profiles:
        v_data = df[df['id_buque'] == pid.strip()]
        if not v_data.empty:
            display_styled_profile(v_data.iloc[0])

    # 3. Gráficos y Texto
    clean_text = re.sub(r"\[.*?\]", "", text)
    blocks = re.split(r"```python\s*(.*?)\s*```", clean_text, flags=re.DOTALL)
    
    for i, block in enumerate(blocks):
        if i % 2 == 1: # Bloque de código
            try:
                namespace = {"df": df, "px": px, "go": go, "pd": pd}
                exec(block, {}, namespace)
                if "fig" in namespace: st.plotly_chart(namespace["fig"], use_container_width=True)
            except Exception as e: st.error(f"Error gráfico: {e}")
        else:
            if block.strip(): st.markdown(block)

# --- INTERFAZ PRINCIPAL ---
st.session_state.df = fetch_master_data()

with st.sidebar:
    st.markdown("<h1 style='text-align:center;'>⚓ RBPE TACTICAL</h1>", unsafe_allow_html=True)
    menu = option_menu(None, ["Súper Agente", "Mapa de Flota", "Config"], icons=["cpu", "map", "gear"], default_index=0)
    st.markdown("---")
    file = st.file_uploader("📂 Cargar Datos Externos", type=["csv", "xlsx"])
    extra_df = None
    if file:
        extra_df = pd.read_csv(file) if file.name.endswith('csv') else pd.read_excel(file)
        st.success("Análisis Multi-Fuente Activo")

if menu == "Súper Agente":
    st.title("🤖 Centro de Inteligencia Marcelo-AI")
    
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": "Sistema en línea. Operador Marcelo, ¿cuál es su comando?"}]

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            parse_agent_response(m["content"], st.session_state.df)

    if prompt := st.chat_input("Ej: 'Genera un reporte de buques chinos' o 'Pon riesgo Alto al buque 48fbc03d'"):
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analizando Red de Datos..."):
                response_text = agent_brain(prompt, st.session_state.df, extra_df)
                parse_agent_response(response_text, st.session_state.df)
                st.session_state.chat.append({"role": "assistant", "content": response_text})
