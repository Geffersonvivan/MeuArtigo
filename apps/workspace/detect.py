"""Detecções determinísticas (grátis, sem LLM) que alimentam os avisos de margem.

- sem-fonte: parágrafo com afirmação factual (lei/ano/número) e SEM citação [[ref]].
- glossário: uso de variante quando o glossário da área tem termo preferido.
Similaridade e "extensão" (linhas > meta) entram depois (embeddings / medição no cliente).
"""

from __future__ import annotations

import re

from .render import render_paragraph

_FATO = re.compile(r"\b(lei|resolu[cç][aã]o|art\.|artigo|s[uú]mula|R\$|\b(19|20)\d{2}\b|\d{3,})", re.I)


def detectar_paragrafo(pid: str, texto: str, refs_by_id: dict, glossario: list) -> tuple[str, list[dict]]:
    """Devolve (html do parágrafo, lista de avisos para ele)."""
    tem_cite = "[[ref:" in texto
    html = render_paragraph(texto, refs_by_id)
    notas: list[dict] = []

    # sem-fonte: afirmação factual sem citação
    if not tem_cite and _FATO.search(texto):
        html = f'<span class="no-source" title="Afirmação sem fonte atribuída">{html}</span>'
        notas.append({
            "id": f"ns-{pid}", "pid": pid, "kind": "err", "source": "det",
            "label": "Sem fonte", "body": "Afirmação factual sem fonte atribuída.",
            "fixAction": "buscar_fonte",
        })

    # glossário: variante fora do vocabulário controlado
    baixo = texto.lower()
    for termo, variantes in glossario:
        for var in variantes:
            if var and var.lower() in baixo and termo.lower() not in baixo:
                notas.append({
                    "id": f"gl-{pid}-{var}", "pid": pid, "kind": "warn", "source": "det",
                    "label": "Glossário",
                    "body": f'"{var}" — o glossário da área usa <em>"{termo}"</em>.',
                    "fixAction": "reescrever",
                })
                break

    return html, notas
