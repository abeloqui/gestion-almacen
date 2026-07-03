"""
Generación de PDF de cierre de caja usando ReportLab.
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generar_pdf_cierre_caja(caja: dict) -> bytes:
    """
    Recibe el dict de una sesión de caja (ya cerrada, con todos los campos)
    y devuelve los bytes del PDF listo para descargar.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A5,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm
    )
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("titulo", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    normal = styles["Normal"]

    elementos = []
    elementos.append(Paragraph("Cierre de Caja", titulo_style))
    elementos.append(Paragraph(f"Sesión N.° {caja['id']}", normal))
    elementos.append(Spacer(1, 0.4 * cm))

    apertura = caja["fecha_apertura"]
    cierre = caja.get("fecha_cierre") or datetime.now()
    elementos.append(Paragraph(f"Apertura: {apertura.strftime('%d/%m/%Y %H:%M')}", normal))
    elementos.append(Paragraph(f"Cierre: {cierre.strftime('%d/%m/%Y %H:%M')}", normal))
    elementos.append(Spacer(1, 0.5 * cm))

    monto_apertura = float(caja["monto_apertura"])
    total_efectivo = float(caja["total_ventas_efectivo"] or 0)
    total_otros = float(caja["total_ventas_otros"] or 0)
    monto_declarado = float(caja["monto_cierre_declarado"] or 0)
    esperado = monto_apertura + total_efectivo
    diferencia = float(caja["diferencia"] or 0)

    data = [
        ["Concepto", "Monto"],
        ["Monto de apertura", f"${monto_apertura:,.2f}"],
        ["Ventas en efectivo", f"${total_efectivo:,.2f}"],
        ["Ventas otros medios", f"${total_otros:,.2f}"],
        ["Efectivo esperado", f"${esperado:,.2f}"],
        ["Efectivo declarado (contado)", f"${monto_declarado:,.2f}"],
        ["Diferencia", f"${diferencia:,.2f}"],
    ]

    tabla = Table(data, colWidths=[8 * cm, 4 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fdecea") if diferencia < 0 else colors.HexColor("#eafaf1")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elementos.append(tabla)

    elementos.append(Spacer(1, 0.6 * cm))
    if abs(diferencia) < 0.01:
        estado_txt = "✔ Caja sin diferencias."
    elif diferencia > 0:
        estado_txt = f"Sobrante de ${diferencia:,.2f} respecto a lo esperado."
    else:
        estado_txt = f"Faltante de ${abs(diferencia):,.2f} respecto a lo esperado."
    elementos.append(Paragraph(estado_txt, normal))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.read()
