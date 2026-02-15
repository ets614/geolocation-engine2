#!/usr/bin/env python3
"""Generate PDF from PROGRESS.md - called automatically after updates."""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime

def generate_pdf(markdown_path: str, output_path: str = "docs/feature/ai-detection-cop-integration/PROGRESS.pdf"):
    """Generate clean PDF from PROGRESS.md."""

    # Read markdown
    with open(markdown_path, 'r') as f:
        lines = f.readlines()

    # Create PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.6*inch,
        bottomMargin=0.6*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )

    # Define styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=6,
        alignment=1
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666'),
        alignment=1,
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=8,
        spaceBefore=12,
        textTransform='uppercase',
        fontSize_adjust=0.8
    )

    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        spaceAfter=4
    )

    # Build elements
    elements = []
    skip_next = False
    in_code = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        line = line.rstrip()

        # Skip empty lines at start
        if not elements and not line:
            continue

        # Handle title
        if line.startswith('# 🎯'):
            title = line.replace('# 🎯 ', '').strip()
            elements.append(Paragraph(title, title_style))
            continue

        if line.startswith('## '):
            heading = line.replace('## ', '').replace('📊 ', '').replace('🏗 ', '').replace('🎁 ', '').replace('📈 ', '').replace('✨ ', '').replace('🚀 ', '').strip()
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(heading, heading_style))
            elements.append(Spacer(1, 0.05*inch))
            continue

        # Handle code blocks (convert to readable text)
        if line.strip().startswith('```'):
            in_code = not in_code
            if not in_code:
                elements.append(Spacer(1, 0.08*inch))
            continue

        if in_code:
            # Add code line as preformatted text
            code_style = ParagraphStyle('Code', fontName='Courier', fontSize=7,
                                       textColor=colors.HexColor('#444'),
                                       leftIndent=20, rightIndent=20)
            elements.append(Paragraph(line or '&nbsp;', code_style))
            continue

        # Handle regular lines
        if line.strip():
            # Skip table lines
            if line.startswith('|'):
                continue

            # Clean up emojis and markdown
            clean_line = line
            for emoji in ['🎯', '📊', '🏗', '🎁', '📈', '✨', '🚀', '✅', '⏳', '⏭', '📄', '📱', '📋', '⏰', '🧪', '🎨', '🔄']:
                clean_line = clean_line.replace(emoji, '')

            clean_line = clean_line.strip()

            if clean_line and not clean_line.startswith('-') and not clean_line.startswith('='):
                elements.append(Paragraph(clean_line, normal_style))

    # Add footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph('_' * 80, styles['Normal']))
    footer_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elements.append(Paragraph(f"<b>Generated:</b> {footer_time}", normal_style))
    elements.append(Paragraph("<b>Project:</b> AI Detection to CoP Integration", normal_style))
    elements.append(Paragraph("<b>Status:</b> Feature Complete", normal_style))

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

    markdown_file = sys.argv[1] if len(sys.argv) > 1 else \
        'docs/feature/ai-detection-cop-integration/PROGRESS.md'

    output_file = sys.argv[2] if len(sys.argv) > 2 else \
        'docs/feature/ai-detection-cop-integration/PROGRESS.pdf'

    try:
        result = generate_pdf(markdown_file, output_file)
        print(f"✅ PDF generated successfully")
        print(f"📄 File: {result['path']}")
        print(f"📊 Size: {result['size']:,} bytes")
        print(f"⏰ Generated: {result['generated']}")
    except FileNotFoundError:
        print(f"❌ Error: Could not find {markdown_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        sys.exit(1)
