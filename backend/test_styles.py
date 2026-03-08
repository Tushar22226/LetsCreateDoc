import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

doc = docx.Document()
print("Available styles in empty docx:")
for s in doc.styles:
    if s.type == docx.enum.style.WD_STYLE_TYPE.TABLE:
        print(f" - {s.name}")

