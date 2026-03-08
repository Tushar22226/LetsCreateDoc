import os
import io
import tempfile
import pypandoc
from src.externals.diagram.generator import diagram_generator
from src.utils.logger import logger

class DOCXGenerator:
    def __init__(self):
        self.markdown_lines = []
        self.figure_count = 1
        self.temp_dir = tempfile.TemporaryDirectory()

    def add_title_page(self, title: str):
        # We can simulate a title page in markdown by adding huge headers and a page break
        title_md = f"""
<br><br><br><br><br>
<div align="center">

# {title}

**Project Documentation**

</div>

```{{=openxml}}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
"""
        self.markdown_lines.append(title_md)

    async def add_markdown_section(self, section_title: str, content: str):
        # Enforce a hard page break before each section using raw OOXML for DOCX reliability
        self.markdown_lines.append("\n```{=openxml}\n<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>\n```\n")
        
        # We want to ensure the top level heading matches the section title 
        # (or at least provide one if it's missing)
        if not content.strip().startswith('# '):
             self.markdown_lines.append(f"# {section_title}\n")
             
        import re
        import json
        
        # 1. Sanitize inline tables: LLMs sometimes strip newlines between rows (`| col | |---| | val |`)
        content = re.sub(r'\|\s+\|', '|\n|', content)
        
        # 2. Extract leaked tool JSON (generate_diagram) into standard mermaid blocks
        def extract_diagram(match):
            json_str = match.group(1)
            try:
                # Try parsing, strict=False allows unescaped newlines inside strings
                data = json.loads(json_str, strict=False)
                code = data.get('code', '') or data.get('content', '') or data.get('mermaid', '')
                if code:
                    return f"\n```mermaid\n{code}\n```\n"
            except Exception:
                # Fallback: regex search for anything inside "code": "..." or "content": "..."
                # This handles severely malformed JSON that json.loads can't rescue
                code_match = re.search(r'"(?:code|content|mermaid)"\s*:\s*"(.*?)"\s*\}', json_str, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                    # Unescape explicit python newlines and quotes
                    code = code.replace('\\n', '\n').replace('\\"', '"')
                    return f"\n```mermaid\n{code}\n```\n"
            return match.group(0)
            
        content = re.sub(r'generate_diagram\(\s*(\{.*?\})\s*\)', extract_diagram, content, flags=re.DOTALL)

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.startswith('```mermaid'):
                # Collect mermaid block
                mermaid_code = ""
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    mermaid_code += lines[i] + '\n'
                    i += 1
                
                # Render diagram
                try:
                    logger.info("Intercepted Mermaid block, converting to image...")
                    img_bytes = await diagram_generator.generate_image(mermaid_code)
                    if img_bytes:
                        # Save to temp file
                        img_path = os.path.join(self.temp_dir.name, f"fig_{self.figure_count}.png")
                        with open(img_path, 'wb') as f:
                            f.write(img_bytes)
                        
                        # Add markdown image reference with caption
                        caption = f"Figure {self.figure_count}: System Diagram"
                        self.markdown_lines.append(f"\n![{caption}]({img_path})\n")
                        self.figure_count += 1
                    else:
                        self.markdown_lines.append("\n*[Failed to render diagram]*\n")
                except Exception as e:
                    logger.error(f"Mermaid rendering failed: {e}")
                    self.markdown_lines.append("\n*[Error rendering diagram]*\n")
            else:
                self.markdown_lines.append(line)
            i += 1

    def get_docx_bytes(self) -> io.BytesIO:
        """Compiles the accumulated markdown into a DOCX using pandoc and post-processes with python-docx."""
        full_markdown = '\n'.join(self.markdown_lines)
        
        # --- Advanced Markdown Sanitization ---
        import re
        import json
        
        # 1. Sanitize unicode dashes
        full_markdown = full_markdown.replace('—', '-').replace('–', '-')
        
        # 2. Fix Inline Tables (LLM sometimes strips newlines: `... | col | |---| | val | ...`)
        # We look for a pipe followed by space, then another pipe to inject a newline.
        # e.g., " | | " becomes " |\n| "
        full_markdown = re.sub(r'\|\s+\|', '|\n|', full_markdown)
        
        # 3. Intercept Leaked Tool JSON (generate_diagram)
        # Sometimes the LLM outputs the raw JSON tool call instead of calling the tool.
        # We can detect this, extract the code, and replace it with a standard markdown block.
        def inject_diagram_block(match):
            json_str = match.group(1)
            try:
                data = json.loads(json_str, strict=False)
                code = data.get('code', '') or data.get('content', '') or data.get('mermaid', '')
                if code:
                    return f"\n\n```mermaid\n{code}\n```\n\n"
            except Exception:
                code_match = re.search(r'"(?:code|content|mermaid)"\s*:\s*"(.*?)"\s*\}', json_str, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                    code = code.replace('\\n', '\n').replace('\\"', '"')
                    return f"\n\n```mermaid\n{code}\n```\n\n"
            return match.group(0) # fallback
            
        full_markdown = re.sub(r'generate_diagram\(\s*(\{.*?\})\s*\)', inject_diagram_block, full_markdown, flags=re.DOTALL)
        
        # Convert to DOCX using pypandoc
        # We save output to a temp file, then read bytes
        out_path = os.path.join(self.temp_dir.name, "output.docx")
        
        try:
            logger.info("Compiling full Markdown to DOCX via Pandoc...")
            pypandoc.convert_text(
                full_markdown, 
                'docx', 
                format='markdown+pipe_tables+grid_tables+raw_attribute', 
                outputfile=out_path,
                extra_args=[
                    '--wrap=none', 
                    '--standalone', 
                    '--syntax-highlighting', 'pygments', 
                    '--toc', 
                    '--toc-depth=3',
                    '--metadata', 'toc-title=Table of Contents',
                    '--metadata', 'table-style=TableGrid'
                ] 
            )
            
            # --- POST-PROCESSING WITH PYTHON-DOCX ---
            try:
                from docx import Document
                from docx.oxml import OxmlElement
                from docx.oxml.ns import qn
                
                logger.info("Applying python-docx post-processing for tables and borders...")
                doc = Document(out_path)
                
                # 1. Force Table Width and Handle Styles safely
                for table in doc.tables:
                    try:
                        table.style = 'Table Grid'
                    except KeyError:
                        # Fallback if Pandoc didn't embed 'Table Grid'
                        try:
                            table.style = 'Normal Table'
                        except KeyError:
                            pass # If all else fails, just keep default 

                    # Force 100% width via XML
                    tbl_w = OxmlElement('w:tblW')
                    tbl_w.set(qn('w:w'), '5000')
                    tbl_w.set(qn('w:type'), 'pct')
                    table._tbl.tblPr.append(tbl_w)
                                        
                    # Inject raw border XML into table properties as ultimate fallback
                    tblBorders = OxmlElement('w:tblBorders')
                    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
                        border = OxmlElement(f'w:{border_name}')
                        border.set(qn('w:val'), 'single')
                        border.set(qn('w:sz'), '4')
                        border.set(qn('w:space'), '0')
                        border.set(qn('w:color'), '000000')
                        tblBorders.append(border)
                    table._tbl.tblPr.append(tblBorders)
                
                # 2. Force Page Borders for all sections in CORRECT XML SEQUENCE
                for section in doc.sections:
                    sectPr = section._sectPr
                    
                    # Ensure we don't add borders twice
                    pgBorders = sectPr.find(qn('w:pgBorders'))
                    if pgBorders is not None:
                        sectPr.remove(pgBorders)
                        
                    pgBorders = OxmlElement('w:pgBorders')
                    pgBorders.set(qn('w:offsetFrom'), 'page')
                    
                    for border_name in ['top', 'left', 'bottom', 'right']:
                        border = OxmlElement(f'w:{border_name}')
                        border.set(qn('w:val'), 'single')
                        border.set(qn('w:sz'), '4')
                        border.set(qn('w:space'), '24')
                        border.set(qn('w:color'), '666666')
                        pgBorders.append(border)
                        
                    # CRITICAL: Microsoft Word schema requires pgBorders to come AFTER pgMar
                    pgMar = sectPr.find(qn('w:pgMar'))
                    if pgMar is not None:
                        pgMar.addnext(pgBorders)
                    else:
                        sectPr.append(pgBorders)
                
                # Save the processed document back to the temp path
                doc.save(out_path)
                logger.info("Post-processing complete.")
            except ImportError:
                logger.warning("python-docx not installed, skipping post-processing formatting.")
            except Exception as e:
                logger.error(f"python-docx post-processing failed: {e}")

            with open(out_path, 'rb') as f:
                docx_bytes = f.read()
                
            return io.BytesIO(docx_bytes)
        except Exception as e:
            logger.error(f"Pandoc conversion failed: {e}")
            raise
        finally:
            self.temp_dir.cleanup()

    def add_image(self, image_bytes: bytes, caption: str = ""):
        # Backward compatibility for service.py 'project_diagrams' 
        # (Though we intercept them inline now, if any are added externally we append them)
        try:
            img_path = os.path.join(self.temp_dir.name, f"ext_fig_{self.figure_count}.png")
            with open(img_path, 'wb') as f:
                f.write(image_bytes)
            
            cap = caption if caption else f"Figure {self.figure_count}: Ext Diagram"
            self.markdown_lines.append(f"\n![{cap}]({img_path})\n")
            self.figure_count += 1
        except Exception as e:
            logger.error(f"Failed to add external image: {e}")

