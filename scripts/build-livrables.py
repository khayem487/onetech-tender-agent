"""Build the OneTech internship report and defence deck.

The source of truth remains the reviewed Markdown files in ``livrables``.
This script creates polished, editable Office files. PDF export is performed
separately through Microsoft Office on Windows.
"""

from __future__ import annotations

import re
import html
import runpy
from pathlib import Path

import markdown
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor as DocxRGB
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.util import Inches as PInches, Pt as PPt


ROOT = Path(__file__).resolve().parents[1]
LIVRABLES = ROOT / "livrables"
REPORT_MD = LIVRABLES / "RAPPORT_STAGE_FINAL.md"
PRESENTATION_MD = LIVRABLES / "PRESENTATION_SOUTENANCE_FINALE.md"
ARCHITECTURE_PNG = LIVRABLES / "architecture_onetech_tender_agent.png"
REPORT_DOCX = LIVRABLES / "RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx"
PRESENTATION_PPTX = LIVRABLES / "PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx"
REPORT_HTML = LIVRABLES / "RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.html"


# Brand palette shared by the report and the deck.
NAVY = "0B1F3A"
BLUE = "2457A6"
TEAL = "00A7A5"
CYAN = "30C5FF"
ORANGE = "FF9F43"
INK = "172033"
MID = "53657A"
PALE = "F4F7FB"
WHITE = "FFFFFF"
GREEN = "22A06B"
RED = "D64545"
YELLOW = "F2C94C"


def strip_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("`", "").replace("*", "")
    text = text.replace("  ", " ")
    return text.strip()


def set_cell_shading(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), color)


def set_cell_margins(cell, top=120, start=120, bottom=120, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_repeat_heading_keep(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    for tag in ("keepNext", "keepLines"):
        el = OxmlElement(f"w:{tag}")
        p_pr.append(el)


def add_field(paragraph, instruction: str, placeholder: str = "1") -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instr, separate, text, end):
        run._r.append(element)


INLINE_PATTERN = re.compile(r"(\*\*.+?\*\*|`.+?`|\*.+?\*)")


def add_inline_runs(paragraph, text: str, color: str | None = None) -> None:
    pos = 0
    for match in INLINE_PATTERN.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos : match.start()])
            if color:
                run.font.color.rgb = DocxRGB.from_string(color)
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Cascadia Mono"
            run.font.size = Pt(9)
            run.font.color.rgb = DocxRGB.from_string(BLUE)
        else:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        if color:
            run.font.color.rgb = DocxRGB.from_string(color)
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        if color:
            run.font.color.rgb = DocxRGB.from_string(color)


def configure_docx_styles(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.0)

    normal = document.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = DocxRGB.from_string(INK)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for style_name, size, color in (
        ("Title", 30, NAVY),
        ("Heading 1", 20, NAVY),
        ("Heading 2", 15, BLUE),
        ("Heading 3", 12, TEAL),
    ):
        style = document.styles[style_name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = DocxRGB.from_string(color)
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True

    if "Code Block" not in [s.name for s in document.styles]:
        style = document.styles.add_style("Code Block", 1)
    else:
        style = document.styles["Code Block"]
    style.font.name = "Cascadia Mono"
    style.font.size = Pt(8)
    style.font.color.rgb = DocxRGB.from_string(INK)
    style.paragraph_format.left_indent = Cm(0.35)
    style.paragraph_format.right_indent = Cm(0.2)
    style.paragraph_format.space_before = Pt(3)
    style.paragraph_format.space_after = Pt(3)

    if "Figure Caption" not in [s.name for s in document.styles]:
        cap = document.styles.add_style("Figure Caption", 1)
    else:
        cap = document.styles["Figure Caption"]
    cap.font.name = "Aptos"
    cap.font.size = Pt(9)
    cap.font.italic = True
    cap.font.color.rgb = DocxRGB.from_string(MID)
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER


def add_docx_header_footer(document: Document) -> None:
    for section in document.sections:
        section.different_first_page_header_footer = True
        header = section.header
        p = header.paragraphs[0]
        p.text = "ONETECH TENDER AGENT  ·  RAPPORT DE STAGE"
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if p.runs:
            p.runs[0].font.name = "Aptos"
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = DocxRGB.from_string(MID)
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("Khayem Ben Ghorbel   ·   ")
        r.font.size = Pt(8)
        r.font.color.rgb = DocxRGB.from_string(MID)
        add_field(fp, "PAGE", "1")


def add_cover(document: Document) -> None:
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("CY TECH   ×   ONE TECH BUSINESS SOLUTIONS")
    r.font.name = "Aptos"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = DocxRGB.from_string(TEAL)

    document.add_paragraph()
    banner = document.add_table(rows=1, cols=1)
    banner.alignment = WD_TABLE_ALIGNMENT.CENTER
    banner.autofit = False
    cell = banner.cell(0, 0)
    cell.width = Cm(16.5)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    set_cell_shading(cell, NAVY)
    set_cell_margins(cell, top=600, start=500, bottom=600, end=500)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("RAPPORT DE STAGE")
    r.font.name = "Aptos Display"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = DocxRGB.from_string(CYAN)
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Développement d’un système IA agentique\npour la gestion des appels d’offres publics")
    r.font.name = "Aptos Display"
    r.font.size = Pt(25)
    r.font.bold = True
    r.font.color.rgb = DocxRGB.from_string(WHITE)
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("OneTech Tender Agent")
    r.font.name = "Aptos"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = DocxRGB.from_string(ORANGE)

    document.add_paragraph()
    metrics = document.add_table(rows=1, cols=3)
    metrics.alignment = WD_TABLE_ALIGNMENT.CENTER
    values = (("100", "AO centralisées"), ("152/152", "documents traités"), ("67/67", "tests Python"))
    for idx, (value, label) in enumerate(values):
        cell = metrics.cell(0, idx)
        set_cell_shading(cell, PALE)
        set_cell_margins(cell, top=170, start=120, bottom=170, end=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(value)
        r.font.size = Pt(18)
        r.font.bold = True
        r.font.color.rgb = DocxRGB.from_string(BLUE)
        p = cell.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(label)
        r.font.size = Pt(8)
        r.font.color.rgb = DocxRGB.from_string(MID)

    document.add_paragraph()
    rows = (
        ("Réalisé par", "Khayem Ben Ghorbel"),
        ("Établissement", "CY Tech"),
        ("Entreprise d’accueil", "One Tech Business Solutions"),
        ("Encadrant entreprise", "Makram Ben Hamed"),
        ("Période / année universitaire", "26/06/2026–26/08/2026 · 2025–2026"),
    )
    info = document.add_table(rows=len(rows), cols=2)
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row, (label, value) in zip(info.rows, rows):
        set_cell_shading(row.cells[0], NAVY)
        set_cell_shading(row.cells[1], "EEF3F8")
        for cell in row.cells:
            set_cell_margins(cell, top=95, start=120, bottom=95, end=120)
        p = row.cells[0].paragraphs[0]
        r = p.add_run(label)
        r.font.bold = True
        r.font.color.rgb = DocxRGB.from_string(WHITE)
        p = row.cells[1].paragraphs[0]
        r = p.add_run(value)
        r.font.color.rgb = DocxRGB.from_string(INK)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    r = p.add_run("Rapport de stage · Année universitaire 2025–2026")
    r.font.size = Pt(9)
    r.font.italic = True
    r.font.color.rgb = DocxRGB.from_string(MID)
    document.add_page_break()


def add_docx_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    width = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=width)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, source_row in enumerate(rows):
        for j in range(width):
            cell = table.cell(i, j)
            text = source_row[j] if j < len(source_row) else ""
            cell.text = ""
            p = cell.paragraphs[0]
            add_inline_runs(p, text)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell, top=90, start=90, bottom=90, end=90)
            if i == 0:
                set_cell_shading(cell, NAVY)
                for run in p.runs:
                    run.font.bold = True
                    run.font.color.rgb = DocxRGB.from_string(WHITE)
            elif i % 2 == 0:
                set_cell_shading(cell, PALE)
    set_repeat_table_header(table.rows[0])


