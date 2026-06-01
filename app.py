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

# --- 4. ARSENAL DE HERRAMIENTAS COMPLETAS (LECTURA Y ESCRITURA SEPARADAS) ---

def ejecutar_sql(query: str) -> str:
    """
    Ejecuta una consulta SQL SELECT en la base de datos y devuelve las filas resultantes en formato JSON.
    Úsala para auditar datos, verificar si existen registros duplicados o elementos repetidos antes de guardar información.
    Only select queries allowed.
    """
    try:
        clean_query = query.strip()
        if not clean_query.lower().startswith("select"):
            return json.dumps({"status": "error", "mensaje": "Solo se permiten consultas SELECT de lectura por seguridad."})
        
        res = supabase.rpc("ejecutar_sql", {"query": clean_query}).execute()
        
        if not res.data:
            return json.dumps({"status": "success", "mensaje": "La consulta se ejecutó correctamente pero devolvió 0 registros."})
            
        total_filas = len(res.data)
        
        if total_filas >= 15:
            df = pd.DataFrame(res.data)
            df.columns = [col.upper() for col in df.columns]
            st.session_state.mensajes_ui.append({
                "role": "assistant", 
                "content": f"📊 **Resultados Optimizados:** Se han extraído {total_filas} registros y se desplegaron en la pantalla.",
                "visualizacion": {"tipo": "tabla", "datos": df.to_dict(orient="records")}
            })
            st.session_state["necesita_rerun"] = True
            
            return json.dumps({
                "status": "success",
                "info": "Datos masivos renderizados directo en pantalla.",
                "total_filas": total_filas,
                "columnas": list(res.data[0].keys()),
                "muestra": res.data[:2]
            })
            
        return json.dumps(res.data)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


def registrar_nuevo_buque(id_buque: str, nombre: str, mmsi: str, id_bandera: int, id_empresa: str, riesgo: str) -> str:
    """
    Registra físicamente un nuevo buque en la tabla 'buques_identidad'. 
    Solo debe ser invocada cuando el usuario haya confirmado explícitamente que los datos previsualizados son correctos.
    """
    try:
        nuevo_registro = {
            "id_buque": id_buque.strip(),
            "nombre": nombre.strip().upper(),
            "mmsi": mmsi.strip(),
            "id_bandera": int(id_bandera),
            "id_empresa": id_empresa.strip(),
            "riesgo": riesgo.strip(),
            "es_actual": True
        }
        res = supabase.table("buques_identidad").insert(nuevo_registro).execute()
        if res.data:
            return json.dumps({"status": "success", "mensaje": f"El buque {nombre.upper()} fue dado de alta de manera exitosa en la base de datos."})
        return json.dumps({"status": "error", "mensaje": "No se pudo confirmar la inserción de datos."})
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})


