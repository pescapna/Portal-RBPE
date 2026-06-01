import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
import re
from supabase import create_client, Client

# --- CONFIGURACIÓN Y ESTÉTICA PREMIUM ---
st.set_page_config(page_title="Charly - Comando Táctico", page_icon="⚓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #07090E;
        color: #E2E8F0;
    }
    .stApp { background-color: #07090E; }
    
    /* Ocultar elementos nativos de Streamlit */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Globos de Chat Premium */
    .stChatMessage {
        background: rgba(22, 27, 34, 0.6) !important;
        border: 1px solid rgba(48, 54, 61, 0.8) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.2rem !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    /* Fichas Tácticas (Glassmorphism) */
    .tactical-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-left: 6px solid #3B82F6;
        border-radius: 12px;
        padding: 24px;
        margin: 20px 0;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(12px);
    }
    
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 15px; margin-top: 20px; }
    .kpi-box { 
        background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.05); 
        padding: 12px; border-radius: 8px; text-align: center; 
    }
    .kpi-label { font-size: 0.65rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
    .kpi-value { font-size: 1.1rem; color: #F8FAFC; font-family: 'JetBrains Mono', monospace; font-weight: 600; margin-top: 4px; display: block; }
    
    /* Alertas de error estéticas */
    .error-card { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.4); padding: 15px; border-radius: 8px; color: #FCA5A5; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN DE ALTA SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><h2 style='text-align:center; color: #F8FAFC; font-weight: 800; letter-spacing: 1px;'>⚓ COMANDO RBPE</h2>", unsafe_allow_html=True)
        user_input = st.text_input("Identificación de Operador")
        pass_input = st.text_input("Código de Acceso", type="password")
        if st.button("INICIAR SESIÓN TÁCTICA", use_container_width=True):
            if user_input in st.secrets["passwords"] and pass_input == st.secrets["passwords"][user_input]:
                st.session_state["password_correct"] = True
                st.session_state["user"] = user_input.capitalize()
                st.rerun()
            else: st.error("Acceso denegado. Credenciales comprometidas.")
    st.stop()

# --- CONEXIÓN DE INFRAESTRUCTURA ---
@st.cache_resource
def init_core():
    supa = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    mod = genai.GenerativeModel('gemini-3.1-flash-lite')
    return supa, mod

supabase, model = init_core()

# --- CARGA MAESTRA DE DATOS (EL CEREBRO DENORMALIZADO) ---
@st.cache_data(ttl=600, show_spinner=False)
def load_fleet_data():
    # Tabla Identidad
    res_id = supabase.table("buques_identidad").select("*, buques_maestro(*), cat_banderas(nombre), cat_tipos_pesca(nombre)").execute()
    datos_limpios = []
    for i in res_id.data:
        m = i.get("buques_maestro") or {}
        datos_limpios.append({
            "ID_Buque": i["id_buque"], "Nombre": i["nombre"], "MMSI": i["mmsi"], "Riesgo": i["riesgo"],
            "Bandera": i["cat_banderas"]["nombre"] if i.get("cat_banderas") else "Desconocida",
            "Tipo": i["cat_tipos_pesca"]["nombre"] if i.get("cat_tipos_pesca") else "Otros",
            "IMO": m.get("imo", "-"), "Eslora": m.get("eslora", 0), "Arqueo": m.get("arqueo_bruto", 0)
        })
    df_id = pd.DataFrame(datos_limpios)
    # Tabla Operaciones y ZEEA
    df_ops = pd.DataFrame(supabase.table("operaciones").select("*").execute().data)
    df_zeea = pd.DataFrame(supabase.table("navegaciones_zeea").select("*").execute().data)
    
    return df_id, df_ops, df_zeea

with st.spinner("Sincronizando con satélites y base de datos central..."):
    df_id, df_ops, df_zeea = load_fleet_data()

# --- RENDERIZADO VISUAL TÁCTICO ---
def renderizar_ficha(buque):
    color_alerta = "#EF4444" if str(buque['Riesgo']).lower() == "alto" else "#10B981"
    st.markdown(f"""
    <div class="tactical-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h2 style="margin: 0; color: #60A5FA; font-weight: 800; font-family: 'Inter', sans-serif;">{buque['Nombre']}</h2>
                <span style="color: #64748B; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">UID: {buque['ID_Buque']}</span>
            </div>
            <div style="background-color: rgba(0,0,0,0.3); border: 1px solid {color_alerta}; padding: 6px 16px; border-radius: 30px;">
                <span style="color: {color_alerta}; font-weight: 800; font-size: 0.8rem; letter-spacing: 1px;">RIESGO {str(buque['Riesgo']).upper()}</span>
            </div>
        </div>
        <div class="kpi-grid">
            <div class="kpi-box"><span class="kpi-label">Bandera</span><span class="kpi-value">{buque['Bandera']}</span></div>
            <div class="kpi-box"><span class="kpi-label">Tipo</span><span class="kpi-value">{buque['Tipo']}</span></div>
            <div class="kpi-box"><span class="kpi-label">MMSI</span><span class="kpi-value">{buque['MMSI']}</span></div>
            <div class="kpi-box"><span class="kpi-label">IMO</span><span class="kpi-value">{buque['IMO']}</span></div>
            <div class="kpi-box"><span class="kpi-label">Eslora</span><span class="kpi-value">{buque['Eslora']} m</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- MOTOR AUTÓNOMO DE EJECUCIÓN (EL CEREBRO DE CHARLY) ---
def procesar_orden_agente(respuesta_ia):
    # 1. Escritura en Supabase
    modificaciones = re.findall(r"\[UPDATE:\s*(.*?),\s*(.*?),\s*(.*?)\]", respuesta_ia)
    for uid, columna, valor in modificaciones:
        try:
            supabase.table("buques_identidad").update({columna.strip().lower(): valor.strip()}).eq("id_buque", uid.strip()).execute()
            st.toast(f"✅ Protocolo ejecutado: Buque {uid} actualizado.", icon="🛡️")
            st.cache_data.clear()
        except Exception as e: st.error(f"Falla de escritura DB: {e}")

    # 2. Renderizado de Fichas
    fichas = re.findall(r"\[FICHA:\s*(.*?)\]", respuesta_ia)
    for fid in fichas:
        match = df_id[df_id['ID_Buque'] == fid.strip()]
        if not match.empty: renderizar_ficha(match.iloc[0])

    # 3. Ejecución de Código Dinámico (Sin alucinaciones numéricas)
    texto_puro = re.sub(r"\[.*?\]", "", respuesta_ia)
    bloques = re.split(r"```python\s*(.*?)\s*```", texto_puro, flags=re.DOTALL)
    
    for i, bloque in enumerate(bloques):
        if i % 2 == 1:
            try:
                # Entorno aislado pero con poder total sobre la UI
                entorno_seguro = {"df_id": df_id, "df_ops": df_ops, "df_zeea": df_zeea, "px": px, "pd": pd, "st": st}
                exec(bloque.strip(), {}, entorno_seguro)
            except Exception as e:
                # Error formateado estéticamente
                st.markdown(f"<div class='error-card'>⚠️ Excepción en el análisis de datos: {str(e)}</div>", unsafe_allow_html=True)
        else:
            if bloque.strip(): st.markdown(bloque)

# --- INTERFAZ DEL COMANDO ---
operador = st.session_state["user"]
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Analista Naval <span style='color: #3B82F6;'>Charly</span></h1>", unsafe_allow_html=True)

if "chat_log" not in st.session_state:
    st.session_state.chat_log = [{"role": "assistant", "content": f"Saludos, Operador **{operador}**. La red de datos está cargada y validada. Poseo control total sobre el motor analítico y la base de datos central. Proceda con sus órdenes."}]

for msg in st.session_state.chat_log:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant": procesar_orden_agente(msg["content"])
        else: st.markdown(msg["content"])

if prompt := st.chat_input("Introduzca parámetros de búsqueda o análisis..."):
    st.session_state.chat_log.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # INSTRUCCIONES ESTRICTAS PARA EL MODELO (Evita asteriscos y fuerza el uso de código)
        instrucciones_maestras = f"""
        Eres Charly, Agente de Inteligencia Naval operando para {operador}. Año: 2026.
        
        ESQUEMA DE DATOS EXACTO (Sensible a mayúsculas/minúsculas):
        - DataFrame 'df_id' (Identidad): {df_id.columns.tolist()}
        - DataFrame 'df_ops' (Operaciones): {df_ops.columns.tolist()}
        - DataFrame 'df_zeea' (Navegaciones): {df_zeea.columns.tolist()}
        
        REGLAS DE ORO ABSOLUTAS:
        1. NUNCA respondas con asteriscos (****) o intentes adivinar un número.
        2. Si el usuario te pide un cálculo (ej: "cuántos buques..."), TIENES que escribir código Python usando la librería 'st' (Streamlit) para mostrarlo. 
           EJEMPLO CORRECTO:
           ```python
           cantidad = len(df_id[df_id['Bandera'] == 'Tanzania'])
           st.write(f"**Resultado:** Hay {{cantidad}} buques registrados.")
           ```
        3. Para gráficos interactivos, crea el objeto 'fig' de Plotly y usa `st.plotly_chart(fig, use_container_width=True)`.
        4. Para mostrar tablas completas, usa `st.dataframe(resultado)`.
        5. Para modificar la base de datos (riesgo o nombre), usa el formato estricto: [UPDATE: ID_Buque, columna, valor].
        6. Para mostrar la ficha de un barco, usa: [FICHA: ID_Buque].
        """
        
        try:
            with st.spinner("Procesando consulta en los servidores centrales..."):
                respuesta = model.generate_content(instrucciones_maestras + "\nOrden: " + prompt)
                procesar_orden_agente(respuesta.text)
                st.session_state.chat_log.append({"role": "assistant", "content": respuesta.text})
        except Exception as e:
            st.error(f"Fallo de conexión con el núcleo de IA: {e}")
