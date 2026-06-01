import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import json

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM MÁSTER ---
st.set_page_config(page_title="Charly - Agente PAPE", page_icon="⚓", layout="wide")

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

# --- 3. INFRAESTRUCTURA INMUNE (CONEXIÓN API HTTPS NATIIVA) ---
@st.cache_resource
def init_connections():
    # Usamos la API web de Supabase (Puerto 443 estándar, inmune a bloqueos)
    supa = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    return supa

supabase = init_connections()

# --- 4. ARSENAL DE PROCESAMIENTO LOCAL (CERO FUGAS DE TOKENS) ---

def buscar_perfil_buque(identificador: str) -> dict:
    """
    Busca información individual detallada de un buque específico por su nombre o MMSI.
    Útil cuando el usuario pregunta puntualmente por una sola unidad.
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


def generar_reporte_buques_por_bandera(nombre_bandera: str) -> dict:
    """
    Filtra y despliega un listado interactivo en tabla de todos los buques pertenecientes a una bandera.
    Usa esta función obligatoriamente cuando pidan listas o tablas de países.
    """
    try:
        # 1. Resolver el ID de la bandera en los catálogos de Supabase
        res_bandera = supabase.table("cat_banderas").select("id_bandera, nombre").ilike("nombre", f"%{nombre_bandera}%").execute()
        if not res_bandera.data:
            return {"status": "success", "mensaje": f"La bandera '{nombre_bandera}' no consta en nuestros registros actuales."}
        
        id_bandera = res_bandera.data[0]['id_bandera']
        pais_real = res_bandera.data[0]['nombre']
        
        # 2. Descargar únicamente las unidades vinculadas a esa bandera
        res_buques = supabase.table("buques_identidad").select("nombre, mmsi, riesgo, id_empresa").eq("id_bandera", id_bandera).execute()
        
        if not res_buques.data:
            return {"status": "success", "mensaje": f"Enlace correcto. Confirmado que actualmente constan 0 buques operando bajo la bandera de {pais_real}."}
        
        df = pd.DataFrame(res_buques.data)
        
        # 3. Cruzar localmente con el catálogo de empresas en el servidor de Streamlit
        res_empresas = supabase.table("cat_empresas").select("id_empresa, nombre").execute()
        if res_empresas.data:
            df_emp = pd.DataFrame(res_empresas.data).rename(columns={"nombre": "Empresa"})
            df = df.merge(df_emp, on="id_empresa", how="left").drop(columns=["id_empresa"], errors="ignore")
        
        # Reordenar columnas para visualización militar limpia
        df.columns = [col.upper() for col in df.columns]

        # 4. Inyección directa en la UI (By-pass de tokens: los datos no viajan a los servidores de Google)
        st.session_state.mensajes_ui.append({
            "role": "assistant", 
            "content": f"📊 **Listado Analítico:** Flota desplegada bajo bandera de **{pais_real}**.",
            "visualizacion": {"tipo": "tabla", "datos": df.to_dict(orient="records")}
        })
        
        # Encendemos el interruptor electrónico de renderizado instantáneo
        st.session_state["necesita_rerun"] = True
        
        # Retorno de bytes mínimos para proteger la API Key
        return {"status": "success", "mensaje": f"Éxito operacional. Encontrados {len(df)} buques de {pais_real}. El componente visual ya se pintó en pantalla. Informa al operador sucintamente."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def generar_grafico_distribucion(variable_analisis: str) -> dict:
    """
    Genera y procesa gráficos estadísticos masivos de la flota ('riesgo' o 'bandera').
    variable_analisis permitidas estrictamente: 'riesgo' o 'bandera'.
    """
    try:
        res_buques = supabase.table("buques_identidad").select("riesgo, id_bandera").execute()
        df = pd.DataFrame(res_buques.data)
        
        if variable_analisis == "riesgo":
            df_df = df['riesgo'].value_counts().reset_index()
            df_df.columns = ['Nivel de Riesgo', 'Cantidad']
            st.session_state.mensajes_ui.append({
                "role": "assistant", 
                "content": "📊 **Análisis:** Distribución geométrica de los Niveles de Riesgo en la Flota.",
                "visualizacion": {"tipo": "grafico_torta", "datos": df_df.to_dict(orient="records"), "x": "Nivel de Riesgo", "y": "Cantidad", "titulo": "Distribución General de Riesgos"}
            })
        elif variable_analisis == "bandera":
            res_banderas = supabase.table("cat_banderas").select("id_bandera, nombre").execute()
            df_band = pd.DataFrame(res_banderas.data).rename(columns={"nombre": "Bandera"})
            df = df.merge(df_band, on="id_bandera", how="left")
            df_df = df['Bandera'].value_counts().reset_index()
            df_df.columns = ['Bandera', 'Cantidad de Buques']
            
            st.session_state.mensajes_ui.append({
                "role": "assistant", 
                "content": "📊 **Análisis:** Concentración de Volumen de Buques por Bandera Operativa.",
                "visualizacion": {"tipo": "grafico_barras", "datos": df_df.to_dict(orient="records"), "x": "Bandera", "y": "Cantidad de Buques", "titulo": "Carga de Flota por Pabellón Nacional"}
            })
            
        st.session_state["necesita_rerun"] = True
        return {"status": "success", "mensaje": f"Gráfico analítico de {variable_analisis} procesado de forma local en servidor y renderizado en UI. Confírmalo militarmente de forma breve."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

herramientas_charly = [buscar_perfil_buque, generar_reporte_buques_por_bandera, generar_grafico_distribucion]

# --- 5. CONFIGURACIÓN DEL AGENTE INTELIGENTE DE CONTROL ---
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite', 
    tools=herramientas_charly,
    system_instruction=f"""
    Eres Charly, el analista naval del Comando RBPE a cargo del Operador {operador}.
    
    PROTOCOLO DE RESPUESTA DIRECTA:
    1. Si la orden requiere listas, visualizaciones, listados, ver los barcos de un país o reportes masivos de toda la flota por banderas o riesgos, invoca inmediatamente tus funciones analíticas correspondientes (`generar_reporte_buques_por_bandera` o `generar_grafico_distribucion`).
    2. Al delegar todo el procesamiento masivo de datos en Python, los datos se inyectan en pantalla directamente sin saturar tu canal de entrada. Cuando las funciones terminen, recibirás una confirmación corta. Tu única labor es informar de forma ejecutiva, militar y concisa que los gráficos o tablas correspondientes ya se encuentran desplegados en pantalla.
    3. Mantén tus textos finales cortos y profesionales. No inventes datos bajo ninguna circunstancia.
    """
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Comando Integrado en línea.** Operador **{operador}**, sistemas de análisis local y renderizado inmediato estabilizados. ¿Cuáles son sus directivas?"}]

# --- 6. INTERFAZ DE CHAT Y DESPLIEGUE RECOBRADO (FRONTEND) ---
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Analista Naval <span style='color: #3B82F6;'>Charly</span></h1>", unsafe_allow_html=True)

# Pintar el historial reactivamente
for msg in st.session_state.mensajes_ui:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Interceptor Electrónico: Si hay datos visuales, se pintan de forma instantánea
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

# Captura de prompts
if prompt := st.chat_input("Ordene su análisis global (ej: 'Listar buques de bandera de Tanzania' o 'Haz un gráfico de barras por bandera')..."):
    st.session_state["necesita_rerun"] = False
    st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Sincronizando radares y base de datos local..."):
            try:
                # El modelo interactúa, manda el JSON minúsculo, Python procesa en servidor e inyecta el gráfico
                respuesta = st.session_state.chat.send_message(prompt)
                st.markdown(respuesta.text)
                st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
                
                # REFRESCAMIENTO SIN DEMORAS: Rompe el Rendering Lag y actualiza el frontend en el mismo milisegundo
                if st.session_state.get("necesita_rerun", False):
                    st.session_state["necesita_rerun"] = False
                    st.rerun()
            except Exception as api_e:
                st.error(f"Fallo de enlace de comunicaciones: {api_e}")
