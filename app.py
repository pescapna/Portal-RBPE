import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import json

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM ---
st.set_page_config(page_title="Charly - Agente RBPE", page_icon="⚓", layout="wide")

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
        if st.button("INICIAR SESIÓN", use_container_width=True):
            if user_input in st.secrets["passwords"] and pass_input == st.secrets["passwords"][user_input]:
                st.session_state["password_correct"] = True
                st.session_state["user"] = user_input.capitalize()
                st.rerun()
            else: 
                st.error("Acceso denegado.")
    st.stop()

operador = st.session_state["user"]

# --- 3. CONEXIÓN DE INFRAESTRUCTURA MÁSTER ---
@st.cache_resource
def init_connections():
    supa = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    # Conexión relacional nativa a Postgres para consultas complejas
    eng = create_engine(st.secrets["supabase"]["postgres_uri"])
    return supa, eng

supabase, engine = init_connections()

# --- 4. ARSENAL DE HERRAMIENTAS DE CHARLY (FUNCTION CALLING) ---

def buscar_perfil_buque(identificador: str) -> dict:
    """
    Busca información individual detallada de un buque por su nombre o número MMSI.
    Devuelve datos de identidad, bandera, tipo de pesca y empresa.
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

def analisis_tactico_sql(query_sql: str) -> dict:
    """
    Ejecuta consultas SQL analíticas de LECTURA en la base de datos PostgreSQL.
    Útil para contar, agrupar (GROUP BY), promediar, cruzar datos (JOIN) y responder 
    preguntas complejas sobre masas de datos de la flota, banderas, riesgos y operaciones globales.
    """
    try:
        # Filtro de Seguridad Crítico: Bloquear comandos de escritura o alteración
        query_upper = query_sql.strip().upper()
        if not query_upper.startswith("SELECT") or "DELETE" in query_upper or "DROP" in query_upper or "UPDATE" in query_upper or "INSERT" in query_upper:
            return {"status": "error", "mensaje": "Comando de base de datos denegado por seguridad. Solo se permiten consultas SELECT de lectura."}
            
        df = pd.read_sql(query_sql, engine)
        
        # Limitar la transferencia de filas para no quebrar la ventana de contexto del LLM
        if len(df) > 60:
            resumen = df.head(60).to_dict(orient="records")
            return {"status": "success", "nota": "Mostrando primeros 60 registros debido al límite de transmisión operacional.", "datos": resumen}
            
        return {"status": "success", "datos": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

def renderizar_visualizacion(tipo: str, titulo: str, datos_en_json: str, x_col: str = None, y_col: str = None) -> dict:
    """
    Ordena al sistema del frontend renderizar un elemento visual interactivo como un Gráfico o Tabla.
    Parámetros obligatorios:
    - tipo: Debe ser 'tabla', 'grafico_barras' o 'grafico_torta'.
    - titulo: Encabezado de la visualización.
    - datos_en_json: Los datos estructurados que quieres graficar en formato string JSON.
    - x_col / y_col: El nombre de las propiedades/columnas que se usarán para los ejes X e Y respectivamente si es un gráfico.
    """
    try:
        # Validar la estructura de datos entrante
        datos = json.loads(datos_en_json)
        
        # Inyectamos de manera segura la orden visual en el historial activo de la UI de Streamlit
        st.session_state.mensajes_ui.append({
            "role": "assistant", 
            "content": f"📊 **Desplegando visualización:** *{titulo}*",
            "visualizacion": {
                "tipo": tipo,
                "datos": datos,
                "titulo": titulo,
                "x": x_col,
                "y": y_col
            }
        })
        return {"status": "success", "mensaje": "Visualización enviada al puente de mando exitosamente."}
    except Exception as e:
        return {"status": "error", "mensaje": f"Error al formatear datos visuales: {str(e)}"}

herramientas_charly = [buscar_perfil_buque, analisis_tactico_sql, renderizar_visualizacion]

# --- 5. CONFIGURACIÓN DEL AGENTE INTELIGENTE ---
MODELO_ACTIVO = 'gemini-3.1-flash-lite' 

model = genai.GenerativeModel(
    model_name=MODELO_ACTIVO, 
    tools=herramientas_charly,
    system_instruction=f"""
    Eres Charly, el sistema de IA y analista naval autónomo del Comando RBPE bajo las órdenes del Operador {operador}.
    
    TU ESTRUCTURA DE TABLAS DISPONIBLES EN POSTGRESQL ES:
    - buques_identidad (id_buque varchar, nombre varchar, mmsi varchar, riesgo varchar, id_bandera int4, id_tipo int4, id_empresa varchar)
    - buques_maestro (id_buque varchar, imo varchar, eslora numeric, arqueo_bruto numeric, fecha_construccion varchar)
    - cat_banderas (id_bandera int4, nombre varchar)
    - cat_tipos_pesca (id_tipo int4, nombre varchar)
    - cat_empresas (id_empresa varchar, nombre varchar, imo varchar)
    - operaciones (id_operacion varchar, id_buque varchar, puerto_origen varchar, fecha_zarpada varchar, area_ingreso varchar, opero_en_zeea varchar...)
    - navegaciones_zeea (id_registro varchar, id_buque varchar, fecha_ingreso_zeea varchar, procedencia varchar...)
    
    REGLAS DE OPERACIÓN CRÍTICAS:
    1. Si te piden recuentos, totales, promedios, cruces o análisis de flotas/banderas/riesgos globales, DEBES estructurar una consulta SQL y ejecutarla usando la herramienta `analisis_tactico_sql`. Haz los JOINs necesarios con los catálogos para mostrar los nombres de los países/empresas en vez de los IDs numéricos.
    2. Cuando obtengas los datos de un análisis global, es tu obligación MANDATORIA mostrárselos al usuario llamando inmediatamente a la función `renderizar_visualizacion`. Pásale los datos en un formato JSON limpio y asigna los tipos correspondientes ('tabla', 'grafico_barras', 'grafico_torta').
    3. Si la base de datos devuelve un error o no arroja registros, detalla el reporte con estricta veracidad militar. No inventes datos bajo ninguna circunstancia.
    4. Tu tono debe ser directo, conciso y altamente analítico.
    """
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Comando Integrado en línea.** Operador **{operador}**, sistemas de análisis global SQL y renderizado de gráficos activados. ¿Cuál es su requerimiento?"}]

# --- 6. INTERFAZ DE CHAT Y DESPLIEGUE VISUAL (FRONTEND) ---
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Analista Naval <span style='color: #3B82F6;'>Charly</span></h1>", unsafe_allow_html=True)

# Renderizado dinámico del historial y componentes visuales reactivos
for msg in st.session_state.mensajes_ui:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Interceptor dinámico: Si el mensaje contiene un empaquetado visual de Charly, Streamlit lo construye aquí
        if "visualizacion" in msg:
            v = msg["visualizacion"]
            df_visual = pd.DataFrame(v["datos"])
            
            # Dibujar el tipo de objeto solicitado de forma interactiva
            if v["tipo"] == "tabla":
                st.dataframe(df_visual, use_container_width=True)
                
            elif v["tipo"] == "grafico_barras" and v["x"] and v["y"]:
                fig = px.bar(df_visual, x=v["x"], y=v["y"], title=v["titulo"], template="plotly_dark")
                # Estilización rápida para combinar con tu paleta oscura premium
                fig.update_traces(marker_color='#3B82F6')
                st.plotly_chart(fig, use_container_width=True)
                
            elif v["tipo"] == "grafico_torta" and v["x"] and v["y"]:
                fig = px.pie(df_visual, names=v["x"], values=v["y"], title=v["titulo"], template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

# Captura de órdenes en lenguaje natural
if prompt := st.chat_input("Ordene un análisis global (ej: 'Dame un gráfico de barras de la cantidad de buques por cada bandera' o 'Muestra una tabla con los buques de alto riesgo')..."):
    st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Procesando comando, estructurando inteligencia SQL y generando gráficos..."):
            try:
                # El modelo procesa, llama a sql_analisis, recibe los datos de postgres, 
                # llama a renderizar_visualizacion y finalmente genera el texto conclusivo.
                respuesta = st.session_state.chat.send_message(prompt)
                
                # Renderiza el texto final explicativo del modelo
                st.markdown(respuesta.text)
                st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
                
                # Hacemos un rerun rápido en caso de que Charly haya inyectado un gráfico para forzar a Streamlit a pintarlo de inmediato
                if "Desplegando visualización" in respuesta.text:
                    st.rerun()
                    
            except Exception as api_e:
                st.error(f"Error de enlace en la matriz de comunicaciones: {api_e}")
