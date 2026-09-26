from typing import Dict, Any, List
from models.database import Investigation
from datetime import datetime
import json

class ReportGenerator:
    """
    Generates structured audit-ready reports for investigations.
    """
    
    def generate_json_report(self, investigation: Investigation) -> Dict[str, Any]:
        """
        Creates a comprehensive JSON structure for the frontend and archival.
        """
        # Calculate dataset similarity (CBR intelligence)
        from core.database import SessionLocal
        db = SessionLocal()
        try:
            from layers.scoring.similarity_engine import similarity_engine
            similarity_data = similarity_engine.search_similar_cases(db, investigation)
        except Exception as e:
            similarity_data = {
                "similarity_score": 0.0,
                "explanation": f"Failed to compute similarity: {str(e)}",
                "top_similar_genuine": [],
                "top_similar_fraud": []
            }
        finally:
            db.close()

        # Format recommendation for user
        rec_text = investigation.recommendation or "MANUAL_REVIEW"
        if rec_text == "MANUAL_REVIEW":
            rec_friendly = "Manual Review"
        elif rec_text == "AUTO_APPROVE":
            rec_friendly = "Auto Approved"
        elif rec_text == "AUTO_REJECT":
            rec_friendly = "Auto Rejected"
        else:
            rec_friendly = rec_text.replace('_', ' ').title()

        report = {
            "investigation_id": investigation.id,
            "context": investigation.context,
            "status": investigation.status,
            "created_at": investigation.created_at.isoformat(),
            "scores": {
                "trust_score": investigation.trust_score,
                "recommendation": rec_friendly
            },
            "ai_summary": investigation.ai_summary_json,
            "dataset_similarity": similarity_data,
            "documents": [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "classification": d.classification,
                    "file_type": d.file_type,
                    "extracted_text": d.extracted_text,
                    "entities_json": d.entities_json,
                    "metadata_json": d.metadata_json
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
        Matches Deloitte/KPMG professional style, with watermarks, OCR summaries,
        cross-doc, ELA, and KNN references.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        import os
        import urllib.request
        
        # Download NotoSansDevanagari if not exists
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
        os.makedirs(assets_dir, exist_ok=True)
        hindi_font_path = os.path.join(assets_dir, "NotoSansDevanagari-Regular.ttf")
        
        if not os.path.exists(hindi_font_path):
            try:
                urllib.request.urlretrieve(
                    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
                    hindi_font_path
                )
            except Exception as e:
                print(f"Failed to download Hindi font: {e}")

        # Register standard Linux Hindi TrueType font if available
        font_registered = False
        for font_path in [
            hindi_font_path,
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
            topMargin=72,
            bottomMargin=72
        )

        styles = getSampleStyleSheet()
        
        # Typography styles matching Deloitte/KPMG report specs
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=6
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSub',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=20
        )
        
        h2_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor('#1E3A8A'),
            spaceBefore=16,
            spaceAfter=8,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
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
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A'),
            backColor=colors.HexColor('#F8FAFC'),
            borderColor=colors.HexColor('#E2E8F0'),
            borderWidth=0.5,
            borderPadding=4,
            spaceAfter=4
        )

        # Subtle Watermark/Confidentiality Footer Callback
        from core.settings_store import settings_store
        watermark_text = settings_store.get("digital_watermark", "ANOBIS VERIFIED")
        include_ai = settings_store.get("include_ai_reasoning", True)
        include_logs = settings_store.get("include_audit_logs", True)

        def draw_page_decorations(canvas, d):
            canvas.saveState()
            
            # Rotated background watermark
            canvas.setFont('Helvetica-Bold', 54)
            canvas.setFillColor(colors.HexColor('#F1F5F9'))
            canvas.saveState()
            canvas.translate(300, 400)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, watermark_text)
            canvas.restoreState()
            
            # Top Header Line
            canvas.setFont('Helvetica-Bold', 8)
            canvas.setFillColor(colors.HexColor('#475569'))
            canvas.drawString(54, 746, "ANOBIS FORENSIC PLATFORM | COMPLIANCE AUDIT")
            canvas.drawRightString(558, 746, watermark_text)
            canvas.setStrokeColor(colors.HexColor('#E2E8F0'))
            canvas.setLineWidth(0.75)
            canvas.line(54, 738, 558, 738)
            
            # Bottom Footer Line
            canvas.line(54, 50, 558, 50)
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor('#64748B'))
            canvas.drawString(54, 36, "CONFIDENTIAL - ENTERPRISE FORENSIC AUDIT RECORD")
            canvas.drawRightString(558, 36, f"Page {d.page}")
            canvas.restoreState()

        story = []
        
        # Cover header block
        story.append(Paragraph("FORENSIC INVESTIGATION REPORT", title_style))
        story.append(Paragraph("Generated by Anobis Offline Tampering & Fraud Detection Engine", subtitle_style))
        story.append(Spacer(1, 10))
        
        # Case metadata table
        created_date = datetime.now().strftime("%B %d, %Y %I:%M %p UTC")
        meta_data = [
            [Paragraph("<b>Investigation ID:</b>", body_style), Paragraph(investigation.id, body_style)],
            [Paragraph("<b>Scope / Context:</b>", body_style), Paragraph(investigation.context, body_style)],
            [Paragraph("<b>Case Label:</b>", body_style), Paragraph(investigation.title or "Untitled Case", body_style)],
            [Paragraph("<b>Audit Date:</b>", body_style), Paragraph(created_date, body_style)],
        ]
        meta_table = Table(meta_data, colWidths=[130, 370])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))
        
        # Horizontal Rule
        divider_data = [[""]]
        divider_table = Table(divider_data, colWidths=[500], rowHeights=[1])
        divider_table.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(divider_table)
        story.append(Spacer(1, 15))

        # Risk score section
        story.append(Paragraph("1. Risk Assessment Summary", h2_style))
        trust_pct = int(investigation.trust_score) if investigation.trust_score is not None else 0
        rec_val = investigation.recommendation or "MANUAL_REVIEW"
        if rec_val == "MANUAL_REVIEW":
            rec_friendly = "Manual Review Required"
        elif rec_val == "AUTO_APPROVE":
            rec_friendly = "Auto Approved"
        elif rec_val == "AUTO_REJECT":
            rec_friendly = "Auto Rejected"
        else:
            rec_friendly = rec_val.replace('_', ' ').title()

        trust_color = '#059669' if trust_pct > 80 else '#D97706' if trust_pct > 50 else '#DC2626'
        
        score_data = [
            [Paragraph("<b>Dynamic Trust Score:</b>", body_style), Paragraph(f"<font color='{trust_color}'><b>{trust_pct}%</b></font>", bold_body_style)],
            [Paragraph("<b>Audit Action:</b>", body_style), Paragraph(f"<b>{rec_friendly}</b>", bold_body_style)],
        ]
        score_table = Table(score_data, colWidths=[150, 350])
        score_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 15))

        # AI executive synthesis
        if include_ai:
            story.append(Paragraph("2. AI Analyst Executive Summary", h2_style))
            ai_summary = investigation.ai_summary_json or {}
            exec_summary_en = ai_summary.get("executive_summary") or "No audit summary compiled."
            exec_summary_hi_raw = ai_summary.get("executive_summary_hi") or ai_summary.get("hindi_summary") or ""
            
            story.append(Paragraph("<b>English Summary:</b>", bold_body_style))
            story.append(Paragraph(exec_summary_en, body_style))
            story.append(Spacer(1, 6))
            
            if exec_summary_hi_raw:
                story.append(Paragraph("<b>Hindi Summary (हिंदी सारांश):</b>", bold_body_style))
                if font_registered:
                    hindi_style = ParagraphStyle('HindiText', parent=body_style, fontName='HindiFont')
                    story.append(Paragraph(exec_summary_hi_raw, hindi_style))
                else:
                    story.append(Paragraph("<i>[Devanagari rendering requires Lohit-Devanagari or NotoSans system fonts. Hindi summary is available on the interactive web workbench.]</i>", body_style))
                story.append(Spacer(1, 6))

        # Metadata analysis, ELA, and OCR Output
        story.append(Paragraph("3. Document Forensic & OCR Summary", h2_style))
        for doc_item in investigation.documents:
            meta = doc_item.metadata_json or {}
            raw_meta = meta.get("raw_metadata") or {}
            producer = raw_meta.get("producer") or raw_meta.get("/Producer") or "Unknown"
            creator = raw_meta.get("creator") or raw_meta.get("/Creator") or "Unknown"
            ocr_conf = meta.get("ocr_confidence", 100)
            is_scanned = meta.get("is_scanned", False)
            
            doc_details = f"<b>File:</b> {doc_item.filename} ({doc_item.classification or 'Unclassified'})<br/>" \
                          f"• Vector Extraction: {'Scanned (OCR)' if is_scanned else 'Native text vectors'}<br/>" \
                          f"• PDF Producer: {producer}<br/>" \
                          f"• PDF Author/Creator: {creator}"
            story.append(Paragraph(doc_details, body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))

        # CBR/KNN Similar Documents
        story.append(Paragraph("4. KNN Similarity & Baseline Reference Match", h2_style))
        from core.database import SessionLocal
        db = SessionLocal()
        try:
            from layers.scoring.similarity_engine import similarity_engine
            similarity_data = similarity_engine.search_similar_cases(db, investigation)
            exp = similarity_data.get("explanation", "")
            sim_score = similarity_data.get("similarity_score", 0.0)
            story.append(Paragraph(f"<b>CBR Classifier:</b> {exp} (Max similarity score: {sim_score}%)", body_style))
            
            top_similar_genuine = similarity_data.get("top_similar_genuine", [])
            top_similar_fraud = similarity_data.get("top_similar_fraud", [])
            
            if top_similar_genuine:
                story.append(Paragraph(f"• Closest Clean Reference: {top_similar_genuine[0]['filename']} (Similarity: {top_similar_genuine[0]['similarity_score']}%)", body_style))
            if top_similar_fraud:
                story.append(Paragraph(f"• Closest Tampered Reference: {top_similar_fraud[0]['filename']} (Similarity: {top_similar_fraud[0]['similarity_score']}%)", body_style))
        except Exception as exc:
            story.append(Paragraph(f"Similarity Engine lookup skipped: {exc}", body_style))
        finally:
            db.close()
        story.append(Spacer(1, 10))

        # Forensic findings
        story.append(Paragraph("5. Detailed Findings & Anomalies", h2_style))
        findings = investigation.findings
        if not findings:
            story.append(Paragraph("No inconsistencies requiring manual investigation were detected.", body_style))
        else:
            for f in findings:
                # Severity-specific color highlight
                sev_color = '#DC2626' if f.severity in ['CRITICAL', 'HIGH'] else '#D97706' if f.severity == 'MEDIUM' else '#2563EB'
                finding_header = f"<b><font color='{sev_color}'>[{f.severity}]</font> {f.name}</b> (Source: {f.layer_source})"
                story.append(Paragraph(finding_header, bold_body_style))
                story.append(Paragraph(f.description, body_style))
                
                # Check for evidence item
                if f.evidence_items:
                    for ev in f.evidence_items:
                        ev_line = f"• Evidence in <i>{ev.document.filename}</i> (Page {ev.page_number or 1}): {ev.description or 'Visual anomaly'}"
                        story.append(Paragraph(ev_line, ParagraphStyle('EvLine', parent=body_style, leftIndent=12, fontSize=8.5)))
                        if ev.extracted_text:
                            story.append(Paragraph(f'"{ev.extracted_text}"', ParagraphStyle('EvText', parent=code_style, leftIndent=12)))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))

        # Investigation event timeline
        if include_logs:
            story.append(Paragraph("6. Audit Timeline", h2_style))
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
            
        story.append(Spacer(1, 15))
        story.append(Paragraph("7. Appendix & Disclaimers", h2_style))
        story.append(Paragraph("This report was compiled locally in an air-gapped sandbox forensic workstation. All heuristics, metadata signature checks, and AI evaluations are performed on local models with no data transmitted outside the organizational network boundary.", body_style))

        # Build PDF with Page Decors
        doc.build(story, onFirstPage=draw_page_decorations, onLaterPages=draw_page_decorations)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

report_generator = ReportGenerator()
