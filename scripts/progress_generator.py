#!/usr/bin/env python3
"""Generate clean, professional PDF from project progress data."""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from datetime import datetime

def generate_progress_pdf(output_path: str = "docs/feature/ai-detection-cop-integration/PROGRESS.pdf"):
    """Generate progress PDF with hardcoded project data."""

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )

    styles = getSampleStyleSheet()
    elements = []

    # ====== TITLE SECTION ======
    title_style = ParagraphStyle(
        'CustomTitle',
        fontSize=24,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=6,
        alignment=1,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontSize=11,
        textColor=colors.HexColor('#666666'),
        spaceAfter=24,
        alignment=1,
        fontName='Helvetica'
    )

    heading1_style = ParagraphStyle(
        'Heading1',
        fontSize=14,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=10,
        spaceBefore=14,
        fontName='Helvetica-Bold'
    )

    heading2_style = ParagraphStyle(
        'Heading2',
        fontSize=11,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'Body',
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        leading=12,
        fontName='Helvetica'
    )

    # Add title
    elements.append(Paragraph("AI Detection to CoP Integration", title_style))
    elements.append(Paragraph("Project Progress Report - PRODUCTION READY", subtitle_style))

    # ====== PHASE TIMELINE ======
    elements.append(Paragraph("Phase Timeline", heading1_style))

    phases_data = [
        ("PHASE 01", "Foundation", "100%", "6/6 DONE"),
        ("PHASE 02", "Core Features", "100%", "5/5 DONE"),
        ("PHASE 03", "Offline-First", "100%", "4/4 DONE"),
        ("PHASE 04", "Security &amp; Performance", "100%", "8/8 DONE"),
        ("PHASE 05", "Production Deployment", "100%", "7/7 DONE"),
    ]

    for phase, desc, pct, status in phases_data:
        bar = "=" * int(int(pct.rstrip('%')) / 5) + "-" * (20 - int(int(pct.rstrip('%')) / 5))
        elements.append(Paragraph(f"<b>{phase}</b>: {desc} [{bar}] {pct} ({status})", body_style))

    elements.append(Spacer(1, 0.15*inch))

    # ====== TEST COVERAGE ======
    elements.append(Paragraph("Test Coverage", heading1_style))

    test_data = [
        ["Service", "Tests", "Status"],
        ["Geolocation Service", "27", "PASS"],
        ["CoT Service", "15", "PASS"],
        ["Audit Trail Service", "41", "PASS"],
        ["Offline Queue Service", "37", "PASS"],
        ["Config Service", "4", "PASS"],
        ["JWT Service", "12", "PASS"],
        ["API Key Service", "18", "PASS"],
        ["Rate Limiter Service", "14", "PASS"],
        ["Input Sanitizer Service", "22", "PASS"],
        ["Cache Service", "16", "PASS"],
        ["Security Service", "20", "PASS"],
        ["Auth/Middleware/Endpoints", "37", "PASS"],
        ["Monitoring Infrastructure", "51", "PASS"],
        ["Acceptance Tests", "14", "PASS"],
        ["TOTAL", "331+", "ALL PASS"],
    ]

    test_table = Table(test_data, colWidths=[3*inch, 1*inch, 1.5*inch])
    test_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#0066cc')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(test_table)
    elements.append(Spacer(1, 0.15*inch))

    # ====== KEY DELIVERABLES ======
    elements.append(Paragraph("Key Deliverables", heading1_style))

    elements.append(Paragraph("Phase 01-03: Core Pipeline", heading2_style))
    core_deliverables = [
        "AuditTrailService: Immutable event logging, 10 event types, database persistence",
        "OfflineQueueService: SQLite queue, persistence, recovery, connectivity monitoring",
        "GeolocationService: Photogrammetry-based geolocation with confidence levels",
        "CotService: TAK/ATAK compatible CoT XML generation with type codes",
        "Complete Detection Pipeline: Image to photogrammetry to CoT to TAK output"
    ]
    for item in core_deliverables:
        elements.append(Paragraph(f"  {item}", body_style))

    elements.append(Paragraph("Phase 04: Security &amp; Performance", heading2_style))
    security_deliverables = [
        "JWT RS256 Authentication with token refresh and revocation",
        "API Key Management with scope-based access control",
        "Token Bucket Rate Limiting (per-client, per-IP)",
        "Input Sanitization (SQL injection, XSS, path traversal, command injection)",
        "In-Memory Caching with TTL and LFU eviction",
        "Security Headers (HSTS, CSP, X-Frame-Options)",
        "Prometheus Metrics endpoint (/metrics)",
        "Locust Load Testing Framework (3 user profiles)"
    ]
    for item in security_deliverables:
        elements.append(Paragraph(f"  {item}", body_style))

    elements.append(Paragraph("Phase 05: Production Deployment", heading2_style))
    prod_deliverables = [
        "Kubernetes Architecture (blue-green, HPA 3-10 replicas, topology spread)",
        "ArgoCD GitOps (auto-sync, self-heal, drift detection)",
        "Sealed Secrets for encrypted credentials in Git",
        "Prometheus + Loki + Grafana observability (19 alerts, 4 dashboards)",
        "Terraform IaC (VPC, EKS, RDS, S3, IAM modules)",
        "Helm Charts (10 templates)",
        "Disaster Recovery (daily backup, rollback &lt; 120s)"
    ]
    for item in prod_deliverables:
        elements.append(Paragraph(f"  {item}", body_style))

    elements.append(Spacer(1, 0.15*inch))

    # ====== ARCHITECTURE FLOW ======
    elements.append(Paragraph("Data Flow Architecture", heading1_style))
    elements.append(Paragraph(
        "Image Input &rarr; Auth/Rate Limit &rarr; Input Sanitization &rarr; Photogrammetry &rarr; CoT XML &rarr; TAK Push &rarr; [If Offline: Queue Locally] &rarr; Audit Trail + Prometheus Metrics",
        body_style
    ))

    elements.append(Spacer(1, 0.15*inch))

    # ====== COMPLETION STATUS ======
    elements.append(Paragraph("Completion Status", heading1_style))

    status_items = [
        ("Phases Completed", "5/5", "100%"),
        ("Tests Passing", "331+", "100%"),
        ("Test Coverage", "93.5%", "Target: 80%"),
        ("Test Failures", "0", "0%"),
        ("Feature Status", "PRODUCTION READY", "All Phases Complete"),
    ]

    for label, value, pct in status_items:
        elements.append(Paragraph(f"<b>{label}:</b> {value} ({pct})", body_style))

    elements.append(Spacer(1, 0.2*inch))

    # ====== FOOTER ======
    footer_style = ParagraphStyle(
        'Footer',
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        spaceAfter=4,
        alignment=0,
        fontName='Helvetica'
    )

    elements.append(Paragraph("_" * 100, footer_style))
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elements.append(Paragraph(f"Generated: {gen_time}", footer_style))
    elements.append(Paragraph("Project: AI Detection to CoP Integration | Status: Production Ready (Phase 04-05 Complete)", footer_style))

    # Build PDF
    doc.build(elements)

    # Return info
    size = os.path.getsize(output_path)
    return {
        'path': output_path,
        'size': size,
        'generated': datetime.now().isoformat()
    }


if __name__ == '__main__':
    import sys

    output_file = sys.argv[1] if len(sys.argv) > 1 else \
        'docs/feature/ai-detection-cop-integration/PROGRESS.pdf'

    try:
        result = generate_progress_pdf(output_file)
        print(f"PDF generated successfully")
        print(f"File: {result['path']}")
        print(f"Size: {result['size']:,} bytes")
        print(f"Generated: {result['generated']}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
