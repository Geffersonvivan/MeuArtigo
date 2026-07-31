"""Grafo de entidades (PROJETO.md §5b) — extração via Claude e consultas de grafo.

Conceitos do domínio (leis, jurisprudência, órgãos, conceitos) viram nós ligados aos
artigos que os citam. Evolução que conversa com a skill /graphify (que gera o grafo
pesado — god nodes, comunidades — por cima do corpus em artigos/).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Q
from django.utils.text import slugify

from apps.articles.models import Article
from apps.llm.models import LLMCall, Papel
from apps.llm.prompts import build_entidades_prompt
from apps.llm.providers import get_provider

from .models import Entity, EntityMention, EntityTipo

_TIPOS_VALIDOS = {t.value for t in EntityTipo}


def _parse_json(texto: str) -> dict:
    t = texto.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


@transaction.atomic
def extrair_entidades(article: Article, *, provider_name: str = "anthropic") -> dict:
    """Extrai entidades do artigo.md via Claude e faz upsert de Entity + EntityMention.

    Retorna {'entidades': n_total, 'novas': n_criadas}. Loga a chamada em LLMCall.
    """
    from pathlib import Path

    md = Path(article.pasta) / "artigo.md"
    texto = md.read_text(encoding="utf-8") if md.exists() else ""
    if not texto.strip():
        return {"entidades": 0, "novas": 0}

    provider = get_provider(provider_name)
    system, user = build_entidades_prompt(texto=texto)
    result = provider.generate(system=system, prompt=user, max_tokens=2000, thinking=False)

    LLMCall.objects.create(
        article=article, papel=Papel.ENTIDADES, provider=result.provider, model=result.model,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        cost_usd=result.cost_usd, ok=True,
    )

    try:
        dados = _parse_json(result.text)
    except json.JSONDecodeError:
        return {"entidades": 0, "novas": 0}

    total = novas = 0
    for item in dados.get("entidades", []):
        nome = (item.get("nome") or "").strip()
        if not nome:
            continue
        tipo = item.get("tipo") if item.get("tipo") in _TIPOS_VALIDOS else EntityTipo.OUTRO
        slug = slugify(nome)[:300]
        if not slug:
            continue
        entity, criada = Entity.objects.get_or_create(
            area_slug=article.area_slug, slug=slug,
            defaults={"nome": nome, "tipo": tipo, "descricao": (item.get("descricao") or "").strip()},
        )
        if not criada and entity.tipo == EntityTipo.OUTRO and tipo != EntityTipo.OUTRO:
            entity.tipo = tipo
            entity.save(update_fields=["tipo"])
        EntityMention.objects.get_or_create(entity=entity, article=article)
        total += 1
        novas += int(criada)

    return {"entidades": total, "novas": novas}


def entidades_do_artigo(article: Article):
    return article.entities.all().order_by("tipo", "nome")


def entidades_relacionadas(entity: Entity, k: int = 8) -> list[tuple[Entity, int]]:
    """Outras entidades da área que co-ocorrem nos mesmos artigos, por nº de artigos comuns."""
    arts = list(entity.articles.values_list("pk", flat=True))
    if not arts:
        return []
    qs = (
        Entity.objects.filter(area_slug=entity.area_slug, mentions__article__in=arts)
        .exclude(pk=entity.pk)
        .annotate(peso=Count("mentions__article", filter=Q(mentions__article__in=arts), distinct=True))
        .order_by("-peso", "nome")[:k]
    )
    return [(e, e.peso) for e in qs]


@dataclass
class GrafoNo:
    id: int
    nome: str
    tipo: str
    artigos: int


@dataclass
class GrafoAresta:
    a: int
    b: int
    peso: int


def grafo_da_area(area_slug: str) -> tuple[list[GrafoNo], list[GrafoAresta]]:
    """Nós (entidades) + arestas (co-ocorrência em artigos) de uma área, para visualização."""
    entidades = list(
        Entity.objects.filter(area_slug=area_slug).annotate(n_art=Count("mentions__article", distinct=True))
    )
    nos = [GrafoNo(id=e.pk, nome=e.nome, tipo=e.tipo, artigos=e.n_art) for e in entidades]

    # arestas: para cada artigo, todas as combinações de suas entidades
    pares: dict[tuple[int, int], int] = {}
    ids_area = {e.pk for e in entidades}
    for art in Article.objects.filter(area_slug=area_slug).prefetch_related("entities"):
        ents = sorted(e.pk for e in art.entities.all() if e.pk in ids_area)
        for i in range(len(ents)):
            for j in range(i + 1, len(ents)):
                chave = (ents[i], ents[j])
                pares[chave] = pares.get(chave, 0) + 1
    arestas = [GrafoAresta(a=a, b=b, peso=p) for (a, b), p in pares.items()]
    return nos, arestas
