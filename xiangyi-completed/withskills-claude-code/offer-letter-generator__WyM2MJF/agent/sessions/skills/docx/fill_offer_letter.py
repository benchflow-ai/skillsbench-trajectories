from docx import Document
import json
import re
import sys

def fill_template(template_path, data_path, output_path):
    """Fill Word template handling split placeholders and conditionals."""

    # Load data
    with open(data_path) as f:
        data = json.load(f)

    # Load template
    doc = Document(template_path)

    # Check if relocation package should be included
    should_include_relocation = data.get('RELOCATION_PACKAGE', '').lower() == 'yes'

    def replace_in_para(para):
        """Replace placeholders in a paragraph, handling splits across runs."""
        text = para.text

        # Handle conditional sections first
        if_pattern = r'\{\{IF_([A-Z_]+)\}\}(.*?)\{\{END_IF_\1\}\}'

        # Check for conditional blocks
        for match in re.finditer(if_pattern, text, re.DOTALL):
            condition_key = match.group(1)
            content = match.group(2)
            full_match = match.group(0)

            if condition_key == 'RELOCATION':
                if should_include_relocation:
                    # Keep content, remove markers, replace placeholders in content
                    new_content = content
                    for key, val in data.items():
                        placeholder = '{{' + key + '}}'
                        new_content = new_content.replace(placeholder, str(val))
                    text = text.replace(full_match, new_content)
                else:
                    # Remove entire conditional block
                    text = text.replace(full_match, '')

        # Replace regular placeholders
        pattern = r'\{\{([A-Z_]+)\}\}'
        for match in re.finditer(pattern, text):
            key = match.group(1)
            placeholder = match.group(0)
            if key in data:
                text = text.replace(placeholder, str(data[key]))

        # Rebuild paragraph with new text if changed
        if text != para.text and para.runs:
            para.runs[0].text = text
            for run in para.runs[1:]:
                run.text = ''

    def process_table(table):
        """Process table including nested tables."""
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_para(para)
                # Handle nested tables
                for nested in cell.tables:
                    process_table(nested)

    # Process main document paragraphs
    for para in doc.paragraphs:
        replace_in_para(para)

    # Process tables
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
    print(f"Offer letter successfully created: {output_path}")

if __name__ == '__main__':
    template_path = '/root/offer_letter_template.docx'
    data_path = '/root/employee_data.json'
    output_path = '/root/offer_letter_filled.docx'

    fill_template(template_path, data_path, output_path)
