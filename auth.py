"""
Autenticación simple para un único usuario (el dueño del almacén).
La contraseña (hasheada con PBKDF2-SHA256, librería estándar de Python)
se guarda en los secrets de Streamlit, nunca en el código ni en el repositorio.
"""
import streamlit as st
import hashlib
import hmac


def verificar_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    """Recalcula el hash con el salt guardado y compara de forma segura."""
    salt = bytes.fromhex(salt_hex)
    calculado = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 200_000
    )
    return hmac.compare_digest(calculado.hex(), hash_hex)


def check_login():
    """
    Muestra el formulario de login si el usuario no está autenticado.
    Devuelve True si ya está logueado, False si no (y detiene la ejecución).
    """
    if st.session_state.get("autenticado"):
        return True

    st.title("🏪 Sistema de Gestión - Almacén")
    st.subheader("Iniciar sesión")

    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar", use_container_width=True)

        if submitted:
            usuario_ok = usuario == st.secrets["APP_USERNAME"]
            password_ok = usuario_ok and verificar_password(
                password,
                st.secrets["APP_PASSWORD_SALT"],
                st.secrets["APP_PASSWORD_HASH"]
            )
            if usuario_ok and password_ok:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    st.stop()


def logout_button():
    """Botón de cerrar sesión para mostrar en el sidebar."""
    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()
        
