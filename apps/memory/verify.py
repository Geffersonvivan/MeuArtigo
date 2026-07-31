"""Verificação de fontes (PROJETO.md §9.2) — anti-alucinação.

Três níveis, do mais barato ao mais rigoroso:
1. Existência da URL (HTTP < 400) + domínio oficial conhecido.
2. Conferência de conteúdo: o `trecho` citado aparece na página?
3. (opcional) cross-check por LLM — não roda em lote por custo; fica como escalonamento.

Fontes `duvidosa`/`inexistente` não entram no texto final.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

import httpx
from django.utils import timezone

from .citations import formatar_abnt
from .models import Reference, StatusVerif

#: domínios oficiais que aumentam a confiança da fonte (PROJETO.md §9.2).
DOMINIOS_OFICIAIS = (
    "planalto.gov.br", "tse.jus.br", "stf.jus.br", "stj.jus.br",
    "senado.leg.br", "camara.leg.br", "in.gov.br", "gov.br", "jus.br",
)

_UA = {"User-Agent": "Mozilla/5.0 (MeuArtigo/1.0; verificador de fontes)"}


def dominio(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def e_oficial(url: str) -> bool:
    host = dominio(url)
    return any(host == d or host.endswith("." + d) or host.endswith(d) for d in DOMINIOS_OFICIAIS)


def _normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).lower().strip()


def _trecho_bate(pagina: str, trecho: str, *, min_palavras: int = 6) -> bool | None:
    """Confere se o trecho (ou seu início) aparece na página. None se não dá pra aferir."""
    trecho = (trecho or "").strip()
    if len(trecho.split()) < min_palavras:
        return None
    alvo = _normalizar(trecho)
    corpo = _normalizar(pagina)
    if alvo in corpo:
        return True
    # tenta pelas primeiras palavras (o snippet pode estar truncado/reformatado)
    prefixo = " ".join(alvo.split()[:min_palavras])
    return prefixo in corpo


def _buscar_pagina(url: str) -> tuple[bool, str]:
    """Devolve (existe, texto_da_pagina). existe=False se status >= 400 ou erro."""
    try:
        r = httpx.get(url, headers=_UA, timeout=20, follow_redirects=True)
    except httpx.HTTPError:
        return (False, "")
    if r.status_code >= 400:
        return (False, "")
    # remove tags para a conferência de conteúdo
    texto = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.DOTALL | re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    return (True, texto)


def verificar_referencia(ref: Reference, *, checar_conteudo: bool = True) -> Reference:
    """Verifica uma referência e grava status + nota + ABNT. Não usa LLM (custo)."""
    if not ref.data_acesso:
        ref.data_acesso = timezone.now().date()

    notas: list[str] = []

    if not ref.url:
        ref.verificada = StatusVerif.DUVIDOSA
        notas.append("sem URL para verificar")
    else:
        existe, pagina = _buscar_pagina(ref.url)
        oficial = e_oficial(ref.url)
        notas.append("domínio oficial" if oficial else "domínio não oficial")

        if not existe:
            ref.verificada = StatusVerif.INEXISTENTE
            notas.append("URL inacessível (>=400 ou erro)")
        else:
            bate = _trecho_bate(pagina, ref.trecho) if checar_conteudo else None
            if bate is True:
                ref.verificada = StatusVerif.OK
                notas.append("trecho confere na página")
            elif bate is False:
                ref.verificada = StatusVerif.DUVIDOSA
                notas.append("trecho NÃO encontrado na página")
            else:
                # URL existe mas não deu pra conferir conteúdo: oficial → ok, senão duvidosa
                ref.verificada = StatusVerif.OK if oficial else StatusVerif.DUVIDOSA
                notas.append("conteúdo não aferível; decidido pelo domínio")

    ref.verificada_em = timezone.now()
    ref.nota_verificacao = "; ".join(notas)
    ref.abnt = formatar_abnt(ref)
    ref.save(update_fields=["verificada", "verificada_em", "nota_verificacao", "abnt", "data_acesso"])
    return ref


def verificar_pendentes(article) -> dict[str, int]:
    """Verifica todas as referências ainda não verificadas de um artigo. Retorna contagem."""
    contagem = {s.value: 0 for s in StatusVerif}
    for ref in article.references.exclude(verificada=StatusVerif.OK):
        verificar_referencia(ref)
        contagem[ref.verificada] += 1
    return contagem
