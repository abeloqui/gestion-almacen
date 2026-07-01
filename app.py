import streamlit as st
from auth import check_login, logout_button
from database import init_db, get_productos, get_total_ventas_hoy, get_caja_abierta

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

# --- Contenido principal ---
st.title("Panel Principal")

productos = get_productos(solo_activos=True)
bajos = [p for p in productos if float(p["stock"]) <= float(p["stock_minimo"]) and float(p["stock_minimo"]) > 0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Productos activos", len(productos))
col2.metric("Con stock bajo", len(bajos))
col3.metric("Ventas de hoy", f"${get_total_ventas_hoy():.2f}")

caja = get_caja_abierta()
col4.metric("Estado de caja", "🔓 Abierta" if caja else "🔒 Cerrada")

st.info(
    "📦 Cargá y editá tus productos desde **Stock**.\n\n"
    "🛒 Registrá ventas rápido desde **Ventas**.\n\n"
    "💰 Abrí y cerrá caja al día desde **Caja**.\n\n"
    "📊 Mirá tus estadísticas en **Reportes**."
)
