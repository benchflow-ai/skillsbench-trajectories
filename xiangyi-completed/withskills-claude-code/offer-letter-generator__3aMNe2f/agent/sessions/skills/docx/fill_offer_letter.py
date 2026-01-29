#!/usr/bin/env python3
"""Fill offer letter template with employee data."""

from docx import Document
import json
import re

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

    # Apply replacement to first run, clear others
    if new_text != text and para.runs:
        para.runs[0].text = new_text
        for run in para.runs[1:]:
            run.text = ''

def handle_conditional_section(doc, condition_key, should_include, data):
    """Handle {{IF_...}}...{{END_IF_...}} sections."""
    start_marker = f'{{{{IF_{condition_key}}}}}'
    end_marker = f'{{{{END_IF_{condition_key}}}}}'

    i = 0
    while i < len(doc.paragraphs):
        para = doc.paragraphs[i]
        text = para.text

        # Check if this paragraph contains the start marker
        if start_marker in text:
            start_para_idx = i
            # Find the end marker
            end_para_idx = None
            for j in range(i, len(doc.paragraphs)):
                if end_marker in doc.paragraphs[j].text:
                    end_para_idx = j
                    break

            if end_para_idx is not None:
                if should_include:
                    # Remove markers but keep content
                    # Process start paragraph
                    start_para = doc.paragraphs[start_para_idx]
                    start_text = start_para.text.replace(start_marker, '')
                    if start_para.runs:
                        start_para.runs[0].text = start_text
                        for run in start_para.runs[1:]:
                            run.text = ''

                    # Process end paragraph
                    end_para = doc.paragraphs[end_para_idx]
                    end_text = end_para.text.replace(end_marker, '')
                    if end_para.runs:
                        end_para.runs[0].text = end_text
                        for run in end_para.runs[1:]:
                            run.text = ''

                    # Replace any placeholders in between
                    for j in range(start_para_idx, end_para_idx + 1):
                        replace_in_paragraph(doc.paragraphs[j], data)

                    i = end_para_idx + 1
                else:
                    # Remove entire section including markers
                    # Delete paragraphs from start to end (inclusive)
                    for j in range(end_para_idx, start_para_idx - 1, -1):
                        p = doc.paragraphs[j]._element
                        p.getparent().remove(p)
                    i = start_para_idx
            else:
                i += 1
        else:
            i += 1

def process_table(table, data):
    """Process table including nested tables."""
    for row in table.rows:
        for cell in row.cells:
            # Process paragraphs in cell
            for para in cell.paragraphs:
                replace_in_paragraph(para, data)

            # Recurse into nested tables
            for nested_table in cell.tables:
                process_table(nested_table, data)

def fill_template(template_path, data_path, output_path):
    """Fill Word template with data."""

    # Load data
    with open(data_path) as f:
        data = json.load(f)

    # Load template
    doc = Document(template_path)

    # Check relocation package
    relocation_enabled = data.get('RELOCATION_PACKAGE', '').lower() == 'yes'

    # Handle conditional sections first (before replacing placeholders)
    handle_conditional_section(doc, 'RELOCATION', relocation_enabled, data)

    # Replace placeholders in main document
    for para in doc.paragraphs:
        replace_in_paragraph(para, data)

    # Replace in tables
    for table in doc.tables:
        process_table(table, data)

    # Replace in headers/footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            replace_in_paragraph(para, data)
        for para in section.footer.paragraphs:
            replace_in_paragraph(para, data)

    # Save output
    doc.save(output_path)
    print(f"Offer letter created successfully: {output_path}")

if __name__ == '__main__':
    fill_template('/root/offer_letter_template.docx',
                  '/root/employee_data.json',
                  '/root/offer_letter_filled.docx')
