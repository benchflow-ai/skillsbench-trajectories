#!/usr/bin/env python3
"""
Fill Word template with data from JSON file.
Handles split placeholders, conditional sections, headers, footers, and nested tables.
"""

from docx import Document
import json
import re
import sys

def fill_template(template_path, data_path, output_path):
    """Fill Word template handling all edge cases."""

    # Load data
    with open(data_path) as f:
        data = json.load(f)

    # Load template
    doc = Document(template_path)

    def replace_in_para(para):
        """Replace placeholders in a paragraph, handling split placeholders."""
        text = para.text

        # Check for conditional sections first
        if_pattern = r'\{\{IF_([A-Z_]+)\}\}(.*?)\{\{END_IF_\1\}\}'

        # Handle conditionals that span the paragraph
        for match in re.finditer(if_pattern, text, re.DOTALL):
            condition_key = match.group(1)
            content = match.group(2)
            full_marker = match.group(0)

            # Check if condition is met (e.g., IF_RELOCATION checks RELOCATION_PACKAGE)
            # Remove the "IF_" prefix to get the data key
            data_key = condition_key
            if data_key in data and data[data_key] == "Yes":
                # Keep content but remove markers
                text = text.replace(full_marker, content)
            else:
                # Remove entire conditional block
                text = text.replace(full_marker, '')

        # Now replace regular placeholders
        pattern = r'\{\{([A-Z_]+)\}\}'
        new_text = text

        for match in re.finditer(pattern, text):
            key = match.group(1)
            placeholder = match.group(0)
            if key in data:
                new_text = new_text.replace(placeholder, str(data[key]))

        # If text changed, rebuild paragraph preserving first run's formatting
        if new_text != text and para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ''

    # Process main document paragraphs
    for para in doc.paragraphs:
        replace_in_para(para)

    # Process tables (with nested table support)
    def process_table(table):
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_para(para)
                # Handle nested tables
                for nested in cell.tables:
                    process_table(nested)

    for table in doc.tables:
        process_table(table)

    # Process headers and footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            replace_in_para(para)
        for para in section.footer.paragraphs:
            replace_in_para(para)

    # Save output
    doc.save(output_path)
    print(f"Successfully created: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python fill_template.py <template.docx> <data.json> <output.docx>")
        sys.exit(1)

    template_path = sys.argv[1]
    data_path = sys.argv[2]
    output_path = sys.argv[3]

    fill_template(template_path, data_path, output_path)
