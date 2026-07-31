"""Renderização de parágrafos para o editor: resolve [[ref:ID]] em <span class="cite">.

Marcações .no-source / .similar (detecção determinística) entram na Fatia 3.
"""

from __future__ import annotations

import html
import re

from django.utils.safestring import mark_safe

_MARCADOR = re.compile(r"\[\[ref:(\d+)\]\]")


def render_paragraph(texto: str, refs_by_id: dict) -> str:
    """Escapa o texto e troca [[ref:ID]] por um span .cite clicável (abre aba Fontes)."""

    def _sub(m):
        rid = int(m.group(1))
        ref = refs_by_id.get(rid)
        if not ref:
            return ""
        rotulo = html.escape(ref.short_title())
        cls = "cite" if ref.ok else "cite duvidosa"
        return f'<span class="{cls}" data-ref="{rid}">{rotulo}</span>'

    partes = []
    fim = 0
    for m in _MARCADOR.finditer(texto):
        partes.append(html.escape(texto[fim:m.start()]))
        partes.append(_sub(m))
        fim = m.end()
    partes.append(html.escape(texto[fim:]))
    return mark_safe("".join(partes))
