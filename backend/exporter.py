import os
import io
import re
from typing import List, Dict, Any
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

class Exporter:
    @staticmethod
    def set_cell_background(cell, fill_hex):
        """Sets table cell background color."""
        tcPr = cell._element.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), fill_hex)
        tcPr.append(shd)

    @staticmethod
    def export_to_docx(title: str, markdown_content: str, papers: List[Dict[str, Any]] = None, is_rtl: bool = True) -> bytes:
        """Converts academic paper markdown content into a professionally styled DOCX file."""
        doc = Document()

        # Page setup - Margins 1 inch
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Base style font
        style = doc.styles['Normal']
        font = style.font
        font.name = 'B Nazanin' if is_rtl else 'Times New Roman'
        font.size = Pt(12)
        font.color.rgb = RGBColor(30, 41, 59)

        # Title
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run(title)
        title_run.font.name = 'B Titr' if is_rtl else 'Arial'
        title_run.font.size = Pt(18)
        title_run.bold = True
        title_run.font.color.rgb = RGBColor(15, 23, 42)
        title_para.paragraph_format.space_after = Pt(20)

        lines = markdown_content.split('\n')
        i = 0
        in_table = False
        table_rows = []

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Check table lines
            if line.startswith('|') and line.endswith('|'):
                table_rows.append([c.strip() for c in line[1:-1].split('|')])
                i += 1
                continue
            elif table_rows:
                # Flush table
                Exporter._render_docx_table(doc, table_rows, is_rtl)
                table_rows = []

            # Headers
            if line.startswith('### '):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(14)
                p.paragraph_format.space_after = Pt(6)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_rtl else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(line[4:].strip())
                run.bold = True
                run.font.size = Pt(13)
                run.font.name = 'B Titr' if is_rtl else 'Arial'
                run.font.color.rgb = RGBColor(30, 58, 138)
            elif line.startswith('## '):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(18)
                p.paragraph_format.space_after = Pt(8)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_rtl else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(line[3:].strip())
                run.bold = True
                run.font.size = Pt(14)
                run.font.name = 'B Titr' if is_rtl else 'Arial'
                run.font.color.rgb = RGBColor(15, 23, 42)
            elif line.startswith('# '):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(22)
                p.paragraph_format.space_after = Pt(10)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_rtl else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(line[2:].strip())
                run.bold = True
                run.font.size = Pt(16)
                run.font.name = 'B Titr' if is_rtl else 'Arial'
                run.font.color.rgb = RGBColor(15, 23, 42)
            elif line.startswith('> '):
                # Blockquote / Highlight
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.4)
                p.paragraph_format.right_indent = Inches(0.4)
                p.paragraph_format.space_after = Pt(8)
                run = p.add_run(line[2:].strip())
                run.italic = True
                run.font.color.rgb = RGBColor(71, 85, 105)
            elif line.startswith('---'):
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(12)
            else:
                # Regular paragraph
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_rtl else WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 1.25
                p.paragraph_format.space_after = Pt(8)
                Exporter._add_styled_runs(p, line, is_rtl)

            i += 1

        if table_rows:
            Exporter._render_docx_table(doc, table_rows, is_rtl)

        output = io.BytesIO()
        doc.save(output)
        return output.getvalue()

    @staticmethod
    def _add_styled_runs(paragraph, text: str, is_rtl: bool):
        """Simple inline bold/italic parser for docx."""
        # Split by bold **text**
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                run = paragraph.add_run(part[2:-2])
                run.bold = True
            elif part.startswith('*') and part.endswith('*'):
                run = paragraph.add_run(part[1:-1])
                run.italic = True
            else:
                paragraph.add_run(part)

    @staticmethod
    def _render_docx_table(doc, rows: List[List[str]], is_rtl: bool):
        """Renders markdown table in DOCX."""
        # Filter divider row like |---|---|
        clean_rows = [r for r in rows if not all(c.replace('-', '').replace(':', '').strip() == '' for c in r)]
        if not clean_rows:
            return

        table = doc.add_table(rows=len(clean_rows), cols=len(clean_rows[0]))
        table.style = 'Table Grid'
        
        for r_idx, row in enumerate(clean_rows):
            for c_idx, cell_text in enumerate(row):
                if c_idx < len(table.columns):
                    cell = table.cell(r_idx, c_idx)
                    cell.text = cell_text
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_rtl else WD_ALIGN_PARAGRAPH.LEFT
                    if r_idx == 0:
                        # Header row styling
                        Exporter.set_cell_background(cell, "F1F5F9")
                        for run in p.runs:
                            run.bold = True
                            run.font.size = Pt(10)
                    else:
                        for run in p.runs:
                            run.font.size = Pt(9.5)
        
        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    @staticmethod
    def export_to_ris(papers: List[Dict[str, Any]]) -> str:
        """Exports papers to RIS format compatible with EndNote, Zotero, Mendeley."""
        lines = []
        for p in papers:
            lines.append("TY  - JOUR")
            title = p.get("title", "")
            if title:
                lines.append(f"TI  - {title}")
            for a in p.get("authors") or []:
                lines.append(f"AU  - {a}")
            if p.get("journal_name"):
                lines.append(f"JO  - {p['journal_name']}")
                lines.append(f"JF  - {p['journal_name']}")
            if p.get("publish_year"):
                lines.append(f"PY  - {p['publish_year']}")
            if p.get("doi"):
                lines.append(f"DO  - {p['doi']}")
            if p.get("url"):
                lines.append(f"UR  - {p['url']}")
            if p.get("abstract"):
                lines.append(f"AB  - {p['abstract']}")
            lines.append("ER  - ")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def export_to_enw(papers: List[Dict[str, Any]]) -> str:
        """Exports papers to EndNote (.enw) format."""
        lines = []
        for p in papers:
            lines.append("%0 Journal Article")
            if p.get("title"):
                lines.append(f"%T {p['title']}")
            for a in p.get("authors") or []:
                lines.append(f"%A {a}")
            if p.get("journal_name"):
                lines.append(f"%J {p['journal_name']}")
            if p.get("publish_year"):
                lines.append(f"%D {p['publish_year']}")
            if p.get("doi"):
                lines.append(f"%R {p['doi']}")
            if p.get("url"):
                lines.append(f"%U {p['url']}")
            if p.get("abstract"):
                lines.append(f"%X {p['abstract']}")
            lines.append("")
        return "\n".join(lines)
