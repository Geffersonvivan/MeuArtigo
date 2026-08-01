from django.db import models


class Estilo(models.TextChoices):
    """Estilos de escrita suportados (mapeiam para instruções de prompt — PROJETO.md §4)."""

    APROFUNDADO = "aprofundado", "Aprofundado"
    RASO = "raso", "Raso"
    INTELECTUAL = "intelectual", "Intelectual"
    POPULAR = "popular", "Popular"
    JURIDIQUES = "juridiques", "Juridiquês"
    TECNICO_POPULAR = "tecnico_popular", "Técnico/Popular"


class StatusArtigo(models.TextChoices):
    """Etapa do artigo no pipeline (PROJETO.md §3)."""

    RASCUNHO = "rascunho", "Rascunho"
    PESQUISA = "pesquisa", "Pesquisa"
    ESTRUTURA = "estrutura", "Estrutura"
    REDACAO = "redacao", "Redação"
    REVISAO = "revisao", "Revisão"
    FINAL = "final", "Final"


class Folder(models.Model):
    """Pasta para organizar artigos na sidebar (ex.: UCEFF, Blog, Modelos)."""

    nome = models.CharField("nome", max_length=200)
    slug = models.SlugField("slug", max_length=200, unique=True)
    ordem = models.PositiveIntegerField("ordem", default=0)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "pasta"
        verbose_name_plural = "pastas"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class SecaoStatus(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    GERANDO = "gerando", "Gerando"
    PRONTO = "pronto", "Pronto"


class Article(models.Model):
    """Um artigo. O banco é a fonte da verdade; o .md é renderizado a partir dele.

    A pasta física vive em artigos/<area_slug>/<assunto_slug>/ (PROJETO.md §6).
    Criação/sincronização disco↔banco é feita exclusivamente por apps.articles.services.
    """

    titulo = models.CharField("título", max_length=300)
    assunto = models.CharField("assunto", max_length=300)
    area = models.CharField("área", max_length=200)

    # Briefing/ideia do autor — injetado em todo prompt do workspace (Fase 6).
    contexto = models.TextField("contexto/ideia", blank=True)

    # Organização (sidebar) e versionamento.
    folder = models.ForeignKey(
        "Folder", on_delete=models.SET_NULL, null=True, blank=True, related_name="articles"
    )
    versao = models.PositiveIntegerField("versão", default=1)

    area_slug = models.SlugField("slug da área", max_length=200)
    assunto_slug = models.SlugField("slug do assunto", max_length=200)

    num_paginas = models.PositiveIntegerField("nº de páginas", default=1)
    num_linhas = models.PositiveIntegerField("nº de linhas", default=10)
    estilo = models.CharField(
        "estilo", max_length=30, choices=Estilo.choices, default=Estilo.TECNICO_POPULAR
    )

    pasta = models.CharField("pasta física", max_length=500)
    status = models.CharField(
        "status", max_length=30, choices=StatusArtigo.choices, default=StatusArtigo.RASCUNHO
    )

    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "artigo"
        verbose_name_plural = "artigos"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["area_slug", "assunto_slug"],
                name="uniq_area_assunto",
            )
        ]

    def __str__(self):
        return f"{self.titulo} ({self.area})"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("workspace:app_article", args=[self.pk])

    def render_markdown(self) -> str:
        """Renderiza o artigo a partir das seções/parágrafos (banco = fonte da verdade)."""
        partes = [f"# {self.titulo}\n"]
        for sec in self.sections.all():
            corpo = sec.render_corpo()
            partes.append(f"## {sec.titulo}\n\n{corpo}" if corpo else f"## {sec.titulo}")
        return "\n\n".join(partes).strip() + "\n"

    @property
    def total_linhas_meta(self) -> int:
        return self.num_paginas * self.num_linhas


class Section(models.Model):
    """Uma seção do artigo. O artigo é uma lista ordenada de seções — geração e edição
    acontecem por seção (e os comentários se ancoram aqui)."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="sections")
    ordem = models.PositiveIntegerField("ordem", default=0)
    titulo = models.CharField("título", max_length=300)
    resumo = models.TextField("o que cobrir", blank=True)   # do Arquiteto
    conteudo = models.TextField("conteúdo", blank=True)       # do Redator/Editor
    meta_linhas = models.PositiveIntegerField("meta de linhas", default=0)
    status = models.CharField(
        "status", max_length=12, choices=SecaoStatus.choices, default=SecaoStatus.PENDENTE
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "seção"
        verbose_name_plural = "seções"
        ordering = ["article_id", "ordem"]
        constraints = [
            models.UniqueConstraint(fields=["article", "ordem"], name="uniq_article_ordem")
        ]

    def __str__(self):
        return f"{self.article_id}·{self.ordem} {self.titulo}"

    def render_corpo(self) -> str:
        """Corpo da seção: junta os parágrafos (fonte da verdade) ou o conteudo legado."""
        paras = list(self.paragraphs.all())
        if paras:
            return "\n\n".join(p.texto.strip() for p in paras if p.texto.strip())
        return self.conteudo.strip()

    @property
    def linhas_atuais(self) -> int:
        return len([l for l in self.render_corpo().splitlines() if l.strip()])


class Paragraph(models.Model):
    """Um parágrafo — unidade de edição da 'bancada' (o Redator reescreve por parágrafo).

    Pode conter marcadores [[ref:ID]] (viram <span class="cite"> na renderização)."""

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="paragraphs")
    ordem = models.PositiveIntegerField("ordem", default=0)
    texto = models.TextField("texto", blank=True)
    locked = models.BooleanField("travado", default=False)
    # ids de avisos de margem (ex.: "ns-p58", "gl-p58-JE") que o autor dispensou.
    avisos_ignorados = models.JSONField("avisos ignorados", default=list, blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "parágrafo"
        verbose_name_plural = "parágrafos"
        ordering = ["section_id", "ordem"]
        constraints = [
            models.UniqueConstraint(fields=["section", "ordem"], name="uniq_section_ordem")
        ]

    def __str__(self):
        return f"§{self.section_id}·{self.ordem}"


class Snapshot(models.Model):
    """Versão congelada do artigo (para comparação de versões e histórico)."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="snapshots")
    versao = models.PositiveIntegerField("versão")
    label = models.CharField("rótulo", max_length=120, blank=True)  # ex.: "02-redacao"
    markdown = models.TextField("markdown")
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "snapshot"
        verbose_name_plural = "snapshots"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.article_id} v{self.versao} ({self.label})"
