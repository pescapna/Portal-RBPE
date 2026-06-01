import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import json
import uuid

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM MÁSTER ---
st.set_page_config(page_title="Charly v2 - Centro de Gestión", page_icon="⚓", layout="wide")

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
        margin-bottom: 1.5rem;
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

# --- 4. ARSENAL DE PROCESAMIENTO SEGURO (BACKEND) ---

def ejecutar_sql(query: str) -> str:
    """Ejecuta una consulta SQL SELECT en la base de datos y devuelve formato JSON."""
    try:
        clean_query = query.strip()
        if not clean_query.lower().startswith("select"):
            return json.dumps({"status": "error", "mensaje": "Solo se permiten consultas SELECT de lectura por seguridad."})
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

def registrar_buque_transaccion(maestro_dict: dict, identidad_dict: dict) -> bool:
    """Inserta de forma ordenada en buques_maestro y luego en buques_identidad para evitar fallos de integridad."""
    try:
        # 1. Insertar características físicas en la tabla maestra
        res_m = supabase.table("buques_maestro").insert(maestro_dict).execute()
        if not res_m.data:
            return False
        # 2. Insertar datos de identidad con el mismo id_buque vinculado
        res_i = supabase.table("buques_identidad").insert(identidad_dict).execute()
        return True if res_i.data else False
    except:
        return False

def registrar_tabla_directa(tabla: str, datos_dict: dict) -> bool:
    """Realiza inserciones genéricas seguras en operaciones o navegaciones_zeea."""
    try:
        res = supabase.table(tabla).insert(datos_dict).execute()
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

# --- 5. CONFIGURACIÓN DEL AGENTE DE INTELIGENCIA CHAT ---
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite', 
    tools=herramientas_react,
    system_instruction=f"Eres Charly v2, un analista de datos experto bajo framework ReAct para el Operador {operador}. Responde consultas analíticas de forma concisa y ejecutiva. No uses modismos militares ni la palabra 'táctica'."
)

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=True)
if "mensajes_ui" not in st.session_state:
    st.session_state.mensajes_ui = [{"role": "assistant", "content": f"⚓ **Sistemas de Análisis Online.** Operador **{operador}**, bases de datos vinculadas por HTTPS. Dispuesto para consultas relacionales o auditorías."}]

# --- 6. DISEÑO DE INTERFAZ MULTI-PESTAÑA (TABS) ---
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Centro de Control General <span style='color: #3B82F6;'>Charly v2</span></h1>", unsafe_allow_html=True)

tab_analisis, tab_buque, tab_operacion, tab_zeea = st.tabs([
    "📊 Centro de Análisis (Chat)", 
    "🚢 Cargar Buque Completo", 
    "📝 Registrar Operación", 
    "🛰️ Navegación ZEEA"
])

# Carga de catálogos en tiempo real para poblar los formularios relacionales de forma limpia
try:
    banderas_res = supabase.table("cat_banderas").select("id_bandera, nombre").execute()
    dict_banderas = {b['nombre']: b['id_bandera'] for b in banderas_res.data} if banderas_res.data else {}
    
    empresas_res = supabase.table("cat_empresas").select("id_empresa, nombre").execute()
    dict_empresas = {e['nombre'] if e['nombre'] else f"ID: {e['id_empresa']}": e['id_empresa'] for e in empresas_res.data} if empresas_res.data else {}
    
    pesca_res = supabase.table("cat_tipos_pesca").select("id_tipo, nombre").execute()
    dict_pesca = {p['nombre']: p['id_tipo'] for p in pesca_res.data} if pesca_res.data else {}
    
    buques_res = supabase.table("buques_identidad").select("id_buque, nombre").eq("es_actual", True).execute()
    dict_buques = {b['nombre']: b['id_buque'] for b in buques_res.data} if buques_res.data else {}