def renderizar_interfaz_visual(tipo: str, titulo: str, datos_en_json: str, x_col: str = None, y_col: str = None) -> dict:
    """
    Renderiza un componente visual interactivo (tabla, grafico_barras o grafico_torta) en la pantalla del usuario.
    """
    try:
        datos = json.loads(datos_en_json)
        df = pd.DataFrame(datos)
        df.columns = [col.upper() for col in df.columns]
        
        st.session_state.mensajes_ui.append({
            "role": "assistant", 
            "content": f"📊 **Visualización Generada:** {titulo}",
            "visualizacion": {"tipo": tipo, "datos": df.to_dict(orient="records"), "x": x_col.upper() if x_col else None, "y": y_col.upper() if y_col else None, "titulo": titulo}
        })
        st.session_state["necesita_rerun"] = True
        return {"status": "success", "mensaje": "Componente proyectado en la pantalla."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

herramientas_react = [ejecutar_sql, registrar_nuevo_buque, renderizar_interfaz_visual]

# --- 5. ESQUEMA DE DATOS ---
esquema_base_datos = """
Tablas y Columnas del Sistema:
1. Table 'cat_banderas': id_bandera (int4, PK), nombre (varchar)
2. Table 'cat_tipos_pesca': id_tipo (int4, PK), nombre (varchar)
3. Table 'cat_empresas': id_empresa (varchar, PK), nombre (varchar), imo (varchar)
4. Table 'buques_maestro': id_buque (varchar, PK), imo (varchar), eslora (numeric), arqueo_bruto (numeric)
5. Table 'buques_identidad': id_historial (uuid, PK), id_buque (varchar), nombre (varchar), id_bandera (int4), mmsi (varchar), id_tipo (int4), id_empresa (varchar), riesgo (varchar), es_actual (bool)
"""

# --- 6. CONFIGURACIÓN DEL AGENTE DE INTELIGENCIA CON PROTOCOLO SEGURO ---
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite', 
    tools=herramientas_react,
    system_instruction=f"""
    Eres Charly v2, un agente de análisis y gestión de datos avanzado bajo el framework ReAct para el Operador {operador}.
    
    PROTOCOLO OBLIGATORIO PARA LA CARGA DE NUEVOS BUQUES:
    Cuando el usuario te solicite registrar, dar de alta o cargar un nuevo buque, DEBES seguir estrictamente esta secuencia de estados sin saltarte ningún paso:
    
    1. VALIDACIÓN DE CAMPOS: Verifica que cuentes con todos los datos necesarios: 'id_buque', 'nombre', 'mmsi', 'id_bandera', 'id_empresa', 'riesgo'. Si falta alguno, detén el proceso y solicita de manera amable todos los campos faltantes en una sola respuesta clara.
    
    2. AUDITORÍA DE ANOMALÍAS (CICLO REACT): Una vez que tengas los datos completos, NO invoques la función de escritura todavía. Primero, debes ejecutar una consulta de lectura con `ejecutar_sql` para verificar anomalías en la base de datos:
       - Busca si el 'id_buque' o el 'mmsi' provistos ya existen dentro de la tabla 'buques_identidad'.
       - Valida reglas de negocio básicas en tu razonamiento (ej. si el MMSI no tiene exactamente 9 dígitos, es una anomalía de formato).
       Si encuentras un duplicado o error de formato, lístalo explícitamente en tu respuesta como una "Anomalía Detectada". Si todo está en orden, reporta: "Auditoría de consistencia: Sin anomalías detectadas".
    
    3. PREVISUALIZACIÓN ESTRUCTURADA: Inmediatamente después de informar sobre las anomalías, debes mostrarle al usuario la estructura completa del bloque de información que se pretende insertar. Preséntala de forma impecable usando un bloque de código estructurado en formato JSON.
    
    4. CORTE Y CONFIRMACIÓN HUMANA: Al final de ese mensaje, haz una pregunta de confirmación directa y clara: "¿Confirma el ingreso de este bloque de información en la base de datos?". En este turno, ESTÁ TERMINANTEMENTE PROHIBIDO invocar la herramienta `registrar_nuevo_buque`. Debes esperar la respuesta del usuario.
    
    5. INSERCIÓN FINAL: Solo cuando el usuario te responda de forma explícita con una afirmación (ej. "Sí", "Proceder", "Confirmado"), procederás en ese nuevo turno a ejecutar la herramienta `registrar_nuevo_buque` con los datos auditados.
    
    REGLAS GENERALES:
    - Está prohibido utilizar la palabra "táctica", "táctico" o modismos militares. Sé directo, pulcro y puramente corporativo.
    - No delegues en el usuario la tarea de buscar o contar duplicados. Tú haces la consulta intermedia y le das las conclusiones en limpio.
    """
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Centro de Análisis Operativo Activo.** Operador **{operador}**, sistemas de consulta ReAct y protocolos de modificación segura en línea. ¿Qué datos desea procesar?"}]

# --- 7. INTERFAZ DE CHAT Y DESPLIEGUE VISUAL ---
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Analista Operativo <span style='color: #3B82F6;'>Charly v2</span></h1>", unsafe_allow_html=True)

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

if prompt := st.chat_input("Introduzca una consulta o solicitud de registro..."):
    st.session_state["necesita_rerun"] = False
    st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Procesando en el ciclo seguro de datos..."):
            try:
                respuesta = st.session_state.chat.send_message(prompt)
                st.markdown(respuesta.text)
                st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
                
                if st.session_state.get("necesita_rerun", False):
                    st.session_state["necesita_rerun"] = False
                    st.rerun()
            except Exception as api_e:
                st.error(f"Fallo de comunicación en la interfaz de datos: {api_e}")
