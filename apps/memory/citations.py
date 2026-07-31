"""Formatação de citações ABNT (NBR 6023/10520) e resolução de marcadores [[ref:ID]].

PROJETO.md §9.3. A `Reference` é a fonte da verdade; aqui viramos texto ABNT e
resolvemos os marcadores que a LLM usou no corpo do artigo.
"""

from __future__ import annotations

import re
from datetime import date

from .models import Reference, TipoFonte

MARCADOR_RE = re.compile(r"\[\[ref:(\d+)\]\]")

_MESES = {
    1: "jan.", 2: "fev.", 3: "mar.", 4: "abr.", 5: "maio", 6: "jun.",
    7: "jul.", 8: "ago.", 9: "set.", 10: "out.", 11: "nov.", 12: "dez.",
}


def _acesso(d: date | None) -> str:
    return f"{d.day} {_MESES[d.month]} {d.year}" if d else "[s.d.]"


def _ano(ref: Reference) -> str:
    if ref.data_pub:
        return str(ref.data_pub.year)
    return "[s.d.]"


def _sobrenome(ref: Reference) -> str:
    """Chave autor-data (NBR 10520). Para normas usa BRASIL; senão, sobrenome em CAIXA."""
    if ref.tipo in (TipoFonte.LEI, TipoFonte.JURISPRUDENCIA):
        return "BRASIL"
    if ref.autor:
        return ref.autor.split()[-1].upper()
    return "BRASIL" if not ref.autor else ref.autor.upper()


def formatar_abnt(ref: Reference) -> str:
    """Devolve a referência formatada em ABNT (NBR 6023), por tipo de fonte."""
    url = ref.url
    disp = f" Disponível em: {url}. Acesso em: {_acesso(ref.data_acesso)}." if url else ""
    ano = _ano(ref)

    if ref.tipo == TipoFonte.LEI:
        return f"BRASIL. *{ref.titulo}*. Brasília, DF: Presidência da República, {ano}.{disp}"
    if ref.tipo == TipoFonte.JURISPRUDENCIA:
        return f"BRASIL. *{ref.titulo}*. {ano}.{disp}"
    if ref.tipo == TipoFonte.DOUTRINA:
        autor = ref.autor.upper() if ref.autor else "[s.a.]"
        return f"{autor}. *{ref.titulo}*. {ano}."
    # notícia / site
    autor = f"{ref.autor.upper()}. " if ref.autor else ""
    return f"{autor}{ref.titulo}. {ano}.{disp}"


def citacao_no_corpo(ref: Reference) -> str:
    """Citação autor-data para inserir no texto: (BRASIL, 1997)."""
    return f"({_sobrenome(ref)}, {_ano(ref)})"


def resolver_marcadores(texto: str, refs: dict[int, Reference]) -> tuple[str, list[Reference]]:
    """Substitui [[ref:ID]] pela citação autor-data e devolve (texto, refs_usadas em ordem).

    Marcadores para IDs inexistentes ou não verificados são removidos (regra de ouro:
    nunca resolver para uma fonte que não está `ok`)."""
    usados: list[Reference] = []
    vistos: set[int] = set()

    def _sub(m: re.Match) -> str:
        rid = int(m.group(1))
        ref = refs.get(rid)
        if ref is None or not ref.ok:
            return ""  # marcador inválido/não verificado é descartado
        if rid not in vistos:
            vistos.add(rid)
            usados.append(ref)
        return citacao_no_corpo(ref)

    return MARCADOR_RE.sub(_sub, texto), usados


def gerar_referencias_md(refs: list[Reference], *, titulo: str = "Referências") -> str:
    """Lista ABNT (ordenada por sobrenome/título) das referências dadas."""
    if not refs:
        return ""
    itens = sorted({formatar_abnt(r) for r in refs})
    corpo = "\n\n".join(itens)
    return f"## {titulo}\n\n{corpo}\n"
