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


# --- Categorías disponibles (valor interno, etiqueta visible) ---
CATEGORIAS = [
    ("carne", "🥩 Carnicería"),
    ("fruta_verdura", "🥬 Frutas y Verduras"),
    ("fiambre", "🧀 Fiambrería"),
    ("limpieza", "🧽 Limpieza"),
    ("almacen", "🛒 Almacén"),
]


def get_productos(solo_activos=True, categoria=None):
    """Devuelve la lista de productos, opcionalmente filtrada."""
    query = "SELECT * FROM productos WHERE 1=1"
    params = []
    if solo_activos:
        query += " AND activo = TRUE"
    if categoria:
        query += " AND categoria = %s"
        params.append(categoria)
    query += " ORDER BY categoria, nombre"
    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def get_producto(producto_id):
    """Devuelve un producto por id."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
        return cur.fetchone()


def crear_producto(nombre, categoria, tipo_venta, precio, stock, stock_minimo):
    with get_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO productos (nombre, categoria, tipo_venta, precio, stock, stock_minimo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (nombre, categoria, tipo_venta, precio, stock, stock_minimo))


def actualizar_producto(producto_id, nombre, categoria, tipo_venta, precio, stock, stock_minimo):
    with get_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE productos
            SET nombre = %s, categoria = %s, tipo_venta = %s,
                precio = %s, stock = %s, stock_minimo = %s
            WHERE id = %s
        """, (nombre, categoria, tipo_venta, precio, stock, stock_minimo, producto_id))


def ajustar_stock(producto_id, nuevo_stock):
    """Actualiza solo el stock de un producto (ajuste manual)."""
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))


def eliminar_producto(producto_id):
    """Baja lógica: no se borra de la base, se marca inactivo."""
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE productos SET activo = FALSE WHERE id = %s", (producto_id,))


def reactivar_producto(producto_id):
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE productos SET activo = TRUE WHERE id = %s", (producto_id,))


# ---------------------------------------------------------------
# Ventas / POS
# ---------------------------------------------------------------

def get_caja_abierta():
    """Devuelve la sesión de caja abierta actual, o None si no hay ninguna."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM caja_sesiones WHERE estado = 'abierta' ORDER BY id DESC LIMIT 1")
        return cur.fetchone()


def crear_venta(items, total, medio_pago, caja_sesion_id=None):
    """
    Registra una venta con sus items y descuenta stock.
    items: lista de dicts con producto_id, nombre, tipo_venta, cantidad, precio_unitario, subtotal
    """
    with get_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO ventas (caja_sesion_id, total, medio_pago)
            VALUES (%s, %s, %s) RETURNING id
        """, (caja_sesion_id, total, medio_pago))
        venta_id = cur.fetchone()["id"]

        for it in items:
            cur.execute("""
                INSERT INTO venta_items
                    (venta_id, producto_id, nombre_producto, tipo_venta, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                venta_id, it["producto_id"], it["nombre"], it["tipo_venta"],
                it["cantidad"], it["precio_unitario"], it["subtotal"]
            ))
            cur.execute("""
                UPDATE productos SET stock = stock - %s WHERE id = %s
            """, (it["cantidad"], it["producto_id"]))

        return venta_id


def get_ventas_hoy():
    """Devuelve las ventas del día actual (hora local del servidor)."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM ventas
            WHERE fecha::date = CURRENT_DATE
            ORDER BY fecha DESC
        """)
        return cur.fetchall()


def get_total_ventas_hoy():
    with get_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(total), 0) AS total
            FROM ventas WHERE fecha::date = CURRENT_DATE
        """)
        return float(cur.fetchone()["total"])


# ---------------------------------------------------------------
# Caja
# ---------------------------------------------------------------

