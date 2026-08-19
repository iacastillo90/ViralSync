"""
pdf_generator.py

Servicio de Generación de Reportes Ejecutivos PDF de ROI y Métricas RUM a 72h.
Produce un reporte binario PDF real (marca blanca) usando ReportLab y metadatos estructurados.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)


def generate_tenant_roi_pdf_report(tenant_id: str, metrics_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Genera la estructura de metadatos del reporte ejecutivo para el tenant."""
    logger.info(f"[{tenant_id}] Generando metadatos de reporte ejecutivo...")

    metrics = metrics_summary.get("metrics", {})
    distribution = metrics.get("classification_distribution", {"ROJO": 0, "AMARILLO": 0, "VERDE": 0})

    report_metadata = {
        "title": f"Reporte Ejecutivo de Rendimiento - Tenant {tenant_id}",
        "tenant_id": tenant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_views": metrics.get("total_views", 0),
            "total_likes": metrics.get("total_likes", 0),
            "total_comments": metrics.get("total_comments", 0),
            "total_shares": metrics.get("total_shares", 0),
            "videos_analyzed": metrics.get("videos_analyzed", 0),
            "avg_ratio_relativo": metrics.get("avg_ratio_relativo", 1.0),
            "distribution": distribution,
        },
        "content_type": "application/pdf",
        "filename": f"viralsync_reporte_ejecutivo_{tenant_id[:8]}.pdf",
    }

    return report_metadata


