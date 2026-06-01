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

# --- ESTILO DARK PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0B0E14; color: #E2E8F0; }
    .stApp { background-color: #0B0E14; }
    .stChatMessage { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 15px !important; }
    .charly-vessel-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border-left: 5px solid #3b82f6; border-radius: 12px; padding: 20px; margin: 15px 0;
    }
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-top: 15px; }
    .stat-item { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }
    .stat-label { font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; }
    .stat-value { font-size: 1rem; font-weight: 600; color: #F8FAFC; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE ACCESO ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align:center;'>⚓ Acceso Táctico</h2>", unsafe_allow_html=True)
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if user in st.secrets["passwords"] and pw == st.secrets["passwords"][user]:
                st.session_state["password_correct"] = True
                st.session_state["usuario_actual"] = user.capitalize()
                st.rerun()
            else: st.error("Credenciales inválidas")
    st.stop()

# --- CONEXIÓN ---
try:
    URL = st.secrets["supabase"]["url"]
    KEY = st.secrets["supabase"]["service_role_key"]
    supabase: Client = create_client(URL, KEY)
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    # MODELO ESTABLE
    modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
except Exception as e:
    st.error(f"Error de sistema: {e}")
    st.stop()

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def fetch_data():
    res = supabase.table("buques_identidad").select(
        "id_buque, nombre, mmsi, riesgo, buques_maestro(imo, eslora, arqueo_bruto, fecha_construccion), cat_banderas(nombre), cat_tipos_pesca(nombre)"
    ).execute()
    rows = []
    for i in res.data:
        m = i.get("buques_maestro") or {}
        rows.append({
            "id_buque": i["id_buque"], "Nombre": i["nombre"], "MMSI": i["mmsi"], "Riesgo": i["riesgo"],
            "IMO": m.get("imo", "-"), "Eslora": m.get("eslora", 0), "Arqueo": m.get("arqueo_bruto", 0),
            "Bandera": i["cat_banderas"]["nombre"] if i.get("cat_banderas") else "-",
            "Tipo": i["cat_tipos_pesca"]["nombre"] if i.get("cat_tipos_pesca") else "-"
        })
    return pd.DataFrame(rows)

def render_vessel(b):
    color = "#EF4444" if str(b['Riesgo']).lower() == "alto" else "#3B82F6"
    st.markdown(f"""
    <div class="charly-vessel-card">
        <h2 style="color: #60A5FA; margin:0;">🚢 {b['Nombre']}</h2>
        <div style="background:{color}; display:inline-block; padding:2px 12px; border-radius:15px; font-size:0.7rem; font-weight:bold;">RIESGO {str(b['Riesgo']).upper()}</div>
        <div class="stat-grid">
            <div class="stat-item"><span class="stat-label">ID</span><br><span class="stat-value">{b['id_buque']}</span></div>
            <div class="stat-item"><span class="stat-label">Bandera</span><br><span class="stat-value">{b['Bandera']}</span></div>
            <div class="stat-item"><span class="stat-label">MMSI</span><br><span class="stat-value">{b['MMSI']}</span></div>
            <div class="stat-item"><span class="stat-label">IMO</span><br><span class="stat-value">{b['IMO']}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def parser_charly(text, df):
    # 1. Comandos de Actualización
    upds = re.findall(r"\[UPDATE:\s*(.*?),\s*(.*?),\s*(.*?)\]", text)
    for uid, field, val in upds:
        col = field.strip().lower()
        if col in ["riesgo", "nombre"]:
            supabase.table("buques_identidad").update({col: val.strip()}).eq("id_buque", uid.strip()).execute()
            st.toast(f"✅ Base de datos sincronizada: {uid}")
            st.cache_data.clear()

    # 2. Comandos de Fichas
    fichas = re.findall(r"\[FICHA:\s*(.*?)\]", text)
    for fid in fichas:
        v = df[df['id_buque'] == fid.strip()]
        if not v.empty: render_vessel(v.iloc[0])

    # 3. Gráficos y Tablas
    clean_text = re.sub(r"\[.*?\]", "", text)
    
    # Bloques de código (Gráficos)
    partes_codigo = re.split(r"```python\s*(.*?)\s*```", clean_text, flags=re.DOTALL)
    for i, p in enumerate(partes_codigo):
        if i % 2 == 1:
            try:
                scope = {"df": df, "px": px, "go": go, "pd": pd}
                exec(p, {}, scope)
                if "fig" in scope: st.plotly_chart(scope["fig"], use_container_width=True)
            except Exception as e: st.error(f"Error gráfico: {e}")
        else:
            # Bloques CSV (Tablas)
            partes_csv = re.split(r"```csv\s*(.*?)\s*```", p, flags=re.DOTALL)
            for j, p_csv in enumerate(partes_csv):
                if j % 2 == 1:
                    try: st.dataframe(pd.read_csv(StringIO(p_csv.strip())), use_container_width=True)
                    except: st.error("Error al procesar tabla")
                else:
                    if p_csv.strip(): st.markdown(p_csv)

# --- CHAT ---
user_name = st.session_state.get("usuario_actual", "Operador")
st.title(f"⚓ Analista Charly")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Hola {user_name}, sistema Charly en línea. Mis datos provienen directamente de Supabase. ¿Qué buque o estadística deseas consultar?"}]

df_actual = fetch_data()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        parser_charly(m["content"], df_actual)

if prompt := st.chat_input("Consulta a Charly..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # --- FILTRO ANTIALUCINACIONES ---
        # Si el usuario pregunta por un nombre, buscamos coincidencias reales
        match_info = ""
        palabras = prompt.split()
        for palabra in palabras:
            if len(palabra) > 3: # Solo buscamos palabras con sentido
                match = df_actual[df_actual['Nombre'].str.contains(palabra, case=False, na=False)]
                if not match.empty:
                    match_info += f"\nCOINCIDENCIA ENCONTRADA EN DB:\n{match.to_csv(index=False)}"
        
        context = f"""Eres Charly, analista de {user_name}. Año: 2026.
        REGLA CRÍTICA: SOLO usa los datos de la tabla adjunta. Si un dato NO está en la tabla, di 'No tengo registro de esa información' y NO inventes IMO ni MMSI.
        
        TABLA DE DATOS DISPONIBLES:
        {match_info if match_info else df_actual.head(50).to_csv(index=False)}
        
        HERRAMIENTAS:
        - [FICHA: ID_BUQUE] para mostrar el perfil visual.
        - [UPDATE: ID_BUQUE, riesgo, VALOR] para editar en Supabase.
        - ```python ``` para gráficos con 'df' y 'fig'.
        - ```csv ``` para tablas de datos.
        """
        try:
            res = modelo_ia.generate_content(context + f"\n{user_name}: " + prompt)
            parser_charly(res.text, df_actual)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            if "[UPDATE:" in res.text: st.rerun()
        except Exception as e: st.error(f"Error: {e}")
