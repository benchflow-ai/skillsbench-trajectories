#!/usr/bin/env python3
"""Fill Word template with data from JSON file."""

from docx import Document
import json
import re
import sys


def replace_in_paragraph(para, data):
    """Replace placeholders in a single paragraph, handling split runs."""
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

    # Only update if text changed
    if new_text != text and para.runs:
        # Keep first run's formatting, clear others
        para.runs[0].text = new_text
        for run in para.runs[1:]:
            run.text = ''


def handle_conditional_sections(doc, data):
    """Handle conditional sections like {{IF_RELOCATION}}...{{END_IF_RELOCATION}}."""

    # Check if we should include relocation package
    should_include_relocation = data.get('RELOCATION_PACKAGE', '').lower() == 'yes'

    def process_conditional_para(para):
        text = para.text

        # Check for relocation conditional
        if '{{IF_RELOCATION}}' in text or '{{END_IF_RELOCATION}}' in text:
            if should_include_relocation:
                # Remove just the markers, keep the content
                new_text = text.replace('{{IF_RELOCATION}}', '').replace('{{END_IF_RELOCATION}}', '')
                # Replace any placeholders inside
                for key, val in data.items():
                    new_text = new_text.replace('{{' + key + '}}', str(val))
            else:
                # Remove entire content
                new_text = ''

            if para.runs:
                para.runs[0].text = new_text
                for run in para.runs[1:]:
                    run.text = ''
            return True
        return False

    # Process main document paragraphs
    for para in doc.paragraphs:
        process_conditional_para(para)

    # Process tables
    def process_table(table):
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    process_conditional_para(para)
                for nested in cell.tables:
                    process_table(nested)

    for table in doc.tables:
        process_table(table)

    # Process headers and footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            process_conditional_para(para)
        for para in section.footer.paragraphs:
            process_conditional_para(para)


def fill_template(template_path, data_path, output_path):
    """Fill Word template handling all edge cases."""

    # Load data
    with open(data_path, 'r') as f:
        data = json.load(f)

    # Load template
    doc = Document(template_path)

    # First handle conditional sections
    handle_conditional_sections(doc, data)

    # Then replace all regular placeholders
    # Process main document
    for para in doc.paragraphs:
        replace_in_paragraph(para, data)

    # Process tables (with nesting)
    def process_table(table):
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_paragraph(para, data)
                for nested in cell.tables:
                    process_table(nested)

    for table in doc.tables:
        process_table(table)

    # Process headers and footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            replace_in_paragraph(para, data)
        for para in section.footer.paragraphs:
            replace_in_paragraph(para, data)

    # Save filled document
    doc.save(output_path)
    print(f"Successfully created offer letter: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python fill_template.py <template.docx> <data.json> <output.docx>")
        sys.exit(1)

    template_path = sys.argv[1]
    data_path = sys.argv[2]
    output_path = sys.argv[3]

    fill_template(template_path, data_path, output_path)
