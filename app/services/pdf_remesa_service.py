import os
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as _pdfgen
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# ──────────────────────────────────────────────────────────────────────────────
# RUTAS ABSOLUTAS (derivadas desde la ubicación de este fichero)
# app/services/pdf_remesa_service.py  →  ../../  →  raíz del proyecto
# ──────────────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

MEDIA_DIR      = str(_PROJECT_ROOT / "media" / "remesas")
IMG_ENCABEZADO = str(_PROJECT_ROOT / "app" / "static" / "encabezado_fgulem.png")
IMG_PIE        = str(_PROJECT_ROOT / "app" / "static" / "pie_fgulem.png")

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE DISEÑO
# ──────────────────────────────────────────────────────────────────────────────

COLOR_CABECERA   = colors.HexColor("#1a3a5c")
COLOR_FILA_PAR   = colors.HexColor("#F5F5F5")
COLOR_FILA_IMPAR = colors.white
COLOR_CAJA_BG    = colors.HexColor("#EEF2F7")
COLOR_PIE_TEXTO  = colors.HexColor("#888888")
COLOR_LINEA_PIE  = colors.HexColor("#CCCCCC")

# Márgenes
MARGIN_LEFT   = 2 * cm
MARGIN_RIGHT  = 2 * cm
MARGIN_TOP    = 3.5 * cm
MARGIN_BOTTOM = 3.0 * cm

# Alturas de imagen
H_IMG_ENCABEZADO = 2.5 * cm
H_IMG_PIE        = 1.8 * cm

_styles = getSampleStyleSheet()

_estilo_titulo = ParagraphStyle(
    "titulo_rem",
    parent=_styles["Normal"],
    fontSize=16,
    fontName="Helvetica-Bold",
    textColor=COLOR_CABECERA,
    alignment=TA_CENTER,
    spaceAfter=8,
)
_estilo_normal = ParagraphStyle(
    "normal_rem",
    parent=_styles["Normal"],
    fontSize=9,
    leading=13,
)
_estilo_pie_texto = ParagraphStyle(
    "pie_rem",
    parent=_styles["Normal"],
    fontSize=8,
    textColor=COLOR_PIE_TEXTO,
    alignment=TA_CENTER,
)


# ──────────────────────────────────────────────────────────────────────────────
# CANVAS NUMERADO (para poder escribir "Página X de Y" en el pie)
# ──────────────────────────────────────────────────────────────────────────────

def _make_canvas_class(fecha_hora_gen: str):
    """
    Devuelve una subclase de Canvas que almacena cada página y en save()
    dibuja el encabezado y pie institucional con el total de páginas correcto.
    """

    class _NumberedCanvas(_pdfgen.Canvas):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states: list[dict] = []

        # Interceptamos showPage para guardar el estado en lugar de volcar
        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        # En save() volcamos todas las páginas con el total real
        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._dibujar_encabezado_pie(num_pages)
                super().showPage()
            super().save()

        def _dibujar_encabezado_pie(self, total_paginas: int):
            w, h = A4

            # ── ENCABEZADO ─────────────────────────────────────────────────
            img_enc_y = h - 0.35 * cm - H_IMG_ENCABEZADO
            if os.path.isfile(IMG_ENCABEZADO):
                self.drawImage(
                    ImageReader(IMG_ENCABEZADO),
                    MARGIN_LEFT, img_enc_y,
                    width=w - MARGIN_LEFT - MARGIN_RIGHT,
                    height=H_IMG_ENCABEZADO,
                    preserveAspectRatio=False,
                    mask="auto",
                )

            # Línea divisoria azul oscuro debajo del encabezado
            self.setStrokeColor(COLOR_CABECERA)
            self.setLineWidth(1)
            self.line(
                MARGIN_LEFT, img_enc_y - 0.15 * cm,
                w - MARGIN_RIGHT, img_enc_y - 0.15 * cm,
            )

            # ── PIE ────────────────────────────────────────────────────────
            # Línea divisoria gris encima del área de pie
            linea_pie_y = MARGIN_BOTTOM - 0.15 * cm
            self.setStrokeColor(COLOR_LINEA_PIE)
            self.setLineWidth(0.5)
            self.line(MARGIN_LEFT, linea_pie_y, w - MARGIN_RIGHT, linea_pie_y)

            # Texto "Página X de Y  |  Generado: …" encima de la imagen del pie
            self.setFont("Helvetica", 8)
            self.setFillColor(COLOR_PIE_TEXTO)
            self.drawRightString(
                w - MARGIN_RIGHT,
                linea_pie_y - 0.4 * cm,
                f"Página {self._pageNumber} de {total_paginas}  |  Generado: {fecha_hora_gen}",
            )

            # Imagen del pie
            if os.path.isfile(IMG_PIE):
                self.drawImage(
                    ImageReader(IMG_PIE),
                    MARGIN_LEFT, 0.2 * cm,
                    width=w - MARGIN_LEFT - MARGIN_RIGHT,
                    height=H_IMG_PIE,
                    preserveAspectRatio=False,
                    mask="auto",
                )

    return _NumberedCanvas


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PÚBLICA
# ──────────────────────────────────────────────────────────────────────────────

