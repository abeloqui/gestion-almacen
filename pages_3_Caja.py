import streamlit as st
from auth import check_login, logout_button
from database import (
    get_caja_abierta, abrir_caja, cerrar_caja, get_historial_cajas,
    get_ventas_de_caja, get_caja_by_id
)
from utils_pdf import generar_pdf_cierre_caja

st.set_page_config(page_title="Caja - Almacén", page_icon="💰", layout="wide")
check_login()

st.sidebar.title("🏪 Mi Almacén")
st.sidebar.markdown("---")
logout_button()

st.title("💰 Caja")

caja = get_caja_abierta()

tab_actual, tab_historial = st.tabs(["🔓 Caja actual", "📜 Historial"])

# ---------------------------------------------------------------
# TAB: Caja actual (abrir / cerrar)
# ---------------------------------------------------------------
with tab_actual:
    if caja is None:
        st.info("No hay ninguna caja abierta en este momento.")
        with st.form("abrir_caja_form"):
            monto_apertura = st.number_input(
                "Monto inicial en efectivo ($)", min_value=0.0, step=100.0, format="%.2f"
            )
            abrir = st.form_submit_button("🔓 Abrir caja", type="primary", use_container_width=True)
            if abrir:
                caja_id = abrir_caja(monto_apertura)
                st.success(f"Caja abierta (sesión N.° {caja_id}) con ${monto_apertura:,.2f}.")
                st.rerun()
    else:
        ventas_caja = get_ventas_de_caja(caja["id"])
        total_efectivo = sum(float(v["total"]) for v in ventas_caja if v["medio_pago"] == "efectivo")
        total_otros = sum(float(v["total"]) for v in ventas_caja if v["medio_pago"] != "efectivo")
        esperado = float(caja["monto_apertura"]) + total_efectivo

        st.success(f"Caja abierta desde {caja['fecha_apertura'].strftime('%d/%m/%Y %H:%M')}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Apertura", f"${float(caja['monto_apertura']):,.2f}")
        col2.metric("Ventas efectivo", f"${total_efectivo:,.2f}")
        col3.metric("Ventas otros medios", f"${total_otros:,.2f}")
        col4.metric("Efectivo esperado", f"${esperado:,.2f}")

        st.markdown(f"**{len(ventas_caja)} venta(s) registradas en esta sesión.**")

        st.markdown("---")
        st.subheader("Cerrar caja")
        with st.form("cerrar_caja_form"):
            monto_declarado = st.number_input(
                "Efectivo contado al cierre ($)", min_value=0.0, step=100.0, format="%.2f"
            )
            cerrar = st.form_submit_button("🔒 Cerrar caja", type="primary", use_container_width=True)
            if cerrar:
                resultado = cerrar_caja(caja["id"], monto_declarado)
                st.session_state["ultimo_cierre_id"] = caja["id"]
                diferencia = resultado["diferencia"]
                if abs(diferencia) < 0.01:
                    st.success("Caja cerrada. Sin diferencias 🎉")
                elif diferencia > 0:
                    st.warning(f"Caja cerrada. Sobrante de ${diferencia:,.2f}.")
                else:
                    st.error(f"Caja cerrada. Faltante de ${abs(diferencia):,.2f}.")
                st.rerun()

    # Descargar PDF del último cierre, si corresponde
    if st.session_state.get("ultimo_cierre_id"):
        caja_cerrada = get_caja_by_id(st.session_state["ultimo_cierre_id"])
        if caja_cerrada and caja_cerrada["estado"] == "cerrada":
            pdf_bytes = generar_pdf_cierre_caja(caja_cerrada)
            st.download_button(
                "📄 Descargar PDF del último cierre",
                data=pdf_bytes,
                file_name=f"cierre_caja_{caja_cerrada['id']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# ---------------------------------------------------------------
# TAB: Historial
# ---------------------------------------------------------------
with tab_historial:
    historial = get_historial_cajas()
    if not historial:
        st.info("Todavía no hay sesiones de caja registradas.")
    else:
        for c in historial:
            estado_icono = "🔓" if c["estado"] == "abierta" else "🔒"
            fecha_str = c["fecha_apertura"].strftime("%d/%m/%Y %H:%M")
            with st.expander(f"{estado_icono} Sesión N.° {c['id']} — {fecha_str}"):
                st.write(f"**Apertura:** ${float(c['monto_apertura']):,.2f}")
                if c["estado"] == "cerrada":
                    st.write(f"**Ventas efectivo:** ${float(c['total_ventas_efectivo'] or 0):,.2f}")
                    st.write(f"**Ventas otros medios:** ${float(c['total_ventas_otros'] or 0):,.2f}")
                    st.write(f"**Declarado al cierre:** ${float(c['monto_cierre_declarado'] or 0):,.2f}")
                    diferencia = float(c["diferencia"] or 0)
                    if diferencia < 0:
                        st.write(f"**Diferencia:** 🔴 Faltante ${abs(diferencia):,.2f}")
                    elif diferencia > 0:
                        st.write(f"**Diferencia:** 🟡 Sobrante ${diferencia:,.2f}")
                    else:
                        st.write("**Diferencia:** 🟢 Sin diferencias")

                    pdf_bytes = generar_pdf_cierre_caja(c)
                    st.download_button(
                        "📄 Descargar PDF",
                        data=pdf_bytes,
                        file_name=f"cierre_caja_{c['id']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{c['id']}"
                    )
                else:
                    st.write("Sesión todavía abierta.")
