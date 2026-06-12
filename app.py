import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import base64
from io import StringIO

# Configuración de página
st.set_page_config(page_title="Control de Lecturas AT", page_icon="⚡", layout="centered")

# --- LÓGICA DE PERSISTENCIA EN GITHUB ---
# Asegúrate de tener los SECRETS configurados en Streamlit Cloud
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO = st.secrets["GITHUB_REPO"]
    ARCHIVO = "registro_piloto_at.csv"
    URL_API = f"https://api.github.com/repos/{REPO}/contents/{ARCHIVO}"
except:
    st.error("Configura GITHUB_TOKEN y GITHUB_REPO en los Secrets de Streamlit.")
    st.stop()

def guardar_en_github(registro_dict):
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # 1. Intentar obtener el archivo existente
    res = requests.get(URL_API, headers=headers)
    sha = res.json()["sha"] if res.status_code == 200 else None
    
    # 2. Consolidar datos
    df_nuevo = pd.DataFrame(registro_dict)
    if res.status_code == 200:
        contenido = base64.b64decode(res.json()["content"]).decode('utf-8-sig')
        df_existente = pd.read_csv(StringIO(contenido))
        df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
    else:
        df_final = df_nuevo
        
    # 3. Subir a GitHub
    csv_b64 = base64.b64encode(df_final.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')).decode('utf-8')
    payload = {"message": "Registro desde app", "content": csv_b64}
    if sha: payload["sha"] = sha
    requests.put(URL_API, headers=headers, json=payload)

# --- INTERFAZ ---
st.title("⚡ Registro Piloto - Lectura AT")
lector = st.selectbox("Gestor", ["", "Pablo Alveal", "Matias Perez"])

if lector:
    if "hora_inicio" not in st.session_state: st.session_state.hora_inicio = None
    
    if st.session_state.hora_inicio is None:
        if st.button("🟢 Iniciar Visita"):
            st.session_state.hora_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()
    else:
        st.success(f"Visita iniciada: {st.session_state.hora_inicio}")
        n_medidor = st.text_input("N° Medidor")
        
        if st.button("🔴 Finalizar y Guardar"):
            if n_medidor:
                registro = {
                    "Gestor": [lector],
                    "Medidor": [n_medidor],
                    "Inicio": [st.session_state.hora_inicio],
                    "Fin": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                }
                guardar_en_github(registro)
                st.session_state.hora_inicio = None
                st.success("¡Guardado permanentemente en GitHub!")
                st.balloons()
            else:
                st.error("Ingresa el número de medidor.")
