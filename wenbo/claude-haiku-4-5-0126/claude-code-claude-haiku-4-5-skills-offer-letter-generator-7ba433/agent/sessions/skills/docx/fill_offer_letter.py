#!/usr/bin/env python3
"""Fill offer letter template with employee data."""

import json
import re
import sys
from docx import Document
from pathlib import Path

def replace_in_paragraph(para, data):
    """Replace all {{PLACEHOLDER}} in a paragraph, handling split placeholders."""
    text = para.text

    # Find all placeholders
    pattern = r'\{\{([A-Z_]+)\}\}'
    matches = re.findall(pattern, text)

    if not matches:
        return

    new_text = text
    for key in matches:
        placeholder = '{{' + key + '}}'
        if key in data:
            new_text = new_text.replace(placeholder, str(data[key]))

    # If text changed, rebuild paragraph
    if new_text != text:
        runs = para.runs
        if runs:
            runs[0].text = new_text
            for run in runs[1:]:
                run.text = ''

def handle_conditional_sections(para, condition_key, should_include, data):
    """Handle {{IF_CONDITION}}...{{END_IF_CONDITION}} sections."""
    start_marker = '{{IF_' + condition_key + '}}'
    end_marker = '{{END_IF_' + condition_key + '}}'

    text = para.text

    if start_marker in text:
        if should_include:
            # Remove just the markers, keep content
            new_text = text.replace(start_marker, '').replace(end_marker, '')
            # Replace any placeholders inside
            pattern = r'\{\{([A-Z_]+)\}\}'
            for match in re.finditer(pattern, new_text):
                key = match.group(1)
                placeholder = match.group(0)
                if key in data:
                    new_text = new_text.replace(placeholder, str(data[key]))
        else:
            # Remove entire conditional section
            new_text = text.replace(start_marker, '').replace(end_marker, '')

        if new_text != text and para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ''

    elif end_marker in text:
        # This is the end marker line
        if should_include:
            # Remove the marker
            new_text = text.replace(end_marker, '')
        else:
            # Remove the entire line
            new_text = ''

        if new_text != text and para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ''

def process_table(table, data, include_relocation):
    """Process table including nested tables."""
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                replace_in_paragraph(para, data)
                handle_conditional_sections(para, 'RELOCATION', include_relocation, data)

            # Recurse into nested tables
            for nested_table in cell.tables:
                process_table(nested_table, data, include_relocation)

def fill_offer_letter(template_path, data_path, output_path):
    """Fill offer letter template with employee data."""

    # Load data
    with open(data_path) as f:
        data = json.load(f)

    # Check if relocation package is included
    include_relocation = data.get('RELOCATION_PACKAGE', '').lower() == 'yes'

    # Load template
    doc = Document(template_path)

    # Process main document paragraphs
    for para in doc.paragraphs:
        replace_in_paragraph(para, data)
        handle_conditional_sections(para, 'RELOCATION', include_relocation, data)

    # Process tables with nesting
    for table in doc.tables:
        process_table(table, data, include_relocation)

    # Process headers and footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            replace_in_paragraph(para, data)
            handle_conditional_sections(para, 'RELOCATION', include_relocation, data)
        for para in section.footer.paragraphs:
            replace_in_paragraph(para, data)
            handle_conditional_sections(para, 'RELOCATION', include_relocation, data)

    # Save output
    doc.save(output_path)
    print(f"Offer letter filled and saved to {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: fill_offer_letter.py <template.docx> <output.docx> <data.json>")
        sys.exit(1)

    template_path = sys.argv[1]
    output_path = sys.argv[2]
    data_path = sys.argv[3]

    fill_offer_letter(template_path, data_path, output_path)
