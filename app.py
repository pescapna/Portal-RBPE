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

# --- ESTILO MODERNO DARK (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0B0E14;
        color: #E2E8F0;
    }
    .stApp { background-color: #0B0E14; }
    .stChatMessage {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 15px !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .charly-vessel-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border-left: 5px solid #3b82f6;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    }
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
        margin-top: 15px;
    }
    .stat-item {
        background: rgba(255,255,255,0.05);
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .stat-label { font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; }
    .stat-value { font-size: 1rem; font-weight: 600; color: #F8FAFC; display: block; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN DE DATOS ---
try:
    URL = st.secrets["supabase"]["url"]
    KEY = st.secrets["supabase"]["service_role_key"]
    supabase: Client = create_client(URL, KEY)
    
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')
except Exception as e:
    st.error(f"Configuración incompleta: {e}")
    st.stop()

# --- FUNCIONES DE ALMACENAMIENTO Y CONSULTA ---
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
            <div class="stat-item"><span class="stat-label">IMO</span><span class="stat-value">{b['IMO']}</span></div>
            <div class="stat-item"><span class="stat-label">Bandera</span><span class="stat-value">{b['Bandera']}</span></div>
            <div class="stat-item"><span class="stat-label">Tipo</span><span class="stat-value">{b['Tipo']}</span></div>
            <div class="stat-item"><span class="stat-label">Eslora</span><span class="stat-value">{b['Eslora']}m</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def ejecutar_comando_charly(texto, df):
    # 1. Procesamiento de Actualizaciones (Edición de datos)
    updates = re.findall(r"\[UPDATE:\s*(.*?),\s*(.*?),\s*(.*?)\]", texto)
    for uid, field, val in updates:
        columna_db = field.strip().lower()
        if columna_db not in ["riesgo", "nombre"]:
            st.error(f"⚠️ Charly intentó modificar una columna inválida: '{columna_db}'")
            continue
            
        try:
            supabase.table("buques_identidad").update({columna_db: val.strip()}).eq("id_buque", uid.strip()).execute()
            st.toast(f"💾 Supabase Sincronizado: Buque {uid} -> {columna_db} = {val}")
            st.cache_data.clear()
        except Exception as db_err:
            st.error(f"Error de persistencia en Supabase: {db_err}")

    # 2. Renderizado de Fichas Técnicas
    fichas = re.findall(r"\[FICHA:\s*(.*?)\]", texto)
    for fid in fichas:
        v = df[df['id_buque'] == fid.strip()]
        if not v.empty: 
            render_vessel(v.iloc[0])

    # 3. Procesamiento e Inyección de Gráficos Dinámicos
    texto_limpio = re.sub(r"\[.*?\]", "", texto)
    partes = re.split(r"```python\s*(.*?)\s*
```", texto_limpio, flags=re.DOTALL)
    
    for i, p in enumerate(partes):
        if i % 2 == 1:
            try:
                scope = {"df": df, "px": px, "go": go, "pd": pd}
                exec(p, {}, scope)
                if "fig" in scope: 
                    st.plotly_chart(scope["fig"], use_container_width=True)
            except Exception as e_graph: 
                st.error(f"⚠️ Error al renderizar el gráfico dinámico generado por la IA. Detalles técnicos: {e_graph}")
        else:
            if p.strip(): 
                st.markdown(p)

# --- INTERFAZ DE USUARIO PRINCIPAL ---
st.title("⚓ Analista Táctico: Charly")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola Marcelo, soy Charly. He mapeado la estructura completa de las tablas en Supabase. Estoy listo para guiarte en el análisis, edición o almacenamiento de datos de la flota de forma segura."}]

df_actual = cargar_datos_supabase()

# Extraemos las columnas reales en texto plano para el prompt de Charly
columnas_reales = ", ".join(df_actual.columns.tolist())

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        ejecutar_comando_charly(m["content"], df_actual)

if prompt := st.chat_input("Instrucción o consulta para Charly..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): 
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        contexto_estricto = f"""Eres Charly, el asistente y analista naval de Marcelo. Tu prioridad es guiarlo paso a paso de forma clara y sin errores. El año actual es 2026.
        
        CONOCIMIENTO EXACTO DEL DATAFRAME LOCAL ('df'):
        - Las columnas disponibles en el DataFrame son únicamente estas: [{columnas_reales}].
        - Cualquier código de Plotly Express (px) que generes DEBE usar obligatoriamente estos nombres exactos de columnas (respetando mayúsculas y minúsculas). No inventes columnas.
        
        REGLAS DE OPERACIÓN SEGURO:
        1. Si Marcelo te pide ver el perfil, la ficha o los datos de un buque, proporciónale un resumen en texto y finaliza incluyendo el tag: [FICHA: ID_DEL_BUQUE]
        2. Si Marcelo te pide EDITAR o CAMBIAR un dato (ej. el riesgo), debes incluir estrictamente el tag: [UPDATE: ID_DEL_BUQUE, riesgo, NUEVO_VALOR]. Las únicas columnas modificables de la tabla 'buques_identidad' son 'riesgo' o 'nombre'. Nunca uses la palabra genérica 'campo'.
        3. Para gráficos interactivos, usa obligatoriamente bloques de código ```python usando el DataFrame llamado 'df' y guarda el objeto final en la variable 'fig'.
        4. Sé didáctico. Explica brevemente qué datos estás procesando antes de mostrar el resultado para evitar errores del operador.
        """
        try:
            response = modelo_ia.generate_content(contexto_estricto + "\nMarcelo: " + prompt)
            ejecutar_comando_charly(response.text, df_actual)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            if "[UPDATE:" in response.text:
                st.cache_data.clear()
                st.rerun()
        except Exception as e:
            st.error(f"Error en la comunicación con el modelo: {e}")
