import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
import re
from supabase import create_client, Client
import traceback
import sys

# --- CONFIGURACIÓN Y ESTÉTICA PREMIUM ---
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
    
    .tactical-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(59, 130, 246, 0.3); border-left: 6px solid #3B82F6;
        border-radius: 12px; padding: 24px; margin: 20px 0;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(12px);
    }
    
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 15px; margin-top: 20px; }
    .kpi-box { background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.05); padding: 12px; border-radius: 8px; text-align: center; }
    .kpi-label { font-size: 0.65rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
    .kpi-value { font-size: 1.1rem; color: #F8FAFC; font-family: 'JetBrains Mono', monospace; font-weight: 600; margin-top: 4px; display: block; }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
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
            else: st.error("Acceso denegado.")
    st.stop()

# --- CONEXIÓN DE INFRAESTRUCTURA ---
@st.cache_resource
def init_core():
    supa = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["service_role_key"])
    genai.configure(api_key=st.secrets["api"]["gemini_key"])
    mod = genai.GenerativeModel('gemini-3.1-flash-lite')
    return supa, mod

supabase, model = init_core()

# --- CARGA MAESTRA DE DATOS ---
@st.cache_data(ttl=600, show_spinner=False)
def load_fleet_data():
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
    df_ops = pd.DataFrame(supabase.table("operaciones").select("*").execute().data)
    df_zeea = pd.DataFrame(supabase.table("navegaciones_zeea").select("*").execute().data)
    return df_id, df_ops, df_zeea

with st.spinner("Sincronizando con satélites y base de datos central..."):
    df_id, df_ops, df_zeea = load_fleet_data()

# --- MOTOR CON AUTO-CORRECCIÓN (AGENTIC LOOP) ---
def ejecutar_con_autocorreccion(instrucciones_base, peticion_usuario, max_intentos=3):
    historial = [
        {"role": "user", "parts": [instrucciones_base + "\nOrden del usuario: " + peticion_usuario]}
    ]
    
    for intento in range(max_intentos):
        try:
            # Pedimos a la IA que genere la respuesta/código
            respuesta = model.generate_content(historial)
            texto_respuesta = respuesta.text
            
            # Buscamos si hay código para ejecutar
            bloques_codigo = re.findall(r"```python\s*(.*?)\s*
```", texto_respuesta, flags=re.DOTALL)
            
            if bloques_codigo:
                # Ejecutamos el primer bloque de código que encontremos
                codigo = bloques_codigo[0]
                entorno_local = {"df_id": df_id, "df_ops": df_ops, "df_zeea": df_zeea, "px": px, "pd": pd, "st": st}
                
                try:
                    exec(codigo, {}, entorno_local)
                    # Si llega acá, el código corrió perfecto. Mostramos la parte de texto (si la hay) y salimos del loop.
                    texto_limpio = re.sub(r"```python.*?```", "", texto_respuesta, flags=re.DOTALL).strip()
                    if texto_limpio:
                        st.markdown(texto_limpio)
                    return texto_respuesta # Éxito
                
                except Exception as e:
                    # ¡FALLO EL CÓDIGO! (Ej. olvidó un paréntesis)
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    # Se lo devolvemos a la IA de forma invisible para que lo arregle
                    historial.append({"role": "model", "parts": [texto_respuesta]})
                    historial.append({"role": "user", "parts": [f"El código generó este error en Python: {error_msg}. Por favor, corrige el error de sintaxis o lógica y vuelve a generar el código completo en un bloque ```python 
```."]})
            else:
                # No hay código, es solo una respuesta de texto
                st.markdown(texto_respuesta)
                return texto_respuesta
                
        except Exception as api_e:
            st.error(f"Error de comunicación con la IA: {api_e}")
            break
            
    # Si superó los 3 intentos y no lo pudo arreglar
    st.error("Charly intentó resolver el problema 3 veces pero no pudo corregir la consulta. Verifique la estructura de los datos.")
    return "Fallo en la ejecución tras múltiples intentos."

# --- INTERFAZ DEL COMANDO ---
operador = st.session_state["user"]
st.markdown(f"<h1 style='color: #F8FAFC; font-weight: 800; font-size: 2.2rem;'>⚓ Analista Naval <span style='color: #3B82F6;'>Charly</span></h1>", unsafe_allow_html=True)

if "chat_log" not in st.session_state:
    st.session_state.chat_log = [{"role": "assistant", "content": f"Saludos, Operador **{operador}**. Motor con auto-corrección habilitado. Cero tolerancia a errores de sintaxis. Proceda."}]

# Mostrar el historial visual (sin ejecutar de nuevo)
for msg in st.session_state.chat_log:
    with st.chat_message(msg["role"]):
        texto = re.sub(r"```python.*?```", "", msg["content"], flags=re.DOTALL).strip()
        if texto:
            st.markdown(texto)

if prompt := st.chat_input("Introduzca su comando..."):
    with st.chat_message("user"): st.markdown(prompt)
    st.session_state.chat_log.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        instrucciones_maestras = f"""
        Eres Charly, analista naval autónomo de {operador}.
        
        DATASETS EN MEMORIA:
        - df_id: {df_id.columns.tolist()}
        - df_ops: {df_ops.columns.tolist()}
        
        REGLAS ESTRICTAS PARA ESCRIBIR CÓDIGO PYTHON:
        1. Tu código se ejecuta directamente. Si cometes un error de sintaxis (como olvidar un paréntesis), el sistema fallará. REVISA BIEN TU SINTAXIS.
        2. Usa SIEMPRE `st.write()`, `st.dataframe()`, o `st.plotly_chart()` para mostrar la información al usuario.
        3. Para buscar "cuántos", hazlo así:
```python
           cantidad = df_id[df_id['Bandera'].str.contains('Kenia', case=False, na=False)].shape[0]
           st.write(f"Tenemos **{{cantidad}}** buques registrados de esa bandera.")
           ```
        4. No respondas "Procedo a buscar...", simplemente escribe el bloque de código y el resultado se mostrará.
        """
        
        with st.spinner("Analizando y validando código en simulador..."):
            # Aquí ocurre la magia: si se equivoca, lo arregla antes de responderte
            respuesta_final = ejecutar_con_autocorreccion(instrucciones_maestras, prompt)
            st.session_state.chat_log.append({"role": "assistant", "content": respuesta_final})