def build_report() -> None:
    source = REPORT_MD.read_text(encoding="utf-8")
    toc_entries: list[tuple[int, str]] = []
    for source_line in source.splitlines():
        if source_line.startswith("# ") and re.match(r"# \d+\.", source_line):
            toc_entries.append((1, strip_markdown(source_line[2:])))
        elif source_line.startswith("## ") and re.match(r"## \d+\.\d+", source_line):
            toc_entries.append((2, strip_markdown(source_line[3:])))
    start = source.find("## Remerciements")
    if start < 0:
        raise RuntimeError("Section Remerciements introuvable dans le rapport.")
    lines = source[start:].splitlines()

    document = Document()
    configure_docx_styles(document)
    add_cover(document)

    in_code = False
    code_language = ""
    code_lines: list[str] = []
    table_rows: list[list[str]] = []
    list_stack: list[tuple[int, str]] = []

    def flush_table() -> None:
        nonlocal table_rows
        if table_rows:
            filtered = [row for row in table_rows if not all(re.fullmatch(r":?-{3,}:?", c.strip()) for c in row)]
            add_docx_table(document, filtered)
            table_rows = []

    def flush_code() -> None:
        nonlocal code_lines
        if not code_lines:
            return
        p = document.add_paragraph(style="Code Block")
        p.paragraph_format.keep_together = True
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "EEF3F8")
        pPr.append(shd)
        border = OxmlElement("w:pBdr")
        left = OxmlElement("w:left")
        left.set(qn("w:val"), "single")
        left.set(qn("w:sz"), "12")
        left.set(qn("w:color"), TEAL)
        border.append(left)
        pPr.append(border)
        p.add_run("\n".join(code_lines))
        code_lines = []

    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        stripped = raw.strip()

        if stripped.startswith("```"):
            flush_table()
            if in_code:
                flush_code()
                in_code = False
                code_language = ""
            else:
                in_code = True
                code_language = stripped[3:].strip()
            i += 1
            continue
        if in_code:
            code_lines.append(raw)
            i += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            table_rows.append([strip_markdown(c) for c in stripped.strip("|").split("|")])
            i += 1
            continue
        flush_table()

        if not stripped or stripped == "---":
            i += 1
            continue

        image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", stripped)
        if image_match:
            image_path = LIVRABLES / image_match.group(2)
            if image_path.exists():
                p = document.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(str(image_path), width=Inches(6.35))
            i += 1
            continue

        if stripped == "[[TABLE_DES_MATIERES]]":
            toc = document.add_paragraph()
            add_field(
                toc,
                ' TOC \\o "1-2" \\h \\z \\u ',
                "Table des matières — mettre à jour le champ si nécessaire",
            )
            document.add_page_break()
            i += 1
            continue

        if stripped.startswith("### "):
            p = document.add_heading(strip_markdown(stripped[4:]), level=3)
            set_repeat_heading_keep(p)
        elif stripped.startswith("## "):
            title = strip_markdown(stripped[3:])
            if title in ("Remerciements", "Résumé exécutif", "Abstract", "Table des matières") and document.paragraphs:
                document.add_page_break()
            if title == "Table des matières":
                p = document.add_paragraph()
                p.style = document.styles["Title"]
                p.add_run(title)
            else:
                p = document.add_heading(title, level=2)
                set_repeat_heading_keep(p)
        elif stripped.startswith("# "):
            if document.paragraphs and not document.paragraphs[-1].text == "":
                document.add_page_break()
            p = document.add_heading(strip_markdown(stripped[2:]), level=1)
            set_repeat_heading_keep(p)
        elif re.match(r"^[-*] ", stripped):
            p = document.add_paragraph(style="List Bullet")
            add_inline_runs(p, stripped[2:])
        elif re.match(r"^\d+\. ", stripped):
            p = document.add_paragraph(style="List Number")
            add_inline_runs(p, re.sub(r"^\d+\. ", "", stripped))
        elif stripped.startswith("> "):
            p = document.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.7)
            p.paragraph_format.right_indent = Cm(0.4)
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:fill"), "E8F7F6")
            pPr.append(shd)
            add_inline_runs(p, stripped[2:], color=NAVY)
        elif stripped.startswith("*") and stripped.endswith("*"):
            p = document.add_paragraph(style="Figure Caption")
            p.add_run(stripped.strip("*")).italic = True
        else:
            # Merge wrapped Markdown lines into one readable paragraph.
            paragraph_parts = [stripped]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or nxt == "---" or nxt.startswith(("#", "- ", "* ", "> ", "```", "|", "![")) or re.match(r"^\d+\. ", nxt):
                    break
                paragraph_parts.append(nxt)
                j += 1
            p = document.add_paragraph()
            add_inline_runs(p, " ".join(paragraph_parts))
            i = j - 1
        i += 1

    flush_table()
    flush_code()
    add_docx_header_footer(document)
    document.core_properties.title = "OneTech Tender Agent — Rapport de stage"
    document.core_properties.subject = "Système IA agentique pour la gestion des appels d’offres publics"
    document.core_properties.author = "Khayem Ben Ghorbel"
    document.core_properties.keywords = "OpenClaw, HAICOP, PostgreSQL, n8n, OCR, MCP, Telegram"
    document.save(REPORT_DOCX)


