import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

doc = docx.Document()
doc.add_paragraph("Hello World")

for section in doc.sections:
    sectPr = section._sectPr
    
    pgBorders = OxmlElement('w:pgBorders')
    pgBorders.set(qn('w:offsetFrom'), 'page')
    
    for border_name in ['top', 'left', 'bottom', 'right']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '24')
        border.set(qn('w:color'), '666666')
        pgBorders.append(border)
        
    pgMar = sectPr.find(qn('w:pgMar'))
    if pgMar is not None:
        pgMar.addnext(pgBorders)
    else:
        sectPr.append(pgBorders)

doc.save('test_borders.docx')
print("Saved test_borders.docx")
