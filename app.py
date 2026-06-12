import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import folium
from streamlit_folium import st_folium
import pytz  # <--- Librería para controlar zonas horarias

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
        "llegada_punto": None,
        "fin_punto": None
    }

# 1. Identificación del Lector/Brigada
lector = st.selectbox("Seleccione el Gestor/Lector *", ["", "Pablo Alveal", "Matias Perez"])

if lector != "":
    st.markdown("---")
    st.markdown(f"<div class='big-text'>📍 OPERACIÓN ACTUAL: PUNTO {st.session_state.n_punto}</div>", unsafe_allow_html=True)
    
    # ------------------------------------------------------------------
    # ESTADO 0: INICIO DEL DÍA / ESPERANDO PRIMER TRASLADO
    # ------------------------------------------------------------------
    if st.session_state.estado_brigada == "INICIO_DIA":
        st.info("🚚 La brigada está ready. Presiona cuando el móvil comience a moverse hacia el primer punto.")
        if st.button("🚀 Iniciar Traslado hacia Punto " + str(st.session_state.n_punto)):
            # Captura hora local de Chile
            st.session_state.timestamps["inicio_traslado"] = datetime.now(zona_cl)
            st.session_state.estado_brigada = "TRASLADO"
            st.rerun()

    # ------------------------------------------------------------------
    # ESTADO 1: EN TRASLADO (Móvil en movimiento)
    # ------------------------------------------------------------------
    elif st.session_state.estado_brigada == "TRASLADO":
        hora_salida = st.session_state.timestamps["inicio_traslado"].strftime("%H:%M:%S")
        st.warning(f"🚚 El móvil va en camino hacia el **Punto {st.session_state.n_punto}** (Salió a las {hora_salida})")
        
        if st.button("🏁 Llegada al Punto (Marcar Hora de Arribo)"):
            # Captura hora local de Chile
            st.session_state.timestamps["llegada_punto"] = datetime.now(zona_cl)
            st.session_state.estado_brigada = "EN_PUNTO"
            st.rerun()

    # ------------------------------------------------------------------
    # ESTADO 2: EN PUNTO (Inspección, Mapa y Toma de Foto)
    # ------------------------------------------------------------------
    elif st.session_state.estado_brigada == "EN_PUNTO":
        hora_llegada = st.session_state.timestamps["llegada_punto"].strftime("%H:%M:%S")
        st.success(f"⏱️ Brigada trabajando en el **Punto {st.session_state.n_punto}** desde las {hora_llegada}")
        
        st.markdown("### 🗺️ ¿Dónde estás exactamente?")
        st.caption("Toca el mapa en el lugar exacto del medidor para clavar el pin de geolocalización.")
        
        m = folium.Map(
            location=[st.session_state.last_clicked["lat"], st.session_state.last_clicked["lng"]], 
            zoom_start=15
        )
        
        folium.Marker(
            [st.session_state.last_clicked["lat"], st.session_state.last_clicked["lng"]],
            popup="Ubicación Medidor",
            icon=folium.Icon(color="red", icon="bolt", prefix="fa")
        ).add_to(m)
        
        map_data = st_folium(m, width=700, height=300, key="mapa_interactivo")
        
        if map_data and map_data.get("last_clicked"):
            click_lat = map_data["last_clicked"]["lat"]
            click_lng = map_data["last_clicked"]["lng"]
            if (click_lat != st.session_state.last_clicked["lat"] or click_lng != st.session_state.last_clicked["lng"]):
                st.session_state.last_clicked = {"lat": click_lat, "lng": click_lng}
                st.rerun()
        
        st.write(f"📍 Coordenadas seleccionadas: `{round(st.session_state.last_clicked['lat'], 5)}, {round(st.session_state.last_clicked['lng'], 5)}`")

        st.markdown("### Captura de Datos")
        n_medidor = st.text_input("N° de Medidor (Instalación) *", help="Ingrese solo números")
        n_medidor = "".join(filter(str.isdigit, n_medidor))
        
        foto = st.camera_input("Tomar FOTO EN VIVO del medidor *")
        
        if st.button("💾 Finalizar Lectura y Guardar Registro"):
            if not n_medidor or foto is None:
                st.error("❌ Error: Debes ingresar el medidor y tomar la foto en vivo antes de finalizar.")
            else:
                # Captura hora local de Chile
                st.session_state.timestamps["fin_punto"] = datetime.now(zona_cl)
                
                t_inicio_traslado = st.session_state.timestamps["inicio_traslado"]
                t_llegada = st.session_state.timestamps["llegada_punto"]
                t_fin = st.session_state.timestamps["fin_punto"]
                
                # Al estar ambas en la misma zona horaria, la resta de HH funcionará perfecto
                horas_traslado = round((t_llegada - t_inicio_traslado).total_seconds() / 3600, 3)
                horas_permanencia = round((t_fin - t_llegada).total_seconds() / 3600, 3)
                
                id_unico = f"{lector.replace(' ', '_')}_{t_fin.strftime('%Y%m%d%H%M%S')}"
                
                ruta_foto = f"fotos_medidores/{id_unico}.jpg"
                os.makedirs("fotos_medidores", exist_ok=True)
                with open(ruta_foto, "wb") as f:
                    f.write(foto.getbuffer())
                
                nuevo_registro = {
                    "ID_Registro": [id_unico],
                    "Gestor": [lector],
                    "Correlativo_Punto": [f"Punto {st.session_state.n_punto}"],
                    "Medidor": [n_medidor],
                    "Hora Inicio Traslado": [t_inicio_traslado.strftime("%Y-%m-%d %H:%M:%S")],
                    "Hora Llegada Punto": [t_llegada.strftime("%Y-%m-%d %H:%M:%S")],
                    "Hora Fin Lectura": [t_fin.strftime("%Y-%m-%d %H:%M:%S")],
                    "Horas Traslado": [horas_traslado],
                    "Horas Permanencia (HH)": [horas_permanencia],
                    "Ruta_Foto": [ruta_foto],
                    "Latitud": [st.session_state.last_clicked["lat"]],
                    "Longitud": [st.session_state.last_clicked["lng"]]
                }
                
                df = pd.DataFrame(nuevo_registro)
                archivo_datos = "registro_piloto_at.csv"
                file_exists = os.path.isfile(archivo_datos)
                df.to_csv(archivo_datos, mode='a', index=False, header=not file_exists, encoding='utf-8-sig')
                
                st.session_state.estado_brigada = "REGISTRADO"
                st.success(f"✅ Punto {st.session_state.n_punto} guardado correctamente.")
                st.balloons()
                time.sleep(2)
                st.rerun()

    # ------------------------------------------------------------------
    # ESTADO 3: REGISTRADO / CONTINÚAN EN TERRENO
    # ------------------------------------------------------------------
    elif st.session_state.estado_brigada == "REGISTRADO":
        st.info(f"✔️ El **Punto {st.session_state.n_punto}** ya fue cerrado con éxito.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("➡ Iniciar Traslado al Siguiente Punto"):
                st.session_state.n_punto += 1
                # Dejar listo el estado con valores limpios
                st.session_state.timestamps["inicio_traslado"] = datetime.now(zona_cl)
                st.session_state.timestamps["llegada_punto"] = None
                st.session_state.timestamps["fin_punto"] = None
                st.session_state.estado_brigada = "TRASLADO"
                st.rerun()
                
        with col2:
            if st.button("⏹ Finalizar Jornada Completa"):
                st.session_state.n_punto = 1
                st.session_state.estado_brigada = "INICIO_DIA"
                st.session_state.last_clicked = {"lat": -34.0601, "lng": -70.7891}
                st.success("Jornada cerrada correctamente.")
                time.sleep(2)
                st.rerun()