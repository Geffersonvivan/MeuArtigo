"""Motor de memória RAG: chunking, indexação e busca semântica (PROJETO.md §5a)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.db import transaction
from pgvector.django import CosineDistance

from apps.articles.models import Article

from .embeddings import get_embedder
from .models import MemoryChunk

#: tamanho-alvo de cada chunk (caracteres). Parágrafos são agrupados até esse limite.
CHUNK_TARGET_CHARS = 800


@dataclass
class Semelhante:
    texto: str
    titulo: str
    article_id: int
    similaridade: float


def chunk_text(texto: str, *, target: int = CHUNK_TARGET_CHARS) -> list[str]:
    """Quebra o texto em blocos ~`target` chars, respeitando parágrafos.

    Ignora linhas que são só comentário HTML de placeholder. Parágrafos maiores que
    `target` são divididos em pedaços.
    """
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.DOTALL)
    paras = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]

    chunks: list[str] = []
    buf = ""
    for p in paras:
        if buf and len(buf) + len(p) + 2 > target:
            chunks.append(buf)
            buf = ""
        if len(p) <= target:
            buf = f"{buf}\n\n{p}".strip() if buf else p
        else:
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(p), target):
                chunks.append(p[i : i + target])
    if buf:
        chunks.append(buf)
    return chunks


@transaction.atomic
def indexar_artigo(article: Article, texto: str, *, embedder=None) -> tuple[int, int]:
    """(Re)indexa um artigo: apaga chunks antigos e grava os novos com embeddings.

    Retorna (nº de chunks, tokens gastos). Levanta EmbedderError se a vetorização falhar
    (a transação reverte, mantendo o índice antigo consistente).
    """
    embedder = embedder or get_embedder()
    pedacos = chunk_text(texto)

    MemoryChunk.objects.filter(article=article).delete()
    if not pedacos:
        return (0, 0)

    result = embedder.embed(pedacos, input_type="document")
    MemoryChunk.objects.bulk_create(
        [
            MemoryChunk(
                article=article,
                ordem=i,
                texto=pedaco,
                embedding=vetor,
                area=article.area,
                area_slug=article.area_slug,
            )
            for i, (pedaco, vetor) in enumerate(zip(pedacos, result.vectors))
        ]
    )
    return (len(pedacos), result.tokens)


def buscar_semelhantes(
    query: str,
    *,
    area_slug: str | None = None,
    k: int = 5,
    exclude_article: int | None = None,
    embedder=None,
) -> list[Semelhante]:
    """Busca os `k` trechos mais semelhantes à `query` (distância de cosseno).

    Filtra por área e, opcionalmente, exclui o próprio artigo. Devolve [] se não houver
    nada indexado no escopo (sem custo de embedding nesse caso)."""
    qs = MemoryChunk.objects.all()
    if area_slug:
        qs = qs.filter(area_slug=area_slug)
    if exclude_article:
        qs = qs.exclude(article_id=exclude_article)
    if not qs.exists():
        return []

    embedder = embedder or get_embedder()
    qvec = embedder.embed_one(query, input_type="query")

    rows = (
        qs.annotate(dist=CosineDistance("embedding", qvec))
        .order_by("dist")
        .values_list("texto", "article__titulo", "article_id", "dist")[:k]
    )
    return [
        Semelhante(texto=t, titulo=titulo, article_id=aid, similaridade=1 - float(dist))
        for (t, titulo, aid, dist) in rows
    ]
