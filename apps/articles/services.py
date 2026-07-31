"""Service única de criação/sincronização de artigos (disco ↔ banco).

Regra de ouro (PROJETO.md §5): o banco é a fonte da verdade e uma ÚNICA service
escreve nos dois lados. Aqui nasce a pasta física e o registro `Article` juntos,
de forma atômica — nunca deixamos banco e disco fora de sincronia.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .models import Article, Estilo, StatusArtigo


class ArticleExistsError(Exception):
    """Já existe um artigo (pasta ou registro) para essa área+assunto."""


@dataclass(frozen=True)
class ArticleParams:
    assunto: str
    area: str
    num_paginas: int
    num_linhas: int
    estilo: str
    titulo: str = ""

    def resolved_titulo(self) -> str:
        return self.titulo.strip() or self.assunto.strip()


def _slugify(value: str) -> str:
    return slugify(value, allow_unicode=False)


def _params_payload(article: Article) -> dict:
    """Conteúdo do params.json — espelho dos parâmetros base do artigo."""
    return {
        "titulo": article.titulo,
        "assunto": article.assunto,
        "area": article.area,
        "area_slug": article.area_slug,
        "assunto_slug": article.assunto_slug,
        "num_paginas": article.num_paginas,
        "num_linhas": article.num_linhas,
        "estilo": article.estilo,
        "status": article.status,
        "criado_em": timezone.now().isoformat(),
    }


def _write_physical_folder(pasta: Path, article: Article) -> None:
    """Cria a árvore física do artigo (PROJETO.md §6). Idempotência não é o objetivo:
    a colisão já foi barrada antes; aqui assumimos pasta inexistente."""
    (pasta / "rascunhos").mkdir(parents=True, exist_ok=False)

    (pasta / "artigo.md").write_text(
        f"# {article.titulo}\n\n"
        f"> Área: {article.area} · Assunto: {article.assunto}\n"
        f"> Estilo: {article.get_estilo_display()} · "
        f"Meta: {article.num_paginas} pág. / {article.num_linhas} linhas\n\n"
        "<!-- Conteúdo gerado pelo pipeline nas próximas fases. -->\n",
        encoding="utf-8",
    )
    (pasta / "referencias.md").write_text(
        f"# Referências — {article.titulo}\n\n"
        "<!-- Fontes verificadas (ABNT) serão registradas aqui pelo pipeline. -->\n",
        encoding="utf-8",
    )
    (pasta / "params.json").write_text(
        json.dumps(_params_payload(article), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


@transaction.atomic
def salvar_corpo(article: Article, texto: str, *, status: str | None = None) -> Article:
    """Grava o corpo do artigo em artigo.md e atualiza o banco (fonte da verdade).

    Escrita atômica disco↔banco: se o disco falhar, a transação reverte o banco.
    Reindexação de embeddings quando o texto muda entra na Fase 3.
    """
    pasta = Path(article.pasta)
    if not pasta.exists():
        raise FileNotFoundError(f"Pasta do artigo não encontrada: {pasta}")

    if status:
        article.status = status
    article.save(update_fields=["status", "atualizado_em"] if status else ["atualizado_em"])

    (pasta / "artigo.md").write_text(texto, encoding="utf-8")
    return article


def salvar_referencias(article: Article, conteudo_md: str) -> Path:
    """Grava a lista ABNT em referencias.md (renderizada a partir dos Reference)."""
    caminho = Path(article.pasta) / "referencias.md"
    caminho.write_text(conteudo_md, encoding="utf-8")
    return caminho


@transaction.atomic
def sincronizar_disco(article: Article, *, bump_versao: bool = False) -> Article:
    """Renderiza o artigo a partir das SEÇÕES (fonte da verdade no banco) e grava o
    artigo.md. Opcionalmente incrementa a versão. Corrige a fragilidade anterior de o
    texto viver só no disco."""
    pasta = Path(article.pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    if bump_versao:
        article.versao = (article.versao or 1) + 1
        article.save(update_fields=["versao", "atualizado_em"])
    (pasta / "artigo.md").write_text(article.render_markdown(), encoding="utf-8")
    return article


def salvar_rascunho(article: Article, nome: str, texto: str) -> Path:
    """Grava um intermediário do pipeline em rascunhos/<nome> (PROJETO.md §6).

    Rascunhos são derivados (não são a fonte da verdade), então a escrita é direta.
    """
    destino = Path(article.pasta) / "rascunhos"
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / nome
    caminho.write_text(texto, encoding="utf-8")
    return caminho


@transaction.atomic
def create_article(params: ArticleParams) -> Article:
    """Cria o registro no banco e a pasta física de forma atômica.

    - Barra colisão de área+assunto (banco ou disco) com ArticleExistsError.
    - Se a escrita em disco falhar, a transação do banco é revertida e a pasta
      parcialmente criada é removida — sem órfãos dos dois lados.
    """
    area_slug = _slugify(params.area)
    assunto_slug = _slugify(params.assunto)

    if not area_slug or not assunto_slug:
        raise ValueError("Área e assunto precisam gerar slugs válidos (texto não vazio).")

    pasta = Path(settings.ARTIGOS_ROOT) / area_slug / assunto_slug

    # Colisão: registro no banco OU pasta já existente no disco.
    if Article.objects.filter(area_slug=area_slug, assunto_slug=assunto_slug).exists():
        raise ArticleExistsError(
            f"Já existe um artigo para “{params.area} / {params.assunto}”."
        )
    if pasta.exists():
        raise ArticleExistsError(
            f"A pasta “{pasta}” já existe no disco. Escolha outro assunto/área."
        )

    article = Article.objects.create(
        titulo=params.resolved_titulo(),
        assunto=params.assunto.strip(),
        area=params.area.strip(),
        area_slug=area_slug,
        assunto_slug=assunto_slug,
        num_paginas=params.num_paginas,
        num_linhas=params.num_linhas,
        estilo=params.estilo,
        pasta=str(pasta),
        status=StatusArtigo.RASCUNHO,
    )

    try:
        _write_physical_folder(pasta, article)
    except Exception:
        # Reverte o disco; a exceção propaga e o @transaction.atomic reverte o banco.
        shutil.rmtree(pasta, ignore_errors=True)
        raise

    return article
