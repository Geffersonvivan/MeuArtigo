import json
from datetime import date
from unittest import mock

import pytest
from django.test import Client

from apps.articles.models import Paragraph, Section, StatusArtigo
from apps.articles.services import ArticleParams, create_article
from apps.memory.models import Reference, StatusVerif, TipoFonte
from apps.workspace import serialize, views
from apps.workspace.render import render_paragraph


def _art_com_conteudo():
    a = create_article(ArticleParams(assunto="Impulsionamento", area="Direito Eleitoral",
        num_paginas=1, num_linhas=10, estilo="raso"))
    ref = Reference.objects.create(article=a, tipo=TipoFonte.LEI, titulo="Lei nº 9.504/1997",
        url="https://www.planalto.gov.br/x", data_pub=date(1997, 9, 30), verificada=StatusVerif.OK)
    dub = Reference.objects.create(article=a, tipo=TipoFonte.SITE, titulo="Blog",
        url="https://x.com", verificada=StatusVerif.DUVIDOSA)
    s = Section.objects.create(article=a, ordem=0, titulo="Intro", meta_linhas=10)
    Paragraph.objects.create(section=s, ordem=0, texto=f"A [[ref:{ref.pk}]] rege o tema.")
    return a, ref, dub, s


def test_render_paragraph_cite():
    class R:
        ok = True
        def short_title(self):
            return "Lei nº 9.504/1997"
    html = render_paragraph("A [[ref:5]] rege.", {5: R()})
    assert 'class="cite" data-ref="5"' in html and "Lei nº 9.504/1997" in html


@pytest.mark.django_db
def test_serialize_shape():
    a, ref, dub, s = _art_com_conteudo()
    d = serialize.article_to_appdata(a)
    assert d["articleId"] == a.pk
    assert d["articles"]["a1"]["sections"][0]["title"] == "Intro"
    assert d["state"]["sourcesToDecide"] == 1  # a duvidosa
    assert "class=\"cite\"" in d["articles"]["a1"]["sections"][0]["paragraphs"][0]["html"]
    assert any(x["badgeClass"] == "duvidosa" for x in d["sources"])


@pytest.mark.django_db
def test_comment_endpoint():
    a, ref, dub, s = _art_com_conteudo()
    p = s.paragraphs.first()
    c = Client()
    r = c.post(f"/workspace/paragraph/{p.pk}/comment/",
               data=json.dumps({"texto": "Rever isto."}), content_type="application/json")
    assert r.status_code == 200
    lst = c.get(f"/workspace/paragraph/{p.pk}/comments/").json()["comments"]
    assert len(lst) == 1 and lst[0]["texto"] == "Rever isto."


@pytest.mark.django_db
def test_reference_decide():
    a, ref, dub, s = _art_com_conteudo()
    c = Client()
    r = c.post(f"/workspace/reference/{dub.pk}/decide/",
               data=json.dumps({"decisao": "aceitar"}), content_type="application/json")
    assert r.json()["badgeClass"] == "verificada"
    dub.refresh_from_db()
    assert dub.verificada == StatusVerif.OK


@pytest.mark.django_db
def test_status_finalize_cria_snapshot():
    a, *_ = _art_com_conteudo()
    c = Client()
    r = c.post(f"/workspace/article/{a.pk}/status/",
               data=json.dumps({"acao": "finalize"}), content_type="application/json")
    assert r.json()["status"] == "final"
    a.refresh_from_db()
    assert a.status == StatusArtigo.FINAL and a.versao == 2
    assert a.snapshots.count() == 1


@pytest.mark.django_db
def test_export_md_resolve_refs():
    a, ref, dub, s = _art_com_conteudo()
    c = Client()
    r = c.get(f"/workspace/article/{a.pk}/export/md/")
    assert r.status_code == 200
    md = r.content.decode()
    assert "(BRASIL, 1997)" in md and "## Referências" in md and "[[ref:" not in md
    assert "RASCUNHO" in md  # não-final


@pytest.mark.django_db
def test_search_semantico(monkeypatch):
    from apps.memory.models import MemoryChunk
    a, *_ = _art_com_conteudo()
    MemoryChunk.objects.create(article=a, ordem=0, texto="impulsionamento pago em redes",
        embedding=[0.1] * 1024, area=a.area, area_slug=a.area_slug)

    class FakeEmb:
        def embed_one(self, *args, **kw):
            return [0.1] * 1024
    monkeypatch.setattr("apps.memory.embeddings.get_embedder", lambda *a, **k: FakeEmb())
    r = Client().get("/workspace/search/?q=impulsionamento")
    assert r.status_code == 200
    assert len(r.json()["results"]) >= 1
