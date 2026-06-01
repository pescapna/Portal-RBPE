import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import json
import uuid  # Para la auto-generación de IDs únicos seguros

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM ---
st.set_page_config(page_title="Charly v2 - Centro de Análisis", page_icon="⚓", layout="wide")

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
    div[data-testid="stForm"] {
        background: rgba(22, 27, 34, 0.4) !important;
        border: 1px solid rgba(48, 54, 61, 0.6) !important;
        border-radius: 16px;
        padding: 2rem;
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

# --- 4. ARSENAL DE FUNCIONES INTERNAS (BACKEND) ---

def ejecutar_sql(query: str) -> str:
    """Ejecuta una consulta SQL SELECT en la base de datos y devuelve formato JSON."""
    try:
        clean_query = query.strip()
        if not clean_query.lower().startswith("select"):
            return json.dumps({"status": "error", "mensaje": "Solo se permiten consultas SELECT de lectura."})
        res = supabase.rpc("ejecutar_sql", {"query": clean_query}).execute()
        if not res.data:
            return json.dumps({"status": "success", "mensaje": "Consulta con 0 registros de respuesta."})
        
        total_filas = len(res.data)
        if total_filas >= 15:
            df = pd.DataFrame(res.data)
            df.columns = [col.upper() for col in df.columns]
            st.session_state.mensajes_ui.append({
                "role": "assistant", 
                "content": f"📊 **Resultados Optimizados:** Se han extraído {total_filas} registros directamente a pantalla.",
                "visualizacion": {"tipo": "tabla", "datos": df.to_dict(orient="records")}
            })
            st.session_state["necesita_rerun"] = True
            return json.dumps({"status": "success", "info": "Datos masivos renderizados directo en pantalla.", "total_filas": total_filas, "columnas": list(res.data[0].keys()), "muestra": res.data[:2]})
            
        return json.dumps(res.data)
    except Exception as e:
        return json.dumps({"status": "error", "mensaje": str(e)})

def registrar_nuevo_buque_backend(registro_dict: dict) -> bool:
    """Inserta el diccionario del buque de forma directa en Supabase."""
    try:
        res = supabase.table("buques_identidad").insert(registro_dict).execute()
        return True if res.data else False
    except:
        return False

def renderizar_interfaz_visual(tipo: str, titulo: str, datos_en_json: str, x_col: str = None, y_col: str = None) -> dict:
    """Renderiza componentes gráficos en la sección de chat."""
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
        return {"status": "success", "mensaje": "Componente proyectado en pantalla."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

herramientas_react = [ejecutar_sql, renderizar_interfaz_visual]

# --- 5. ESQUEMA DE DATOS PARA EL CHAT ---
esquema_base_datos = "Table 'buques_identidad' y catalogos relacionales ('cat_banderas', 'cat_empresas')."

# --- 6. AGENTE INTELIGENTE DE DIÁLOGO ---
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite', 
    tools=herramientas_react,
    system_instruction=f"Eres Charly v2, un analista de datos experto bajo framework ReAct para el Operador {operador}. Responde consultas analíticas con lenguaje profesional y ejecutivo. Prohibido usar modismos militares o la palabra 'táctica'."
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)
if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Centro de Análisis Online.** Operador **{operador}**, sistemas de consulta listos. ¿Qué información de la flota desea evaluar?"}]

# --- 7. DISEÑO DE INTERFAZ EN PESTAÑAS (TABS) ---
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Centro de Control <span style='color: #3B82F6;'>Charly v2</span></h1>", unsafe_allow_html=True)

tab_analisis, tab_registro = st.tabs(["📊 Centro de Análisis (Chat)", "📝 Registro Automatizado de Buques"])

# =====================================================================
# PESTAÑA 1: CHAT ANALÍTICO LIBRE
# =====================================================================
with tab_analisis:
    for msg in st.session_state.mensajes_ui:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "visualizacion" in msg:
                v = msg["visualizacion"]
                df_visual = pd.DataFrame(v["datos"])
                if v["tipo"] == "tabla":
                    st.dataframe(df_visual, use_container_width=True)
                elif v["tipo"] == "grafico_barras":
                    fig = px.bar(df_visual, x=v["x"], y=v["y"], title=v["titulo"], template="plotly_dark")
                    fig.update_traces(marker_color='#3B82F6')
                    st.plotly_chart(fig, use_container_width=True)
                elif v["tipo"] == "grafico_torta":
                    fig = px.pie(df_visual, names=v["x"], values=v["y"], title=v["titulo"], template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)

    if prompt := st.chat_input("Consulte duplicados, historiales o datos generales..."):
        st.session_state["necesita_rerun"] = False
        st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analizando información..."):
                try:
                    respuesta = st.session_state.chat.send_message(prompt)
                    st.markdown(respuesta.text)
                    st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
                    if st.session_state.get("necesita_rerun", False):
                        st.session_state["necesita_rerun"] = False
                        st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# =====================================================================
# PESTAÑA 2: FORMULARIO AUTOMATIZADO CON AUDITORÍA DE ANOMALÍAS
# =====================================================================
with tab_registro:
    st.markdown("### 📝 Alta de Unidades en el Sistema")
    st.write("Complete la información comercial e identificativa del buque. El sistema resolverá los identificadores relacionales y auditará anomalías automáticamente.")

    # Carga dinámica de catálogos desde Supabase para poblar los selectores
    try:
        banderas_res = supabase.table("cat_banderas").select("id_bandera, nombre").execute()
        dict_banderas = {item['nombre']: item['id_bandera'] for item in banderas_res.data} if banderas_res.data else {}
        
        empresas_res = supabase.table("cat_empresas").select("id_empresa, nombre").execute()
        dict_empresas = {item['nombre'] if item['nombre'] else f"ID: {item['id_empresa']}": item['id_empresa'] for item in empresas_res.data} if empresas_res.data else {}
    except Exception as e:
        st.error(f"Error al conectar con los catálogos del servidor: {e}")
        dict_banderas, dict_empresas = {}, {}

    # Estructura del Formulario de Entrada
    with st.form("formulario_alta_buque"):
        col_form1, col_form2 = st.columns(2)
        with col_form1:
            input_nombre = st.text_input("Nombre del Buque *", placeholder="Ej: XINRUN 579").strip()
            input_mmsi = st.text_input("Número MMSI *", placeholder="Ej: 224142000 (9 dígitos)").strip()
            input_riesgo = st.selectbox("Clasificación de Riesgo *", ["Bajo", "Medio", "Alto"])
        
        with col_form2:
            input_bandera = st.selectbox("Pabellón / Bandera *", list(dict_banderas.keys()))
            input_empresa = st.selectbox("Empresa Propietaria/Operadora *", list(dict_empresas.keys()))
            input_llamada = st.text_input("Indicativo de Llamada (Opcional)", placeholder="Ej: LI2345").strip()

        btn_auditar = st.form_submit_button("🛡️ AUDITAR REGISTRO Y PREVISUALIZAR BLOCK JSON")

    # Lógica del botón de procesamiento y control de estados
    if btn_auditar:
        # Validación de campos requeridos vacíos en el Frontend
        if not input_nombre or not input_mmsi:
            st.error("Error de entrada: El 'Nombre del Buque' y el 'Número MMSI' son obligatorios.")
        elif len(input_mmsi) != 9 or not input_mmsi.isdigit():
            st.error("Anomalía de formato: El código MMSI debe estar compuesto estrictamente por 9 caracteres numéricos.")
        else:
            with st.spinner("Ejecutando auditoría cruzada de consistencia..."):
                # Ejecutar verificaciones en Supabase para detectar anomalías de duplicados
                nombre_duplicado = supabase.table("buques_identidad").select("nombre").ilike("nombre", input_nombre).execute()
                mmsi_duplicado = supabase.table("buques_identidad").select("mmsi").eq("mmsi", input_mmsi).execute()
                
                anomalies = []
                if nombre_duplicado.data:
                    anomalies.append(f"Alerta: Ya existe un buque registrado con el nombre '{input_nombre.upper()}' en la base de datos.")
                if mmsi_duplicado.data:
                    anomalies.append(f"Alerta: El número MMSI '{input_mmsi}' ya está asignado a otra unidad registrada.")

                # Imprimir informe de auditoría
                if anomalies:
                    st.warning("### ⚠️ Anomalías Críticas Detectadas")
                    for a in anomalies: st.write(f"- {a}")
                    st.session_state["bloque_confirmado"] = None
                else:
                    st.success("###  Auditoría de Consistencia: Sin anomalías detectadas")
                    st.write("La información es válida y no genera colisiones de identidad en los registros actuales.")
                    
                    # Generación automática y transparente del ID de Buque único
                    id_generado = f"BQ-{input_nombre[:3].upper()}-{uuid.uuid4().hex[:5].upper()}"
                    
                    # Ensamblar el bloque de información estructurado en formato TOML/JSON listo para el Operador
                    bloque_informacion = {
                        "id_buque": id_generado,
                        "nombre": input_nombre.upper(),
                        "mmsi": input_mmsi,
                        "id_bandera": dict_banderas[input_bandera],
                        "id_empresa": dict_empresas[input_empresa],
                        "indicativo_llamada": input_llamada if input_llamada else None,
                        "riesgo": input_riesgo,
                        "es_actual": True
                    }
                    
                    # Almacenamos el bloque temporalmente en la sesión para que sobreviva al refresco de Streamlit
                    st.session_state["bloque_confirmado"] = bloque_informacion

    # Fase de confirmación explícita (Muestra el JSON y habilita el botón físico final)
    if st.session_state.get("bloque_confirmado") is not None:
        st.markdown("---")
        st.markdown("### 📋 Estructura Completa del Bloque de Información (Previsualización)")
        st.json(st.session_state["bloque_confirmado"])
        
        st.write("¿Confirma el ingreso permanente de este bloque de información estructurado en la base de datos?")
        
        if st.button("CONFIRMAR E INSERTAR REGISTRO", use_container_width=True):
            exito = registrar_nuevo_buque_backend(st.session_state["bloque_confirmado"])
            if exito:
                st.success(f" Registro Guardado: La unidad '{st.session_state['bloque_confirmado']['nombre']}' fue dada de alta con éxito en el sistema.")
                st.session_state["bloque_confirmado"] = None  # Limpiamos el buffer
            else:
                st.error("Fallo de escritura: No se pudo consolidar el registro en el servidor remoto.")
