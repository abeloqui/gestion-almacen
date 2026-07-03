import streamlit as st
from auth import check_login, logout_button
from database import (
    CATEGORIAS, get_productos, crear_venta, get_caja_abierta
)

st.set_page_config(page_title="Ventas - Almacén", page_icon="🛒", layout="wide")
check_login()

st.sidebar.title("🏪 Mi Almacén")
st.sidebar.markdown("---")
logout_button()

st.title("🛒 Punto de Venta")

CATEGORIA_LABELS = dict(CATEGORIAS)
CATEGORIA_KEYS = [c[0] for c in CATEGORIAS]

if "carrito" not in st.session_state:
    st.session_state.carrito = []  # lista de dicts

caja = get_caja_abierta()
if not caja:
    st.warning(
        "⚠️ No hay una caja abierta. Podés seguir vendiendo, pero la venta no va a "
        "quedar asociada a una sesión de caja hasta que agreguemos ese módulo en la Parte 4."
    )

col_productos, col_carrito = st.columns([3, 2])

# ---------------------------------------------------------------
# Columna izquierda: selección de productos
# ---------------------------------------------------------------
with col_productos:
    filtro_categoria = st.selectbox(
        "Categoría",
        options=["todas"] + CATEGORIA_KEYS,
        format_func=lambda k: "Todas las categorías" if k == "todas" else CATEGORIA_LABELS[k]
    )
    busqueda = st.text_input("🔎 Buscar producto", placeholder="Escribí para filtrar...")

    categoria_query = None if filtro_categoria == "todas" else filtro_categoria
    productos = get_productos(solo_activos=True, categoria=categoria_query)

    if busqueda.strip():
        productos = [p for p in productos if busqueda.strip().lower() in p["nombre"].lower()]

    if not productos:
        st.info("No hay productos que coincidan.")

    for p in productos:
        unidad_label = "kg" if p["tipo_venta"] == "kg" else "un."
        sin_stock = float(p["stock"]) <= 0

        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.markdown(f"**{p['nombre']}**")
                st.caption(f"{CATEGORIA_LABELS[p['categoria']]} · ${float(p['precio']):.2f}/{unidad_label}")
                if sin_stock:
                    st.caption("🔴 Sin stock")
                else:
                    st.caption(f"Stock: {float(p['stock']):.2f} {unidad_label}")
            with c2:
                if p["tipo_venta"] == "kg":
                    cantidad = st.number_input(
                        "Kg", min_value=0.0, step=0.100, format="%.3f",
                        key=f"cant_{p['id']}", label_visibility="collapsed"
                    )
                else:
                    cantidad = st.number_input(
                        "Cant.", min_value=0, step=1, format="%d",
                        key=f"cant_{p['id']}", label_visibility="collapsed"
                    )
            with c3:
                if st.button("➕ Agregar", key=f"add_{p['id']}", use_container_width=True):
                    if cantidad <= 0:
                        st.error("Ingresá una cantidad mayor a 0.")
                    else:
                        subtotal = round(float(cantidad) * float(p["precio"]), 2)
                        st.session_state.carrito.append({
                            "producto_id": p["id"],
                            "nombre": p["nombre"],
                            "tipo_venta": p["tipo_venta"],
                            "cantidad": float(cantidad),
                            "precio_unitario": float(p["precio"]),
                            "subtotal": subtotal
                        })
                        st.rerun()

# ---------------------------------------------------------------
# Columna derecha: carrito / ticket
# ---------------------------------------------------------------
with col_carrito:
    st.subheader("🧾 Ticket actual")

    if not st.session_state.carrito:
        st.info("El carrito está vacío. Agregá productos desde la izquierda.")
    else:
        total = 0.0
        for idx, item in enumerate(st.session_state.carrito):
            unidad_label = "kg" if item["tipo_venta"] == "kg" else "un."
            total += item["subtotal"]
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(
                    f"**{item['nombre']}** — {item['cantidad']:.2f} {unidad_label} "
                    f"× ${item['precio_unitario']:.2f} = **${item['subtotal']:.2f}**"
                )
            with c2:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()

        st.markdown("---")
        st.markdown(f"## Total: ${total:.2f}")

        medio_pago = st.selectbox(
            "Medio de pago",
            options=["efectivo", "tarjeta", "transferencia", "otro"],
            format_func=lambda v: {
                "efectivo": "💵 Efectivo",
                "tarjeta": "💳 Tarjeta",
                "transferencia": "📲 Transferencia",
                "otro": "🔁 Otro"
            }[v]
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Confirmar venta", type="primary", use_container_width=True):
                caja_id = caja["id"] if caja else None
                crear_venta(st.session_state.carrito, total, medio_pago, caja_id)
                st.session_state.carrito = []
                st.success(f"Venta registrada por ${total:.2f}.")
                st.rerun()
        with col_b:
            if st.button("🧹 Vaciar carrito", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
