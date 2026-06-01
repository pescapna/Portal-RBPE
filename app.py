import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import json

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM MÁSTER ---
st.set_page_config(page_title="Charly - Centro de Análisis", page_icon="⚓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=300;400;600;800&family=JetBrains+Mono:wght=400&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #07090E; color: #E2E8F0; }
    .stApp { background-color: #07090E; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .stChatMessage {
        background: rgba(22, 27, 24, 0.6) !important;
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

# --- 4. ARSENAL DE PROCESAMIENTO GENERAL ---

def consultar_tabla_general(tabla: str, columna_filtro: str = None, valor_filtro: str = None) -> dict:
    """
    Consulta cualquier tabla de la base de datos permitiendo filtrar por una columna y un valor específico.
    Usa esta función para responder CUALQUIER tema general, listados de empresas, tipos de pesca, operaciones globales, catálogos o cualquier pregunta independiente del tema.
    Tablas disponibles: 'buques_identidad', 'buques_maestro', 'operaciones', 'navegaciones_zeea', 'cat_banderas', 'cat_tipos_pesca', 'cat_empresas'.
    """
    try:
        tablas_permitidas = ['buques_identidad', 'buques_maestro', 'operaciones', 'navegaciones_zeea', 'cat_banderas', 'cat_tipos_pesca', 'cat_empresas']
        if tabla not in tablas_permitidas:
            return {"status": "error", "mensaje": f"La tabla '{tabla}' no está autorizada o no existe."}
        
        query = supabase.table(tabla).select("*")
        
        if columna_filtro and valor_filtro:
            query = query.ilike(columna_filtro, f"%{valor_filtro}%")
            
        res = query.limit(150).execute()
        
        if not res.data:
            return {"status": "success", "mensaje": f"No se encontraron registros en la tabla '{tabla}' para los criterios solicitados."}
            
        df = pd.DataFrame(res.data)
        df.columns = [col.upper() for col in df.columns]
        
        st.session_state.mensajes_ui.append({
            "role": "assistant", 
            "content": f"📊 **Resultados del Sistema:** Registros extraídos de la tabla `{tabla}`.",
            "visualizacion": {"tipo": "tabla", "datos": df.to_dict(orient="records")}
        })
        st.session_state["necesita_rerun"] = True
        return {"status": "success", "mensaje": f"Se proyectaron {len(df)} filas de la tabla {tabla} directamente en la pantalla. Informa al usuario de manera directa."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def buscar_perfil_buque(identificador: str) -> dict:
    """
    Busca información de identidad y características físicas estructurales de un buque específico por su nombre o MMSI.
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


def consultar_historial_operaciones(identificador: str) -> dict:
    """
    Consulta y despliega el historial cronológico completo de operaciones y movimientos en la ZEEA de un buque específico (ej: XINRUN 579).
    """
    try:
        res_id = supabase.table("buques_identidad").select("id_buque, nombre, mmsi").or_(f"nombre.ilike.%{identificador}%,mmsi.eq.{identificador}").execute()
        if not res_id.data:
            return {"status": "success", "mensaje": f"No se localizó el buque '{identificador}' en los registros de identidad."}
        
        id_buque = res_id.data[0]['id_buque']
        nombre_real = res_id.data[0]['nombre']
        
        res_ops = supabase.table("operaciones").select(
            "puerto_origen, fecha_zarpada, area_procedente, temporada, fecha_ingreso_area, area_ingreso, puerto_amarre, fecha_amarre"
        ).eq("id_buque", id_buque).execute()
        
        res_zeea = supabase.table("navegaciones_zeea").select(
            "fecha_ingreso_zeea, procedencia, fecha_egreso_zeea, destino"
        ).eq("id_buque", id_buque).execute()
        
        tiene_registros = False
        
        if res_ops.data:
            tiene_registros = True
            df_ops = pd.DataFrame(res_ops.data)
            df_ops.columns = [col.upper() for col in df_ops.columns]
            st.session_state.mensajes_ui.append({
                "role": "assistant", 
                "content": f"📋 **Historial de Operaciones Portuarias** para el buque **{nombre_real}**:",
                "visualizacion": {"tipo": "tabla", "datos": df_ops.to_dict(orient="records")}
            })
            
        if res_zeea.data:
            tiene_registros = True
            df_zeea = pd.DataFrame(res_zeea.data)
            df_zeea.columns = [col.upper() for col in df_zeea.columns]
            st.session_state.mensajes_ui.append({
                "role": "assistant", 
                "content": f"⚓ **Historial de Navegaciones en ZEEA** para el buque **{nombre_real}**:",
                "visualizacion": {"tipo": "tabla", "datos": df_zeea.to_dict(orient="records")}
            })
            
        if not tiene_registros:
            return {"status": "success", "mensaje": f"El buque '{nombre_real}' existe, pero no registra movimientos actualizados en las bitácoras históricas."}
            
        st.session_state["necesita_rerun"] = True
        return {"status": "success", "mensaje": f"Historial de movimientos de {nombre_real} fijado en pantalla de forma exitosa."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def generar_reporte_buques_por_bandera(nombre_bandera: str) -> dict:
    """
    Filtra y despliega un listado de todos los buques de un país o bandera específica.
    """
    try:
        res_bandera = supabase.table("cat_banderas").select("id_bandera, nombre").ilike("nombre", f"%{nombre_bandera}%").execute()
        if not res_bandera.data:
            return {"status": "success", "mensaje": f"La bandera '{nombre_bandera}' no consta en nuestros registros."}
        
        id_bandera = res_bandera.data[0]['id_bandera']
        pais_real = res_bandera.data[0]['nombre']
        
        res_buques = supabase.table("buques_identidad").select("nombre, mmsi, riesgo, id_empresa").eq("id_bandera", id_bandera).execute()
        if not res_buques.data:
            return {"status": "success", "mensaje": f"Confirmado que actualmente constan 0 buques operando bajo la bandera de {pais_real}."}
        
        df = pd.DataFrame(res_buques.data)
        
        res_empresas = supabase.table("cat_empresas").select("id_empresa, nombre").execute()
        if res_empresas.data:
            df_emp = pd.DataFrame(res_empresas.data).rename(columns={"nombre": "Empresa"})
            df = df.merge(df_emp, on="id_empresa", how="left").drop(columns=["id_empresa"], errors="ignore")
        
        df.columns = [col.upper() for col in df.columns]

        st.session_state.mensajes_ui.append({
            "role": "assistant", 
            "content": f"📊 **Listado General:** Flota registrada bajo la bandera de **{pais_real}**.",
            "visualizacion": {"tipo": "tabla", "datos": df.to_dict(orient="records")}
        })
        st.session_state["necesita_rerun"] = True
        return {"status": "success", "mensaje": f"Encontrados {len(df)} buques. Tabla desplegada."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def generar_grafico_distribucion(variable_analisis: str) -> dict:
    """
    Genera y procesa gráficos estadísticos de la flota completa ('riesgo' o 'bandera').
    """
    try:
        res_buques = supabase.table("buques_identidad").select("riesgo, id_bandera").execute()
        df = pd.DataFrame(res_buques.data)
        
        if variable_analisis == "riesgo":
            df_df = df['riesgo'].value_counts().reset_index()
            df_df.columns = ['Nivel de Riesgo', 'Cantidad']
            st.session_state.mensajes_ui.append({
                "role": "assistant", 
                "content": "📊 **Análisis:** Distribución de los Niveles de Riesgo en la Flota.",
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
                "content": "📊 **Análisis:** Volumen de Buques por Bandera Registrada.",
                "visualizacion": {"tipo": "grafico_barras", "datos": df_df.to_dict(orient="records"), "x": "Bandera", "y": "Cantidad de Buques", "titulo": "Flota por Pabellón"}
            })
            
        st.session_state["necesita_rerun"] = True
        return {"status": "success", "mensaje": f"Gráfico de {variable_analisis} desplegado en la UI."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

herramientas_charly = [consultar_tabla_general, buscar_perfil_buque, consultar_historial_operaciones, generar_reporte_buques_por_bandera, generar_grafico_distribucion]

# --- 5. CONFIGURACIÓN DEL AGENTE INTELIGENTE ---
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite', 
    tools=herramientas_charly,
    system_instruction=f"""
    Eres Charly, un analista de datos experto especializado en la base de datos de la flota de buques para el Operador {operador}.
    
    INSTRUCCIONES DIRECTAS DE ATENCIÓN:
    1. Debes responder CUALQUIER tipo de consulta sobre la base de datos independientemente del tema (empresas, operaciones, navegaciones, tipos de pesca, buques, etc.). No des excusas de falta de datos si tienes herramientas disponibles.
    2. Si te preguntan por movimientos, historiales, zarpadas o qué hizo un barco específico, usa `consultar_historial_operaciones`.
    3. Si te piden características físicas de un barco, usa `buscar_perfil_buque`.
    4. Si te piden listas de un país, usa `generar_reporte_buques_por_bandera`.
    5. Si te piden gráficos estadísticos generales, usa `generar_grafico_distribucion`.
    6. PARA CUALQUIER OTRO TEMA (ej. listado de empresas, ver tipos de pesca, operaciones generales en un puerto, inspeccionar catálogos, etc.), utiliza obligatoriamente la función `consultar_tabla_general` especificando el nombre de la tabla y columnas si deseas filtrar.
    7. Cuando una función se ejecute, el sistema pintará los datos en pantalla inmediatamente. Informa al usuario de forma clara, directa y muy profesional que la información correspondiente ya se encuentra desplegada en la pantalla.
    8. Está estrictamente prohibido utilizar la palabra "táctica", "táctico" o modismos de simulación militar. Sé directo y ejecutivo.
    """
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)

if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Sistema de Análisis Online.** Operador **{operador}**, bases de datos integradas y listas para consultas multipropósito de cualquier índole. ¿Qué información requiere?"}]

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

if prompt := st.chat_input("Introduzca su consulta sobre cualquier dato o historial..."):
    st.session_state["necesita_rerun"] = False
    st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Procesando consulta en la base de datos general..."):
            try:
                respuesta = st.session_state.chat.send_message(prompt)
                st.markdown(respuesta.text)
                st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
                
                if st.session_state.get("necesita_rerun", False):
                    st.session_state["necesita_rerun"] = False
                    st.rerun()
            except Exception as api_e:
                st.error(f"Fallo de enlace de comunicaciones: {api_e}")
