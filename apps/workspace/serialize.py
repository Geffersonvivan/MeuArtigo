"""Serializa um Article real no formato EXATO que o app.js do protótipo espera
(window.__DATA__): documento + avisos de margem + estado. Pipeline/sidebar/fontes/
memória entram nos próximos blocos desta mesma ligação real.
"""

from __future__ import annotations

from decimal import Decimal
from itertools import groupby

from django.conf import settings
from django.utils import timezone

from apps.llm.models import LLMCall, Papel
from apps.memory.models import StatusVerif, Term

from .detect import detectar_paragrafo

_BADGE = {
    "ok": ("verificada", "Verificada", False),
    "duvidosa": ("duvidosa", "Duvidosa", True),
    # rejeitada/não localizada é uma DECISÃO tomada (descartada) — não fica mais
    # pendente nem bloqueia o fechamento; só não pode ser citada no texto.
    "inexistente": ("nao-loc", "Não localizada", False),
    "pendente": ("duvidosa", "Pendente", True),
}


def _ago(dt) -> str:
    dias = (timezone.now() - dt).days
    if dias <= 0:
        return "hoje"
    if dias == 1:
        return "há 1 dia"
    if dias < 7:
        return f"há {dias} dias"
    if dias < 30:
        sem = dias // 7
        return f"há {sem} sem"
    return f"há {dias // 30} mês(es)"


def _sidebar(atual_pk: int) -> list:
    from apps.articles.models import Article
    arts = list(Article.objects.select_related("folder").order_by("area", "-criado_em"))
    grupos = []
    for area, itens in groupby(arts, key=lambda a: a.area):
        lst = []
        for a in itens:
            sc = _STATUS_MAP.get(a.status, ("draft", "Rascunho"))[0]
            lst.append({
                "url": f"/workspace/app/{a.pk}/", "title": a.titulo,
                "statusClass": sc, "active": a.pk == atual_pk,
                "meta": f"{a.num_paginas} pág · {a.get_status_display().lower()} · {_ago(a.criado_em)}",
            })
        grupos.append({"area": area, "items": lst})
    return grupos


def _sources(article) -> list:
    # conta citações reais por fonte ([[ref:pk]] nos parágrafos)
    from apps.articles.models import Paragraph
    paras = list(Paragraph.objects.filter(section__article=article).values_list("texto", flat=True))
    out = []
    for r in article.references.all():
        cls, label, decide = _BADGE.get(r.verificada, ("duvidosa", "Pendente", True))
        citacoes = sum(1 for t in paras if f"[[ref:{r.pk}]]" in t)
        out.append({
            "id": r.pk, "title": r.titulo, "badgeClass": cls, "badgeLabel": label,
            "tipo": r.get_tipo_display(), "decide": decide, "url": r.url,
            "trecho": r.trecho or (r.nota_verificacao or "—"), "afirmacao": r.trecho or r.titulo,
            "citacoes": citacoes,
        })
    return out


def _memory(article) -> list:
    from apps.articles.views import _memoria_relacionada
    try:
        return [{"title": s.titulo, "summary": s.texto[:200]} for s in _memoria_relacionada(article)]
    except Exception:
        return []