def generar_pdf_remesa(remesa: dict, pagos: list[dict]) -> str:
    """
    Genera el PDF de resumen de una remesa con encabezado y pie institucionales.

    Args:
        remesa: dict con los datos de la remesa (campos de remesas_service).
        pagos:  lista de dicts con los datos de cada PEG/pago incluido.
                Cada pago debe tener: nombre_proveedor, cif_nif, descripcion_gasto,
                iban, base_imponible, importe_iva, importe_total.

    Returns:
        Ruta relativa del PDF generado (ej. "media/remesas/remesa_1_20260403.pdf").
    """
    os.makedirs(MEDIA_DIR, exist_ok=True)

    fecha_hoy      = datetime.now().strftime("%Y%m%d")
    fecha_hora_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    nombre_fichero = f"remesa_{remesa['id_remesa']}_{fecha_hoy}.pdf"
    ruta_absoluta  = os.path.join(MEDIA_DIR, nombre_fichero)
    # Ruta relativa al proyecto para almacenar en la BD/mock
    ruta_relativa  = f"media/remesas/{nombre_fichero}"

    # ── DOCUMENTO ──────────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        ruta_absoluta,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )

    w = A4[0]
    body_width = w - MARGIN_LEFT - MARGIN_RIGHT

    # Frame: el área de contenido queda entre los márgenes
    frame = Frame(
        MARGIN_LEFT, MARGIN_BOTTOM,
        body_width,
        A4[1] - MARGIN_TOP - MARGIN_BOTTOM,
        id="main",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

    # ── STORY ─────────────────────────────────────────────────────────────────
    story = []

    # Título centrado
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Resumen de Remesa", _estilo_titulo))
    story.append(Spacer(1, 0.4 * cm))

    # ── DATOS EN DOS COLUMNAS (tabla sin bordes) ───────────────────────────────
    datos_remesa = [
        [
            Paragraph(f"<b>Código:</b> {remesa.get('codigo_remesa', '-')}", _estilo_normal),
            Paragraph(f"<b>Estado:</b> {remesa.get('estado', '-')}", _estilo_normal),
        ],
        [
            Paragraph(f"<b>Descripción:</b> {remesa.get('descripcion', '-')}", _estilo_normal),
            Paragraph(f"<b>Fecha creación:</b> {remesa.get('fecha_creacion', '-')}", _estilo_normal),
        ],
        [
            Paragraph(f"<b>Creado por:</b> {remesa.get('creado_por', '-')}", _estilo_normal),
            Paragraph(f"<b>Fecha cierre:</b> {remesa.get('fecha_cierre') or '-'}", _estilo_normal),
        ],
    ]
    col_datos = body_width / 2
    tabla_datos = Table(datos_remesa, colWidths=[col_datos, col_datos])
    tabla_datos.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(tabla_datos)
    story.append(Spacer(1, 0.5 * cm))

    # ── CAJA DE TOTALES ────────────────────────────────────────────────────────
    base_total    = sum(p.get("base_imponible", 0) for p in pagos)
    iva_total     = sum(p.get("importe_iva",    0) for p in pagos)
    importe_total = sum(p.get("importe_total",  0) for p in pagos)
    num_pagos     = len(pagos)

    estilo_total_normal = ParagraphStyle(
        "tot_n", parent=_styles["Normal"], fontSize=9, leading=13,
    )
    estilo_total_bold = ParagraphStyle(
        "tot_b", parent=_styles["Normal"],
        fontSize=13, fontName="Helvetica-Bold", leading=16,
    )

    totales_data = [[
        Paragraph(f"Nº de pagos: <b>{num_pagos}</b>",              estilo_total_normal),
        Paragraph(f"Base imponible: <b>{base_total:,.2f} €</b>",   estilo_total_normal),
        Paragraph(f"IVA total: <b>{iva_total:,.2f} €</b>",         estilo_total_normal),
        Paragraph(f"IMPORTE TOTAL: {importe_total:,.2f} €",        estilo_total_bold),
    ]]
    col_tot = [body_width * p for p in (0.20, 0.25, 0.20, 0.35)]
    tabla_totales = Table(totales_data, colWidths=col_tot)
    tabla_totales.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_CAJA_BG),
        ("BOX",           (0, 0), (-1, -1), 1, COLOR_CABECERA),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    story.append(tabla_totales)
    story.append(Spacer(1, 0.7 * cm))

    # ── TABLA DE PAGOS ─────────────────────────────────────────────────────────
    estilo_cab = ParagraphStyle(
        "cab_rem", parent=_styles["Normal"],
        fontSize=8, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER,
    )
    estilo_celda = ParagraphStyle(
        "cel_rem", parent=_styles["Normal"], fontSize=7.5, leading=10,
    )
    estilo_celda_der = ParagraphStyle(
        "cel_der_rem", parent=_styles["Normal"], fontSize=7.5, leading=10,
        alignment=TA_RIGHT,
    )

    cabeceras = [
        Paragraph("Nº",        estilo_cab),
        Paragraph("Proveedor", estilo_cab),
        Paragraph("NIF",       estilo_cab),
        Paragraph("Concepto",  estilo_cab),
        Paragraph("IBAN",      estilo_cab),
        Paragraph("Base",      estilo_cab),
        Paragraph("IVA",       estilo_cab),
        Paragraph("Total",     estilo_cab),
    ]

    filas = [cabeceras]
    for idx, pago in enumerate(pagos, start=1):
        iban = pago.get("iban") or "-"
        iban_display = iban if len(iban) <= 10 else f"···{iban[-4:]}"
        filas.append([
            Paragraph(str(idx),                                   estilo_celda),
            Paragraph(pago.get("nombre_proveedor", "-"),          estilo_celda),
            Paragraph(pago.get("cif_nif", "-"),                   estilo_celda),
            Paragraph(pago.get("descripcion_gasto", "-"),         estilo_celda),
            Paragraph(iban_display,                               estilo_celda),
            Paragraph(f"{pago.get('base_imponible', 0):,.2f} €", estilo_celda_der),
            Paragraph(f"{pago.get('importe_iva', 0):,.2f} €",    estilo_celda_der),
            Paragraph(f"{pago.get('importe_total', 0):,.2f} €",  estilo_celda_der),
        ])

    # Anchos proporcionales al body_width total (17cm a 2cm de margen)
    col_pagos = [
        body_width * p for p in (0.045, 0.225, 0.135, 0.240, 0.110, 0.115, 0.110, 0.130)
    ]
    tabla_pagos = Table(filas, colWidths=col_pagos, repeatRows=1)

    estilo_tabla = [
        ("BACKGROUND",    (0, 0), (-1, 0), COLOR_CABECERA),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("LINEBELOW",     (0, 0), (-1, 0),  1,   COLOR_CABECERA),
        ("ALIGN",         (5, 1), (7, -1),  "RIGHT"),
    ]
    for i in range(1, len(filas)):
        bg = COLOR_FILA_PAR if i % 2 == 0 else COLOR_FILA_IMPAR
        estilo_tabla.append(("BACKGROUND", (0, i), (-1, i), bg))

    tabla_pagos.setStyle(TableStyle(estilo_tabla))
    story.append(tabla_pagos)

    # ── BUILD ──────────────────────────────────────────────────────────────────
    doc.build(story, canvasmaker=_make_canvas_class(fecha_hora_gen))
    return ruta_relativa
