"""Orquestração do pipeline de escrita (PROJETO.md §3).

Nesta fase implementamos apenas a primeira REDAÇÃO com Claude. As demais etapas
(pesquisa, estrutura, revisão, edição final) entram nas próximas fases.
"""

from __future__ import annotations

import logging

from apps.articles import services as article_services
from apps.articles.models import Article, StatusArtigo
from apps.memory.citations import gerar_referencias_md, resolver_marcadores
from apps.memory.embeddings import EmbedderError
from apps.memory.models import StatusVerif
from apps.memory.retrieval import buscar_semelhantes, indexar_artigo
from apps.memory.sources import criar_referencias_de_fontes
from apps.memory.verify import verificar_pendentes

from .models import LLMCall, Papel
from .prompts import (
    build_edicao_prompt,
    build_estrutura_prompt,
    build_pesquisa_prompt,
    build_redacao_prompt,
    build_revisao_prompt,
)
from .providers import LLMProviderError, LLMResult, get_provider

logger = logging.getLogger(__name__)


def _max_tokens_para(num_paginas: int) -> int:
    """Estimativa de teto de saída a partir da meta de páginas (~1500 tokens/página)."""
    return max(4000, min(32000, num_paginas * 1500))


def _log_call(article: Article, papel: str, result: LLMResult) -> LLMCall:
    return LLMCall.objects.create(
        article=article,
        papel=papel,
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
        ok=True,
    )


def _fontes_md(result: LLMResult) -> str:
    """Apêndice de fontes brutas (NÃO verificadas) de uma etapa Perplexity — insumo p/ Fase 5."""
    if not result.sources:
        return ""
    linhas = [
        f"- {s.get('title') or s.get('url')} — {s.get('url')}"
        for s in result.sources
    ]
    return "\n\n---\n\n## Fontes (brutas, não verificadas — Fase 5)\n" + "\n".join(linhas) + "\n"


def _memoria_para(article: Article) -> list[dict]:
    """Trechos já ditos nesta área (RAG), não fatal se falhar."""
    try:
        sem = buscar_semelhantes(
            f"{article.titulo}. {article.assunto}",
            area_slug=article.area_slug, k=5, exclude_article=article.pk,
        )
        return [{"titulo": s.titulo, "texto": s.texto} for s in sem]
    except EmbedderError as exc:
        logger.warning("Busca de memória falhou (seguindo sem RAG): %s", exc)
        return []


def gerar_primeira_redacao(article: Article, *, provider_name: str = "anthropic") -> LLMCall:
    """Gera a primeira versão do artigo, grava em artigo.md e registra o custo.

    Retorna o LLMCall (registro de tokens/custo). Levanta LLMProviderError se a
    chamada ao provedor falhar — o erro também é persistido no LLMCall.
    """
    # RAG: "o que já foi dito" nesta área, em outros artigos (não fatal se falhar).
    memoria: list[dict] = []
    try:
        semelhantes = buscar_semelhantes(
            f"{article.titulo}. {article.assunto}",
            area_slug=article.area_slug,
            k=5,
            exclude_article=article.pk,
        )
        memoria = [{"titulo": s.titulo, "texto": s.texto} for s in semelhantes]
    except EmbedderError as exc:
        logger.warning("Busca de memória falhou (seguindo sem RAG): %s", exc)

    system, user = build_redacao_prompt(
        titulo=article.titulo,
        assunto=article.assunto,
        area=article.area,
        num_paginas=article.num_paginas,
        num_linhas=article.num_linhas,
        estilo=article.estilo,
        memoria=memoria,
    )

    provider = get_provider(provider_name)

    try:
        result = provider.generate(
            system=system,
            prompt=user,
            max_tokens=_max_tokens_para(article.num_paginas),
        )
    except LLMProviderError as exc:
        LLMCall.objects.create(
            article=article,
            papel=Papel.REDACAO,
            provider=provider_name,
            model=getattr(provider, "default_model", ""),
            ok=False,
            erro=str(exc),
        )
        raise

    # Persiste o corpo via service única (disco + banco).
    article_services.salvar_corpo(article, result.text, status=StatusArtigo.REDACAO)

    # Reindexa a memória a partir do novo texto (não fatal se a Voyage falhar).
    try:
        n_chunks, _ = indexar_artigo(article, result.text)
        logger.info("Artigo %s reindexado em %d chunks", article.pk, n_chunks)
    except EmbedderError as exc:
        logger.warning("Reindexação falhou para o artigo %s: %s", article.pk, exc)

    return LLMCall.objects.create(
        article=article,
        papel=Papel.REDACAO,
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
        ok=True,
    )


