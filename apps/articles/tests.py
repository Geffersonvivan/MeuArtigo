from pathlib import Path
from unittest import mock

import pytest

from apps.articles import services
from apps.articles.models import Article, Paragraph, Section
from apps.articles.services import ArticleExistsError, ArticleParams, create_article


def _params(**kw):
    base = dict(assunto="Tema X", area="Teste Área", num_paginas=1, num_linhas=10, estilo="raso")
    base.update(kw)
    return ArticleParams(**base)


@pytest.mark.django_db
def test_create_article_cria_pasta_e_registro():
    a = create_article(_params())
    assert Article.objects.filter(pk=a.pk).exists()
    assert Path(a.pasta).is_dir()
    assert (Path(a.pasta) / "artigo.md").exists()
    assert (Path(a.pasta) / "params.json").exists()


@pytest.mark.django_db
def test_create_article_colisao():
    create_article(_params(assunto="Repetido"))
    with pytest.raises(ArticleExistsError):
        create_article(_params(assunto="Repetido"))


@pytest.mark.django_db
def test_create_article_rollback_atomico():
    n = Article.objects.count()
    with mock.patch.object(services, "_write_physical_folder", side_effect=OSError("disco cheio")):
        with pytest.raises(OSError):
            create_article(_params(assunto="Falha"))
    assert Article.objects.count() == n


@pytest.mark.django_db
def test_render_markdown_das_secoes():
    a = create_article(_params(assunto="Render", titulo="Render"))
    s = Section.objects.create(article=a, ordem=0, titulo="Intro")
    Paragraph.objects.create(section=s, ordem=0, texto="Primeiro parágrafo.")
    md = a.render_markdown()
    assert "# Render" in md and "## Intro" in md and "Primeiro parágrafo." in md


@pytest.mark.django_db
def test_sincronizar_disco_grava_do_banco():
    a = create_article(_params(assunto="Sync"))
    s = Section.objects.create(article=a, ordem=0, titulo="Seção")
    Paragraph.objects.create(section=s, ordem=0, texto="Conteúdo real.")
    services.sincronizar_disco(a, bump_versao=True)
    assert a.versao == 2
    assert "Conteúdo real." in (Path(a.pasta) / "artigo.md").read_text()
