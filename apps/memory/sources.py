"""Cria registros `Reference` a partir das fontes reais retornadas pela Perplexity.

As fontes entram como `pendente`; a verificação (verify.py) define o status. Só as `ok`
podem ser citadas no texto (regra de ouro §9.2).
"""

from __future__ import annotations

import re
from datetime import date

from .models import Reference, TipoFonte


def inferir_tipo(url: str, titulo: str) -> str:
    u = (url or "").lower()
    t = (titulo or "").lower()
    if "planalto.gov.br" in u or re.search(r"\b(lei|decreto|constitui|resolu[cç])", t):
        return TipoFonte.LEI
    if any(d in u for d in ("tse.jus.br", "stf.jus.br", "stj.jus.br")) and re.search(
        r"ac[oó]rd|recurso|habeas|s[uú]mula|processo|mandado", t
    ):
        return TipoFonte.JURISPRUDENCIA
    if re.search(r"noticia|not[ií]cias|/news/", u):
        return TipoFonte.NOTICIA
    return TipoFonte.SITE


def _parse_data(valor) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def criar_referencias_de_fontes(article, sources: list[dict]) -> list[Reference]:
    """Cria (sem duplicar por URL) Reference a partir de search_results da Perplexity."""
    criadas: list[Reference] = []
    existentes = set(article.references.exclude(url="").values_list("url", flat=True))

    for s in sources:
        url = (s.get("url") or "").strip()
        titulo = (s.get("title") or url or "Fonte sem título").strip()[:400]
        if url and url in existentes:
            continue
        ref = Reference.objects.create(
            article=article,
            tipo=inferir_tipo(url, titulo),
            titulo=titulo,
            url=url,
            trecho=(s.get("snippet") or "").strip(),
            data_pub=_parse_data(s.get("date") or s.get("last_updated")),
        )
        criadas.append(ref)
        if url:
            existentes.add(url)
    return criadas