def _pipeline_data(article, gloss_count: int, red_flags: int) -> tuple[dict, dict, dict]:
    """Devolve (pipeline actions, roleCosts BRL, models reais) para o painel."""
    calls = list(article.llm_calls.all())
    brl = Decimal(str(getattr(settings, "USD_BRL", 5.4)))

    def custo(papeis) -> float:
        return float(sum((c.cost_usd for c in calls if c.papel in papeis), Decimal("0")) * brl)

    tem = lambda p: any(c.papel == p for c in calls)  # noqa: E731
    n_sec = article.sections.count()
    n_linhas = sum(s.meta_linhas for s in article.sections.all())
    n_fontes = article.references.count()
    dub = article.references.filter(
        verificada__in=[StatusVerif.DUVIDOSA, StatusVerif.PENDENTE]).count()

    pipeline = {
        "redator": [
            {"name": "Propor estrutura", "status": "done" if tem(Papel.ESTRUTURA) else "idle",
             "count": f"{n_sec} seções"},
            {"name": "Redigir seções", "status": "done" if tem(Papel.REDACAO) else "idle",
             "count": f"{n_linhas} linhas"},
            {"name": "Reescrever parágrafo", "status": "idle", "count": "sob comando"},
        ],
        "pesquisador": [
            {"name": "Levantar fontes", "status": "done" if n_fontes else "idle",
             "count": f"{n_fontes} fontes"},
            {"name": "Verificar fontes", "status": "done" if tem(Papel.VERIFICACAO) or n_fontes else "idle",
             "count": f"{dub} a decidir" if dub else "todas ok", "warn": dub > 0},
        ],
        "revisor": [
            {"name": "Estilo", "status": "wait", "count": "aguardando"},
            {"name": "Glossário", "status": "done", "count": f"{gloss_count} aviso"},
            {"name": "Coerência entre seções", "status": "wait", "count": "aguardando"},
        ],
        "det": [
            {"name": "Contagem de linhas por seção", "status": "done", "count": f"{n_sec}/{n_sec} seções"},
            {"name": "Similaridade com acervo", "status": "done", "count": "—"},
            {"name": "Afirmação sem fonte", "status": "done", "count": f"{red_flags} vermelho"},
            {"name": "Termos fora do glossário", "status": "done", "count": f"{gloss_count} aviso"},
        ],
    }
    role_costs = {
        "redator": custo([Papel.ESTRUTURA, Papel.REDACAO, Papel.EDICAO]),
        "pesquisador": custo([Papel.PESQUISA, Papel.VERIFICACAO]),
        "revisor": custo([Papel.REVISAO]),
    }
    models = {
        "redator": settings.MODELO_REDATOR,
        "pesquisador": getattr(settings, "PERPLEXITY_MODEL", "sonar"),
        "revisor": settings.MODELO_REVISOR,
    }
    return pipeline, role_costs, models

_STATUS_MAP = {
    "rascunho": ("draft", "Rascunho"), "pesquisa": ("draft", "Rascunho"),
    "estrutura": ("draft", "Rascunho"), "redacao": ("draft", "Rascunho"),
    "revisao": ("review", "Em revisão"), "final": ("final", "Final"),
}


def _glossario(area_slug: str) -> list:
    return [(t.termo, t.lista_variantes()) for t in Term.objects.filter(area_slug=area_slug)]


def article_to_appdata(article) -> dict:
    refs_by_id = {r.pk: r for r in article.references.all()}
    glossario = _glossario(article.area_slug)
    status_class, status_label = _STATUS_MAP.get(article.status, ("draft", "Rascunho"))

    sections, notes = [], []
    for sec in article.sections.all():
        paras = []
        for p in sec.paragraphs.all():
            pid = f"p{p.pk}"
            ignorados = set(p.avisos_ignorados or [])
            html, pnotes = detectar_paragrafo(pid, p.texto, refs_by_id, glossario, ignorados)
            paras.append({"id": pid, "html": html})
            notes.extend(pnotes)
        sections.append({
            "id": f"s{sec.pk}", "title": sec.titulo,
            "target": sec.meta_linhas, "paragraphs": paras,
        })

    red_flags = sum(1 for n in notes if n["kind"] == "err")
    gloss_count = sum(1 for n in notes if n["label"] == "Glossário")
    # "a decidir" = só as que ainda esperam decisão (duvidosa/pendente). Uma fonte
    # já decidida (verificada=ok, ou descartada=inexistente) não conta como bloqueador.
    sources_to_decide = article.references.filter(
        verificada__in=[StatusVerif.DUVIDOSA, StatusVerif.PENDENTE]).count()
    pipeline, role_costs, models = _pipeline_data(article, gloss_count, red_flags)

    from apps.articles.models import Article
    areas_existentes = sorted({a for a in Article.objects.values_list("area", flat=True) if a})

    return {
        "articleId": article.pk,
        "areas": areas_existentes,
        "pipeline": pipeline,
        "roleCosts": role_costs,
        "models": models,
        "sidebar": _sidebar(article.pk),
        "sources": _sources(article),
        "memory": _memory(article),
        "articles": {
            "a1": {"id": "a1", "title": article.titulo, "area": article.area,
                   "status": status_class, "sections": sections}
        },
        "notes": notes,
        "currentArticle": "a1",
        "topbar": {"title": article.titulo, "area": article.area,
                   "statusClass": status_class, "statusLabel": status_label,
                   "version": f"v{article.versao}"},
        "state": {"status": status_class, "version": f"v{article.versao}",
                  "sourcesToDecide": sources_to_decide, "redFlags": red_flags},
    }