def build_report_html() -> None:
    """Create a print-ready A4 HTML fallback for deterministic PDF export."""
    source = REPORT_MD.read_text(encoding="utf-8")
    start = source.find("## Remerciements")
    if start < 0:
        raise RuntimeError("Section Remerciements introuvable dans le rapport.")
    body_source = source[start:].replace("[[TABLE_DES_MATIERES]]", "[TOC]")
    rendered = markdown.markdown(
        body_source,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
        output_format="html5",
    )
    cover = """
    <section class="cover">
      <div class="institutions">CY TECH <span>×</span> ONE TECH BUSINESS SOLUTIONS</div>
      <div class="cover-panel">
        <div class="eyebrow">RAPPORT DE STAGE</div>
        <h1>Développement d’un système IA agentique<br>pour la gestion des appels d’offres publics</h1>
        <h2>OneTech Tender Agent</h2>
      </div>
      <div class="metric-row">
        <div><strong>100</strong><span>AO centralisées</span></div>
        <div><strong>152/152</strong><span>documents traités</span></div>
        <div><strong>67/67</strong><span>tests Python</span></div>
      </div>
      <table class="cover-info">
        <tr><th>Réalisé par</th><td>Khayem Ben Ghorbel</td></tr>
        <tr><th>Établissement</th><td>CY Tech — Cycle ingénieur Informatique ING1</td></tr>
        <tr><th>Entreprise d’accueil</th><td>One Tech Business Solutions</td></tr>
        <tr><th>Encadrant entreprise</th><td>Makram Ben Hamed</td></tr>
        <tr><th>Période</th><td>26 juin 2026 – 26 août 2026 · Année 2025–2026</td></tr>
      </table>
      <p class="cover-date">Rapport de stage · Année universitaire 2025–2026</p>
    </section>
    """
    css = f"""
    @page {{ size: A4; margin: 18mm 17mm 18mm 19mm; }}
    * {{ box-sizing: border-box; }}
    html {{ font-family: 'Aptos', 'Segoe UI', Arial, sans-serif; color: #{INK}; font-size: 10.25pt; }}
    body {{ margin: 0; line-height: 1.48; background: white; }}
    .cover {{ page-break-after: always; min-height: 0; display: flex; flex-direction: column; justify-content: flex-start; }}
    .institutions {{ text-align:center; color: #{TEAL}; font-weight: 800; letter-spacing: 1px; margin: 3mm 0 8mm; }}
    .institutions span {{ color: #{ORANGE}; padding: 0 7px; }}
    .cover-panel {{ background: #{NAVY}; color: white; border-radius: 14px; padding: 12mm 12mm; text-align:center; }}
    .cover-panel .eyebrow {{ color: #{CYAN}; font-size: 11pt; font-weight: 800; letter-spacing: 1.4px; }}
    .cover-panel h1 {{ color:white; font-size: 25pt; line-height:1.16; margin: 8mm 0 5mm; border:0; page-break-before:avoid; }}
    .cover-panel h2 {{ color: #{ORANGE}; font-size: 15pt; margin:0; }}
    .metric-row {{ display:grid; grid-template-columns: repeat(3,1fr); gap: 6mm; margin: 6mm 0; }}
    .metric-row div {{ background: #{PALE}; border:1px solid #dce5ee; border-radius:10px; text-align:center; padding:5mm 2mm; }}
    .metric-row strong {{ display:block; color: #{BLUE}; font-size:19pt; }}
    .metric-row span {{ display:block; color: #{MID}; font-size:8.5pt; font-weight:700; margin-top:1.5mm; }}
    .cover-info {{ width:100%; border-collapse:separate; border-spacing:0 1.5mm; }}
    .cover-info th {{ width:34%; background:#{NAVY}; color:white; text-align:left; padding:1.6mm 3mm; border-radius:6px 0 0 6px; }}
    .cover-info td {{ background:#eef3f8; padding:1.6mm 3mm; border-radius:0 6px 6px 0; }}
    .cover-date {{ text-align:center; color:#{MID}; font-style:italic; margin-top:2mm; font-size:8pt; }}
    h1 {{ color:#{NAVY}; font-size:20pt; line-height:1.2; margin:0 0 7mm; padding-bottom:2mm; border-bottom:3px solid #{TEAL}; page-break-before:always; page-break-after:avoid; }}
    h2 {{ color:#{BLUE}; font-size:15pt; margin:8mm 0 3mm; page-break-after:avoid; }}
    h3 {{ color:#{TEAL}; font-size:12pt; margin:5mm 0 2mm; page-break-after:avoid; }}
    p {{ margin:0 0 3mm; text-align:justify; orphans:3; widows:3; }}
    ul,ol {{ margin:2mm 0 4mm 6mm; padding-left:5mm; }}
    li {{ margin:1mm 0; }}
    blockquote {{ margin:4mm 0; padding:3mm 5mm; background:#e8f7f6; border-left:4px solid #{TEAL}; color:#{NAVY}; }}
    table {{ width:100%; border-collapse:collapse; margin:4mm 0 6mm; font-size:9pt; page-break-inside:auto; }}
    th {{ background:#{NAVY}; color:white; text-align:left; padding:2.2mm; }}
    td {{ border:1px solid #dce5ee; padding:2.1mm; vertical-align:top; }}
    tr:nth-child(even) td {{ background:#{PALE}; }}
    tr {{ page-break-inside:avoid; }}
    pre {{ white-space:pre-wrap; word-break:break-word; background:#eef3f8; border-left:4px solid #{TEAL}; padding:3mm; font:8pt 'Cascadia Mono', Consolas, monospace; page-break-inside:avoid; }}
    code {{ font-family:'Cascadia Mono', Consolas, monospace; color:#{BLUE}; font-size:.9em; }}
    img {{ display:block; max-width:100%; max-height:150mm; object-fit:contain; margin:5mm auto 2mm; page-break-inside:avoid; }}
    em {{ color:#{MID}; }}
    .toc {{ background:#{PALE}; border-radius:10px; padding:5mm 8mm; }}
    .toc ul {{ list-style:none; padding-left:0; }}
    .toc ul ul {{ padding-left:6mm; }}
    .toc a {{ color:#{NAVY}; text-decoration:none; }}
    a {{ color:#{BLUE}; }}
    """
    document = f"""<!doctype html>
    <html lang="fr"><head><meta charset="utf-8">
    <title>OneTech Tender Agent — Rapport de stage</title>
    <style>{css}</style></head><body>{cover}<main>{rendered}</main></body></html>"""
    REPORT_HTML.write_text(document, encoding="utf-8")