def abrir_caja(monto_apertura):
    with get_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO caja_sesiones (monto_apertura, estado)
            VALUES (%s, 'abierta') RETURNING id
        """, (monto_apertura,))
        return cur.fetchone()["id"]


def cerrar_caja(caja_id, monto_declarado):
    with get_cursor(commit=True) as cur:
        cur.execute("""
            SELECT
                COALESCE(SUM(total) FILTER (WHERE medio_pago = 'efectivo'), 0) AS efectivo,
                COALESCE(SUM(total) FILTER (WHERE medio_pago != 'efectivo'), 0) AS otros
            FROM ventas WHERE caja_sesion_id = %s
        """, (caja_id,))
        row = cur.fetchone()
        total_efectivo = float(row["efectivo"])
        total_otros = float(row["otros"])

        cur.execute("SELECT monto_apertura FROM caja_sesiones WHERE id = %s", (caja_id,))
        monto_apertura = float(cur.fetchone()["monto_apertura"])

        esperado = monto_apertura + total_efectivo
        diferencia = round(float(monto_declarado) - esperado, 2)

        cur.execute("""
            UPDATE caja_sesiones
            SET fecha_cierre = NOW(),
                monto_cierre_declarado = %s,
                total_ventas_efectivo = %s,
                total_ventas_otros = %s,
                diferencia = %s,
                estado = 'cerrada'
            WHERE id = %s
        """, (monto_declarado, total_efectivo, total_otros, diferencia, caja_id))

        return {
            "monto_apertura": monto_apertura,
            "total_efectivo": total_efectivo,
            "total_otros": total_otros,
            "esperado": esperado,
            "monto_declarado": float(monto_declarado),
            "diferencia": diferencia
        }


def get_historial_cajas(limit=30):
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM caja_sesiones
            ORDER BY fecha_apertura DESC LIMIT %s
        """, (limit,))
        return cur.fetchall()


def get_caja_by_id(caja_id):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM caja_sesiones WHERE id = %s", (caja_id,))
        return cur.fetchone()


def get_ventas_de_caja(caja_id):
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM ventas WHERE caja_sesion_id = %s ORDER BY fecha
        """, (caja_id,))
        return cur.fetchall()


# ---------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------

def get_ventas_por_dia(fecha_inicio, fecha_fin):
    with get_cursor() as cur:
        cur.execute("""
            SELECT fecha::date AS dia, COALESCE(SUM(total), 0) AS total
            FROM ventas
            WHERE fecha::date BETWEEN %s AND %s
            GROUP BY fecha::date
            ORDER BY fecha::date
        """, (fecha_inicio, fecha_fin))
        return cur.fetchall()


def get_ventas_por_categoria(fecha_inicio, fecha_fin):
    with get_cursor() as cur:
        cur.execute("""
            SELECT p.categoria AS categoria, COALESCE(SUM(vi.subtotal), 0) AS total
            FROM venta_items vi
            JOIN ventas v ON v.id = vi.venta_id
            LEFT JOIN productos p ON p.id = vi.producto_id
            WHERE v.fecha::date BETWEEN %s AND %s
            GROUP BY p.categoria
            ORDER BY total DESC
        """, (fecha_inicio, fecha_fin))
        return cur.fetchall()


def get_top_productos(fecha_inicio, fecha_fin, limit=10):
    with get_cursor() as cur:
        cur.execute("""
            SELECT vi.nombre_producto AS nombre,
                   SUM(vi.cantidad) AS cantidad_total,
                   SUM(vi.subtotal) AS total_vendido
            FROM venta_items vi
            JOIN ventas v ON v.id = vi.venta_id
            WHERE v.fecha::date BETWEEN %s AND %s
            GROUP BY vi.nombre_producto
            ORDER BY total_vendido DESC
            LIMIT %s
        """, (fecha_inicio, fecha_fin, limit))
        return cur.fetchall()


def get_resumen_periodo(fecha_inicio, fecha_fin):
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                COALESCE(SUM(total), 0) AS total_vendido,
                COUNT(*) AS cantidad_ventas,
                COALESCE(SUM(total) FILTER (WHERE medio_pago = 'efectivo'), 0) AS total_efectivo,
                COALESCE(SUM(total) FILTER (WHERE medio_pago != 'efectivo'), 0) AS total_otros
            FROM ventas
            WHERE fecha::date BETWEEN %s AND %s
        """, (fecha_inicio, fecha_fin))
        return cur.fetchone()
    
