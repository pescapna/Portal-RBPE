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

# --- 4. LA HERRAMIENTA UNIVERSAL REACT V2 (NÚCLEO DEL AGENTE) ---

def ejecutar_sql(query: str) -> str:
    """
    Ejecuta de manera directa una consulta SQL de tipo SELECT en la base de datos y devuelve las filas resultantes en formato JSON.
    Permite realizar auditorías de duplicados, comparaciones por cualquier columna (IMO, MMSI), cálculos estadísticos, promedios y relaciones complejas.
    Solo se admiten instrucciones SELECT de lectura.
    """
    try:
        # Validación de seguridad básica en la capa de la aplicación
        clean_query = query.strip()
        if not clean_query.lower().startswith("select"):
            return json.dumps({"status": "error", "mensaje": "Restricción de seguridad: Solo se permiten consultas SELECT de lectura."})
        
        # Invocación remota segura mediante la pasarela HTTPS RPC
        res = supabase.rpc("ejecutar_sql", {"query": clean_query}).execute()
        
        if not res.data:
            return json.dumps({"status": "success", "mensaje": "La consulta se ejecutó correctamente pero devolvió 0 registros."})
            
        # Retorna el JSON crudo directo a la ventana de observación de Gemini
        return json.dumps(res.data)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


def renderizar_interfaz_visual(tipo: str, titulo: str, datos_en_json: str, x_col: str = None, y_col: str = None) -> dict:
    """
    Renderiza de forma interactiva un componente visual (tabla, grafico_barras o grafico_torta) en la pantalla del usuario.
    Usa esta función en el paso final de tu razonamiento si los datos merecen ser tabulados o graficados para el operador.
    - datos_en_json: String con la estructura limpia de los registros finales a mostrar.
    """
    try:
        datos = json.loads(datos_en_json)
        df = pd.DataFrame(datos)
        df.columns = [col.upper() for col in df.columns]
        
        # Convertir columnas x e y a mayúsculas si se proveen para hacer match con el dataframe purgado
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
6. Table 'operaciones': id_operacion (varchar, PK), id_buque (varchar), puerto_origen (varchar), fecha_zarpada (varchar), area_procedente (varchar), area_fao_procedente (varchar), temporada (varchar), fecha_ingreso_area (varchar), area_ingreso (varchar), puertos_operaciones (text), cantidad_arribos (int4), encuentros (text), operó_en_zeea (varchar), operó_en_adyacente (varchar), operó_en_malvinas (varchar), salida_destino (varchar), fecha_egreso (varchar), puerto_amarre (varchar), fecha_amarre (varchar)
7. Table 'navegaciones_zeea': id_registro (varchar, PK), id_buque (varchar), fecha_ingreso_zeea (varchar), procedencia (varchar), fecha_egreso_zeea (varchar), destino (varchar)
"""

# --- 6. CONFIGURACIÓN DEL AGENTE DE INTELIGENCIA REACT ---
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite', 
    tools=herramientas_react,
    system_instruction=f"""
    Eres Charly v2, un agente de análisis de datos avanzado configurado bajo el framework ReAct para el Operador {operador}.
    
    TÚ ESQUEMA COGNITIVO (CICLO REACT):
    1. RAZONAR: Analiza la solicitud del usuario. Identifica qué tablas necesitas consultar basándote en el siguiente esquema: {esquema_base_datos}. Planifica la consulta SQL SELECT exacta que resolverá el problema de forma óptima.
    2. ACTUAR: Escribe la consulta SQL limpia y ejecútala invocando ÚNICAMENTE la herramienta `ejecutar_sql`.
    3. OBSERVACIÓN DINÁMICA: Cuando la herramienta te devuelva las filas en formato JSON, leelas con atención. Tú eres el cerebro analítico. Inspecciona si hay valores duplicados, promedios, cruces o vacíos.
    4. EVALUACIÓN DE SUFICIENCIA: Si los datos recolectados no bastan o necesitas cruzar otra tabla (ej. resolver nombres de empresas o banderas a partir de sus IDs), vuelve al paso 1 y genera un nuevo SQL. Itera las veces que sea necesario.
    5. RESPUESTA FINAL: Cuando tengas la conclusión analítica exacta, si consideras útil desplegar los resultados en una tabla estructurada o gráfico para el usuario, invoca primero la función `renderizar_interfaz_visual`. Posteriormente redacta tu narrativa final de forma directa, concisa, profesional y ejecutiva.
    
    DIRECTRICES ESTRICTAS:
    - Tienes visibilidad absoluta sobre el JSON que devuelve `ejecutar_sql`. Por ende, está estrictamente prohibido pedirle al usuario que verifique, cuente o busque datos de forma manual. Tú debes darle la respuesta masticada y el análisis final (ej. si hay duplicados, indica cuáles son y cuántas veces se repiten exactamente).
    - No uses bajo ningún concepto la palabra "táctica", "táctico" ni modismos de simulación militar. Sé directo y de alta corporatividad.
    """
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Centro de Análisis ReAct v2 Online.** Operador **{operador}**, pasarela SQL universal activa sobre protocolo HTTPS. Introduzca su consulta analítica."}]

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
