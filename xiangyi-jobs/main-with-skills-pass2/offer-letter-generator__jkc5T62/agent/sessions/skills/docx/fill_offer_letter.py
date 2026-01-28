#!/usr/bin/env python3
"""Fill Word template with employee data, handling split placeholders and conditional sections."""

from docx import Document
import json
import re
import sys


def replace_in_paragraph(para, data):
    """Replace placeholders in a paragraph, handling split placeholders."""
    text = para.text
    pattern = r'\{\{([A-Z_]+)\}\}'

    if not re.search(pattern, text):
        return

    new_text = text
    for match in re.finditer(pattern, text):
        key = match.group(1)
        placeholder = match.group(0)
        if key in data:
            new_text = new_text.replace(placeholder, str(data[key]))

    # If text changed, rebuild paragraph to handle split placeholders
    if new_text != text and para.runs:
        # Keep first run's formatting, put all text there
        para.runs[0].text = new_text
        # Clear all other runs
        for run in para.runs[1:]:
            run.text = ''


def handle_conditional_in_paragraph(para, data):
    """Handle conditional sections like {{IF_RELOCATION}}...{{END_IF_RELOCATION}}."""
    text = para.text

    # Check for relocation conditional
    if_pattern = r'\{\{IF_RELOCATION\}\}'
    end_pattern = r'\{\{END_IF_RELOCATION\}\}'

    if re.search(if_pattern, text) or re.search(end_pattern, text):
        should_include = data.get('RELOCATION_PACKAGE', '').lower() == 'yes'

        if should_include:
            # Keep content but remove markers
            new_text = re.sub(if_pattern, '', text)
            new_text = re.sub(end_pattern, '', new_text)
        else:
            # Remove entire line/paragraph
            new_text = ''

        if para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ''


def process_table(table, data):
    """Process table including nested tables."""
    for row in table.rows:
        for cell in row.cells:
            # Process paragraphs in cell
            for para in cell.paragraphs:
                handle_conditional_in_paragraph(para, data)
                replace_in_paragraph(para, data)

            # Recurse into nested tables
            for nested_table in cell.tables:
                process_table(nested_table, data)


def fill_template(template_path, data_path, output_path):
    """Fill Word template with data from JSON file."""

    # Load data
    with open(data_path, 'r') as f:
        data = json.load(f)

    # Load template
    doc = Document(template_path)

    # Process main document paragraphs
    for para in doc.paragraphs:
        handle_conditional_in_paragraph(para, data)
        replace_in_paragraph(para, data)

    # Process tables (with nesting support)
    for table in doc.tables:
        process_table(table, data)

    # Process headers and footers
    for section in doc.sections:
        # Header
        for para in section.header.paragraphs:
            handle_conditional_in_paragraph(para, data)
            replace_in_paragraph(para, data)

        # Process tables in header
        for table in section.header.tables:
            process_table(table, data)

        # Footer
        for para in section.footer.paragraphs:
            handle_conditional_in_paragraph(para, data)
            replace_in_paragraph(para, data)

        # Process tables in footer
        for table in section.footer.tables:
            process_table(table, data)

    # Save output
    doc.save(output_path)
    print(f"Successfully created: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python fill_offer_letter.py <template.docx> <output.docx> <data.json>")
        sys.exit(1)

    template_path = sys.argv[1]
    output_path = sys.argv[2]
    data_path = sys.argv[3]

    fill_template(template_path, data_path, output_path)
