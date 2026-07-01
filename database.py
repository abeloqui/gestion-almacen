"""
Módulo de conexión a la base de datos (Neon PostgreSQL)
y creación del esquema inicial.
"""
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


def get_connection():
    """Crea una conexión nueva a la base de datos usando los secrets de Streamlit."""
    return psycopg2.connect(
        st.secrets["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )


@contextmanager
def get_cursor(commit=False):
    """Context manager para manejar conexión y cursor de forma segura."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def init_db():
    """Crea las tablas si no existen. Se llama una vez al iniciar la app."""
    with get_cursor(commit=True) as cur:
        # Tabla de productos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(150) NOT NULL,
                categoria VARCHAR(50) NOT NULL,
                tipo_venta VARCHAR(10) NOT NULL CHECK (tipo_venta IN ('kg', 'unidad')),
                precio NUMERIC(10,2) NOT NULL,
                stock NUMERIC(10,2) NOT NULL DEFAULT 0,
                stock_minimo NUMERIC(10,2) NOT NULL DEFAULT 0,
                activo BOOLEAN NOT NULL DEFAULT TRUE,
                creado_en TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)

        # Tabla de sesiones de caja
        cur.execute("""
            CREATE TABLE IF NOT EXISTS caja_sesiones (
                id SERIAL PRIMARY KEY,
                fecha_apertura TIMESTAMP NOT NULL DEFAULT NOW(),
                fecha_cierre TIMESTAMP,
                monto_apertura NUMERIC(10,2) NOT NULL,
                monto_cierre_declarado NUMERIC(10,2),
                total_ventas_efectivo NUMERIC(10,2) DEFAULT 0,
                total_ventas_otros NUMERIC(10,2) DEFAULT 0,
                diferencia NUMERIC(10,2),
                estado VARCHAR(10) NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta', 'cerrada'))
            );
        """)

        # Tabla de ventas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id SERIAL PRIMARY KEY,
                caja_sesion_id INTEGER REFERENCES caja_sesiones(id),
                fecha TIMESTAMP NOT NULL DEFAULT NOW(),
                total NUMERIC(10,2) NOT NULL,
                medio_pago VARCHAR(20) NOT NULL CHECK (medio_pago IN ('efectivo', 'tarjeta', 'transferencia', 'otro'))
            );
        """)

        # Detalle de items por venta
        cur.execute("""
            CREATE TABLE IF NOT EXISTS venta_items (
                id SERIAL PRIMARY KEY,
                venta_id INTEGER REFERENCES ventas(id) ON DELETE CASCADE,
                producto_id INTEGER REFERENCES productos(id),
                nombre_producto VARCHAR(150) NOT NULL,
                tipo_venta VARCHAR(10) NOT NULL,
                cantidad NUMERIC(10,3) NOT NULL,
                precio_unitario NUMERIC(10,2) NOT NULL,
                subtotal NUMERIC(10,2) NOT NULL
            );
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria);")