# ---------- PowerPoint helpers ----------


def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def set_slide_background(slide, color: str) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb(color)


def add_rect(slide, x, y, w, h, fill, radius=True, line=None, transparency=0):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, PInches(x), PInches(y), PInches(w), PInches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    shape.fill.transparency = transparency
    if line:
        shape.line.color.rgb = rgb(line)
        shape.line.width = PPt(1)
    else:
        shape.line.fill.background()
    return shape


def add_text(slide, text, x, y, w, h, size=18, color=INK, bold=False,
             align=PP_ALIGN.LEFT, font="Aptos", valign=MSO_ANCHOR.TOP,
             margin=0.05, italic=False):
    box = slide.shapes.add_textbox(PInches(x), PInches(y), PInches(w), PInches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = PInches(margin)
    tf.margin_right = PInches(margin)
    tf.margin_top = PInches(margin)
    tf.margin_bottom = PInches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    p.space_after = 0
    r = p.add_run()
    r.text = text
    r.font.name = font
    r.font.size = PPt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = rgb(color)
    return box


def add_multiline(slide, lines, x, y, w, h, size=17, color=INK,
                  bullet=True, accent=TEAL, gap=8):
    box = slide.shapes.add_textbox(PInches(x), PInches(y), PInches(w), PInches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = PInches(0.05)
    tf.margin_right = PInches(0.02)
    tf.margin_top = PInches(0.02)
    first = True
    for line in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = 0
        p.space_after = PPt(gap)
        p.line_spacing = 1.05
        p.alignment = PP_ALIGN.LEFT
        if bullet:
            p.text = "•  " + strip_markdown(line)
        else:
            p.text = strip_markdown(line)
        for run in p.runs:
            run.font.name = "Aptos"
            run.font.size = PPt(size)
            run.font.color.rgb = rgb(color)
    return box


def add_top_bar(slide, title: str, number: int, kicker="ONETECH TENDER AGENT") -> None:
    add_rect(slide, 0, 0, 13.333, 0.12, TEAL, radius=False)
    add_text(slide, kicker, 0.55, 0.28, 5.2, 0.28, size=9, color=TEAL, bold=True)
    add_text(slide, title, 0.55, 0.67, 12.0, 0.58, size=25, color=NAVY, bold=True, font="Aptos Display")
    add_text(slide, f"{number:02d}", 12.15, 0.33, 0.65, 0.35, size=12, color=MID, bold=True, align=PP_ALIGN.RIGHT)


def add_footer(slide, number: int) -> None:
    add_rect(slide, 0.55, 7.13, 12.23, 0.018, "D9E1EA", radius=False)
    add_text(slide, "Khayem Ben Ghorbel  ·  CY Tech × One Tech Business Solutions", 0.58, 7.18, 9.0, 0.2, size=7.5, color=MID)
    add_text(slide, str(number), 12.2, 7.18, 0.55, 0.2, size=7.5, color=MID, align=PP_ALIGN.RIGHT)


def add_card(slide, title, body, x, y, w, h, accent=TEAL, title_size=15, body_size=11.5):
    add_rect(slide, x, y, w, h, WHITE, radius=True, line="DCE5EE")
    add_rect(slide, x, y, 0.08, h, accent, radius=False)
    add_text(slide, title, x + 0.25, y + 0.18, w - 0.45, 0.35, size=title_size, color=NAVY, bold=True)
    add_text(slide, body, x + 0.25, y + 0.68, w - 0.45, h - 0.85, size=body_size, color=MID)


def add_metric(slide, value, label, x, y, w=2.25, h=1.25, color=TEAL):
    add_rect(slide, x, y, w, h, WHITE, radius=True, line="DCE5EE")
    add_text(slide, value, x + 0.12, y + 0.12, w - 0.24, 0.53, size=24, color=color, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, label, x + 0.14, y + 0.72, w - 0.28, 0.32, size=10, color=MID, bold=True, align=PP_ALIGN.CENTER)


def add_notes(slide, notes: str) -> None:
    try:
        tf = slide.notes_slide.notes_text_frame
        tf.text = notes.strip()
    except Exception:
        pass


def parse_presentation_notes() -> dict[int, str]:
    text = PRESENTATION_MD.read_text(encoding="utf-8")
    notes: dict[int, str] = {}
    for match in re.finditer(
        r"## Diapositive (\d+) .*?### Notes orateur\s+(.+?)(?=\n---|\Z)",
        text,
        flags=re.S,
    ):
        notes[int(match.group(1))] = strip_markdown(match.group(2).replace("\n", " "))
    return notes


def create_deck() -> None:
    # The defence deck has its own visual generator. Keep this wrapper as the
    # single public entry point so a full rebuild cannot restore stale slides.
    runpy.run_path(str(LIVRABLES / "_tools" / "generate_soutenance.py"), run_name="__main__")
    return

    # Legacy implementation kept below temporarily for historical comparison.
    prs = Presentation()
    prs.slide_width = PInches(13.333)
    prs.slide_height = PInches(7.5)
    blank = prs.slide_layouts[6]
    notes = parse_presentation_notes()

    # 1 — title
    slide = prs.slides.add_slide(blank)
    set_slide_background(slide, NAVY)
    add_rect(slide, 0, 0, 13.333, 0.15, TEAL, radius=False)
    add_rect(slide, 9.7, -0.35, 4.2, 4.2, BLUE, radius=True, transparency=25)
    add_rect(slide, 10.5, 3.5, 3.8, 3.8, TEAL, radius=True, transparency=20)
    add_text(slide, "PROJET DE STAGE · CY TECH × ONE TECH", 0.72, 0.72, 7.8, 0.35, size=11, color=CYAN, bold=True)
    add_text(slide, "OneTech\nTender Agent", 0.72, 1.35, 8.0, 1.65, size=36, color=WHITE, bold=True, font="Aptos Display")
    add_text(slide, "Système IA agentique pour collecter, analyser et diffuser les appels d’offres publics", 0.77, 3.15, 7.8, 1.0, size=19, color="DDE7F3", bold=False)
    add_text(slide, "Khayem Ben Ghorbel", 0.77, 5.0, 4.0, 0.4, size=17, color=WHITE, bold=True)
    add_text(slide, "Soutenance de stage · 2026", 0.77, 5.45, 4.5, 0.3, size=11, color="A9B9CB")
    add_metric(slide, "100", "AO centralisées", 6.05, 5.72, 2.0, 1.15, TEAL)
    add_metric(slide, "152", "documents traités", 8.28, 5.72, 2.0, 1.15, CYAN)
    add_metric(slide, "3", "canaux de diffusion", 10.51, 5.72, 2.0, 1.15, ORANGE)
    add_notes(slide, notes.get(1, ""))

    # 2 — problem
    slide = prs.slides.add_slide(blank); set_slide_background(slide, PALE); add_top_bar(slide, "Le problème métier", 2)
    add_card(slide, "AVANT", "Informations dispersées\n\nFormats hétérogènes\n\nÉchéances et critères difficiles à suivre", 0.65, 1.55, 5.7, 4.65, RED, 18, 17)
    add_card(slide, "BESOIN", "Centraliser les faits officiels\n\nPrioriser les opportunités\n\nProduire une recommandation explicable", 6.95, 1.55, 5.7, 4.65, TEAL, 18, 17)
    add_rect(slide, 5.95, 3.2, 1.42, 0.62, NAVY, radius=True)
    add_text(slide, "→", 6.05, 3.22, 1.2, 0.4, size=24, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 2); add_notes(slide, notes.get(2, ""))

    # 3 — scope
    slide = prs.slides.add_slide(blank); set_slide_background(slide, PALE); add_top_bar(slide, "Objectifs et périmètre du MVP", 3)
    included = ["Collecter HAICOP", "Stocker et dédupliquer", "Lire PDF, DOCX, DOC et scans", "Analyser Go/No-Go", "Diffuser Gmail + Telegram", "Exposer les outils via MCP"]
    excluded = ["Digest Gmail", "Bot Telegram", "Cinq outils MCP", "Restauration validée"]
    add_rect(slide, 0.65, 1.5, 7.1, 4.85, WHITE, radius=True, line="DCE5EE")
    add_text(slide, "INCLUS", 0.95, 1.8, 2.1, 0.35, size=16, color=GREEN, bold=True)
    add_multiline(slide, included, 0.95, 2.35, 6.35, 3.6, size=16, color=INK, bullet=True)
    add_rect(slide, 8.05, 1.5, 4.6, 4.85, "FFF4F2", radius=True, line="F2D7D3")
    add_text(slide, "PREUVES LIVRÉES", 8.35, 1.8, 3.6, 0.35, size=16, color=GREEN, bold=True)
    add_multiline(slide, excluded, 8.35, 2.35, 3.75, 3.5, size=15, color=INK, bullet=True)
    add_footer(slide, 3); add_notes(slide, notes.get(3, ""))

    # 4 — roles
    slide = prs.slides.add_slide(blank); set_slide_background(slide, WHITE); add_top_bar(slide, "Un système agentique, pas seulement un LLM", 4)
    roles = [
        ("OpenClaw", "orchestration", BLUE), ("Modèle", "raisonnement", ORANGE),
        ("Python / SQL / OCR", "exécution fiable", TEAL), ("Skills", "procédures", GREEN),
        ("Phi-4 Mini", "second avis", MID),
    ]
    x = 0.65
    for title, body, color in roles:
        add_card(slide, title, body, x, 1.7, 2.32, 2.1, color, 14, 12)
        x += 2.48
    add_rect(slide, 1.25, 4.45, 10.83, 1.15, NAVY, radius=True)
    add_text(slide, "« L’agent utilise un modèle, mais l’agent n’est pas le modèle. »", 1.55, 4.72, 10.2, 0.5, size=21, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "Le code gère ce qui doit être déterministe ; le modèle intervient là où le sens compte.", 1.6, 5.92, 10.1, 0.35, size=12, color=MID, align=PP_ALIGN.CENTER)
    add_footer(slide, 4); add_notes(slide, notes.get(4, ""))

    # 5 — architecture
    slide = prs.slides.add_slide(blank); set_slide_background(slide, WHITE); add_top_bar(slide, "Architecture de bout en bout", 5)
    if ARCHITECTURE_PNG.exists():
        slide.shapes.add_picture(str(ARCHITECTURE_PNG), PInches(0.55), PInches(1.32), width=PInches(12.25), height=PInches(5.55))
    add_footer(slide, 5); add_notes(slide, notes.get(5, ""))

    # 6 — database
    slide = prs.slides.add_slide(blank); set_slide_background(slide, PALE); add_top_bar(slide, "Collecte HAICOP et socle PostgreSQL", 6)
    db_nodes = [("collectes", "journal"), ("appels_offres", "faits JSONB"), ("documents_ao", "fichiers + texte"), ("analyses_ao", "scores + fiche")]
    x = 0.7
    for idx, (name, desc) in enumerate(db_nodes):
        add_card(slide, name, desc, x, 1.65, 2.65, 1.55, TEAL if idx > 0 else BLUE, 14, 11)
        if idx < len(db_nodes) - 1:
            add_text(slide, "→", x + 2.62, 2.07, 0.42, 0.35, size=20, color=MID, bold=True, align=PP_ALIGN.CENTER)
        x += 3.05
    add_card(slide, "IDEMPOTENCE", "UPSERT par tender_id\nUnicité documentaire\nTransactions et clés étrangères", 0.9, 4.05, 3.55, 1.7, GREEN, 15, 13)
    add_card(slide, "TRAÇABILITÉ", "Payload HAICOP original\nHorodatage des collectes\nErreurs et volumes journalisés", 4.85, 4.05, 3.55, 1.7, BLUE, 15, 13)
    add_card(slide, "SÉPARATION", "Faits officiels ≠ analyse IA\nRejeu sans doublon\nAudit possible", 8.8, 4.05, 3.55, 1.7, ORANGE, 15, 13)
    add_footer(slide, 6); add_notes(slide, notes.get(6, ""))

    # 7 — documents
    slide = prs.slides.add_slide(blank); set_slide_background(slide, WHITE); add_top_bar(slide, "Pipeline documentaire complet", 7)
    stages = ["Télécharger", "Valider", "SHA-256", "Extraire", "OCR / DOC", "PostgreSQL"]
    x = 0.45
    for idx, stage in enumerate(stages):
        add_rect(slide, x, 1.68, 1.78, 0.9, TEAL if idx in (4, 5) else BLUE, radius=True)
        add_text(slide, stage, x + 0.07, 1.96, 1.64, 0.32, size=13, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        if idx < len(stages) - 1:
            add_text(slide, "→", x + 1.75, 1.94, 0.38, 0.3, size=18, color=MID, bold=True, align=PP_ALIGN.CENTER)
        x += 2.12
    add_metric(slide, "152 / 152", "fichiers + hash + texte", 0.9, 3.45, 3.4, 1.5, TEAL)
    add_metric(slide, "41 · 35 · 74", "PDF · DOC · DOCX", 4.95, 3.45, 3.4, 1.5, BLUE)
    add_metric(slide, "fra + ara + eng", "OCR Tesseract", 9.0, 3.45, 3.4, 1.5, ORANGE)
    add_text(slide, "Extraction native d’abord · OCR uniquement quand le texte manque · traitement reprenable", 1.1, 5.55, 11.1, 0.55, size=15, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 7); add_notes(slide, notes.get(7, ""))

    # 8 — scoring
    slide = prs.slides.add_slide(blank); set_slide_background(slide, PALE); add_top_bar(slide, "Analyse Go/No-Go traçable", 8)
    score_items = [("Adéquation", "20 / 25"), ("Délai", "8 / 25"), ("Administratif", "4 / 25"), ("Risque", "4 / 25")]
    for idx, (label, value) in enumerate(score_items):
        row, col = divmod(idx, 2)
        add_card(slide, label, value, 0.75 + col * 3.05, 1.55 + row * 1.45, 2.7, 1.15, [TEAL, BLUE, ORANGE, RED][idx], 13, 18)
    add_rect(slide, 7.2, 1.55, 5.25, 4.25, NAVY, radius=True)
    add_text(slide, "CAS DÉMONTRÉ", 7.55, 1.92, 3.2, 0.35, size=12, color=CYAN, bold=True)
    add_text(slide, "Tender-103307", 7.55, 2.38, 4.1, 0.45, size=24, color=WHITE, bold=True)
    add_text(slide, "2/2 documents lus", 7.55, 3.08, 3.6, 0.35, size=15, color="DDE7F3")
    add_text(slide, "36 / 100", 7.55, 3.75, 2.25, 0.55, size=30, color=ORANGE, bold=True)
    add_rect(slide, 10.05, 3.78, 1.75, 0.52, RED, radius=True)
    add_text(slide, "NO_GO", 10.12, 3.88, 1.6, 0.27, size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "Replay du même contexte → même analyse ID 53", 7.55, 4.75, 4.2, 0.45, size=13, color="DDE7F3", bold=True)
    add_text(slide, "Une analyse partielle ne peut jamais produire un GO définitif.", 0.9, 5.65, 5.7, 0.5, size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 8); add_notes(slide, notes.get(8, ""))

    # 9 — automation
    slide = prs.slides.add_slide(blank); set_slide_background(slide, WHITE); add_top_bar(slide, "Automatisation et diffusion multicanale", 9)
    add_rect(slide, 0.8, 1.55, 11.75, 0.72, NAVY, radius=True)
    add_text(slide, "08:00 · jours ouvrés · Europe/Paris", 1.05, 1.74, 3.2, 0.3, size=14, color=WHITE, bold=True)
    add_text(slide, "n8n  →  ao-worker  →  OpenClaw  →  collecte / analyse / digest", 4.15, 1.74, 7.75, 0.3, size=14, color="DDE7F3", bold=True, align=PP_ALIGN.CENTER)
    channels = [("MAILPIT", "preuve locale", BLUE), ("GMAIL", "multi-destinataires", TEAL), ("TELEGRAM", "digest + réponses", CYAN)]
    for idx, (name, desc, color) in enumerate(channels):
        add_card(slide, name, desc, 0.85 + idx * 4.15, 3.05, 3.8, 1.8, color, 17, 14)
    add_text(slide, "Registre PostgreSQL anti-doublon par canal et destinataire", 1.4, 5.5, 10.55, 0.55, size=16, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 9); add_notes(slide, notes.get(9, ""))

    # 10 — MCP/Phi
    slide = prs.slides.add_slide(blank); set_slide_background(slide, PALE); add_top_bar(slide, "Interopérabilité et expérimentation locale", 10)
    add_rect(slide, 0.65, 1.45, 5.8, 4.9, WHITE, radius=True, line="DCE5EE")
    add_text(slide, "MCP · 5 outils bornés", 0.95, 1.78, 4.7, 0.45, size=19, color=TEAL, bold=True)
    add_multiline(slide, ["collect_tenders", "list_open_tenders", "get_tender", "analyze_tender", "generate_digest"], 1.0, 2.5, 4.8, 3.3, size=16, color=INK, bullet=False, gap=8)
    add_rect(slide, 6.85, 1.45, 5.8, 4.9, NAVY, radius=True)
    add_text(slide, "Phi-4 Mini via Ollama", 7.2, 1.78, 4.7, 0.45, size=19, color=CYAN, bold=True)
    add_text(slide, "79–105 s / AO", 7.2, 2.65, 4.5, 0.65, size=28, color=ORANGE, bold=True)
    add_multiline(slide, ["2 NO_GO attendus retrouvés", "justifications parfois inventées", "second avis uniquement"], 7.2, 3.55, 4.6, 2.05, size=15, color=WHITE, bullet=True)
    add_rect(slide, 9.78, 5.42, 2.25, 0.5, ORANGE, radius=True)
    add_text(slide, "BENCHMARK TERMINÉ", 9.83, 5.53, 2.15, 0.25, size=11, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 10); add_notes(slide, notes.get(10, ""))

    # 11 — metrics
    slide = prs.slides.add_slide(blank); set_slide_background(slide, WHITE); add_top_bar(slide, "Résultats et preuves de qualité", 11)
    metrics = [("100", "AO stockées", TEAL), ("152 / 152", "documents complets", BLUE), ("0", "doublon AO / document", GREEN), ("67 / 67", "tests Python", ORANGE), ("6 / 6", "scripts SQL", CYAN), ("9", "tables restaurées", NAVY)]
    for idx, (value, label, color) in enumerate(metrics):
        row, col = divmod(idx, 3)
        add_metric(slide, value, label, 0.8 + col * 4.18, 1.55 + row * 1.75, 3.65, 1.4, color)
    add_text(slide, "Complétude · idempotence · reproductibilité · auditabilité", 1.1, 5.55, 11.1, 0.55, size=17, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 11); add_notes(slide, notes.get(11, ""))

    # 12 — demo
    slide = prs.slides.add_slide(blank); set_slide_background(slide, PALE); add_top_bar(slide, "Démonstration de bout en bout", 12)
    steps = ["Healthcheck", "PostgreSQL", "Analyse OpenClaw", "Fiche persistée", "Replay", "Gmail + Telegram"]
    for idx, label in enumerate(steps):
        y = 1.45 + idx * 0.76
        add_rect(slide, 0.8, y, 0.48, 0.48, TEAL, radius=True)
        add_text(slide, str(idx + 1), 0.88, y + 0.08, 0.32, 0.25, size=12, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, label, 1.55, y + 0.06, 4.8, 0.35, size=15, color=INK, bold=True)
    add_card(slide, "PLAN DE SECOURS", "HAICOP indisponible → données persistées\n\nModèle lent → fiche validée\n\nCanal externe indisponible → Mailpit", 7.0, 1.55, 5.15, 3.65, ORANGE, 17, 14)
    add_text(slide, "Prouver : sources lues · décision persistée · aucun doublon au replay", 6.95, 5.63, 5.25, 0.58, size=13.5, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_footer(slide, 12); add_notes(slide, notes.get(12, ""))

    # 13 — limits and skills
    slide = prs.slides.add_slide(blank); set_slide_background(slide, WHITE); add_top_bar(slide, "Qualité et apprentissages", 13)
    limits = ["SHA-256", "Idempotence", "Outils bornés", "Faits séparés", "Backup restauré", "Validation humaine"]
    skills = ["Architecture agentique", "Python & parsing", "PostgreSQL & JSONB", "Docker & n8n", "OAuth & Telegram", "Tests & sécurité"]
    add_rect(slide, 0.65, 1.5, 5.8, 4.85, "FFF4F2", radius=True, line="F2D7D3")
    add_text(slide, "GARDE-FOUS LIVRÉS", 0.95, 1.82, 4.3, 0.35, size=16, color=GREEN, bold=True)
    add_multiline(slide, limits, 0.95, 2.35, 4.95, 3.55, size=14.5, color=INK, bullet=True)
    add_rect(slide, 6.85, 1.5, 5.8, 4.85, "EAF8F7", radius=True, line="CBE8E6")
    add_text(slide, "COMPÉTENCES ACQUISES", 7.15, 1.82, 4.6, 0.35, size=16, color=TEAL, bold=True)
    add_multiline(slide, skills, 7.15, 2.35, 4.95, 3.55, size=14.5, color=INK, bullet=True)
    add_footer(slide, 13); add_notes(slide, notes.get(13, ""))

    # 14 — conclusion
    slide = prs.slides.add_slide(blank); set_slide_background(slide, NAVY)
    add_rect(slide, 0, 0, 13.333, 0.15, TEAL, radius=False)
    add_text(slide, "CONCLUSION", 0.72, 0.55, 3.0, 0.32, size=11, color=CYAN, bold=True)
    add_text(slide, "Une chaîne de décision\nexplicable, testée et réutilisable", 0.72, 1.25, 7.2, 1.45, size=29, color=WHITE, bold=True, font="Aptos Display")
    add_multiline(slide, ["Base factuelle centralisée", "Analyse traçable", "Diffusion multicanale idempotente", "Architecture extensible par skills et MCP"], 0.78, 3.15, 5.75, 2.4, size=15.5, color="DDE7F3", bullet=True)
    add_rect(slide, 7.25, 1.25, 5.35, 4.65, "17385E", radius=True)
    add_text(slide, "RÉSULTATS", 7.6, 1.62, 3.6, 0.35, size=15, color=ORANGE, bold=True)
    add_multiline(slide, ["Mesurer le gain métier", "Calibrer le scoring", "Surveiller les modifications d’AO", "Ajouter un tableau de bord", "Étendre les sources publiques"], 7.55, 2.25, 4.4, 3.1, size=15, color=WHITE, bullet=True)
    add_text(slide, "Questions ?", 0.75, 6.42, 3.0, 0.45, size=22, color=TEAL, bold=True)
    add_text(slide, "Khayem Ben Ghorbel", 9.0, 6.5, 3.5, 0.3, size=10, color="A9B9CB", align=PP_ALIGN.RIGHT)
    add_notes(slide, notes.get(14, ""))

    prs.core_properties.title = "OneTech Tender Agent — Soutenance"
    prs.core_properties.subject = "Stage — système IA agentique pour les appels d’offres publics"
    prs.core_properties.author = "Khayem Ben Ghorbel"
    prs.core_properties.keywords = "OpenClaw, HAICOP, PostgreSQL, n8n, OCR, MCP, Telegram"
    prs.save(PRESENTATION_PPTX)


if __name__ == "__main__":
    build_report()
    build_report_html()
    create_deck()
    print(REPORT_DOCX)
    print(REPORT_HTML)
    print(PRESENTATION_PPTX)
