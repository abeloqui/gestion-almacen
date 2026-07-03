import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from auth import check_login, logout_button
from database import (
    CATEGORIAS, get_ventas_por_dia, get_ventas_por_categoria,
    get_top_productos, get_resumen_periodo
)

st.set_page_config(page_title="Reportes - Almacén", page_icon="📊", layout="wide")
check_login()

st.sidebar.title("🏪 Mi Almacén")
st.sidebar.markdown("---")
logout_button()

st.title("📊 Reportes")

CATEGORIA_LABELS = dict(CATEGORIAS)

# --- Selector de rango de fechas ---
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    fecha_inicio = st.date_input("Desde", value=date.today() - timedelta(days=7))
with col2:
    fecha_fin = st.date_input("Hasta", value=date.today())
with col3:
    atajo = st.radio(
        "Atajo", options=["Hoy", "Últimos 7 días", "Últimos 30 días", "Este mes"],
        horizontal=True, label_visibility="collapsed"
    )
    if atajo == "Hoy":
        fecha_inicio = fecha_fin = date.today()
    elif atajo == "Últimos 7 días":
        fecha_inicio = date.today() - timedelta(days=7)
        fecha_fin = date.today()
    elif atajo == "Últimos 30 días":
        fecha_inicio = date.today() - timedelta(days=30)
        fecha_fin = date.today()
    elif atajo == "Este mes":
        fecha_inicio = date.today().replace(day=1)
        fecha_fin = date.today()

if fecha_inicio > fecha_fin:
    st.error("La fecha 'Desde' no puede ser posterior a 'Hasta'.")
    st.stop()

# --- Resumen general ---
resumen = get_resumen_periodo(fecha_inicio, fecha_fin)
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Total vendido", f"${float(resumen['total_vendido']):,.2f}")
col_b.metric("Cantidad de ventas", int(resumen["cantidad_ventas"]))
col_c.metric("En efectivo", f"${float(resumen['total_efectivo']):,.2f}")
col_d.metric("Otros medios", f"${float(resumen['total_otros']):,.2f}")

st.markdown("---")

# --- Ventas por día ---
st.subheader("Ventas por día")
ventas_dia = get_ventas_por_dia(fecha_inicio, fecha_fin)
if ventas_dia:
    df_dia = pd.DataFrame(ventas_dia)
    df_dia["dia"] = pd.to_datetime(df_dia["dia"])
    df_dia["total"] = df_dia["total"].astype(float)
    fig_dia = px.bar(df_dia, x="dia", y="total", labels={"dia": "Fecha", "total": "Total vendido ($)"})
    fig_dia.update_layout(showlegend=False)
    st.plotly_chart(fig_dia, use_container_width=True)
else:
    st.info("No hay ventas registradas en este período.")

# --- Ventas por categoría ---
col_cat, col_top = st.columns(2)

with col_cat:
    st.subheader("Ventas por categoría")
    ventas_cat = get_ventas_por_categoria(fecha_inicio, fecha_fin)
    if ventas_cat:
        df_cat = pd.DataFrame(ventas_cat)
        df_cat["categoria"] = df_cat["categoria"].apply(
            lambda c: CATEGORIA_LABELS.get(c, "Sin categoría") if c else "Sin categoría"
        )
        df_cat["total"] = df_cat["total"].astype(float)
        fig_cat = px.pie(df_cat, names="categoria", values="total", hole=0.4)
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("Sin datos para este período.")

with col_top:
    st.subheader("Top 10 productos más vendidos")
    top = get_top_productos(fecha_inicio, fecha_fin, limit=10)
    if top:
        df_top = pd.DataFrame(top)
        df_top["total_vendido"] = df_top["total_vendido"].astype(float)
        df_top["cantidad_total"] = df_top["cantidad_total"].astype(float)
        df_top = df_top.rename(columns={
            "nombre": "Producto", "cantidad_total": "Cantidad", "total_vendido": "Total ($)"
        })
        st.dataframe(
            df_top[["Producto", "Cantidad", "Total ($)"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Sin datos para este período.")

# --- Exportar CSV ---
st.markdown("---")
if ventas_dia:
    csv = pd.DataFrame(ventas_dia).to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar ventas por día (CSV)",
        data=csv,
        file_name=f"ventas_{fecha_inicio}_{fecha_fin}.csv",
        mime="text/csv"
    )
