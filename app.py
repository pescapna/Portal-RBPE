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

# --- CONEXIÓN DE DATOS (SUPABASE & GEMINI) ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["service_role_key"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de Configuración: {e}")
    st.stop()

# --- CSS: DARK PREMIUM TACTICAL ---
st.markdown("""
<style>
    .stApp { background-color: #0B0E14; color: #F1F5F9; }
    .stChatMessage { background-color: #121620 !important; border: 1px solid #21262D !important; border-radius: 12px !important; }
    .buque-perfil { 
        background: linear-gradient(145deg, #1e293b, #0f172a); 
        border: 1px solid #3b82f6; border-radius: 15px; padding: 25px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5); margin: 15px 0;
    }
    .stat-box { background: #161B22; padding: 10px; border-radius: 8px; border: 1px solid #30363D; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE SOPORTE ---
@st.cache_data(ttl=60)
def cargar_flota_completa():
    query = supabase.table("buques_identidad").select(
        "id_buque, nombre, mmsi, riesgo, buques_maestro(imo, eslora, arqueo_bruto, fecha_construccion), cat_banderas(nombre), cat_tipos_pesca(nombre)"
    ).execute()
    data = []
    for i in query.data:
        m = i.get("buques_maestro") or {}
        data.append({
            "id_buque": i["id_buque"], "Nombre": i["nombre"], "MMSI": i["mmsi"], "Riesgo": i["riesgo"],
            "IMO": m.get("imo"), "Eslora": m.get("eslora"), "Arqueo": m.get("arqueo_bruto"),
            "Construccion": m.get("fecha_construccion"), "Bandera": i["cat_banderas"]["nombre"], "Tipo": i["cat_tipos_pesca"]["nombre"]
        })
    return pd.DataFrame(data)

def generar_ficha_estilizada(b):
    """Genera el HTML de la ficha técnica de alto impacto"""
    color_riesgo = "#EF4444" if str(b['Riesgo']).lower() == "alto" else "#10B981"
    return f"""
    <div class="buque-perfil">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <h1 style="color: #60A5FA; margin:0;">🚢 {b['Nombre']}</h1>
                <p style="color: #94A3B8; font-size: 1.1rem;">ID Sistema: {b['id_buque']}</p>
            </div>
            <div style="background: {color_riesgo}; padding: 5px 15px; border-radius: 20px; font-weight: bold; color: white;">
                RIESGO: {str(b['Riesgo']).upper()}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px;">
            <div class="stat-box"><small>BANDERA</small><br><strong>{b['Bandera']}</strong></div>
            <div class="stat-box"><small>TIPO</small><br><strong>{b['Tipo']}</strong></div>
            <div class="stat-box"><small>MMSI</small><br><strong>{b['MMSI']}</strong></div>
            <div class="stat-box"><small>IMO</small><br><strong>{b['IMO']}</strong></div>
            <div class="stat-box"><small>ESLORA</small><br><strong>{b['Eslora']} m</strong></div>
            <div class="stat-box"><small>ARQUEO</small><br><strong>{b['Arqueo']} GT</strong></div>
            <div class="stat-box"><small>CONSTRUIDO</small><br><strong>{b['Construccion']}</strong></div>
            <div class="stat-box"><small>ESTADO</small><br><strong style="color:#34D399;">ACTIVO</strong></div>
        </div>
    </div>
    """

# --- EL MOTOR DEL SÚPER AGENTE ---
def motor_agente(prompt, df_contexto, extra_file_df=None):
    # Consolidar contexto
    csv_data = df_contexto.to_csv(index=False)
    archivo_contexto = f"\nDATOS ARCHIVO SUBIDO:\n{extra_file_df.to_csv(index=False)}" if extra_file_df is not None else ""
    
    contexto_master = f"""
    Eres el Súper Agente Táctico RBPE. Tu misión es analizar la flota, generar cambios y producir visualizaciones.
    BASE DE DATOS ACTUAL: {csv_data} {archivo_contexto}
    
    REGLAS DE ORO:
    1. Si te piden información de un buque específico, responde con: [VESSEL_PROFILE: ID_DEL_BUQUE]
    2. Si te piden un gráfico, genera un bloque de código python usando 'df' y 'fig': ```python ... ```
    3. Si te piden cambiar algo (Riesgo), usa: [DB_ACTION: UPDATE KEY="id" FIELD="Riesgo" VALUE="Nuevo"]
    4. El año actual es 2026. Calcula antigüedades basándote en eso.
    5. Sé directo, táctico y profesional.
    """
    
    response = modelo_ia.generate_content(contexto_master + "\nUsuario: " + prompt)
    return response.text

def procesar_respuesta(texto, df):
    # 1. Detectar Fichas Estilizadas
    vessel_match = re.search(r"\[VESSEL_PROFILE:\s*(.*?)\]", texto)
    if vessel_match:
        vid = vessel_match.group(1).strip()
        v_data = df[df['id_buque'] == vid]
        if not v_data.empty:
            st.markdown(generar_ficha_estilizada(v_data.iloc[0]), unsafe_allow_html=True)

    # 2. Detectar Cambios en Base de Datos
    db_match = re.search(r"\[DB_ACTION:\s*UPDATE\s*KEY=\"(.*?)\"\s*FIELD=\"(.*?)\"\s*VALUE=\"(.*?)\"\]", texto)
    if db_match:
        kid, field, val = db_match.groups()
        try:
            field_db = "riesgo" if field.lower() == "riesgo" else field
            supabase.table("buques_identidad").update({field_db: val}).eq("id_buque", kid).execute()
            st.success(f"⚙️ Sistema Actualizado: Buque {kid} -> {field}={val}")
            st.cache_data.clear() # Limpiar para ver el cambio
        except Exception as e: st.error(f"Error DB: {e}")

    # 3. Detectar y Ejecutar Gráficos
    texto_limpio = re.sub(r"\[.*?\]", "", texto)
    partes = re.split(r"```python\s*(.*?)\s*```", texto_limpio, flags=re.DOTALL)
    
    for i, p in enumerate(partes):
        if i % 2 == 1:
            try:
                namespace = {"df": df, "px": px, "go": go, "pd": pd}
                exec(p, {}, namespace)
                if "fig" in namespace: st.plotly_chart(namespace["fig"], use_container_width=True)
            except Exception as e: st.error(f"Error en gráfico dinámico: {e}")
        else:
            if p.strip(): st.markdown(p)

# --- INTERFAZ PRINCIPAL ---
st.session_state.df = cargar_flota_completa()

with st.sidebar:
    st.title("⚓ Centro de Mando")
    menu = option_menu(None, ["Súper Agente", "Dashboard", "Gestión"], icons=["cpu", "bar-chart", "database"], default_index=0)
    st.markdown("---")
    uploaded_file = st.file_uploader("📁 Subir Archivo Inteligente (CSV/XLSX)", type=["csv", "xlsx"])
    extra_df = None
    if uploaded_file:
        extra_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
        st.success("Archivo cargado para análisis.")

if menu == "Súper Agente":
    st.header("🤖 Analista Táctico RBPE")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Listo para operar, Marcelo. ¿Qué buque o tendencia analizamos hoy?"}]

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            procesar_respuesta(m["content"], st.session_state.df)

    if prompt := st.chat_input("Comando..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Procesando inteligencia..."):
                res = motor_agente(prompt, st.session_state.df, extra_df)
                procesar_respuesta(res, st.session_state.df)
                st.session_state.messages.append({"role": "assistant", "content": res})