except Exception as e:
    st.error(f"Fallo de sincronización con catálogos centrales: {e}")
    dict_banderas, dict_empresas, dict_pesca, dict_buques = {}, {}, {}, {}

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
                if v["tipo"] == "tabla": st.dataframe(df_visual, use_container_width=True)
                elif v["tipo"] == "grafico_barras":
                    fig = px.bar(df_visual, x=v["x"], y=v["y"], title=v["titulo"], template="plotly_dark")
                    fig.update_traces(marker_color='#3B82F6')
                    st.plotly_chart(fig, use_container_width=True)
                elif v["tipo"] == "grafico_torta":
                    fig = px.pie(df_visual, names=v["x"], values=v["y"], title=v["titulo"], template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)

    if prompt := st.chat_input("Consulte duplicados, auditorías o cruces generales de tablas..."):
        st.session_state["necesita_rerun"] = False
        st.session_state.mensajes_ui.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Procesando consulta analítica..."):
                try:
                    respuesta = st.session_state.chat.send_message(prompt)
                    st.markdown(respuesta.text)
                    st.session_state.mensajes_ui.append({"role": "assistant", "content": respuesta.text})
                    if st.session_state.get("necesita_rerun", False):
                        st.session_state["necesita_rerun"] = False
                        st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# =====================================================================
