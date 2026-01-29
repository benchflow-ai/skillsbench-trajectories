#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import os
import re

# Register namespaces
namespaces = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'p14': 'http://schemas.microsoft.com/office/powerpoint/2010/main',
    'a16': 'http://schemas.microsoft.com/office/drawing/2014/main',
}

for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

# Define slide dimensions (in EMUs - English Metric Units)
# Standard slide: 10" x 5.625" = 9144000 x 5143500 EMUs
SLIDE_WIDTH = 9144000
SLIDE_HEIGHT = 5143500

# Paper titles extracted from slides
PAPER_TITLES = [
    "Foam-Agent: Towards Automated Intelligent CFD Workflows",
    "ReAct: Synergizing Reasoning and Acting in Language Models",
    "Why Do Multi-Agent LLM Systems Fail?",
    "MultiAgentBench: Evaluating the Collaboration and Competition of LLM agents"
]

def update_slide(slide_num):
    """Process a slide to move title to bottom center with proper formatting."""
    slide_path = f'/logs/agent/sessions/skills/pptx/unpacked_pptx/ppt/slides/slide{slide_num}.xml'

    tree = ET.parse(slide_path)
    root = tree.getroot()

    # Find the textbox with the paper title (usually the last shape)
    shapes = root.findall('.//p:sp', namespaces)

    if not shapes:
        return None

    # Find textbox with title (non-placeholder shapes at bottom of slide)
    title_shape = None
    for shape in shapes:
        nvpr = shape.find('.//p:nvSpPr', namespaces)
        if nvpr is not None:
            txbox = nvpr.find('.//p:cNvSpPr', namespaces)
            if txbox is not None and txbox.get('txBox') == '1':
                title_shape = shape
                break

    if title_shape is None:
        return None

    # Get title text
    title_text = ''
    for t_elem in title_shape.findall('.//a:t', namespaces):
        if t_elem.text:
            title_text += t_elem.text

    if not title_text.strip():
        return None

    # Update the textbox positioning and formatting
    spPr = title_shape.find('.//p:spPr', namespaces)
    if spPr is None:
        spPr = ET.Element('{http://schemas.openxmlformats.org/presentationml/2006/main}spPr')
        title_shape.insert(1, spPr)

    # Update transform - position at bottom center
    xfrm = spPr.find('.//a:xfrm', namespaces)
    if xfrm is None:
        xfrm = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm')
        spPr.insert(0, xfrm)

    # Remove existing off/ext if present
    for child in list(xfrm):
        if child.tag in ['{http://schemas.openxmlformats.org/drawingml/2006/main}off',
                         '{http://schemas.openxmlformats.org/drawingml/2006/main}ext']:
            xfrm.remove(child)

    # Set position and size - bottom center
    # Estimate width based on text length, centered
    text_width = len(title_text) * 60000 + 200000  # rough estimate
    text_width = min(text_width, 8000000)  # max width
    x_pos = (SLIDE_WIDTH - text_width) // 2
    y_pos = SLIDE_HEIGHT - 600000  # near bottom

    off = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}off')
    off.set('x', str(x_pos))
    off.set('y', str(y_pos))
    xfrm.append(off)

    ext = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}ext')
    ext.set('cx', str(text_width))
    ext.set('cy', str(400000))  # height
    xfrm.append(ext)

    # Remove geometry if present
    for elem in list(spPr):
        if 'Geom' in elem.tag:
            spPr.remove(elem)

    # Update text formatting
    txBody = title_shape.find('.//p:txBody', namespaces)
    if txBody is not None:
        # Clear existing paragraphs
        for p in list(txBody.findall('.//a:p', namespaces)):
            txBody.remove(p)

        # Create new paragraph with formatted text
        p = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}p')

        # Set paragraph alignment to center
        pPr = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}pPr')
        pPr.set('algn', 'ctr')
        p.append(pPr)

        # Create text run with formatting
        r = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}r')

        rPr = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}rPr')
        rPr.set('lang', 'en-US')
        rPr.set('sz', '1600')  # 16pt = 1600 in PPTX units
        rPr.set('dirty', '0')
        rPr.set('b', '0')  # no bold

        # Set color to #989596
        solidFill = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill')
        srgbClr = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr')
        srgbClr.set('val', '989596')
        solidFill.append(srgbClr)
        rPr.append(solidFill)

        # Set font to Arial
        latin = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}latin')
        latin.set('typeface', 'Arial')
        rPr.append(latin)

        r.append(rPr)

        # Add text
        t = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}t')
        t.text = title_text.strip()
        r.append(t)

        p.append(r)

        # Add end paragraph properties
        endParaRPr = ET.Element('{http://schemas.openxmlformats.org/drawingml/2006/main}endParaRPr')
        endParaRPr.set('lang', 'en-US')
        endParaRPr.set('dirty', '0')
        p.append(endParaRPr)

        txBody.append(p)

    tree.write(slide_path, encoding='ascii', xml_declaration=True)
    print(f"Updated slide {slide_num}: {title_text[:60]}")
    return title_text.strip()

