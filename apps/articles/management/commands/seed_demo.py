"""Semeia um artigo-demo (Direito Eleitoral) para exercitar o shell do workspace.

Curado, sem LLM. Cria seções + parágrafos + fontes (verificada/duvidosa) + chamadas de
LLM (para o painel Pipeline mostrar custo). Idempotente por área+assunto.

Uso: python manage.py seed_demo
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.articles.models import (Article, Folder, Paragraph, Section, SecaoStatus,
                                  StatusArtigo)
from apps.articles.services import ArticleExistsError, ArticleParams, create_article, sincronizar_disco
from apps.llm.models import LLMCall, Papel
from apps.memory.models import Reference, StatusVerif, TipoFonte

ASSUNTO = "Impulsionamento eleitoral em redes sociais"


class Command(BaseCommand):
    help = "Semeia um artigo-demo para o workspace."

    def handle(self, *args, **opts):
        import shutil
        from pathlib import Path

        from django.conf import settings
        from django.utils.text import slugify

        Article.objects.filter(assunto=ASSUNTO).delete()
        # remove a pasta física também, senão create_article colide (bug do seed).
        pasta = Path(settings.ARTIGOS_ROOT) / slugify("Direito Eleitoral") / slugify(ASSUNTO)
        shutil.rmtree(pasta, ignore_errors=True)
        folder, _ = Folder.objects.get_or_create(slug="uceff", defaults={"nome": "UCEFF"})

        try:
            a = create_article(ArticleParams(
                titulo=ASSUNTO, assunto=ASSUNTO, area="Direito Eleitoral",
                num_paginas=8, num_linhas=30, estilo="juridiques",
            ))
        except ArticleExistsError:
            self.stdout.write(self.style.WARNING("Demo já existe."))
            return
        a.folder = folder
        a.contexto = ("Artigo técnico-jurídico sobre os limites legais do impulsionamento "
                      "eleitoral pago em redes sociais, com base na Lei 9.504/97.")
        a.status = StatusArtigo.REVISAO
        a.versao = 2
        a.save()

        # Fontes
        lei9504 = Reference.objects.create(
            article=a, tipo=TipoFonte.LEI, titulo="Lei nº 9.504, de 30 de setembro de 1997",
            url="https://www.planalto.gov.br/ccivil_03/leis/l9504.htm",
            data_pub=date(1997, 9, 30), data_acesso=date(2026, 7, 30),
            verificada=StatusVerif.OK)
        lei13488 = Reference.objects.create(
            article=a, tipo=TipoFonte.LEI, titulo="Lei nº 13.488, de 6 de outubro de 2017",
            url="https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2017/lei/l13488.htm",
            data_pub=date(2017, 10, 6), data_acesso=date(2026, 7, 30),
            verificada=StatusVerif.OK)
        res23610 = Reference.objects.create(
            article=a, tipo=TipoFonte.JURISPRUDENCIA, titulo="Resolução TSE nº 23.610/2019",
            url="https://www.tse.jus.br/legislacao/compilada/res/2019/resolucao-no-23-610",
            data_pub=date(2019, 12, 18), data_acesso=date(2026, 7, 30),
            verificada=StatusVerif.OK)
        Reference.objects.create(
            article=a, tipo=TipoFonte.SITE, titulo="Notícia sobre gastos de impulsionamento (2024)",
            url="https://exemplo-fonte-duvidosa.com/materia", verificada=StatusVerif.DUVIDOSA,
            nota_verificacao="domínio não oficial; trecho não confirmado")

        secoes = [
            ("Introdução", 10, StatusArtigo and SecaoStatus.PRONTO, [
                "O debate sobre a permeabilidade das redes sociais no processo eleitoral "
                "brasileiro deixou de ser especulativo. Desde 2018, a plataforma digital "
                "tornou-se palco central da disputa política — e, com ela, a compra de "
                "alcance passou a ser prática rotineira, ainda que juridicamente delicada.",
            ]),
            ("O marco legal do impulsionamento", 40, SecaoStatus.PRONTO, [
                f"A [[ref:{lei9504.pk}]], com a redação dada pela [[ref:{lei13488.pk}]], "
                "autorizou expressamente o impulsionamento de conteúdo eleitoral, desde que "
                "contratado por partido, coligação ou candidato, com identificação do "
                "responsável. A vedação recai sobre o impulsionamento por terceiros, prática "
                "que o Tribunal Superior Eleitoral tem tratado com rigor crescente.",
                f"A [[ref:{res23610.pk}]] regulamentou a propaganda eleitoral em rede e "
                "detalhou o que se entende por \"impulsionamento\": o pagamento pela ampliação "
                "artificial do alcance de uma postagem, distinto do disparo em massa e da "
                "propaganda tradicional. Essa distinção conceitual, embora sutil, é o que "
                "separa o lícito do ilícito na prática cotidiana das campanhas.",
                "A doutrina tem convergido no sentido de que o impulsionamento é modalidade "
                "especial de propaganda paga, sujeita a regime próprio e não subsumível às "
                "regras gerais de arrecadação de recursos. A tese, porém, ainda encontra "
                "resistência em parte da jurisprudência regional.",
            ]),
            ("Limites de gasto e prestação de contas", 35, SecaoStatus.PRONTO, [
                "Os gastos com impulsionamento integram o teto de gastos da campanha e devem "
                "ser declarados na prestação de contas, sob pena de rejeição das contas e "
                "possível cassação. A comprovação exige nota fiscal do provedor da plataforma "
                "e identificação do CPF/CNPJ do contratante.",
            ]),
        ]

        for i, (titulo, meta, status, paras) in enumerate(secoes):
            sec = Section.objects.create(
                article=a, ordem=i, titulo=titulo, meta_linhas=meta, status=status)
            for j, texto in enumerate(paras):
                Paragraph.objects.create(section=sec, ordem=j, texto=texto)

        # custos (para o painel Pipeline / SESSÃO)
        LLMCall.objects.create(article=a, papel=Papel.PESQUISA, provider="perplexity",
                               model="sonar", input_tokens=800, output_tokens=1200,
                               cost_usd=Decimal("0.0780"))
        LLMCall.objects.create(article=a, papel=Papel.ESTRUTURA, provider="anthropic",
                               model="claude-opus-5", input_tokens=1500, output_tokens=900,
                               cost_usd=Decimal("0.0525"))
        LLMCall.objects.create(article=a, papel=Papel.REDACAO, provider="anthropic",
                               model="claude-sonnet-5", input_tokens=3000, output_tokens=4200,
                               cost_usd=Decimal("0.3405"))

        sincronizar_disco(a)
        # snapshots de versão (para a comparação de versões)
        from apps.articles.models import Snapshot
        Snapshot.objects.create(article=a, versao=1, label="estrutura",
            markdown=f"# {ASSUNTO}\n\n## Introdução\n\nEsboço inicial da introdução, ainda sem "
                     "desenvolvimento.\n\n## O marco legal do impulsionamento\n\nRascunho do marco legal.")
        Snapshot.objects.create(article=a, versao=2, label="redação", markdown=a.render_markdown())
        # indexa no RAG (para a busca semântica da sidebar)
        try:
            from apps.memory.retrieval import indexar_artigo
            indexar_artigo(a, a.render_markdown())
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Indexação RAG falhou: {exc}"))
        self.stdout.write(self.style.SUCCESS(
            f"Demo criada: id={a.pk} · {a.sections.count()} seções · "
            f"{Paragraph.objects.filter(section__article=a).count()} parágrafos · "
            f"{a.references.count()} fontes."))
