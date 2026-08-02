import json
import logging
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from django.views.decorators.csrf import ensure_csrf_cookie

from apps.articles import services as article_services
from apps.articles.models import Article, Folder, Paragraph
from apps.llm import roles
from apps.llm.models import LLMCall, Papel
from apps.llm.providers import LLMProviderError, get_provider

from .models import ChatTurn
from .prompts import build_reescrita_prompt, build_section_edit_prompt
from .render import render_paragraph
from .sections import parse_sections, replace_section

logger = logging.getLogger(__name__)


def _brl(usd) -> Decimal:
    taxa = Decimal(str(getattr(settings, "USD_BRL", 5.4)))
    return (Decimal(usd) * taxa).quantize(Decimal("0.01"))


#: etapas do Pipeline (ordem fixa, como o handoff), mapeadas a papel/modelo.
_ETAPAS = [
    (Papel.PESQUISA, "Pesquisa", "pesquisador"),
    (Papel.ESTRUTURA, "Estrutura", "arquiteto"),
    (Papel.REDACAO, "Redação", "redator"),
    (Papel.REVISAO, "Revisão", "revisor"),
    (Papel.EDICAO, "Edição final", "editor"),
]


def _pipeline(article) -> tuple[list[dict], Decimal]:
    calls = list(article.llm_calls.all())
    total_usd = sum((c.cost_usd for c in calls), start=Decimal("0"))
    etapas = []
    for papel_val, label, papel_nome in _ETAPAS:
        do_papel = [c for c in calls if c.papel == papel_val]
        custo = sum((c.cost_usd for c in do_papel), start=Decimal("0"))
        p = roles.papel(papel_nome)
        etapas.append({
            "label": label, "modelo": p["model"], "dot": p["dot"],
            "custo_brl": _brl(custo), "feito": bool(do_papel),
        })
    return etapas, _brl(total_usd)


def _sections_render(article):
    refs_by_id = {r.pk: r for r in article.references.all()}
    out = []
    for sec in article.sections.all():
        paras = [{
            "id": p.pk, "ordem": p.ordem, "locked": p.locked,
            "html": render_paragraph(p.texto, refs_by_id),
        } for p in sec.paragraphs.all()]
        out.append({
            "id": sec.pk, "num": f"{sec.ordem + 1:02d}", "titulo": sec.titulo,
            "meta": sec.meta_linhas, "usadas": sec.linhas_atuais, "paragraphs": paras,
        })
    return out


@ensure_csrf_cookie
def app_workspace(request, pk=None):
    """Shell do workspace — protótipo transplantado (fiel ao Modelo_Template).

    Ligação real COMPLETA: documento, avisos de margem, estado, pipeline (custos+modelos
    reais), sidebar, fontes e memória — tudo de `window.__DATA__`, no design exato do
    modelo. Sem artigo real, cai no mock do protótipo (estado vazio).
    """
    from django.utils.safestring import mark_safe

    from .serialize import article_to_appdata

    if pk:
        artigo = get_object_or_404(Article, pk=pk)
    else:
        artigo = (Article.objects.filter(sections__isnull=False).distinct().first()
                  or Article.objects.first())

    data_json = None
    if artigo:
        # escapa "</" para não permitir quebra do <script> (XSS via "</script>" no conteúdo)
        raw = json.dumps(article_to_appdata(artigo), ensure_ascii=False).replace("</", "<\\/")
        data_json = mark_safe(raw)
    return render(request, "workspace/app.html", {"data_json": data_json})


def _ler_corpo(article: Article) -> str:
    md = Path(article.pasta) / "artigo.md"
    return md.read_text(encoding="utf-8") if md.exists() else ""


def _memoria(article: Article) -> list[dict]:
    from apps.memory.embeddings import EmbedderError
    from apps.memory.models import MemoryChunk
    from apps.memory.retrieval import buscar_semelhantes

    tem = (
        MemoryChunk.objects.filter(area_slug=article.area_slug)
        .exclude(article_id=article.pk).exists()
    )
    if not tem:
        return []
    try:
        sem = buscar_semelhantes(f"{article.titulo}. {article.assunto}",
                                 area_slug=article.area_slug, k=4, exclude_article=article.pk)
        return [{"titulo": s.titulo, "texto": s.texto} for s in sem]
    except EmbedderError:
        return []


