import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import json

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM ---
st.set_page_config(page_title="Charly v2 - Centro de Análisis ReAct", page_icon="⚓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=300;400;600;800&family=JetBrains+Mono:wght=400&display=swap');
    
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

# --- 2. SISTEMA DE LOGIN DE OPERADORES ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><h2 style='text-align:center; color: #F8FAFC; font-weight: 800; letter-spacing: 1px;'>⚓ CENTRO DE CONTROL</h2>", unsafe_allow_html=True)
        user_input = st.text_input("Identificación de Operador")
        pass_input = st.text_input("Código de Acceso", type="password")
        if st.button("INICIAR SESIÓN", use_container_width=True):
            if user_input in st.secrets["passwords"] and pass_input == st.secrets["passwords"][user_input]:
                st.session_state["password_correct"] = True
                st.session_state["user"] = user_input.capitalize()
                st.rerun()
            else: 
                st.error("Acceso denegado.")
    st.stop()

operador = st.session_state["user"]

# --- 3. INFRAESTRUCTURA DE CONEXIÓN API HTTPS ---
@st.cache_resource
def init_connections():
    supa = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    return supa

supabase = init_connections()

# --- 4. LA HERRAMIENTA UNIVERSAL REACT CON ESCUDO DE TOKENS ---

def ejecutar_sql(query: str) -> str:
    """
    Ejecuta una consulta SQL SELECT en la base de datos y devuelve las filas resultantes en formato JSON.
    Úsala para auditorías de duplicados, comparaciones por cualquier columna (IMO, MMSI), cálculos estadísticos y relaciones complejas.
    """
    try:
        clean_query = query.strip()
        if not clean_query.lower().startswith("select"):
            return json.dumps({"status": "error", "mensaje": "Solo se permiten consultas SELECT de lectura."})
        
        # Ejecutar consulta vía RPC remota
        res = supabase.rpc("ejecutar_sql", {"query": clean_query}).execute()
        
        if not res.data:
            return json.dumps({"status": "success", "mensaje": "La consulta se ejecutó correctamente pero devolvió 0 registros."})
            
        total_filas = len(res.data)
        
        # ESCUDO ANTI-429: Si el resultado es masivo, lo interceptamos y renderizamos de forma directa
        if total_filas >= 15:
            df = pd.DataFrame(res.data)
            df.columns = [col.upper() for col in df.columns]
            
            # Lo guardamos en la interfaz de Streamlit directamente sin pasar por los tokens de Gemini
            st.session_state.mensajes_ui.append({
                "role": "assistant", 
                "content": f"📊 **Resultados Optimizados:** Se han extraído {total_filas} registros de la base de datos y se desplegaron directamente en la pantalla para proteger la cuota del sistema.",
                "visualizacion": {"tipo": "tabla", "datos": df.to_dict(orient="records")}
            })
            st.session_state["necesita_rerun"] = True
            
            # Le pasamos a Gemini solo una ficha técnica ultraligera de lo que se acaba de imprimir
            columnas = list(res.data[0].keys())
            muestra_inicial = res.data[:2]
            
            resumen_ligero = {
                "status": "success",
                "info": "AVISO: El volumen de datos era masivo. Python ya interceptó el JSON y pintó la tabla completa directamente en la pantalla del usuario.",
                "total_filas_desplegadas_en_pantalla": total_filas,
                "columnas_de_la_tabla": columnas,
                "muestra_primeras_filas_para_tu_analisis": muestra_inicial
            }
            return json.dumps(resumen_ligero)
            
        # Si el resultado es pequeño, se lo damos completo a Gemini para que lo lea sin riesgo de cuota
        return json.dumps(res.data)
        
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


def renderizar_interfaz_visual(tipo: str, titulo: str, datos_en_json: str, x_col: str = None, y_col: str = None) -> dict:
    """
    Renderiza un componente visual interactivo (tabla, grafico_barras o grafico_torta) en la pantalla del usuario.
    Usa esta función si los datos devueltos por ejecutar_sql fueron pequeños (<15) pero deseas darle un formato gráfico o de tabla limpia.
    """
    try:
        datos = json.loads(datos_en_json)
        df = pd.DataFrame(datos)
        df.columns = [col.upper() for col in df.columns]
        
        x_purgado = x_col.upper() if x_col else None
        y_purgado = y_col.upper() if y_col else None
        
        st.session_state.mensajes_ui.append({
            "role": "assistant", 
            "content": f"📊 **Visualización Generada:** {titulo}",
            "visualizacion": {"tipo": tipo, "datos": df.to_dict(orient="records"), "x": x_purgado, "y": y_purgado, "titulo": titulo}
        })
        st.session_state["necesita_rerun"] = True
        return {"status": "success", "mensaje": "Componente proyectado en la pantalla del usuario."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

herramientas_react = [ejecutar_sql, renderizar_interfaz_visual]

# --- 5. ESQUEMA DE DATOS PARA ORIENTACIÓN DEL MODELO ---
esquema_base_datos = """
Tablas y Columnas del Sistema:
1. Table 'cat_banderas': id_bandera (int4, PK), nombre (varchar)
2. Table 'cat_tipos_pesca': id_tipo (int4, PK), nombre (varchar)
3. Table 'cat_empresas': id_empresa (varchar, PK), nombre (varchar), imo (varchar), direccion (text)
4. Table 'buques_maestro': id_buque (varchar, PK), imo (varchar), eslora (numeric), arqueo_bruto (numeric), fecha_construccion (varchar)
5. Table 'buques_identidad': id_historial (uuid, PK), id_buque (varchar), nombre (varchar), id_bandera (int4), mmsi (varchar), mmsi_2 (varchar), indicativo_llamada (varchar), id_tipo (int4), id_empresa (varchar), riesgo (varchar), es_actual (bool)
6. Table 'operaciones': id_operacion (varchar, PK), id_buque (varchar), puerto_origen (varchar), fecha_zarpada (varchar), area_procedente (varchar), area_fao_procedente (varchar), temporada (varchar), fecha_ingreso_area (varchar), area_ingreso (varchar), puertos_operaciones (text), cantidad_arribos (int4), encuentros (text), operó_en_zeea (varchar), salida_destino (varchar), fecha_egreso (varchar), puerto_amarre (varchar), fecha_amarre (varchar)
7. Table 'navegaciones_zeea': id_registro (varchar, PK), id_buque (varchar), fecha_ingreso_zeea (varchar), procedencia (varchar), fecha_egreso_zeea (varchar), destino (varchar)
"""

# --- 6. CONFIGURACIÓN DEL AGENTE DE INTELIGENCIA REACT ---
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite', 
    tools=herramientas_react,
    system_instruction=f"""
    Eres Charly v2, un agente de análisis de datos avanzado configurado bajo el framework ReAct para el Operador {operador}.
    
    TÚ ESQUEMA COGNITIVO (CICLO REACT):
    1. RAZONAR: Analiza la solicitud del usuario. Planifica la consulta SQL SELECT exacta utilizando este esquema: {esquema_base_datos}.
    2. RECOMENDACIÓN DE EFICIENCIA: Para preguntas analíticas complejas (como buscar duplicados o contar registros), intenta escribir consultas SQL que agrupen o filtren (ej. usando COUNT, GROUP BY, HAVING) en lugar de descargar tablas completas.
    3. ACTUAR: Invoca la herramienta `ejecutar_sql`.
    4. OBSERVACIÓN DINÁMICA: Lee la respuesta de la herramienta. 
       - Si el resultado de la consulta fue masivo (>=15 filas), la herramienta interceptará los datos, los pintará en la pantalla del usuario automáticamente y te devolverá un resumen con el conteo de filas y una pequeña muestra. Utiliza esa información resumida para elaborar tu conclusión.
    5. RESPUESTA FINAL: Redacta tu informe final de forma directa, concisa, profesional y corporativa. Confirma los hallazgos numéricos exactos apoyándote en lo observado.
    
    DIRECTRICES ESTRICTAS:
    - Está terminantemente prohibido utilizar la palabra "táctica", "táctico" o modismos de simulación militar. Sé ejecutivo.
    - No mandes al usuario a contar o revisar registros a mano. Si la herramienta te indica el número total de filas o duplicados procesados, menciona esa cifra con autoridad.
    """
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Centro de Análisis ReAct v2 Estabilizado.** Operador **{operador}**, pasarela SQL protegida contra saturación de cuota. Introduzca su requerimiento."}]

# --- 7. INTERFAZ DE CHAT Y DESPLIEGUE VISUAL REACTIVO ---
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Analista ReAct <span style='color: #3B82F6;'>Charly v2</span></h1>", unsafe_allow_html=True)

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

if prompt := st.chat_input("Ordene cualquier consulta analítica o auditoría cruzada..."):
    st.session_state["necesita_rerun"] = False
    st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Ejecutando ciclo ReAct (Razonamiento, Acción y Observación)..."):
            try:
                respuesta = st.session_state.chat.send_message(prompt)
                st.markdown(respuesta.text)
                st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
                
                if st.session_state.get("necesita_rerun", False):
                    st.session_state["necesita_rerun"] = False
                    st.rerun()
            except Exception as api_e:
                st.error(f"Fallo de comunicación en el bucle ReAct: {api_e}")
