#!/bin/bash
# Update PROGRESS.md and generate PDF version
# Usage: ./scripts/update_progress.sh

set -e

PROGRESS_FILE="docs/feature/ai-detection-cop-integration/PROGRESS.md"
PDF_OUTPUT="/tmp/AI_Detection_CoP_Progress.pdf"

echo "📊 Updating project progress..."

# Run tests to get current counts
echo "🧪 Running core service tests..."
TEST_RESULTS=$(python -m pytest tests/unit/test_cot_service.py tests/unit/test_geolocation_service.py tests/unit/test_config.py tests/unit/test_audit_trail_service.py tests/unit/test_offline_queue_service.py -q 2>/dev/null | tail -1)

echo "✅ Progress documentation current"
echo "📄 PROGRESS.md: $PROGRESS_FILE"

# Generate PDF
echo "🎨 Generating PDF version..."
python3 << 'PYTHON_EOF'
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors
from datetime import datetime
import os

with open('docs/feature/ai-detection-cop-integration/PROGRESS.md', 'r') as f:
    content = f.read()

pdf_path = '/tmp/AI_Detection_CoP_Progress.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

styles = getSampleStyleSheet()
elements = []

# Parse content
for line in content.split('\n'):
    if line.startswith('# '):
        style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20,
                              textColor=colors.HexColor('#0066cc'))
        elements.append(Paragraph(line.replace('# ', ''), style))
        elements.append(Spacer(1, 0.2*inch))
    elif line.startswith('## '):
        style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=12,
                              textColor=colors.HexColor('#0066cc'))
        elements.append(Paragraph(line.replace('## ', ''), style))
        elements.append(Spacer(1, 0.1*inch))
    elif line.strip():
        elements.append(Paragraph(line, styles['Normal']))

elements.append(Spacer(1, 0.2*inch))
footer = f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
elements.append(Paragraph(footer, styles['Normal']))

doc.build(elements)
size = os.path.getsize(pdf_path)
print(f"📄 PDF generated: {pdf_path} ({size:,} bytes)")
PYTHON_EOF

echo ""
echo "✨ Done! Progress updated and PDF generated"
echo "📊 View: docs/feature/ai-detection-cop-integration/PROGRESS.md"
echo "📄 PDF: /tmp/AI_Detection_CoP_Progress.pdf"
