"""Detecções determinísticas (grátis, sem LLM) que alimentam os avisos de margem.

- sem-fonte: parágrafo com afirmação factual (lei/ano/número) e SEM citação [[ref]].
- glossário: uso de variante quando o glossário da área tem termo preferido.
Similaridade e "extensão" (linhas > meta) entram depois (embeddings / medição no cliente).
"""

from __future__ import annotations

import re

from .render import render_paragraph

_FATO = re.compile(r"\b(lei|resolu[cç][aã]o|art\.|artigo|s[uú]mula|R\$|\b(19|20)\d{2}\b|\d{3,})", re.I)


def detectar_paragrafo(pid: str, texto: str, refs_by_id: dict, glossario: list,
                       ignorados: set | None = None) -> tuple[str, list[dict]]:
    """Devolve (html do parágrafo, lista de avisos para ele).

    `ignorados`: ids de avisos que o autor dispensou — quando presente, o aviso NÃO
    entra na lista e (para "sem fonte") o sublinhado ondulado também não é aplicado.
    """
    ignorados = ignorados or set()
    tem_cite = "[[ref:" in texto
    html = render_paragraph(texto, refs_by_id)
    notas: list[dict] = []

    # sem-fonte: afirmação factual sem citação
    if not tem_cite and _FATO.search(texto) and f"ns-{pid}" not in ignorados:
        html = f'<span class="no-source" title="Afirmação sem fonte atribuída">{html}</span>'
        notas.append({
            "id": f"ns-{pid}", "pid": pid, "kind": "err", "source": "det",
            "label": "Sem fonte", "body": "Afirmação factual sem fonte atribuída.",
            "fixAction": "buscar_fonte",
        })

    # glossário: variante fora do vocabulário controlado.
    # Casa por PALAVRA INTEIRA (\b) — senão "JE" casaria dentro de "sujeita",
    # "objeto" etc. (falso positivo). Só avisa se o termo preferido não aparece.
    for termo, variantes in glossario:
        for var in variantes:
            if not var:
                continue
            if re.search(rf"\b{re.escape(var)}\b", texto, re.I) and not re.search(
                rf"\b{re.escape(termo)}\b", texto, re.I
            ):
                if f"gl-{pid}-{var}" in ignorados:
                    break
                notas.append({
                    "id": f"gl-{pid}-{var}", "pid": pid, "kind": "warn", "source": "det",
                    "label": "Glossário",
                    "body": f'"{var}" — o glossário da área usa <em>"{termo}"</em>.',
                    "fixInstrucao": f'Substitua "{var}" por "{termo}", o termo preferido do glossário da área.',
                    "fixAction": "reescrever",
                })
                break

    return html, notas