def add_reference_slide():
    """Add a new reference slide with all paper titles."""
    slides_dir = '/logs/agent/sessions/skills/pptx/unpacked_pptx/ppt/slides'

    # Find next slide number
    existing_slides = sorted([int(f.replace('slide', '').replace('.xml', ''))
                             for f in os.listdir(slides_dir) if f.startswith('slide') and f.endswith('.xml')])
    next_slide_num = max(existing_slides) + 1

    # Create new slide XML
    slide_xml = f'''<?xml version="1.0" encoding="ascii"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg>
      <p:bgPr>
        <a:solidFill>
          <a:srgbClr val="FFFFFF"/>
        </a:solidFill>
        <a:effectLst/>
        <p:effectLst/>
      </p:bgPr>
    </p:bg>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="2" name="Title 1"/>
          <p:cNvSpPr>
            <a:spLocks noGrp="1"/>
          </p:cNvSpPr>
          <p:nvPr>
            <p:ph type="title"/>
          </p:nvPr>
        </p:nvSpPr>
        <p:spPr/>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr lang="en-US" dirty="0"/>
              <a:t>Reference</a:t>
            </a:r>
            <a:endParaRPr lang="en-US" dirty="0"/>
          </a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="3" name="Content Placeholder 2"/>
          <p:cNvSpPr>
            <a:spLocks noGrp="1"/>
          </p:cNvSpPr>
          <p:nvPr>
            <p:ph idx="1"/>
          </p:nvPr>
        </p:nvSpPr>
        <p:spPr/>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
'''

    # Add numbered bullet points for each unique paper
    unique_titles = []
    for title in PAPER_TITLES:
        if title not in unique_titles:
            unique_titles.append(title)

    for title in unique_titles:
        slide_xml += f'''          <a:p>
            <a:pPr lvl="0">
              <a:buAutoNum type="arabicPeriod"/>
            </a:pPr>
            <a:r>
              <a:rPr lang="en-US" dirty="0"/>
              <a:t>{title}</a:t>
            </a:r>
            <a:endParaRPr lang="en-US" dirty="0"/>
          </a:p>
'''

    slide_xml += '''        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>
'''

    # Write slide file
    slide_path = os.path.join(slides_dir, f'slide{next_slide_num}.xml')
    with open(slide_path, 'w', encoding='ascii') as f:
        f.write(slide_xml)

    # Create relationship file for new slide
    rels_dir = os.path.join(slides_dir, '_rels')
    rels_path = os.path.join(rels_dir, f'slide{next_slide_num}.xml.rels')
    rels_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
'''
    with open(rels_path, 'w', encoding='utf-8') as f:
        f.write(rels_content)

    print(f"Created new reference slide {next_slide_num}")
    return next_slide_num

def update_presentation_xml(new_slide_num):
    """Update presentation.xml to include the new slide."""
    pres_path = '/logs/agent/sessions/skills/pptx/unpacked_pptx/ppt/presentation.xml'
    tree = ET.parse(pres_path)
    root = tree.getroot()

    # Find sldIdLst
    sldIdLst = root.find('.//p:sldIdLst', namespaces)

    if sldIdLst is not None:
        # Find max id
        max_id = 0
        max_rid = 0
        for sldId in sldIdLst.findall('.//p:sldId', namespaces):
            slide_id = int(sldId.get('id', 0))
            max_id = max(max_id, slide_id)
            rid = sldId.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', '')
            if rid:
                rid_num = int(rid.replace('rId', ''))
                max_rid = max(max_rid, rid_num)

        # Add new slide
        new_sldId = ET.Element('{http://schemas.openxmlformats.org/presentationml/2006/main}sldId')
        new_sldId.set('id', str(max_id + 1))
        new_sldId.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', f'rId{max_rid + 1}')
        sldIdLst.append(new_sldId)

    tree.write(pres_path, encoding='ascii', xml_declaration=True)

def update_presentation_rels(new_slide_num):
    """Update presentation.xml.rels to include the new slide."""
    rels_path = '/logs/agent/sessions/skills/pptx/unpacked_pptx/ppt/_rels/presentation.xml.rels'
    tree = ET.parse(rels_path)
    root = tree.getroot()

    # Find max rId
    max_rid = 0
    for rel in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
        rid = rel.get('Id', '')
        if rid.startswith('rId'):
            rid_num = int(rid.replace('rId', ''))
            max_rid = max(max_rid, rid_num)

    # Add new relationship
    new_rel = ET.Element('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship')
    new_rel.set('Id', f'rId{max_rid + 1}')
    new_rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide')
    new_rel.set('Target', f'slides/slide{new_slide_num}.xml')
    root.append(new_rel)

    tree.write(rels_path, encoding='utf-8', xml_declaration=True)

def update_content_types(new_slide_num):
    """Update [Content_Types].xml to include the new slide."""
    ct_path = '/logs/agent/sessions/skills/pptx/unpacked_pptx/[Content_Types].xml'
    tree = ET.parse(ct_path)
    root = tree.getroot()

    # Check if slide already exists in Content_Types
    ns = {'ct': 'http://schemas.openxmlformats.org/package/2006/content-types'}
    ET.register_namespace('', 'http://schemas.openxmlformats.org/package/2006/content-types')

    override_path = f'/ppt/slides/slide{new_slide_num}.xml'
    exists = False
    for override in root.findall('.//ct:Override', ns):
        if override.get('PartName') == override_path:
            exists = True
            break

    if not exists:
        new_override = ET.Element('{http://schemas.openxmlformats.org/package/2006/content-types}Override')
        new_override.set('PartName', override_path)
        new_override.set('ContentType', 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
        root.append(new_override)

    tree.write(ct_path, encoding='utf-8', xml_declaration=True)

def main():
    print("Processing slides...")

    # Update slides 2-6 with formatted titles at bottom center
    collected_titles = []
    for slide_num in range(2, 7):
        title = update_slide(slide_num)
        if title:
            collected_titles.append(title)

    print(f"\nCollected titles: {collected_titles}")

    # Add reference slide
    new_slide_num = add_reference_slide()
    update_presentation_xml(new_slide_num)
    update_presentation_rels(new_slide_num)
    update_content_types(new_slide_num)

    print(f"\nAdded reference slide with {len(set(PAPER_TITLES))} unique papers")
    print("Done!")

if __name__ == '__main__':
    main()
