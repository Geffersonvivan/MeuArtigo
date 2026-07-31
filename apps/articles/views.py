from pathlib import Path

import markdown as md_lib
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from apps.llm.pipeline import gerar_primeira_redacao, rodar_pipeline_completo
from apps.llm.providers import LLMProviderError

from .forms import ArticleForm
from .models import Article
from .services import ArticleExistsError, ArticleParams, create_article


def article_list(request):
    """Home: lista os artigos existentes."""
    artigos = Article.objects.all()
    return render(request, "articles/list.html", {"artigos": artigos})


def article_create(request):
    """Formulário de criação → cria pasta física + registro (via service)."""
    if request.method == "POST":
        form = ArticleForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            params = ArticleParams(
                titulo=cd["titulo"],
                assunto=cd["assunto"],
                area=cd["area"],
                num_paginas=cd["num_paginas"],
                num_linhas=cd["num_linhas"],
                estilo=cd["estilo"],
            )
            try:
                artigo = create_article(params)
            except ArticleExistsError as exc:
                form.add_error(None, str(exc))
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"Artigo “{artigo.titulo}” criado.")
                return redirect(artigo.get_absolute_url())
    else:
        form = ArticleForm()

    return render(request, "articles/form.html", {"form": form})


def article_detail(request, pk):
    """Detalhe do artigo: parâmetros + caminho físico + arquivos + corpo do artigo.md."""
    artigo = get_object_or_404(Article, pk=pk)
    pasta = Path(artigo.pasta)
    arquivos = sorted(p.name for p in pasta.iterdir()) if pasta.exists() else []

    corpo = ""
    md = pasta / "artigo.md"
    if md.exists():
        corpo = md.read_text(encoding="utf-8")
    tem_redacao = "<!-- Conteúdo gerado" not in corpo and corpo.strip() != ""
    corpo_html = mark_safe(md_lib.markdown(corpo, extensions=["extra", "sane_lists"])) if tem_redacao else ""

    rascunhos_dir = pasta / "rascunhos"
    rascunhos = sorted(p.name for p in rascunhos_dir.iterdir()) if rascunhos_dir.exists() else []

    custos = list(artigo.llm_calls.all())
    total_usd = sum((c.cost_usd for c in custos), start=0)

    referencias = list(artigo.references.all())
    entidades = list(artigo.entities.all().order_by("tipo", "nome"))

    return render(
        request,
        "articles/detail.html",
        {
            "artigo": artigo,
            "arquivos": arquivos,
            "pasta_existe": pasta.exists(),
            "corpo": corpo,
            "corpo_html": corpo_html,
            "tem_redacao": tem_redacao,
            "rascunhos": rascunhos,
            "custos": custos,
            "total_usd": total_usd,
            "referencias": referencias,
            "entidades": entidades,
            "memoria": _memoria_relacionada(artigo),
        },
    )


def _memoria_relacionada(artigo):
    """Trechos semelhantes de OUTROS artigos da mesma área (RAG). Só embeda se houver
    algo indexado no escopo — evita custo/latência quando não há memória a buscar."""
    from apps.memory.embeddings import EmbedderError
    from apps.memory.models import MemoryChunk
    from apps.memory.retrieval import buscar_semelhantes

    tem_outros = (
        MemoryChunk.objects.filter(area_slug=artigo.area_slug)
        .exclude(article_id=artigo.pk)
        .exists()
    )
    if not tem_outros:
        return []
    try:
        return buscar_semelhantes(
            f"{artigo.titulo}. {artigo.assunto}",
            area_slug=artigo.area_slug,
            k=5,
            exclude_article=artigo.pk,
        )
    except EmbedderError:
        return []


@require_POST
def article_write(request, pk):
    """Dispara a primeira redação (Claude) para o artigo e volta ao detalhe."""
    artigo = get_object_or_404(Article, pk=pk)
    try:
        call = gerar_primeira_redacao(artigo)
    except LLMProviderError as exc:
        messages.error(request, f"Falha na redação: {exc}")
    else:
        messages.success(
            request,
            f"Primeira redação gerada ({call.output_tokens} tokens · ${call.cost_usd}).",
        )
    return redirect(artigo.get_absolute_url())


@require_POST
def article_pipeline(request, pk):
    """Roda o pipeline multi-LLM completo (Perplexity + Claude) e volta ao detalhe."""
    artigo = get_object_or_404(Article, pk=pk)
    try:
        calls = rodar_pipeline_completo(artigo)
    except LLMProviderError as exc:
        messages.error(request, f"Falha no pipeline: {exc}")
    else:
        total = sum((c.cost_usd for c in calls), start=0)
        messages.success(
            request,
            f"Pipeline completo em {len(calls)} etapas · custo total ${total:.4f}.",
        )
    return redirect(artigo.get_absolute_url())


@require_POST
def article_extract_entities(request, pk):
    """Extrai entidades do artigo (Claude) para o grafo e volta ao detalhe."""
    from apps.memory.graph import extrair_entidades

    artigo = get_object_or_404(Article, pk=pk)
    try:
        r = extrair_entidades(artigo)
    except LLMProviderError as exc:
        messages.error(request, f"Falha ao extrair entidades: {exc}")
    else:
        messages.success(
            request,
            f"{r['entidades']} entidades ({r['novas']} novas) extraídas para o grafo.",
        )
    return redirect(artigo.get_absolute_url())


@require_POST
def article_verify_sources(request, pk):
    """(Re)verifica as fontes do artigo (URL → domínio → trecho) e volta ao detalhe."""
    from apps.memory.verify import verificar_pendentes

    artigo = get_object_or_404(Article, pk=pk)
    contagem = verificar_pendentes(artigo)
    messages.success(
        request,
        "Fontes verificadas — ok: {ok}, duvidosa: {duvidosa}, inexistente: {inexistente}.".format(
            ok=contagem.get("ok", 0),
            duvidosa=contagem.get("duvidosa", 0),
            inexistente=contagem.get("inexistente", 0),
        ),
    )
    return redirect(artigo.get_absolute_url())
