import io
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import structlog

logger = structlog.get_logger()


class SituationReporter:
    """PDF Compiler compiling metereological and operational checks into a downloadable SitRep."""

    def compile_report(
        self,
        district_name: str,
        forecast_rain: float,
        warning_level: str,
        risk_score: float,
        sop_actions: List[str],
        officer_name: str
    ) -> bytes:
        """Generates a formatted binary PDF document in memory."""
        logger.info("Compiling situation report PDF", district=district_name, score=risk_score)
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
        
        styles = getSampleStyleSheet()
        
        # Define Custom Color Palette (vibrant / harmonized colors)
        primary_color = colors.HexColor("#0D3B66")
        accent_color = colors.HexColor("#F4D35E")
        text_color = colors.HexColor("#333333")
        
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=primary_color,
            spaceAfter=15
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=primary_color,
            spaceBefore=15,
            spaceAfter=10
        )
        
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            textColor=text_color
        )

        story = []
        
        # Title
        story.append(Paragraph(f"WEATHER SITUATION REPORT - {district_name.upper()}", title_style))
        story.append(Spacer(1, 10))
        
        # Meta metadata table
        meta_data = [
            [Paragraph("<b>Date Generated:</b>", body_style), Paragraph(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), body_style)],
            [Paragraph("<b>Prepared By:</b>", body_style), Paragraph(officer_name, body_style)],
            [Paragraph("<b>Status:</b>", body_style), Paragraph("OFFICIAL / EMERGENCY USE ONLY", body_style)]
        ]
        t_meta = Table(meta_data, colWidths=[120, 300])
        t_meta.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8F9FA"))
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 20))
        
        # Weather Summary
        story.append(Paragraph("1. Meteorological Forecast Summary", section_style))
        weather_summary = (
            f"Official meteorological updates indicate that {district_name} district has a forecasted rainfall "
            f"total of <b>{forecast_rain} mm</b>. Based on active warnings, the India Meteorological Department "
            f"has placed the district under a <b>{warning_level.upper()}</b> warning alert."
        )
        story.append(Paragraph(weather_summary, body_style))
        story.append(Spacer(1, 15))
        
        # Risk evaluation metrics table
        story.append(Paragraph("2. Hazard Risk Evaluation", section_style))
        risk_level = "CRITICAL" if risk_score >= 0.75 else ("ELEVATED" if risk_score >= 0.50 else "NORMAL")
        
        metrics_data = [
            [Paragraph("<b>Vulnerability Indicator</b>", body_style), Paragraph("<b>Value / Score</b>", body_style)],
            [Paragraph("Forecast Rainfall Volume", body_style), Paragraph(f"{forecast_rain} mm", body_style)],
            [Paragraph("Calculated Flood Risk Score", body_style), Paragraph(f"{risk_score}", body_style)],
            [Paragraph("Emergency Warning Class", body_style), Paragraph(risk_level, body_style)]
        ]
        t_metrics = Table(metrics_data, colWidths=[200, 220])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")])
        ]))
        story.append(t_metrics)
        story.append(Spacer(1, 20))
        
        # SOP Action checklist
        story.append(Paragraph("3. Recommended Emergency SOP Actions", section_style))
        for index, action in enumerate(sop_actions, 1):
            story.append(Paragraph(f"<b>[ ] {index}.</b> {action}", body_style))
            story.append(Spacer(1, 8))
            
        story.append(Spacer(1, 30))
        
        # Disclaimer footer
        disclaimer_style = ParagraphStyle(
            'DisclaimerText',
            parent=body_style,
            fontSize=8,
            leading=10,
            textColor=colors.gray
        )
        story.append(Paragraph(
            "<b>Disclaimer:</b> This document was generated automatically by Project Varun based on forecast data "
            "provided by official sources. Local disaster management officers must verify recommendations in "
            "coordination with relevant field units.",
            disclaimer_style
        ))
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info("PDF situation report compiled successfully", size_bytes=len(pdf_bytes))
        return pdf_bytes
