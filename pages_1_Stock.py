import streamlit as st
import pandas as pd
from auth import check_login, logout_button
from database import (
    CATEGORIAS, get_productos, crear_producto,
    actualizar_producto, ajustar_stock, eliminar_producto, reactivar_producto
)

st.set_page_config(page_title="Stock - Almacén", page_icon="📦", layout="wide")
check_login()

st.sidebar.title("🏪 Mi Almacén")
st.sidebar.markdown("---")
logout_button()

st.title("📦 Gestión de Stock")

CATEGORIA_LABELS = dict(CATEGORIAS)
CATEGORIA_KEYS = [c[0] for c in CATEGORIAS]

tab_listado, tab_nuevo = st.tabs(["📋 Listado y edición", "➕ Nuevo producto"])

# ---------------------------------------------------------------
# TAB: Nuevo producto
# ---------------------------------------------------------------
with tab_nuevo:
    st.subheader("Agregar producto")
    with st.form("nuevo_producto_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre del producto *")
            categoria = st.selectbox(
                "Categoría *",
                options=CATEGORIA_KEYS,
                format_func=lambda k: CATEGORIA_LABELS[k]
            )
            tipo_venta = st.radio(
                "Se vende por *",
                options=["kg", "unidad"],
                format_func=lambda v: "Peso (kg)" if v == "kg" else "Unidad",
                horizontal=True
            )
        with col2:
            precio = st.number_input(
                "Precio ($ por kg o por unidad) *",
                min_value=0.0, step=10.0, format="%.2f"
            )
            stock = st.number_input(
                "Stock inicial", min_value=0.0, step=1.0, format="%.2f"
            )
            stock_minimo = st.number_input(
                "Alertar cuando el stock baje de", min_value=0.0, step=1.0, format="%.2f"
            )

        submitted = st.form_submit_button("Guardar producto", use_container_width=True)
        if submitted:
            if not nombre.strip():
                st.error("El nombre del producto es obligatorio.")
            elif precio <= 0:
                st.error("El precio debe ser mayor a 0.")
            else:
                crear_producto(nombre.strip(), categoria, tipo_venta, precio, stock, stock_minimo)
                st.success(f"Producto '{nombre}' agregado correctamente.")
                st.rerun()

# ---------------------------------------------------------------
# TAB: Listado y edición
# ---------------------------------------------------------------
with tab_listado:
    col_filtro, col_mostrar = st.columns([2, 1])
    with col_filtro:
        filtro_categoria = st.selectbox(
            "Filtrar por categoría",
            options=["todas"] + CATEGORIA_KEYS,
            format_func=lambda k: "Todas las categorías" if k == "todas" else CATEGORIA_LABELS[k]
        )
    with col_mostrar:
        mostrar_inactivos = st.checkbox("Mostrar productos dados de baja")

    categoria_query = None if filtro_categoria == "todas" else filtro_categoria
    productos = get_productos(solo_activos=not mostrar_inactivos, categoria=categoria_query)

    if not productos:
        st.info("No hay productos cargados todavía. Agregá el primero en la pestaña 'Nuevo producto'.")
    else:
        # Alerta de stock bajo
        bajos = [p for p in productos if p["activo"] and float(p["stock"]) <= float(p["stock_minimo"]) and float(p["stock_minimo"]) > 0]
        if bajos:
            nombres_bajos = ", ".join(p["nombre"] for p in bajos)
            st.warning(f"⚠️ Stock bajo en: {nombres_bajos}")

        st.markdown(f"**{len(productos)} producto(s)**")

        for p in productos:
            unidad_label = "kg" if p["tipo_venta"] == "kg" else "un."
            stock_bajo = float(p["stock"]) <= float(p["stock_minimo"]) and float(p["stock_minimo"]) > 0
            estado_icono = "🔴" if stock_bajo else "🟢"
            inactivo_tag = " 🚫 (baja)" if not p["activo"] else ""

            with st.expander(
                f"{estado_icono} {CATEGORIA_LABELS[p['categoria']]} — **{p['nombre']}**{inactivo_tag}  "
                f"| ${float(p['precio']):.2f}/{unidad_label} | Stock: {float(p['stock']):.2f} {unidad_label}"
            ):
                with st.form(f"edit_form_{p['id']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        e_nombre = st.text_input("Nombre", value=p["nombre"], key=f"nombre_{p['id']}")
                        e_categoria = st.selectbox(
                            "Categoría", options=CATEGORIA_KEYS,
                            index=CATEGORIA_KEYS.index(p["categoria"]),
                            format_func=lambda k: CATEGORIA_LABELS[k],
                            key=f"cat_{p['id']}"
                        )
                        e_tipo = st.radio(
                            "Se vende por", options=["kg", "unidad"],
                            index=0 if p["tipo_venta"] == "kg" else 1,
                            format_func=lambda v: "Peso (kg)" if v == "kg" else "Unidad",
                            horizontal=True, key=f"tipo_{p['id']}"
                        )
                    with c2:
                        e_precio = st.number_input(
                            "Precio", min_value=0.0, step=10.0, format="%.2f",
                            value=float(p["precio"]), key=f"precio_{p['id']}"
                        )
                        e_stock = st.number_input(
                            "Stock actual", min_value=0.0, step=1.0, format="%.2f",
                            value=float(p["stock"]), key=f"stock_{p['id']}"
                        )
                        e_stock_min = st.number_input(
                            "Alertar debajo de", min_value=0.0, step=1.0, format="%.2f",
                            value=float(p["stock_minimo"]), key=f"stockmin_{p['id']}"
                        )

                    b1, b2 = st.columns(2)
                    with b1:
                        guardar = st.form_submit_button("💾 Guardar cambios", use_container_width=True)
                    with b2:
                        if p["activo"]:
                            baja = st.form_submit_button("🚫 Dar de baja", use_container_width=True)
                        else:
                            baja = st.form_submit_button("♻️ Reactivar", use_container_width=True)

                    if guardar:
                        actualizar_producto(
                            p["id"], e_nombre.strip(), e_categoria, e_tipo,
                            e_precio, e_stock, e_stock_min
                        )
                        st.success("Producto actualizado.")
                        st.rerun()

                    if baja:
                        if p["activo"]:
                            eliminar_producto(p["id"])
                            st.success("Producto dado de baja.")
                        else:
                            reactivar_producto(p["id"])
                            st.success("Producto reactivado.")
                        st.rerun()
