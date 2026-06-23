from typing import Dict, Any, List
from models.database import Investigation
import json

class ReportGenerator:
    """
    Generates structured audit-ready reports for investigations.
    """
    
    def generate_json_report(self, investigation: Investigation) -> Dict[str, Any]:
        """
        Creates a comprehensive JSON structure for the frontend and archival.
        """
        report = {
            "investigation_id": investigation.id,
            "context": investigation.context,
            "status": investigation.status,
            "created_at": investigation.created_at.isoformat(),
            "scores": {
                "trust_score": investigation.trust_score,
                "confidence_score": investigation.confidence_score,
                "recommendation": investigation.recommendation
            },
            "ai_summary": investigation.ai_summary_json,
            "documents": [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "classification": d.classification,
                    "file_type": d.file_type
                } for d in investigation.documents
            ],
            "findings": [
                {
                    "id": f.id,
                    "name": f.name,
                    "severity": f.severity,
                    "description": f.description,
                    "layer_source": f.layer_source,
                    "evidence": [
                        {
                            "document": e.document.filename,
                            "document_id": e.document_id,
                            "page": e.page_number,
                            "text": e.extracted_text,
                            "description": e.description,
                            "coordinates": e.coordinates
                        } for e in f.evidence_items
                    ]
                } for f in investigation.findings
            ],
            "timeline": [
                {
                    "timestamp": ev.timestamp.isoformat(),
                    "type": ev.event_type,
                    "message": ev.message
                } for ev in investigation.events
            ]
        }
        return report

    def generate_pdf_report(self, investigation: Investigation) -> bytes:
        """
        Generates a comprehensive forensic PDF report using ReportLab.
        Supports dual translations, scores, findings, evidence, and logs.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        import os

        # Register standard Linux Hindi TrueType font if available
        font_registered = False
        for font_path in [
            "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('HindiFont', font_path))
                    font_registered = True
                    break
                except:
                    pass

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()
        
        # Customized report formatting
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=15
        )
        
        h2_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1E3A8A'),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#334155'),
            spaceAfter=6
        )
        
        bold_body_style = ParagraphStyle(
            'BoldBodyTextCustom',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        code_style = ParagraphStyle(
            'CodeStyle',
            parent=styles['Code'],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#475569'),
            backColor=colors.HexColor('#F8FAFC'),
            borderColor=colors.HexColor('#E2E8F0'),
            borderWidth=0.5,
            borderPadding=5,
            spaceAfter=6
        )

        story = []
        
        # Header / Title Block
        story.append(Paragraph("Anobis Forensic Investigation Audit Report", title_style))
        story.append(Spacer(1, 10))
        
        # Case metadata mapping
        created_date = investigation.created_at.strftime("%B %d, %Y %I:%M %p UTC")
        meta_data = [
            [Paragraph("<b>Investigation ID:</b>", body_style), Paragraph(investigation.id, body_style)],
            [Paragraph("<b>Case Title:</b>", body_style), Paragraph(investigation.title or "Untitled Case", body_style)],
            [Paragraph("<b>Investigation Context:</b>", body_style), Paragraph(investigation.context, body_style)],
            [Paragraph("<b>Generated Time:</b>", body_style), Paragraph(created_date, body_style)],
        ]
        meta_table = Table(meta_data, colWidths=[130, 370])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 12))
        
        # Divider
        divider_data = [[""]]
        divider_table = Table(divider_data, colWidths=[500], rowHeights=[1])
        divider_table.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(divider_table)
        story.append(Spacer(1, 10))

        # Risk assessment scores
        story.append(Paragraph("Executive Risk Assessment & Scores", h2_style))
        trust_pct = int(investigation.trust_score * 100) if investigation.trust_score is not None else 0
        conf_pct = int(investigation.confidence_score * 100) if investigation.confidence_score is not None else 0
        rec_text = (investigation.recommendation or "MANUAL_REVIEW").replace('_', ' ')
        
        trust_color = '#059669' if trust_pct > 80 else '#D97706' if trust_pct > 50 else '#DC2626'
        
        score_data = [
            [Paragraph("<b>Final Trust Score:</b>", body_style), Paragraph(f"<font color='{trust_color}'><b>{trust_pct}%</b></font> (Deductions calculated dynamically)", bold_body_style)],
            [Paragraph("<b>Confidence Score:</b>", body_style), Paragraph(f"<b>{conf_pct}%</b> (Dynamic extraction density metrics)", bold_body_style)],
            [Paragraph("<b>Auditor Recommendation:</b>", body_style), Paragraph(f"<b>{rec_text}</b>", bold_body_style)],
        ]
        score_table = Table(score_data, colWidths=[150, 350])
        score_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 12))

        # AI synthesis summaries
        ai_summary = investigation.ai_summary_json or {}
        exec_summary_en = ai_summary.get("executive_summary") or "No audit summary compiled."
        exec_summary_hi_raw = ai_summary.get("executive_summary_hi") or ai_summary.get("hindi_summary") or ""
        reviewer_notes = ai_summary.get("reviewer_notes") or "No reviewer/auditor notes logged."
        
        story.append(Paragraph("English Analysis Summary", h2_style))
        story.append(Paragraph(exec_summary_en, body_style))
        story.append(Spacer(1, 6))
        
        # Configure Hindi summary with TrueType support
        if exec_summary_hi_raw:
            story.append(Paragraph("Hindi Analysis Summary (हिंदी सारांश)", h2_style))
            if font_registered:
                hindi_style = ParagraphStyle('HindiText', parent=body_style, fontName='HindiFont')
                story.append(Paragraph(exec_summary_hi_raw, hindi_style))
            else:
                story.append(Paragraph("<i>[Devanagari rendering requires Lohit-Devanagari or NotoSans system fonts. Please check the digital dashboard layout for translation text.]</i>", body_style))
            story.append(Spacer(1, 6))

        story.append(Paragraph("Reviewer Action Items", h2_style))
        story.append(Paragraph(reviewer_notes, body_style))
        story.append(Spacer(1, 12))

        # Forensic findings list
        story.append(Paragraph("Identified Findings & Discrepancies", h2_style))
        findings = investigation.findings
        if not findings:
            story.append(Paragraph("No critical forensic flags or identity mismatch findings detected across the document set.", body_style))
        else:
            for f in findings:
                finding_title = f"<b>• [{f.severity}] {f.name}</b> (Source: {f.layer_source})"
                story.append(Paragraph(finding_title, bold_body_style))
                story.append(Paragraph(f.description, body_style))
                
                if f.evidence_items:
                    for ev in f.evidence_items:
                        ev_meta = f"<i>Evidence</i>: {ev.document.filename} {f' (Page {ev.page_number})' if ev.page_number else ''} - {ev.description or ''}"
                        story.append(Paragraph(ev_meta, ParagraphStyle('EvStyle', parent=body_style, leftIndent=12, fontSize=8.5, leading=11)))
                        if ev.extracted_text:
                            story.append(Paragraph(f'"{ev.extracted_text}"', ParagraphStyle('EvText', parent=code_style, leftIndent=12)))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 12))

        # Log timeline
        story.append(Paragraph("Investigation Process Timeline", h2_style))
        events = investigation.events
        if not events:
            story.append(Paragraph("No activity events logged for this case.", body_style))
        else:
            timeline_data = []
            for ev in events:
                time_str = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                timeline_data.append([
                    Paragraph(f"<b>{time_str}</b>", body_style),
                    Paragraph(f"[{ev.event_type}] {ev.message}", body_style)
                ])
            timeline_table = Table(timeline_data, colWidths=[120, 380])
            timeline_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(timeline_table)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

report_generator = ReportGenerator()
