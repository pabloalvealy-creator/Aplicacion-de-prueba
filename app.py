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

# Configuración
zona_cl = pytz.timezone('America/Santiago')
st.set_page_config(page_title="Control de Rutas", layout="centered", initial_sidebar_state="collapsed")

# --- LÓGICA DE GITHUB ---
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]
    ARCHIVO_DATOS = "registro_piloto_at.csv"
    URL_API = f"https://api.github.com/repos/{REPO}/contents/{ARCHIVO_DATOS}"
except:
    st.error("Configura GITHUB_TOKEN y GITHUB_REPO en los Secrets")
    st.stop()

def guardar_en_github(nuevo_registro_dict):
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(URL_API, headers=headers)
    sha = res.json()["sha"] if res.status_code == 200 else None
    
    if res.status_code == 200:
        contenido = base64.b64decode(res.json()["content"]).decode('utf-8-sig')
        df_actual = pd.read_csv(StringIO(contenido))
        df_nuevo = pd.DataFrame(nuevo_registro_dict)
        df_consolidado = pd.concat([df_actual, df_nuevo], ignore_index=True)
    else:
        df_consolidado = pd.DataFrame(nuevo_registro_dict)
        
    csv_b64 = base64.b64encode(df_consolidado.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')).decode('utf-8')
    payload = {"message": "Guardado automático", "content": csv_b64}
    if sha: payload["sha"] = sha
    requests.put(URL_API, headers=headers, json=payload)

# --- ESTADO DE LA APP ---
if "n_punto" not in st.session_state: st.session_state.n_punto = 1
if "estado" not in st.session_state: st.session_state.estado = "INICIO"

st.title("⚡ Control de Procesos")
lector = st.selectbox("Gestor", ["", "Pablo Alveal", "Matias Perez"])

if lector:
    if st.session_state.estado == "INICIO":
        if st.button("Iniciar Traslado"):
            st.session_state.estado = "TRASLADO"
            st.rerun()
            
    elif st.session_state.estado == "TRASLADO":
        if st.button("Llegada al Punto"):
            st.session_state.estado = "EN_PUNTO"
            st.rerun()

    elif st.session_state.estado == "EN_PUNTO":
        n_medidor = st.text_input("N° Medidor")
        if st.button("Guardar Registro"):
            registro = {
                "Gestor": [lector],
                "Punto": [st.session_state.n_punto],
                "Medidor": [n_medidor],
                "Hora": [datetime.now(zona_cl).strftime("%H:%M:%S")]
            }
            guardar_en_github(registro)
            st.success("Guardado correctamente")
            st.session_state.n_punto += 1
            st.session_state.estado = "INICIO"
            st.rerun()
