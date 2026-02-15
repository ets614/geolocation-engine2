#!/usr/bin/env python3
"""Render PROGRESS.md to beautiful PDF preserving markdown visual appearance."""

import os
import re
from markdown import markdown
from weasyprint import HTML, CSS
from datetime import datetime


def read_progress_markdown(file_path: str) -> str:
    """Read PROGRESS.md file."""
    with open(file_path, 'r') as f:
        return f.read()


def create_styled_html(markdown_content: str) -> str:
    """Convert markdown to HTML with professional CSS styling."""

    # Convert markdown to HTML
    html_content = markdown(markdown_content, extensions=['tables', 'codehilite', 'nl2br'])

    # Professional CSS matching IDE appearance
    css = """
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        line-height: 1.6;
        color: #24292e;
        background: white;
        padding: 40px;
        max-width: 960px;
        margin: 0 auto;
    }

    h1 {
        font-size: 28px;
        font-weight: 600;
        color: #0066cc;
        margin: 24px 0 16px;
        padding-bottom: 0.3em;
        border-bottom: 2px solid #e1e4e8;
        line-height: 1.25;
    }

    h2 {
        font-size: 21px;
        font-weight: 600;
        color: #0066cc;
        margin: 24px 0 16px;
        padding-bottom: 0.3em;
        border-bottom: 1px solid #e1e4e8;
        line-height: 1.25;
    }

    h3 {
        font-size: 16px;
        font-weight: 600;
        color: #24292e;
        margin: 16px 0 8px;
        line-height: 1.25;
    }

    p {
        margin-bottom: 16px;
        line-height: 1.6;
    }

    code {
        background-color: rgba(27, 31, 35, 0.05);
        border-radius: 3px;
        margin: 0;
        padding: 0.2em 0.4em;
        font-family: 'Courier New', monospace;
        font-size: 0.85em;
        color: #24292e;
    }

    pre {
        background-color: #f6f8fa;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 16px;
        margin: 16px 0;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.85em;
        line-height: 1.45;
    }

    pre code {
        background-color: transparent;
        border: none;
        padding: 0;
        margin: 0;
        color: #24292e;
    }

    table {
        border-collapse: collapse;
        width: 100%;
        margin: 16px 0;
    }

    table th {
        background-color: #f6f8fa;
        color: #24292e;
        padding: 12px;
        text-align: left;
        font-weight: 600;
        border: 1px solid #d1d5da;
    }

    table td {
        padding: 12px;
        border: 1px solid #d1d5da;
    }

    table tr:nth-child(even) {
        background-color: #f6f8fa;
    }

    ul, ol {
        margin: 0 0 16px 0;
        padding-left: 2em;
    }

    li {
        margin-bottom: 8px;
        line-height: 1.6;
    }

    blockquote {
        padding: 0 1em;
        color: #6a737d;
        border-left: 0.25em solid #dfe2e5;
        margin: 0 0 16px 0;
    }

    hr {
        background-color: #e1e4e8;
        border: 0;
        height: 2px;
        margin: 24px 0;
    }

    .footer {
        border-top: 1px solid #e1e4e8;
        margin-top: 48px;
        padding-top: 16px;
        font-size: 12px;
        color: #6a737d;
        text-align: center;
    }

    @page {
        size: letter;
        margin: 0.5in;
    }
    """

    # Wrap in HTML document
    html_document = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Detection to CoP Integration - Project Progress</title>
        <style>
            {css}
        </style>
    </head>
    <body>
        {html_content}
        <div class="footer">
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """

    return html_document


def render_progress_to_pdf(markdown_path: str, output_path: str = "docs/feature/ai-detection-cop-integration/PROGRESS.pdf"):
    """Convert PROGRESS.md to PDF using WeasyPrint."""

    content = read_progress_markdown(markdown_path)
    html_doc = create_styled_html(content)

    try:
        # Render to PDF
        HTML(string=html_doc).write_pdf(output_path)

        size = os.path.getsize(output_path)
        return {
            'path': output_path,
            'size': size,
            'generated': datetime.now().isoformat()
        }
    except Exception as e:
        raise Exception(f"Failed to render PDF: {e}")


if __name__ == '__main__':
    import sys

    markdown_file = sys.argv[1] if len(sys.argv) > 1 else \
        'docs/feature/ai-detection-cop-integration/PROGRESS.md'

    output_file = sys.argv[2] if len(sys.argv) > 2 else \
        'docs/feature/ai-detection-cop-integration/PROGRESS.pdf'

    try:
        result = render_progress_to_pdf(markdown_file, output_file)
        print(f"✅ PDF rendered successfully")
        print(f"📄 File: {result['path']}")
        print(f"📊 Size: {result['size']:,} bytes")
        print(f"⏰ Generated: {result['generated']}")
    except Exception as e:
        print(f"❌ Error rendering PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
