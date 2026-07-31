"""Divisão do artigo.md em seções por cabeçalho Markdown, e recomposição (splice).

Cada seção vai de uma linha de cabeçalho (# … ######) até antes do próximo cabeçalho.
Texto antes do primeiro cabeçalho (raro) vira uma seção de "preâmbulo" sem título.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Section:
    index: int
    nivel: int          # 0 = preâmbulo sem cabeçalho
    heading: str        # texto do cabeçalho (sem os #), "" no preâmbulo
    texto: str          # bloco completo (cabeçalho + corpo), como está no arquivo


def parse_sections(md: str) -> list[Section]:
    linhas = md.splitlines()
    blocos: list[list[str]] = []
    atual: list[str] = []

    for linha in linhas:
        if _HEADING_RE.match(linha):
            if atual:
                blocos.append(atual)
            atual = [linha]
        else:
            atual.append(linha)
    if atual:
        blocos.append(atual)

    secoes: list[Section] = []
    for i, bloco in enumerate(blocos):
        m = _HEADING_RE.match(bloco[0])
        if m:
            nivel, heading = len(m.group(1)), m.group(2).strip()
        else:
            nivel, heading = 0, ""
        secoes.append(Section(index=i, nivel=nivel, heading=heading, texto="\n".join(bloco).strip()))
    return secoes


def replace_section(md: str, index: int, novo_texto: str) -> str:
    """Substitui a seção `index` por `novo_texto`, preservando as demais."""
    secoes = parse_sections(md)
    if index < 0 or index >= len(secoes):
        raise IndexError(f"Seção {index} inexistente (há {len(secoes)}).")
    partes = [s.texto for s in secoes]
    partes[index] = novo_texto.strip()
    return "\n\n".join(p for p in partes if p) + "\n"
