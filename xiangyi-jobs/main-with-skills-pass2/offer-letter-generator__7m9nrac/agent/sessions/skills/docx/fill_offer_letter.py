#!/usr/bin/env python3
import json
import re
from docx import Document
from docx.oxml import OxmlElement

def fill_offer_letter(template_path, data_path, output_path):
    """Fill Word template with employee data, handling conditional sections."""

    # Load employee data
    with open(data_path) as f:
        data = json.load(f)

    # Load template document
    doc = Document(template_path)

    # Determine if relocation section should be included
    include_relocation = data.get('RELOCATION_PACKAGE', '').lower() == 'yes'

    def replace_in_para(para):
        """Replace placeholders in a paragraph."""
        text = para.text
        pattern = r'\{\{([A-Z_]+)\}\}'

        if not re.search(pattern, text):
            return

        new_text = text

        # Handle conditional sections
        if '{{IF_RELOCATION}}' in text:
            if include_relocation:
                # Remove just the markers
                new_text = new_text.replace('{{IF_RELOCATION}}', '').replace('{{END_IF_RELOCATION}}', '')
            else:
                # Remove entire conditional content
                new_text = re.sub(r'\{\{IF_RELOCATION\}\}.*?\{\{END_IF_RELOCATION\}\}', '', new_text, flags=re.DOTALL)

        # Replace placeholders with values
        for match in re.finditer(pattern, new_text):
            key = match.group(1)
            if key not in ['IF_RELOCATION', 'END_IF_RELOCATION']:  # Skip conditional markers
                placeholder = match.group(0)
                if key in data:
                    new_text = new_text.replace(placeholder, str(data[key]))

        # Update paragraph runs if text changed
        if new_text != text and para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ''

    def process_element(element):
        """Process paragraphs in any element (handles nested content)."""
        if hasattr(element, 'paragraphs'):
            for para in element.paragraphs:
                replace_in_para(para)

        if hasattr(element, 'tables'):
            for table in element.tables:
                for row in table.rows:
                    for cell in row.cells:
                        process_element(cell)

    # Process main document body
    process_element(doc)

    # Process all sections (headers/footers)
    for section in doc.sections:
        for para in section.header.paragraphs:
            replace_in_para(para)
        for para in section.footer.paragraphs:
            replace_in_para(para)

    # Save output document
    doc.save(output_path)
    print(f"✓ Offer letter created: {output_path}")
    print(f"  Relocation section: {'INCLUDED' if include_relocation else 'REMOVED'}")

if __name__ == '__main__':
    fill_offer_letter('/root/offer_letter_template.docx', '/root/employee_data.json', '/root/offer_letter_filled.docx')
