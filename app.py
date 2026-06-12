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

# Configuración de zona horaria y página
zona_cl = pytz.timezone('America/Santiago')
st.set_page_config(
    page_title="Control de Rutas y Lecturas AT", 
    page_icon="⚡", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilos CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.8em; font-size: 18px !important; font-weight: bold; border-radius: 12px; }
    .big-text { font-size: 20px; font-weight: bold; color: #003366; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Control de Procesos y HH - AT")

# Configuración GitHub
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]
except:
    st.error("❌ Faltan GITHUB_TOKEN y GITHUB_REPO en los Secrets.")
    st.stop()

ARCHIVO_DATOS = "registro_piloto_at.csv"
URL_API = f"https://api.github.com/repos/{REPO}/contents/{ARCHIVO_DATOS}"

def guardar_registro_en_github(nuevo_registro_dict):
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    respuesta = requests.get(URL_API, headers=headers)
    sha = None
    
    if respuesta.status_code == 200:
        datos_archivo = respuesta.json()
        sha = datos_archivo["sha"]
        contenido_decodificado = base64.b64decode(datos_archivo["content"]).decode('utf-8-sig')
        df_actual = pd.read_csv(StringIO(contenido_decodificado))
        df_consolidado = pd.concat([df_actual, pd.DataFrame(nuevo_registro_dict)], ignore_index=True)
    else:
        df_consolidado = pd.DataFrame(nuevo_registro_dict)
        
    csv_b64 = base64.b64encode(df_consolidado.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')).decode('utf-8')
    payload = {"message": "Registro automático", "content": csv_b64}
    if sha: payload["sha"] = sha
    
    subida = requests.put(URL_API, headers=headers, json=payload)
    return subida.status_code in [200, 201]

def cargar_historial():
    headers = {"Authorization": f"token {TOKEN}"}
    respuesta = requests.get(URL_API, headers=headers)
    if respuesta.status_code == 200:
        contenido = base64.b64decode(respuesta.json()["content"]).decode('utf-8-sig')
        return pd.read_csv(StringIO(contenido))
    return None

# --- ESTADO ---
if "estado_brigada" not in st.session_state: st.session_state.estado_brigada = "INICIO_DIA"
if "n_punto" not in st.session_state: st.session_state.n_punto = 1

lector = st.selectbox("Seleccione Gestor", ["", "Pablo Alveal", "Matias Perez"])

if lector:
    if st.session_state.estado_brigada == "INICIO_DIA":
        if st.button("🚀 Iniciar Traslado"):
            st.session_state.estado_brigada = "TRASLADO"
            st.rerun()
    elif st.session_state.estado_brigada == "TRASLADO":
        if st.button("🏁 Llegada al Punto"):
            st.session_state.estado_brigada = "EN_PUNTO"
            st.rerun()
    elif st.session_state.estado_brigada == "EN_PUNTO":
        n_medidor = st.text_input("N° Medidor")
        if st.button("💾 Guardar"):
            registro = {
                "Gestor": [lector],
                "Punto": [st.session_state.n_punto],
                "Medidor": [n_medidor],
                "Hora": [datetime.now(zona_cl).strftime("%H:%M:%S")]
            }
            if guardar_registro_en_github(registro):
                st.success("Guardado exitosamente")
                st.session_state.estado_brigada = "INICIO_DIA"
                st.session_state.n_punto += 1
                st.rerun()

st.markdown("---")
historial = cargar_historial()
if historial is not None: st.dataframe(historial)
