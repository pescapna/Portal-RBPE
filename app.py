import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import json

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM ---
st.set_page_config(page_title="Charly - Comando Táctico", page_icon="⚓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #07090E; color: #E2E8F0; }
    .stApp { background-color: #07090E; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .stChatMessage {
        background: rgba(22, 27, 34, 0.6) !important;
        border: 1px solid rgba(48, 54, 61, 0.8) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.2rem !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SISTEMA DE LOGIN ---
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
            else: 
                st.error("Acceso denegado.")
    st.stop()

operador = st.session_state["user"]

# --- 3. CONEXIÓN DE INFRAESTRUCTURA INMUNE (SÓLO API REST) ---
@st.cache_resource
def init_connections():
    # Usamos la conexión estándar de Supabase que ya sabemos que te funciona al 100%
    supa = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    return supa

supabase = init_connections()

# --- 4. ARSENAL DE HERRAMIENTAS DE CHARLY (FUNCTION CALLING) ---

def buscar_perfil_buque(identificador: str) -> dict:
    """
    Busca información individual detallada de un buque por su nombre o número MMSI.
    """
    try:
        res = supabase.table("buques_identidad").select(
            "id_buque, nombre, mmsi, riesgo, indicativo_llamada, "
            "cat_banderas(nombre), cat_tipos_pesca(nombre), cat_empresas(nombre)"
        ).or_(f"nombre.ilike.%{identificador}%,mmsi.eq.{identificador}").execute()
        
        if not res.data:
            return {"status": "error", "mensaje": f"No se encontró el buque: {identificador}"}
        
        id_buque = res.data[0]['id_buque']
        res_maestro = supabase.table("buques_maestro").select(
            "eslora, arqueo_bruto, fecha_construccion, imo"
        ).eq("id_buque", id_buque).execute()

        return {
            "status": "success", 
            "identidad": res.data, 
            "datos_fisicos": res_maestro.data if res_maestro.data else "No disponibles"
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def descargar_universo_datos(tabla: str) -> dict:
    """
    Descarga los datos completos de una tabla específica para realizar análisis masivos y cruces de datos globales.
    Tablas permitidas obligatoriamente: 'buques_identidad', 'buques_maestro', 'cat_banderas', 'cat_tipos_pesca', 'cat_empresas', 'operaciones'.
    """
    try:
        # Descarga directa vía API HTTP (Inmune a fallos de puertos Postgres)
        if tabla == "buques_identidad":
            res = supabase.table("buques_identidad").select("id_buque, nombre, mmsi, riesgo, id_bandera, id_tipo, id_empresa").execute()
        elif tabla == "buques_maestro":
            res = supabase.table("buques_maestro").select("id_buque, imo, eslora, arqueo_bruto, fecha_construccion").execute()
        elif tabla == "cat_banderas":
            res = supabase.table("cat_banderas").select("id_bandera, nombre").execute()
        elif tabla == "cat_tipos_pesca":
            res = supabase.table("cat_tipos_pesca").select("id_tipo, nombre").execute()
        elif tabla == "cat_empresas":
            res = supabase.table("cat_empresas").select("id_empresa, nombre").execute()
        elif tabla == "operaciones":
            res = supabase.table("operaciones").select("id_operacion, id_buque, puerto_origen, fecha_zarpada, opero_en_zeea").execute()
        else:
            return {"status": "error", "mensaje": f"Tabla '{tabla}' no autorizada o inexistente."}
            
        return {"status": "success", "datos": res.data}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def renderizar_visualizacion(tipo: str, titulo: str, datos_en_json: str, x_col: str = None, y_col: str = None) -> dict:
    """
    Ordena al sistema del frontend renderizar un elemento visual interactivo como un Gráfico o Tabla en la pantalla del usuario.
    - tipo: Debe ser 'tabla', 'grafico_barras' o 'grafico_torta'.
    - datos_en_json: String JSON estructurado con los resultados finales procesados.
    """
    try:
        datos = json.loads(datos_en_json)
        st.session_state.mensajes_ui.append({
            "role": "assistant", 
            "content": f"📊 **Desplegando reporte visual:** *{titulo}*",
            "visualizacion": {"tipo": tipo, "datos": datos, "titulo": titulo, "x": x_col, "y": y_col}
        })
        return {"status": "success", "mensaje": "Visualización enviada al puente de mando."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

herramientas_charly = [buscar_perfil_buque, descargar_universo_datos, renderizar_visualizacion]

# --- 5. CONFIGURACIÓN DEL AGENTE INTELIGENTE ---
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite', 
    tools=herramientas_charly,
    system_instruction=f"""
    Eres Charly, analista naval del Comando RBPE bajo las órdenes del Operador {operador}.
    
    METODOLOGÍA DE ANÁLISIS ABSOLUTA:
    1. Si te piden recuentos, listados, gráficos o análisis globales de una bandera, riesgo o empresa, NO puedes usar SQL directo. 
    2. En su lugar, DEBES llamar a la función `descargar_universo_datos` pasándole la tabla principal (ej: 'buques_identidad'). Si requieres nombres de países o empresas para cruzar los datos, descarga también los catálogos correspondientes ('cat_banderas', 'cat_empresas').
    3. Una vez que el sistema te devuelva los datos de las funciones, tú actuarás como el motor analítico: haz las agrupaciones, filtros y cruces de IDs internamente en tu mente de IA.
    4. Cuando tengas el resultado del análisis final procesado, DEBES invocar inmediatamente la función `renderizar_visualizacion` pasándole tus conclusiones tabuladas en formato JSON para pintar gráficos de barras, tortas o tablas en pantalla.
    5. Mantén un lenguaje táctico, limpio y militar. No inventes datos.
    """
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Comando Táctico Online.** Conexión HTTP Nativa establecida. Sistema inmune a errores de puerto. ¿Cuáles son sus órdenes?"}]

# --- 6. INTERFAZ DE CHAT Y DESPLIEGUE VISUAL (FRONTEND) ---
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Analista Naval <span style='color: #3B82F6;'>Charly</span></h1>", unsafe_allow_html=True)

for msg in st.session_state.mensajes_ui:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        if "visualizacion" in msg:
            v = msg["visualizacion"]
            df_visual = pd.DataFrame(v["datos"])
            
            if v["tipo"] == "tabla":
                st.dataframe(df_visual, use_container_width=True)
            elif v["tipo"] == "grafico_barras" and v["x"] and v["y"]:
                fig = px.bar(df_visual, x=v["x"], y=v["y"], title=v["titulo"], template="plotly_dark")
                fig.update_traces(marker_color='#3B82F6')
                st.plotly_chart(fig, use_container_width=True)
            elif v["tipo"] == "grafico_torta" and v["x"] and v["y"]:
                fig = px.pie(df_visual, names=v["x"], values=v["y"], title=v["titulo"], template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

if prompt := st.chat_input("Ordene su análisis global..."):
    st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Sincronizando inteligencia de datos..."):
            try:
                respuesta = st.session_state.chat.send_message(prompt)
                st.markdown(respuesta.text)
                st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
                
                if "Desplegando reporte visual" in respuesta.text:
                    st.rerun()
            except Exception as api_e:
                st.error(f"Fallo de enlace: {api_e}")
