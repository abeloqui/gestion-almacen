import streamlit as st
from auth import check_login, logout_button
from database import init_db

st.set_page_config(
    page_title="Gestión Almacén",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Login ---
check_login()

# --- Inicializar base de datos (crea tablas si no existen) ---
try:
    init_db()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()

# --- Sidebar ---
st.sidebar.title("🏪 Mi Almacén")
st.sidebar.markdown("---")
logout_button()

# --- Contenido principal (dashboard, se completa en próximas partes) ---
st.title("Panel Principal")
st.info(
    "✅ Conexión a base de datos OK y estructura inicial creada.\n\n"
    "Las secciones de **Stock**, **Ventas**, **Caja** y **Reportes** "
    "se agregan en las próximas partes como páginas del menú lateral "
    "(carpeta `pages/`)."
)

col1, col2, col3 = st.columns(3)
col1.metric("Productos cargados", "—")
col2.metric("Ventas de hoy", "—")
col3.metric("Estado de caja", "—")
