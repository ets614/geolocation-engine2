#!/usr/bin/env python3
"""Generate PDF from PROGRESS.md - called automatically after updates."""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime

def generate_pdf(markdown_path: str, output_path: str = "/tmp/AI_Detection_CoP_Progress.pdf"):
    """Generate PDF from PROGRESS.md."""

    # Read markdown
    with open(markdown_path, 'r') as f:
        content = f.read()

    # Create PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=20,
        alignment=1  # center
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=10,
        spaceBefore=10
    )

    normal_style = styles['Normal']

    # Build document
    elements = []

    # Parse content
    in_code_block = False
    code_lines = []

    for line in content.split('\n'):
        # Handle code blocks
        if line.startswith('```'):
            if in_code_block:
                # End code block
                code_text = '\n'.join(code_lines).strip()
                code_style = ParagraphStyle(
                    'Code',
                    fontName='Courier',
                    fontSize=7,
                    textColor=colors.HexColor('#333'),
                    backColor=colors.HexColor('#f5f5f5'),
                    leftIndent=10,
                    rightIndent=10,
                    spaceAfter=10
                )
                if code_text:
                    elements.append(Paragraph(f"<pre>{code_text}</pre>", code_style))
                elements.append(Spacer(1, 0.1*inch))
                in_code_block = False
                code_lines = []
            else:
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Handle headings
        if line.startswith('# '):
            title = line.replace('# ', '').replace('🎯 ', '').replace('✨ ', '')
            elements.append(Paragraph(title, title_style))
            elements.append(Spacer(1, 0.2*inch))

        elif line.startswith('## '):
            heading = line.replace('## ', '').replace('📊 ', '').replace('🏗 ', '').replace('🎁 ', '').replace('📈 ', '').replace('✨ ', '').replace('🚀 ', '')
            elements.append(Paragraph(heading, heading_style))
            elements.append(Spacer(1, 0.1*inch))

        elif line.strip() and not line.startswith('|'):
            elements.append(Paragraph(line.strip(), normal_style))

        elif line.startswith('|'):
            # Skip table markers - too complex to parse
            pass

    # Add footer
    elements.append(Spacer(1, 0.3*inch))
    footer_text = (
        f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
        f"<b>Project:</b> AI Detection to CoP Integration<br/>"
        f"<b>Status:</b> Feature Complete ✅"
    )
    elements.append(Paragraph(footer_text, normal_style))

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
        '/tmp/AI_Detection_CoP_Progress.pdf'

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