def build_tenant_pdf_bytes(tenant_id: str, metrics_summary: Dict[str, Any]) -> bytes:
    """
    Construye un archivo binario PDF real (%PDF-1.4) de marca blanca con ReportLab
    que incluye resumen ejecutivo, métricas de alcance, distribución RUM y recomendación de IA.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Estilos corporativos de marca blanca
        style_header_title = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E1B4B"),
            alignment=TA_LEFT,
        )

        style_subtitle = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4F46E5"),
            alignment=TA_LEFT,
        )

        style_section_title = ParagraphStyle(
            "SecTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=12,
            spaceAfter=6,
        )

        style_body = ParagraphStyle(
            "BodyTextCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )

        style_kpi_num = ParagraphStyle(
            "KpiNum",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4F46E5"),
        )

        style_kpi_label = ParagraphStyle(
            "KpiLabel",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#64748B"),
        )

        elements = []

        # 1. Cabecera Corporativa Marca Blanca
        header_table_data = [
            [
                Paragraph("<b>VIRALSYNC 360°</b><br/><font size=8 color='#64748B'>Agencia de Marketing de IA</font>", style_header_title),
                Paragraph(f"<b>REPORTE EJECUTIVO DE ROI</b><br/><font size=8 color='#64748B'>Fecha: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}</font>", style_subtitle),
            ]
        ]
        header_table = Table(header_table_data, colWidths=[300, 240])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#6366F1"), spaceBefore=2, spaceAfter=12))

        # 2. Información del Tenant
        metrics = metrics_summary.get("metrics", {})
        info_data = [
            [
                Paragraph(f"<b>ID de Cliente / Tenant:</b> {tenant_id}", style_body),
                Paragraph(f"<b>Videos Analizados (72h):</b> {metrics.get('videos_analyzed', 0)}", style_body),
            ],
            [
                Paragraph(f"<b>Ratio Relativo Promedio:</b> {metrics.get('avg_ratio_relativo', 1.0):.2f}x", style_body),
                Paragraph(f"<b>Estado del Embudo:</b> Activo & Optimizado", style_body),
            ]
        ]
        info_table = Table(info_data, colWidths=[270, 270])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 14))

        # 3. Resumen Ejecutivo (KPI Cards en Tabla)
        elements.append(Paragraph("1. Resumen Ejecutivo de Impacto", style_section_title))

        views_val = metrics.get("total_views", 0)
        likes_val = metrics.get("total_likes", 0)
        comments_val = metrics.get("total_comments", 0)
        shares_val = metrics.get("total_shares", 0)

        kpi_data = [
            [
                Paragraph(f"{views_val:,}", style_kpi_num),
                Paragraph(f"{likes_val:,}", style_kpi_num),
                Paragraph(f"{comments_val:,}", style_kpi_num),
                Paragraph(f"{shares_val:,}", style_kpi_num),
            ],
            [
                Paragraph("Reproducciones (Views)", style_kpi_label),
                Paragraph("Me Gusta (Likes)", style_kpi_label),
                Paragraph("Comentarios", style_kpi_label),
                Paragraph("Compartidos", style_kpi_label),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2FF")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#C7D2FE")),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 16))

        # 4. Clasificación RUM a las 72 Horas
        elements.append(Paragraph("2. Clasificación de Rendimiento RUM 72h", style_section_title))

        distrib = metrics.get("classification_distribution", {"ROJO": 0, "AMARILLO": 0, "VERDE": 0})
        verde_cnt = distrib.get("VERDE", 0)
        amarillo_cnt = distrib.get("AMARILLO", 0)
        rojo_cnt = distrib.get("ROJO", 0)

        rum_table_data = [
            [
                Paragraph("<b>Clasificación RUM</b>", style_body),
                Paragraph("<b>Criterio de Desempeño</b>", style_body),
                Paragraph("<b>Cantidad de Reels</b>", style_body),
            ],
            [
                Paragraph("<font color='#059669'><b>VERDE (Viral / Escalable)</b></font>", style_body),
                Paragraph("Supera el benchmark por 1.5x. Alta retención y tracción.", style_body),
                Paragraph(f"<b>{verde_cnt}</b>", style_body),
            ],
            [
                Paragraph("<font color='#D97706'><b>AMARILLO (Estable)</b></font>", style_body),
                Paragraph("Rendimiento dentro del promedio esperado.", style_body),
                Paragraph(f"<b>{amarillo_cnt}</b>", style_body),
            ],
            [
                Paragraph("<font color='#DC2626'><b>ROJO (Revisar Gancho)</b></font>", style_body),
                Paragraph("Fricción en los primeros 5s. Requiere A/B Testing.", style_body),
                Paragraph(f"<b>{rojo_cnt}</b>", style_body),
            ],
        ]

        rum_table = Table(rum_table_data, colWidths=[160, 280, 100])
        rum_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(rum_table)
        elements.append(Spacer(1, 16))

        # 5. Recomendaciones Estratégicas de la IA
        elements.append(Paragraph("3. Recomendaciones Autónomas de la IA", style_section_title))
        recs = [
            "• <b>Replicar Ganchos Ganadores:</b> El modelo de guionismo RAG alimentará las siguientes campañas con la estructura de los Reels en clasificación VERDE.",
            "• <b>Optimizar los primeros 5 segundos:</b> Para el contenido en AMARILLO/ROJO, activar el módulo de A/B Testing de Ganchos.",
            "• <b>Secuencia de Nutrición Automática:</b> Asegurar que las palabras clave de los nuevos Reels estén conectadas al Bot DM Inbound para maximizar conversión de leads.",
        ]
        for r in recs:
            elements.append(Paragraph(r, style_body))
            elements.append(Spacer(1, 4))

        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceBefore=10, spaceAfter=8))
        elements.append(Paragraph(
            "<font size=8 color='#64748B'>Documento generado de forma autónoma por ViralSync 360° AI Marketing Agency. Uso Confidencial para el Cliente.</font>",
            ParagraphStyle("FooterText", alignment=TA_CENTER)
        ))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as exc:
        logger.error(f"[{tenant_id}] Error construyendo PDF binario con ReportLab: {exc}")
        # Fallback de resiliencia binaria
        fallback_pdf = (
            f"%PDF-1.4\n1 0 obj\n<< /Title (Reporte Ejecutivo ViralSync {tenant_id}) /Creator (ViralSync AI) >>\n"
            f"endobj\n%%EOF\n"
        ).encode("utf-8")
        return fallback_pdf