def workspace(request, pk):
    """Tela de escrita: contexto + seções + chat (Fase 6)."""
    artigo = get_object_or_404(Article, pk=pk)
    corpo = _ler_corpo(artigo)
    secoes = parse_sections(corpo) if corpo.strip() else []
    return render(request, "workspace/workspace.html", {
        "artigo": artigo,
        "secoes": secoes,
        "turnos": artigo.chat_turns.all()[:20],
    })


def _ref_json(ref):
    from .serialize import _BADGE
    cls, label, decide = _BADGE.get(ref.verificada, ("duvidosa", "Pendente", True))
    return {"id": ref.pk, "status": ref.verificada, "badgeClass": cls,
            "badgeLabel": label, "decide": decide, "nota": ref.nota_verificacao}


_ESTILO_MAP = {
    "aprofundado": "aprofundado", "raso": "raso", "intelectual": "intelectual",
    "popular": "popular", "juridiquês": "juridiques", "juridiques": "juridiques",
    "técnico/popular": "tecnico_popular", "tecnico/popular": "tecnico_popular",
}


def _gerar_estrutura(article):
    """Arquiteto (Opus): propõe seções em JSON e cria Section rows (skeleton)."""
    import re

    from apps.articles.models import Section
    total = article.num_paginas * article.num_linhas
    provider = get_provider("anthropic")
    area = article.area or "conhecimento geral"
    system = (f"Você é o Arquiteto: propõe a estrutura de um artigo especializado da área de "
              f"{area}. Responda SOMENTE "
              'JSON válido: {"secoes":[{"titulo":"...","resumo":"...","linhas":N}]}. '
              "O 'resumo' deve ter no máximo 12 palavras. Entre 4 e 8 seções, sem redigir o "
              f"conteúdo. Some os 'linhas' para aproximadamente {total}.")
    user = (f"Assunto: {article.assunto}\nÁrea: {article.area}\n"
            f"Estilo: {article.get_estilo_display()}\n"
            + (f"Público-alvo: {article.publico_alvo}\n" if article.publico_alvo else "")
            + (f"Tese: {article.contexto}\n" if article.contexto else "")
            + f"Extensão-alvo: {article.num_paginas} páginas × {article.num_linhas} linhas.")
    res = provider.generate(system=system, prompt=user, max_tokens=4000,
                            model=settings.MODELO_ARQUITETO, thinking=False)
    LLMCall.objects.create(article=article, papel=Papel.ESTRUTURA, provider=res.provider,
                           model=res.model, input_tokens=res.input_tokens,
                           output_tokens=res.output_tokens, cost_usd=res.cost_usd, ok=True)
    txt = re.sub(r"^```(?:json)?|```$", "", res.text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(txt)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        data = json.loads(m.group(0)) if m else {"secoes": []}
    for i, s in enumerate(data.get("secoes", [])):
        Section.objects.create(
            article=article, ordem=i, titulo=(s.get("titulo") or f"Seção {i+1}")[:300],
            resumo=(s.get("resumo") or ""), meta_linhas=int(s.get("linhas") or article.num_linhas),
        )
    article_services.sincronizar_disco(article)


def _ensure_pesquisa(article) -> str:
    """Roda a pesquisa (Perplexity → fontes verificadas) UMA vez por artigo.
    Devolve o texto de apoio (vazio se já rodou antes ou se falhar)."""
    from apps.llm.prompts import build_pesquisa_prompt
    from apps.memory.sources import criar_referencias_de_fontes
    from apps.memory.verify import verificar_pendentes
    if article.llm_calls.filter(papel=Papel.PESQUISA).exists():
        return ""  # já pesquisamos este artigo antes
    try:
        ppx = get_provider("perplexity")
        s, u = build_pesquisa_prompt(assunto=article.assunto, area=article.area)
        pesq = ppx.generate(system=s, prompt=u, max_tokens=1200, search_recency="year")
    except LLMProviderError:
        return ""
    LLMCall.objects.create(article=article, papel=Papel.PESQUISA, provider=pesq.provider,
                           model=pesq.model, input_tokens=pesq.input_tokens,
                           output_tokens=pesq.output_tokens, cost_usd=pesq.cost_usd, ok=True)
    criar_referencias_de_fontes(article, pesq.sources)
    verificar_pendentes(article)
    return pesq.text[:1500]


def _redacao_prompts(article, sec, pesquisa_txt: str = "", n_paras: int = 2):
    """(system, user) para o Redator escrever UMA seção, citando só fontes verificadas."""
    refs_ok = list(article.references.filter(verificada="ok"))
    refs_lst = "\n".join(f'- [[ref:{r.pk}]] {r.titulo}' for r in refs_ok) or "(nenhuma)"
    from apps.llm.prompts import ESTILO_INSTRUCTIONS
    area = article.area or "conhecimento geral"
    estilo_desc = ESTILO_INSTRUCTIONS.get(article.estilo, article.get_estilo_display())
    publico = (article.publico_alvo or "").strip()
    system = (f"Você é o Redator: escreve UMA seção de um artigo especializado da área de {area}. "
              f"ESTILO: {estilo_desc} "
              + (f"PÚBLICO-ALVO: escreva pensando em {publico}. " if publico else "")
              + "Cite fontes apenas via [[ref:ID]] usando os IDs fornecidos; não invente citações. "
              f"Escreva {n_paras} parágrafos desenvolvidos. Português do Brasil; devolva só o corpo "
              "(parágrafos separados por linha em branco), sem repetir o título da seção.")
    user = (f"SEÇÃO: {sec.titulo}\nO que cobrir: {sec.resumo}\nMeta: ~{sec.meta_linhas} linhas.\n"
            f"FONTES VERIFICADAS:\n{refs_lst}\n"
            + (f"\nPESQUISA DE APOIO:\n{pesquisa_txt}\n" if pesquisa_txt else ""))
    return system, user


def _gerar_conteudo(article, profundidade):
    """Gera o conteúdo de TODAS as seções em lote. O fluxo padrão do wizard é sob
    demanda (section_write); esta função existe para geração em bloco quando pedida."""
    if profundidade in ("skeleton", "esqueleto"):
        return
    pesquisa_txt = _ensure_pesquisa(article)
    n = 2 if profundidade == "completo" else 1
    claude = get_provider("anthropic")
    for sec in article.sections.all():
        system, user = _redacao_prompts(article, sec, pesquisa_txt, n_paras=n)
        try:
            res = claude.generate(system=system, prompt=user, max_tokens=1500,
                                  model=settings.MODELO_REDATOR, thinking=False)
        except LLMProviderError:
            continue
        LLMCall.objects.create(article=article, papel=Papel.REDACAO, provider=res.provider,
                               model=res.model, input_tokens=res.input_tokens,
                               output_tokens=res.output_tokens, cost_usd=res.cost_usd, ok=True)
        paras = [p.strip() for p in res.text.split("\n\n") if p.strip()]
        for i, ptxt in enumerate(paras):
            Paragraph.objects.create(section=sec, ordem=i, texto=ptxt)
    article_services.sincronizar_disco(article)


@require_POST
def workspace_overlap(request):
    """Detecção de sobreposição (embeddings): artigos da área semanticamente próximos."""
    import math

    from django.utils.text import slugify

    from apps.articles.models import Article
    from apps.memory.embeddings import EmbedderError, get_embedder
    p = json.loads(request.body or "{}")
    assunto = (p.get("assunto") or "").strip()
    existing = list(Article.objects.filter(area_slug=slugify(p.get("area") or "")))
    if not assunto or not existing:
        return JsonResponse({"overlaps": []})
    try:
        vecs = get_embedder().embed([assunto] + [a.assunto or a.titulo for a in existing],
                                    input_type="query").vectors
    except EmbedderError:
        return JsonResponse({"overlaps": []})

    def cos(a, b):
        d = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1
        nb = math.sqrt(sum(y * y for y in b)) or 1
        return d / (na * nb)

    q = vecs[0]
    ov = []
    for i, a in enumerate(existing):
        sim = cos(q, vecs[i + 1])
        if sim > 0.45:
            ov.append({"title": a.titulo, "pct": round(sim * 100), "articleId": a.pk,
                       "sections": [s.titulo for s in a.sections.all()[:2]]})
    ov.sort(key=lambda x: -x["pct"])
    return JsonResponse({"overlaps": ov})


@require_POST
def workspace_create(request):
    """Cria o artigo (params do wizard) + gera a estrutura (Arquiteto). Devolve a URL."""
    from apps.articles.services import ArticleExistsError, ArticleParams, create_article
    p = json.loads(request.body or "{}")
    estilo = _ESTILO_MAP.get((p.get("estilo") or "").strip().lower(), "tecnico_popular")
    try:
        art = create_article(ArticleParams(
            titulo=(p.get("assunto") or "").strip(), assunto=(p.get("assunto") or "").strip(),
            area=(p.get("area") or "").strip(), num_paginas=int(p.get("num_paginas") or 1),
            num_linhas=int(p.get("num_linhas") or 10), estilo=estilo,
        ))
    except ArticleExistsError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    except (ValueError, TypeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    campos = ["estilo_citacao", "perfil_layout"]
    # citação: "Autor-data" → autor_data | "Nota de rodapé" → nota_rodape
    cit = (p.get("estilo_citacao") or "").strip().lower()
    art.estilo_citacao = "nota_rodape" if cit.startswith("nota") else "autor_data"
    # layout: casa pelo prefixo do rótulo do wizard
    lay = (p.get("perfil_layout") or "").strip().lower()
    art.perfil_layout = ("editorial" if lay.startswith("editorial")
                         else "web" if lay.startswith("web") else "abnt")
    if p.get("tese"):
        art.contexto = p["tese"].strip()
        campos.append("contexto")
    if p.get("publico_alvo"):
        art.publico_alvo = p["publico_alvo"].strip()[:200]
        campos.append("publico_alvo")
    art.save(update_fields=campos + ["atualizado_em"])
    aviso = None
    try:
        # Só a estrutura (rápido). O conteúdo é redigido seção a seção, sob demanda,
        # via section_write — evita a espera de 60-80s e o risco de timeout.
        _gerar_estrutura(art)
    except Exception as exc:  # artigo é criado mesmo se a estrutura falhar
        logger.warning("Geração de estrutura falhou para o artigo %s: %s", art.pk, exc)
        aviso = "Não consegui montar a estrutura automaticamente. Adicione as seções manualmente."
    payload = {"pk": art.pk, "url": f"/workspace/app/{art.pk}/"}
    if aviso:
        payload["aviso"] = aviso
    return JsonResponse(payload)


def article_snapshots(request, pk):
    """Lista os snapshots (versões) do artigo para a comparação."""
    from apps.articles.models import Article
    article = get_object_or_404(Article, pk=pk)
    return JsonResponse({"snapshots": [
        {"versao": s.versao, "label": s.label or f"v{s.versao}", "markdown": s.markdown,
         "criado": s.criado_em.strftime("%d/%m %H:%M")} for s in article.snapshots.all()]})


def article_export(request, pk, fmt):
    """Exporta o artigo em md/docx/pdf (download)."""
    from django.http import HttpResponse
    from django.utils.text import slugify

    from apps.articles.models import Article
    from .export import EXPORTERS
    article = get_object_or_404(Article, pk=pk)
    if fmt not in EXPORTERS:
        return JsonResponse({"error": "formato inválido"}, status=400)
    fn, content_type, ext = EXPORTERS[fmt]
    data = fn(article)
    resp = HttpResponse(data, content_type=content_type)
    nome = slugify(article.titulo)[:60] or f"artigo-{article.pk}"
    resp["Content-Disposition"] = f'attachment; filename="{nome}.{ext}"'
    return resp


@require_POST
def article_delete(request, pk):
    """Exclui o artigo (pasta física + registro em cascata). Devolve a URL do próximo
    artigo (ou a raiz do workspace) para a UI redirecionar."""
    from apps.articles.services import excluir_artigo
    article = get_object_or_404(Article, pk=pk)
    prox = Article.objects.exclude(pk=pk).order_by("-atualizado_em").first()
    excluir_artigo(article)
    url = f"/workspace/app/{prox.pk}/" if prox else "/workspace/app/"
    return JsonResponse({"ok": True, "url": url})


@require_POST
def article_status(request, pk):
    """Transições de fechamento: review → approve/finalize (final + versão + Snapshot) → reabrir."""
    from apps.articles.models import Article, Snapshot, StatusArtigo
    article = get_object_or_404(Article, pk=pk)
    try:
        acao = (json.loads(request.body or "{}").get("acao") or "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"error": "payload inválido"}, status=400)

    if acao == "review":
        article.status = StatusArtigo.REVISAO
        article.save(update_fields=["status", "atualizado_em"])
    elif acao in ("approve", "finalize"):
        article.status = StatusArtigo.FINAL
        article.versao = (article.versao or 1) + 1
        article.save(update_fields=["status", "versao", "atualizado_em"])
        Snapshot.objects.create(article=article, versao=article.versao,
                                label="final", markdown=article.render_markdown())
    elif acao == "reabrir":
        article.status = StatusArtigo.RASCUNHO
        article.versao = (article.versao or 1) + 1
        article.save(update_fields=["status", "versao", "atualizado_em"])
    else:
        return JsonResponse({"error": "ação inválida"}, status=400)

    from .serialize import _STATUS_MAP
    cls, label = _STATUS_MAP.get(article.status, ("draft", "Rascunho"))
    return JsonResponse({"status": cls, "statusLabel": label, "version": f"v{article.versao}"})


@require_POST
def reference_verify(request, pk):
    """(Re)verifica uma fonte (URL → domínio → trecho) — sem LLM."""
    from apps.memory.models import Reference
    from apps.memory.verify import verificar_referencia
    ref = get_object_or_404(Reference, pk=pk)
    verificar_referencia(ref)
    return JsonResponse(_ref_json(ref))


@require_POST
def reference_decide(request, pk):
    """Decide manualmente uma fonte: aceitar (ok) ou rejeitar (inexistente)."""
    from django.utils import timezone

    from apps.memory.models import Reference, StatusVerif
    ref = get_object_or_404(Reference, pk=pk)
    try:
        decisao = (json.loads(request.body or "{}").get("decisao") or "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"error": "payload inválido"}, status=400)
    if decisao == "aceitar":
        ref.verificada = StatusVerif.OK
    elif decisao == "rejeitar":
        ref.verificada = StatusVerif.INEXISTENTE
    else:
        return JsonResponse({"error": "decisão inválida"}, status=400)
    ref.verificada_em = timezone.now()
    ref.save(update_fields=["verificada", "verificada_em"])
    return JsonResponse(_ref_json(ref))


@require_POST
def reference_buscar(request, pk):
    """Pesquisador (Perplexity) busca uma fonte oficial melhor para a afirmação."""
    from apps.memory.models import Reference
    ref = get_object_or_404(Reference, pk=pk)
    provider = get_provider("perplexity")
    area = (ref.article.area if ref.article_id else "") or "conhecimento geral"
    system = (f"Você é pesquisador da área de {area}. Encontre a fonte mais confiável e "
              "verificável (priorize fontes oficiais, institucionais ou acadêmicas) que "
              "sustente a afirmação. Responda curto: a melhor fonte e o link.")
    prompt = f"Tema/afirmação: {ref.titulo}. {ref.trecho}".strip()
    try:
        res = provider.generate(system=system, prompt=prompt, max_tokens=400, search_recency="year")
    except LLMProviderError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    LLMCall.objects.create(
        article=ref.article, papel=Papel.PESQUISA, provider=res.provider, model=res.model,
        input_tokens=res.input_tokens, output_tokens=res.output_tokens, cost_usd=res.cost_usd, ok=True,
    )
    fonte = res.sources[0] if res.sources else None
    return JsonResponse({
        "texto": res.text[:600],
        "fonte": ({"titulo": fonte.get("title"), "url": fonte.get("url")} if fonte else None),
    })


@require_POST
def paragraph_rewrite(request, pk):
    """Reescreve UM parágrafo com o Redator (Sonnet) em streaming (SSE)."""
    para = get_object_or_404(Paragraph, pk=pk)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "payload inválido"}, status=400)
    instrucao = (payload.get("instrucao") or "").strip() or "Melhore a clareza e a fluidez deste parágrafo."

    article = para.section.article
    system, user = build_reescrita_prompt(
        contexto=article.contexto or article.titulo, secao_titulo=para.section.titulo,
        paragrafo=para.texto, instrucao=instrucao,
    )
    provider = get_provider("anthropic")
    _ALLOWED = {"claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"}
    modelo = payload.get("model") if payload.get("model") in _ALLOWED else None
    modelo = modelo or getattr(settings, "MODELO_REDATOR", "claude-sonnet-5")

    def sse():
        holder: dict = {}
        try:
            for pedaco in provider.stream_generate(
                system=system, prompt=user, max_tokens=1200, model=modelo,
                on_done=lambda r: holder.update(res=r),
            ):
                yield f"data: {json.dumps({'delta': pedaco})}\n\n"
        except LLMProviderError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return
        res = holder.get("res")
        if res:
            LLMCall.objects.create(
                article=article, papel=Papel.REDACAO, provider=res.provider, model=res.model,
                input_tokens=res.input_tokens, output_tokens=res.output_tokens,
                cost_usd=res.cost_usd, ok=True,
            )
        yield "data: " + json.dumps({"done": True, "text": (res.text if res else "").strip()}) + "\n\n"

    resp = StreamingHttpResponse(sse(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


def section_write(request, pk):
    """Redige UMA seção sob demanda com o Redator (SSE). Substitui os parágrafos
    existentes da seção. A pesquisa (fontes) roda uma única vez, na 1ª seção."""
    from apps.articles.models import Section
    sec = get_object_or_404(Section, pk=pk)
    article = sec.article
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}
    _ALLOWED = {"claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"}
    modelo = payload.get("model") if payload.get("model") in _ALLOWED else None
    modelo = modelo or getattr(settings, "MODELO_REDATOR", "claude-sonnet-5")

    def sse():
        try:
            pesquisa_txt = _ensure_pesquisa(article)
        except Exception as exc:  # pesquisa é best-effort; segue sem ela
            logger.warning("Pesquisa falhou p/ artigo %s: %s", article.pk, exc)
            pesquisa_txt = ""
        system, user = _redacao_prompts(article, sec, pesquisa_txt, n_paras=2)
        provider = get_provider("anthropic")
        holder: dict = {}
        try:
            for pedaco in provider.stream_generate(
                system=system, prompt=user, max_tokens=1500, model=modelo,
                on_done=lambda r: holder.update(res=r),
            ):
                yield f"data: {json.dumps({'delta': pedaco})}\n\n"
        except LLMProviderError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return
        res = holder.get("res")
        texto = (res.text if res else "").strip()
        paras = [p.strip() for p in texto.split("\n\n") if p.strip()]
        if res and paras:
            LLMCall.objects.create(
                article=article, papel=Papel.REDACAO, provider=res.provider, model=res.model,
                input_tokens=res.input_tokens, output_tokens=res.output_tokens,
                cost_usd=res.cost_usd, ok=True,
            )
            sec.paragraphs.all().delete()
            for i, ptxt in enumerate(paras):
                Paragraph.objects.create(section=sec, ordem=i, texto=ptxt)
            article_services.sincronizar_disco(article)
        yield "data: " + json.dumps({"done": True, "count": len(paras)}) + "\n\n"

    resp = StreamingHttpResponse(sse(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


@require_POST
def paragraph_ignore_note(request, pk):
    """Persiste (ou remove) a dispensa de um aviso de margem de um parágrafo.
    Assim o "Ignorar" sobrevive ao reload (some o aviso E o sublinhado ondulado)."""
    para = get_object_or_404(Paragraph, pk=pk)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "payload inválido"}, status=400)
    note_id = (payload.get("note_id") or "").strip()
    if not note_id:
        return JsonResponse({"error": "note_id ausente"}, status=400)
    ignorados = list(para.avisos_ignorados or [])
    if payload.get("ignore", True):
        if note_id not in ignorados:
            ignorados.append(note_id)
    else:
        ignorados = [n for n in ignorados if n != note_id]
    para.avisos_ignorados = ignorados
    para.save(update_fields=["avisos_ignorados"])
    return JsonResponse({"ok": True, "ignorados": ignorados})


@require_POST
def paragraph_comment(request, pk):
    """Adiciona um comentário à seção do parágrafo (comentários por seção)."""
    from .models import Comment
    para = get_object_or_404(Paragraph, pk=pk)
    texto = (json.loads(request.body or "{}").get("texto") or "").strip()
    if not texto:
        return JsonResponse({"error": "comentário vazio"}, status=400)
    c = Comment.objects.create(section=para.section, texto=texto)
    return JsonResponse({"id": c.pk, "texto": c.texto, "criado": c.criado_em.strftime("%d/%m %H:%M")})


def paragraph_comments(request, pk):
    """Lista os comentários da seção do parágrafo."""
    from .models import Comment
    para = get_object_or_404(Paragraph, pk=pk)
    cs = Comment.objects.filter(section=para.section)
    return JsonResponse({"comments": [
        {"id": c.pk, "texto": c.texto, "criado": c.criado_em.strftime("%d/%m %H:%M"),
         "resolvido": c.resolvido} for c in cs]})


def workspace_search(request):
    """Busca semântica no acervo (RAG): trechos parecidos com a query, por artigo."""
    from apps.memory.embeddings import EmbedderError, get_embedder
    from apps.memory.models import MemoryChunk
    from pgvector.django import CosineDistance
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    try:
        qvec = get_embedder().embed_one(q, input_type="query")
    except EmbedderError:
        return JsonResponse({"results": []})
    rows = (MemoryChunk.objects.annotate(dist=CosineDistance("embedding", qvec))
            .order_by("dist").select_related("article")[:8])
    return JsonResponse({"results": [
        {"articleId": r.article_id, "article": r.article.titulo,
         "snippet": r.texto[:160], "sim": round(1 - float(r.dist), 2)} for r in rows]})


@require_POST
def paragraph_accept(request, pk):
    """Aceita a reescrita: grava o novo texto no parágrafo e sincroniza o disco."""
    para = get_object_or_404(Paragraph, pk=pk)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "payload inválido"}, status=400)
    texto = (payload.get("texto") or "").strip()
    if texto:
        para.texto = texto
        para.save(update_fields=["texto", "atualizado_em"])
        article_services.sincronizar_disco(para.section.article)
    return JsonResponse({"ok": True})


@require_POST
def salvar_contexto(request, pk):
    artigo = get_object_or_404(Article, pk=pk)
    artigo.contexto = request.POST.get("contexto", "").strip()
    artigo.save(update_fields=["contexto", "atualizado_em"])
    messages.success(request, "Contexto salvo.")
    return redirect("workspace:home", pk=pk)


@require_POST
def stream_section(request, pk):
    """Streama (SSE) a reescrita de uma seção. Ao final, cria um ChatTurn (proposta)."""
    artigo = get_object_or_404(Article, pk=pk)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "payload inválido"}, status=400)

    instrucao = (payload.get("instrucao") or "").strip()
    try:
        secao_index = int(payload.get("secao_index"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "seção inválida"}, status=400)
    if not instrucao:
        return JsonResponse({"error": "instrução vazia"}, status=400)

    corpo = _ler_corpo(artigo)
    secoes = parse_sections(corpo)
    if secao_index < 0 or secao_index >= len(secoes):
        return JsonResponse({"error": "seção inexistente"}, status=400)
    secao = secoes[secao_index]

    system, user = build_section_edit_prompt(
        contexto=artigo.contexto, artigo_md=corpo, memoria=_memoria(artigo),
        secao_texto=secao.texto, instrucao=instrucao,
    )
    provider = get_provider("anthropic")

    def sse():
        holder: dict = {}
        try:
            for pedaco in provider.stream_generate(
                system=system, prompt=user, max_tokens=2000,
                on_done=lambda r: holder.update(res=r),
            ):
                yield f"data: {json.dumps({'delta': pedaco})}\n\n"
        except LLMProviderError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return

        res = holder.get("res")
        proposta = (res.text if res else "").strip()
        turno = ChatTurn.objects.create(
            article=artigo, instrucao=instrucao, secao_index=secao_index,
            secao_heading=secao.heading, proposta=proposta,
            input_tokens=res.input_tokens if res else 0,
            output_tokens=res.output_tokens if res else 0,
            cost_usd=res.cost_usd if res else 0,
        )
        yield "data: " + json.dumps({
            "done": True, "turn_id": turno.pk, "proposta": proposta, "cost": str(turno.cost_usd)
        }) + "\n\n"

    resp = StreamingHttpResponse(sse(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


@require_POST
def apply_section(request, pk):
    """Aplica a proposta de um ChatTurn: faz o splice na seção, salva e reindexa."""
    artigo = get_object_or_404(Article, pk=pk)
    turno = get_object_or_404(ChatTurn, pk=request.POST.get("turn_id"), article=artigo)

    corpo = _ler_corpo(artigo)
    try:
        novo = replace_section(corpo, turno.secao_index, turno.proposta)
    except IndexError:
        messages.error(request, "A seção mudou; não foi possível aplicar. Gere de novo.")
        return redirect("workspace:home", pk=pk)

    article_services.salvar_corpo(artigo, novo)
    turno.aplicada = True
    turno.save(update_fields=["aplicada"])

    from apps.memory.embeddings import EmbedderError
    from apps.memory.retrieval import indexar_artigo
    try:
        indexar_artigo(artigo, novo)
    except EmbedderError:
        pass

    messages.success(request, "Seção atualizada.")
    return redirect("workspace:home", pk=pk)
