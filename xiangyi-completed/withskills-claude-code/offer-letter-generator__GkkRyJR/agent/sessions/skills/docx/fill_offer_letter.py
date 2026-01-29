#!/usr/bin/env python3
"""Fill offer letter template with employee data, handling split placeholders and conditionals."""

import json
import re
import sys
from docx import Document
from copy import deepcopy

def fill_template(template_path, data_path, output_path):
    """Fill Word template handling split placeholders and conditional sections."""

    # Load data
    with open(data_path) as f:
        data = json.load(f)

    # Load template
    doc = Document(template_path)

    def replace_in_para(para):
        """Replace placeholders in a paragraph, handling split runs and conditionals."""
        text = para.text

        # First, handle conditional sections within this paragraph
        # Pattern: {{IF_CONDITION}}...{{END_IF_CONDITION}}
        pattern = r'\{\{IF_([A-Z_]+)\}\}(.*?)\{\{END_IF_\1\}\}'
        matches = list(re.finditer(pattern, text, re.DOTALL))

        if matches:
            # Process conditionals
            for match in reversed(matches):  # Reverse to maintain indices
                condition_key = match.group(1)
                content = match.group(2)
                full_match = match.group(0)

                # Check if condition should be included
                condition_value = data.get(condition_key, '').lower()
                should_include = condition_value in ['yes', 'true', '1']

                if should_include:
                    # Remove markers but keep content
                    replacement = content
                else:
                    # Remove entire conditional section
                    replacement = ''

                text = text[:match.start()] + replacement + text[match.end():]

        # Now handle placeholder replacements
        pattern = r'\{\{([A-Z_]+)\}\}'
        if not re.search(pattern, text):
            return

        new_text = text
        for match in re.finditer(pattern, text):
            key = match.group(1)
            placeholder = match.group(0)
            if key in data:
                new_text = new_text.replace(placeholder, str(data[key]))

        if new_text != text and para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ''

    # Process main document paragraphs
    for para in doc.paragraphs:
        replace_in_para(para)

    # Process tables (with nesting support)
    def process_table(table):
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_para(para)
                # Handle nested tables
                for nested_table in cell.tables:
                    process_table(nested_table)

    for table in doc.tables:
        process_table(table)

    # Process headers and footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            replace_in_para(para)
        for para in section.footer.paragraphs:
            replace_in_para(para)

    # Save the filled document
    doc.save(output_path)
    print(f"✓ Offer letter created: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python fill_offer_letter.py <template.docx> <data.json> <output.docx>")
        sys.exit(1)

    template_path = sys.argv[1]
    data_path = sys.argv[2]
    output_path = sys.argv[3]

    try:
        fill_template(template_path, data_path, output_path)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
