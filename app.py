import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import requests
import base64
from io import StringIO
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN ---
zona_cl = pytz.timezone('America/Santiago')
st.set_page_config(page_title="Control de Rutas", layout="centered")

# --- CONEXIÓN GITHUB ---
# Asegúrate de tener GITHUB_TOKEN y GITHUB_REPO en los Secrets de Streamlit
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
ARCHIVO = "registro_piloto_at.csv"
URL_API = f"https://api.github.com/repos/{REPO}/contents/{ARCHIVO}"

def guardar_en_github(nuevo_registro_dict):
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # Obtener archivo actual para no sobrescribir
    res = requests.get(URL_API, headers=headers)
    sha = res.json()["sha"] if res.status_code == 200 else None
    
    if res.status_code == 200:
        contenido = base64.b64decode(res.json()["content"]).decode('utf-8-sig')
        df_actual = pd.read_csv(StringIO(contenido))
        df_final = pd.concat([df_actual, pd.DataFrame(nuevo_registro_dict)], ignore_index=True)
    else:
        df_final = pd.DataFrame(nuevo_registro_dict)
    
    # Codificar y subir
    csv_b64 = base64.b64encode(df_final.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')).decode('utf-8')
    payload = {"message": "Guardado automático de punto", "content": csv_b64}
    if sha: payload["sha"] = sha
    
    requests.put(URL_API, headers=headers, json=payload)

# --- ESTADO Y LÓGICA ---
if "estado" not in st.session_state: st.session_state.estado = "INICIO"
if "n_punto" not in st.session_state: st.session_state.n_punto = 1

st.title("⚡ Control de Procesos")
lector = st.selectbox("Gestor", ["", "Pablo Alveal", "Matias Perez"])

if lector:
    # 1. Inicio
    if st.session_state.estado == "INICIO":
        if st.button("🚀 Iniciar Traslado"):
            st.session_state.estado = "TRASLADO"
            st.rerun()
            
    # 2. Traslado
    elif st.session_state.estado == "TRASLADO":
        if st.button("🏁 Llegada al Punto"):
            st.session_state.estado = "EN_PUNTO"
            st.rerun()

    # 3. En punto (con mapa)
    elif st.session_state.estado == "EN_PUNTO":
        st.subheader(f"📍 Punto {st.session_state.n_punto}")
        m = folium.Map(location=[-34.06, -70.78], zoom_start=15)
        st_folium(m, height=300)
        
        n_medidor = st.text_input("N° Medidor")
        if st.button("💾 Guardar Registro"):
            registro = {
                "Gestor": [lector],
                "Punto": [st.session_state.n_punto],
                "Medidor": [n_medidor],
                "Hora": [datetime.now(zona_cl).strftime("%H:%M:%S")]
            }
            guardar_en_github(registro)
            st.success("✅ Datos guardados correctamente en GitHub")
            st.session_state.n_punto += 1
            st.session_state.estado = "INICIO"
            st.rerun()