def rodar_pipeline_completo(article: Article) -> list[LLMCall]:
    """Pipeline multi-LLM completo (PROJETO.md §3):

    Perplexity(pesquisa) → Claude(estrutura) → Claude(redação) →
    Perplexity(revisão/fato-check) → Claude(edição final).

    Grava os intermediários em rascunhos/ e o texto final em artigo.md, logando o custo
    de cada etapa. As fontes da pesquisa/revisão ficam nos rascunhos como insumo da Fase 5
    (ainda NÃO viram citações no texto — a regra de ouro segue valendo).
    """
    claude = get_provider("anthropic")
    ppx = get_provider("perplexity")
    memoria = _memoria_para(article)
    calls: list[LLMCall] = []

    # [1] PESQUISA — Perplexity (fontes reais/atuais)
    s, u = build_pesquisa_prompt(assunto=article.assunto, area=article.area)
    pesquisa = ppx.generate(system=s, prompt=u, max_tokens=1500, search_recency="year")
    calls.append(_log_call(article, Papel.PESQUISA, pesquisa))
    article_services.salvar_rascunho(article, "00-pesquisa.md", pesquisa.text + _fontes_md(pesquisa))

    # [V] FONTES + VERIFICAÇÃO (Fase 5): cria Reference das fontes reais e verifica.
    criar_referencias_de_fontes(article, pesquisa.sources)
    verificar_pendentes(article)
    refs_ok = list(article.references.filter(verificada=StatusVerif.OK))
    refs_prompt = [{"id": r.pk, "titulo": r.titulo} for r in refs_ok]
    logger.info("Artigo %s: %d fontes verificadas (ok)", article.pk, len(refs_ok))

    # [2] ESTRUTURA — Claude
    s, u = build_estrutura_prompt(
        titulo=article.titulo, assunto=article.assunto, area=article.area,
        num_paginas=article.num_paginas, num_linhas=article.num_linhas,
        estilo=article.estilo, pesquisa=pesquisa.text, memoria=memoria,
    )
    estrutura = claude.generate(system=s, prompt=u, max_tokens=4000)
    calls.append(_log_call(article, Papel.ESTRUTURA, estrutura))
    article_services.salvar_rascunho(article, "01-estrutura.md", estrutura.text)

    # [3] REDAÇÃO — Claude (com roteiro + pesquisa + memória + fontes verificadas)
    s, u = build_redacao_prompt(
        titulo=article.titulo, assunto=article.assunto, area=article.area,
        num_paginas=article.num_paginas, num_linhas=article.num_linhas,
        estilo=article.estilo, memoria=memoria,
        estrutura=estrutura.text, pesquisa=pesquisa.text, referencias=refs_prompt,
    )
    redacao = claude.generate(system=s, prompt=u, max_tokens=_max_tokens_para(article.num_paginas))
    calls.append(_log_call(article, Papel.REDACAO, redacao))
    article_services.salvar_rascunho(article, "02-redacao.md", redacao.text)

    # [4] REVISÃO — Perplexity (fato-check web-grounded)
    s, u = build_revisao_prompt(texto=redacao.text)
    revisao = ppx.generate(system=s, prompt=u, max_tokens=1500, search_recency="year")
    calls.append(_log_call(article, Papel.REVISAO, revisao))
    article_services.salvar_rascunho(article, "03-revisao.md", revisao.text + _fontes_md(revisao))

    # [5] EDIÇÃO FINAL — Claude (aplica revisão, preserva [[ref:ID]])
    s, u = build_edicao_prompt(
        titulo=article.titulo, estilo=article.estilo,
        num_paginas=article.num_paginas, num_linhas=article.num_linhas,
        redacao=redacao.text, revisao=revisao.text, referencias=refs_prompt,
    )
    final = claude.generate(system=s, prompt=u, max_tokens=_max_tokens_para(article.num_paginas))
    calls.append(_log_call(article, Papel.EDICAO, final))

    # [ABNT] Resolve [[ref:ID]] → citação autor-data + seção "Referências".
    refs_by_id = {r.pk: r for r in refs_ok}
    texto_final, usados = resolver_marcadores(final.text, refs_by_id)
    if usados:
        texto_final = texto_final.rstrip() + "\n\n" + gerar_referencias_md(usados)
    article_services.salvar_corpo(article, texto_final, status=StatusArtigo.FINAL)

    # referencias.md: lista ABNT completa das fontes verificadas do artigo.
    ref_md = gerar_referencias_md(refs_ok) or "## Referências\n\n(nenhuma fonte verificada)\n"
    article_services.salvar_referencias(article, ref_md)

    # Reindexa a memória a partir do texto final (não fatal).
    try:
        indexar_artigo(article, texto_final)
    except EmbedderError as exc:
        logger.warning("Reindexação falhou para o artigo %s: %s", article.pk, exc)

    return calls