# PESTAÑA 2: CARGAR BUQUE COMPLETO (MAESTRO + IDENTIDAD)
# =====================================================================
with tab_buque:
    st.markdown("### 🚢 Alta de Unidades e Infraestructura Física")
    st.write("Este módulo ingresa de forma simultánea los datos de ingeniería estructural y la identidad comercial de la embarcación.")
    
    with st.form("form_alta_buque_completo"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Identidad y Clasificación**")
            b_nombre = st.text_input("Nombre de la Embarcación *", placeholder="Ej: XINRUN 579").strip()
            b_mmsi = st.text_input("Número MMSI *", placeholder="Ej: 224142000").strip()
            b_bandera = st.selectbox("Pabellón / Nacionalidad", list(dict_banderas.keys()))
            b_empresa = st.selectbox("Empresa Propietaria", list(dict_empresas.keys()))
            b_tipo = st.selectbox("Artes de Pesca autorizadas", list(dict_pesca.keys()))
            b_riesgo = st.selectbox("Asignación de Riesgo", ["Bajo", "Medio", "Alto"])
            b_llamada = st.text_input("Indicativo de Llamada", placeholder="Ej: LI2345").strip()
        with c2:
            st.markdown("**Características de Ingeniería (Datos Maestro)**")
            b_imo = st.text_input("Número IMO *", placeholder="Ej: 9842293").strip()
            b_eslora = st.number_input("Eslora Total (Metros)", min_value=0.0, step=0.1, format="%.1f")
            b_arqueo = st.number_input("Arqueo Bruto (TRG)", min_value=0.0, step=1.0)
            b_construccion = st.text_input("Fecha de Construcción", placeholder="Ej: 2018-12-01").strip()
            
        btn_auditar_b = st.form_submit_button("🛡️ AUDITAR REGISTRO Y PREVISUALIZAR ESTRUCTURA")

    if btn_auditar_b:
        if not b_nombre or not b_mmsi or not b_imo:
            st.error("Error de entrada: Nombre, MMSI e IMO son campos obligatorios.")
        elif len(b_mmsi) != 9 or not b_mmsi.isdigit():
            st.error("Anomalía de formato: El código MMSI debe poseer exactamente 9 dígitos numéricos.")
        else:
            with st.spinner("Buscando colisiones de identidad en el servidor..."):
                dup_nombre = supabase.table("buques_identidad").select("nombre").ilike("nombre", b_nombre).execute()
                dup_mmsi = supabase.table("buques_identidad").select("mmsi").eq("mmsi", b_mmsi).execute()
                dup_imo = supabase.table("buques_maestro").select("imo").eq("imo", b_imo).execute()
                
                anomalias = []
                if dup_nombre.data: anomalias.append(f"El nombre '{b_nombre.upper()}' ya consta asignado a un buque.")
                if dup_mmsi.data: anomalias.append(f"El número MMSI '{b_mmsi}' ya está ocupado.")
                if dup_imo.data: anomalias.append(f"El número IMO '{b_imo}' ya existe en el registro maestro.")
                
                if anomalias:
                    st.warning("### ⚠️ Anomalías Críticas Detectadas")
                    for a in anomalias: st.write(f"- {a}")
                    st.session_state["preview_buque"] = None
                else:
                    st.success("###  Consistencia de Datos Homologada")
                    id_buque_nuevo = f"BQ-{b_nombre[:3].upper()}-{uuid.uuid4().hex[:5].upper()}"
                    
                    st.session_state["preview_buque"] = {
                        "maestro": {
                            "id_buque": id_buque_nuevo, "imo": b_imo, "eslora": b_eslora if b_eslora > 0 else None,
                            "arqueo_bruto": b_arqueo if b_arqueo > 0 else None, "fecha_construccion": b_construccion if b_construccion else None
                        },
                        "identidad": {
                            "id_buque": id_buque_nuevo, "nombre": b_nombre.upper(), "mmsi": b_mmsi,
                            "id_bandera": dict_banderas[b_bandera], "id_empresa": dict_empresas[b_empresa],
                            "id_tipo": dict_pesca[b_tipo], "indicativo_llamada": b_llamada if b_llamada else None,
                            "riesgo": b_riesgo, "es_actual": True
                        }
                    }

    if st.session_state.get("preview_buque") is not None:
        st.markdown("---")
        st.markdown("### 📋 Estructura de Inserción Atómica (JSON)")
        st.json(st.session_state["preview_buque"])
        if st.button("CONFIRMAR E INSERTAR BUQUE COMPLETO", use_container_width=True):
            exito = registrar_buque_transaccion(st.session_state["preview_buque"]["maestro"], st.session_state["preview_buque"]["identidad"])
            if exito:
                st.success(f"Registro Consolidado: El buque '{st.session_state['preview_buque']['identidad']['nombre']}' fue dado de alta con sus características de ingeniería.")
                st.session_state["preview_buque"] = None
                st.rerun()
            else: st.error("Fallo de escritura en el servidor remoto.")

# =====================================================================
# PESTAÑA 3: REGISTRAR OPERACIÓN PORTUARIA / EVENTO
# =====================================================================
with tab_operacion:
    st.markdown("### 📝 Registro de Eventos y Operaciones Portuarias")
    if not dict_buques: st.info("No hay buques disponibles en el sistema.")
    else:
        with st.form("form_alta_operacion"):
            op_buque_name = st.selectbox("Seleccione el Buque Asociado *", list(dict_buques.keys()))
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                op_puerto = st.text_input("Puerto de Origen / Operación *", placeholder="Ej: Montevideo").strip()
                op_zarpe = st.text_input("Fecha de Zarpada (AAAA-MM-DD) *", placeholder="Ej: 2026-03-15").strip()
                op_procedencia = st.text_input("Área Procedente", placeholder="Ej: Alta Mar").strip()
                op_temporada = st.text_input("Temporada Operativa", placeholder="Ej: 2026").strip()
            with col_o2:
                op_ingreso_area = st.text_input("Fecha de Ingreso al Área", placeholder="Ej: 2026-03-20").strip()
                op_area_ing = st.text_input("Área de Ingreso", placeholder="Ej: Zona Común").strip()
                op_puerto_amarre = st.text_input("Puerto de Amarre Final", placeholder="Ej: Puerto Madryn").strip()
                op_fecha_amarre = st.text_input("Fecha de Amarre Final", placeholder="Ej: 2026-04-10").strip()
                
            btn_auditar_o = st.form_submit_button("🛡️ AUDITAR Y PREVISUALIZAR OPERACIÓN")

        if btn_auditar_o:
            if not op_puerto or not op_zarpe:
                st.error("Error de entrada: El puerto de origen y la fecha de zarpada son requeridos.")
            else:
                id_op_generado = f"OP-{uuid.uuid4().hex[:8].upper()}"
                st.session_state["preview_op"] = {
                    "id_operacion": id_op_generado,
                    "id_buque": dict_buques[op_buque_name],
                    "puerto_origen": op_puerto, "fecha_zarpada": op_zarpe,
                    "area_procedente": op_procedencia if op_procedencia else None,
                    "temporada": op_temporada if op_temporada else None,
                    "fecha_ingreso_area": op_ingreso_area if op_ingreso_area else None,
                    "area_income": op_area_ing if op_area_ing else None,
                    "puerto_amarre": op_puerto_amarre if op_puerto_amarre else None,
                    "fecha_amarre": op_fecha_amarre if op_fecha_amarre else None
                }

        if st.session_state.get("preview_op") is not None:
            st.markdown("---")
            st.json(st.session_state["preview_op"])
            if st.button("CONFIRMAR E INSERTAR OPERACIÓN", use_container_width=True):
                if registrar_tabla_directa("operaciones", st.session_state["preview_op"]):
                    st.success("Bitácora Actualizada: El evento operacional fue registrado permanentemente.")
                    st.session_state["preview_op"] = None
                    st.rerun()
                else: st.error("Error al consolidar la operación en el servidor.")

# =====================================================================
# PESTAÑA 4: REGISTRAR NAVEGACIÓN ZEEA (INCURSIONES)
# =====================================================================
with tab_zeea:
    st.markdown("### 🛰️ Registro de Navegaciones e Incursiones en ZEEA")
    if not dict_buques: st.info("No hay buques disponibles en el sistema.")
    else:
        with st.form("form_alta_zeea"):
            z_buque_name = st.selectbox("Seleccione la Unidad *", list(dict_buques.keys()))
            col_z1, col_z2 = st.columns(2)
            with col_z1:
                z_ingreso = st.text_input("Fecha Ingreso ZEEA *", placeholder="Ej: 2026-05-01 14:30:00").strip()
                z_procedencia = st.text_input("Procedencia Inmediata", placeholder="Ej: Milla 201").strip()
            with col_z2:
                z_egreso = st.text_input("Fecha Egreso ZEEA", placeholder="Ej: 2026-05-05 08:15:00").strip()
                z_destino = st.text_input("Destino Posterior", placeholder="Ej: Montevideo").strip()
                
            btn_auditar_z = st.form_submit_button("🛡️ AUDITAR Y PREVISUALIZAR NAVEGACIÓN")

        if btn_auditar_z:
            if not z_ingreso:
                st.error("Error de entrada: La fecha de ingreso a la ZEEA es obligatoria.")
            else:
                id_z_generado = f"REG-{uuid.uuid4().hex[:8].upper()}"
                st.session_state["preview_zeea"] = {
                    "id_registro": id_z_generado,
                    "id_buque": dict_buques[z_buque_name],
                    "fecha_ingreso_zeea": z_ingreso,
                    "procedencia": z_procedencia if z_procedencia else None,
                    "fecha_egreso_zeea": z_egreso if z_egreso else None,
                    "destino": z_destino if z_destino else None
                }

        if st.session_state.get("preview_zeea") is not None:
            st.markdown("---")
            st.json(st.session_state["preview_zeea"])
            if st.button("CONFIRMAR E INSERTAR REGISTRO ZEEA", use_container_width=True):
                if registrar_tabla_directa("navegaciones_zeea", st.session_state["preview_zeea"]):
                    st.success("Registro Satelital Asentado: La navegación en ZEEA fue guardada de forma definitiva.")
                    st.session_state["preview_zeea"] = None
                    st.rerun()
                else: st.error("Error al consolidar el registro ZEEA en el servidor.")
