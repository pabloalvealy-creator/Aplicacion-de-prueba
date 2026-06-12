import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import folium
from streamlit_folium import st_folium
import pytz
import requests
import base64
from io import StringIO

# Configuración de la zona horaria de Chile
zona_cl = pytz.timezone('America/Santiago')

# Configuración de la página para celulares
st.set_page_config(
    page_title="Control de Rutas y Lecturas AT", 
    page_icon="⚡", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilos CSS para botones grandes y mapa adaptado a pantallas táctiles
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 3.8em;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 12px;
    }
    div[data-testid="stCameraInput"] button {
        width: 100% !important;
        background-color: #262730 !important;
        color: white !important;
    }
    .big-text {
        font-size: 20px;
        font-weight: bold;
        color: #003366;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Control de Procesos y HH - AT")
st.write("Seguimiento correlativo de traslados, tiempos y geolocalización en terreno.")

# ------------------------------------------------------------------
# CONFIGURACIÓN AUTOMÁTICA DE GITHUB (Asegurar persistencia)
# ------------------------------------------------------------------
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]
except Exception:
    st.error("❌ Faltan las credenciales 'GITHUB_TOKEN' y 'GITHUB_REPO' en los Secrets de Streamlit.")
    st.stop()

ARCHIVO_DATOS = "registro_piloto_at.csv"
URL_API = f"https://api.github.com/repos/{REPO}/contents/{ARCHIVO_DATOS}"

def guardar_registro_en_github(nuevo_registro_dict):
    """Descarga el CSV actual de GitHub, le agrega la nueva fila y lo sube automáticamente con alertas de error"""
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    respuesta = requests.get(URL_API, headers=headers)
    sha = None
    
    if respuesta.status_code == 200:
        datos_archivo = respuesta.json()
        sha = datos_archivo["sha"]
        contenido_b64 = datos_archivo["content"]
        contenido_decodificado = base64.b64decode(contenido_b64).decode('utf-8-sig')
        df_actual = pd.read_csv(StringIO(contenido_decodificado))
        df_nuevo = pd.DataFrame(nuevo_registro_dict)
        df_consolidado = pd.concat([df_actual, df_nuevo], ignore_index=True)
    elif respuesta.status_code == 404:
        # El archivo no existe aún en GitHub, se crea el primero
        df_consolidado = pd.DataFrame(nuevo_registro_dict)
    else:
        st.error(f"⚠️ Error de conexión inicial con GitHub. Código: {respuesta.status_code}. Detalle: {respuesta.text}")
        return False
        
    csv_datos = df_consolidado.to_csv(index=False, encoding='utf-8-sig')
    csv_b64 = base64.b64encode(csv_datos.encode('utf-8-sig')).decode('utf-8')
    
    datos_subida = {
        "message": f"🤖 Registro automático: Punto por {nuevo_registro_dict['Gestor'][0]}",
        "content": csv_b64
    }
    if sha:
        datos_subida["sha"] = sha
        
    subida = requests.put(URL_API, headers=headers, json=datos_subida)
    
    if subida.status_code in [200, 201]:
        return True
    else:
        st.error(f"❌ GitHub rechazó el guardado. Código: {subida.status_code}. Mensaje: {subida.json().get('message', subida.text)}")
        return False

def cargar_historial_desde_github():
    """Lee el archivo acumulado directamente desde GitHub de forma actualizada"""
    headers = {"Authorization": f"token {TOKEN}"}
    respuesta = requests.get(URL_API, headers=headers)
    if respuesta.status_code == 200:
        contenido_b64 = respuesta.json()["content"]
        contenido_decodificado = base64.b64decode(contenido_b64).decode('utf-8-sig')
        return pd.read_csv(StringIO(contenido_decodificado))
    return None

# ------------------------------------------------------------------
# VARIABLES DE CONTROL DE ESTADO (Session State)
# ------------------------------------------------------------------
if "n_punto" not in st.session_state:
    st.session_state.n_punto = 1
if "estado_brigada" not in st.session_state:
    st.session_state.estado_brigada = "INICIO_DIA"
if "last_clicked" not in st.session_state:
    st.session_state.last_clicked = {"lat": -34.0601, "lng": -70.7891} 

if "timestamps" not in st.session_state:
    st.session_state.timestamps = {
        "inicio_traslado": None,
