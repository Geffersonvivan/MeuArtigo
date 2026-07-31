"""Exportação do artigo em Markdown, DOCX e PDF.

Resolve os marcadores [[ref:ID]] para citação autor-data + seção Referências (ABNT).
Se o artigo não estiver 'final', prefixa "RASCUNHO — não citar".
"""

from __future__ import annotations

import io
import re

import markdown as md_lib

from apps.memory.citations import gerar_referencias_md, resolver_marcadores


def resolved_markdown(article) -> str:
    refs = {r.pk: r for r in article.references.filter(verificada="ok")}
    partes = [f"# {article.titulo}"]
    usados = []
    for sec in article.sections.all():
        partes.append(f"## {sec.titulo}")
        resolvido, u = resolver_marcadores(sec.render_corpo(), refs)
        usados.extend(u)
        if resolvido.strip():
            partes.append(resolvido.strip())
    md = "\n\n".join(partes).strip() + "\n"
    if usados:
        md += "\n\n" + gerar_referencias_md(usados)
    if article.status != "final":
        md = "> **RASCUNHO — não citar**\n\n" + md
    return md


def to_markdown(article) -> bytes:
    return resolved_markdown(article).encode("utf-8")


def to_docx(article) -> bytes:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    for raw in resolved_markdown(article).splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=0)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=1)
        elif line.startswith("> "):
            p = doc.add_paragraph()
            r = p.add_run(re.sub(r"[*_>]", "", line[2:]).strip())
            r.italic = True
            r.font.size = Pt(11)
        else:
            doc.add_paragraph(re.sub(r"\*\*(.+?)\*\*", r"\1", line))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def to_pdf(article) -> bytes:
    from xhtml2pdf import pisa

    corpo = md_lib.markdown(resolved_markdown(article), extensions=["extra"])
    html = f"""<html><head><meta charset="utf-8"><style>
      @page {{ margin: 2.5cm; }}
      body {{ font-family: Times, serif; font-size: 12pt; line-height: 1.5; color: #111; }}
      h1 {{ font-size: 20pt; }} h2 {{ font-size: 15pt; margin-top: 18pt; }}
      blockquote {{ color: #b45309; font-weight: bold; }}
      p {{ text-align: justify; }}
    </style></head><body>{corpo}</body></html>"""
    buf = io.BytesIO()
    pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
    return buf.getvalue()


EXPORTERS = {
    "md": (to_markdown, "text/markdown", "md"),
    "docx": (to_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "pdf": (to_pdf, "application/pdf", "pdf"),
}
