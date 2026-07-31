from datetime import date
from unittest import mock

import pytest

from apps.articles.services import ArticleParams, create_article
from apps.memory import verify
from apps.memory.citations import (citacao_no_corpo, formatar_abnt,
                                   gerar_referencias_md, resolver_marcadores)
from apps.memory.models import Reference, StatusVerif, TipoFonte
from apps.workspace.detect import detectar_paragrafo


def _art():
    return create_article(ArticleParams(assunto="Fontes", area="Teste", num_paginas=1,
                                        num_linhas=10, estilo="raso"))


@pytest.mark.django_db
def test_formatar_abnt_lei():
    a = _art()
    r = Reference.objects.create(article=a, tipo=TipoFonte.LEI,
        titulo="Lei nº 9.504, de 30 de setembro de 1997",
        url="https://www.planalto.gov.br/x", data_pub=date(1997, 9, 30),
        data_acesso=date(2026, 7, 30), verificada=StatusVerif.OK)
    abnt = formatar_abnt(r)
    assert "BRASIL" in abnt and "1997" in abnt and "Acesso em" in abnt
    assert citacao_no_corpo(r) == "(BRASIL, 1997)"


@pytest.mark.django_db
def test_resolver_marcadores_so_ok():
    a = _art()
    ok = Reference.objects.create(article=a, tipo=TipoFonte.LEI, titulo="Lei nº 1/2000",
        data_pub=date(2000, 1, 1), verificada=StatusVerif.OK)
    dub = Reference.objects.create(article=a, tipo=TipoFonte.SITE, titulo="Fonte X",
        url="https://x.com", verificada=StatusVerif.DUVIDOSA)
    refs = {ok.pk: ok, dub.pk: dub}
    texto, usados = resolver_marcadores(f"A [[ref:{ok.pk}]] e [[ref:{dub.pk}]] e [[ref:999]].", refs)
    assert "(BRASIL, 2000)" in texto
    assert [u.pk for u in usados] == [ok.pk]  # duvidosa e inexistente descartadas
    assert "## Referências" in gerar_referencias_md(usados)


@pytest.mark.django_db
def test_detectar_sem_fonte_e_glossario():
    a = _art()
    # afirmação factual (ano) sem [[ref]] → sem-fonte
    html, notas = detectar_paragrafo("p1", "Em 2024 houve mudança.", {}, [])
    assert any(n["label"] == "Sem fonte" for n in notas)
    assert 'class="no-source"' in html
    # variante do glossário → aviso de glossário
    _, notas2 = detectar_paragrafo("p2", "Falou-se em boost pago nas redes [[ref:1]].", {},
                                   [("impulsionamento pago", ["boost"])])
    assert any(n["label"] == "Glossário" for n in notas2)


@pytest.mark.django_db
def test_verificar_referencia_oficial_e_inexistente():
    a = _art()
    ok = Reference.objects.create(article=a, tipo=TipoFonte.LEI, titulo="Lei",
        url="https://www.planalto.gov.br/lei")
    resp = mock.Mock(status_code=200, text="conteúdo")
    with mock.patch.object(verify.httpx, "get", return_value=resp):
        verify.verificar_referencia(ok)
    assert ok.verificada == StatusVerif.OK

    bad = Reference.objects.create(article=a, tipo=TipoFonte.SITE, titulo="X",
        url="https://x.com/y")
    with mock.patch.object(verify.httpx, "get", return_value=mock.Mock(status_code=404, text="")):
        verify.verificar_referencia(bad)
    assert bad.verificada == StatusVerif.INEXISTENTE
