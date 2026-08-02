from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class TipoFonte(models.TextChoices):
    LEI = "lei", "Lei/norma"
    JURISPRUDENCIA = "jurisprudencia", "Jurisprudência"
    DOUTRINA = "doutrina", "Doutrina"
    NOTICIA = "noticia", "Notícia"
    SITE = "site", "Site/artigo"
    VIDEO = "video", "Vídeo"


class StatusVerif(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    OK = "ok", "Verificada"
    DUVIDOSA = "duvidosa", "Duvidosa"
    INEXISTENTE = "inexistente", "Inexistente"


class EntityTipo(models.TextChoices):
    LEI = "lei", "Lei/norma"
    JURISPRUDENCIA = "jurisprudencia", "Jurisprudência"
    CONCEITO = "conceito", "Conceito"
    ORGAO = "orgao", "Órgão/instituição"
    PESSOA = "pessoa", "Pessoa"
    OUTRO = "outro", "Outro"


class Entity(models.Model):
    """Nó do grafo de entidades (PROJETO.md §5b) — conceito/lei/órgão do domínio,
    escopado por área. Conecta-se aos artigos que o citam (via EntityMention).
    Evolução que conversa com a skill /graphify."""

    nome = models.CharField("nome", max_length=300)
    slug = models.SlugField("slug", max_length=300)
    tipo = models.CharField("tipo", max_length=20, choices=EntityTipo.choices, default=EntityTipo.CONCEITO)
    area_slug = models.SlugField("slug da área", max_length=200)
    descricao = models.TextField("descrição", blank=True)
    articles = models.ManyToManyField(
        "articles.Article", through="EntityMention", related_name="entities"
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "entidade"
        verbose_name_plural = "entidades"
        ordering = ["area_slug", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["area_slug", "slug"], name="uniq_area_entity")
        ]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class EntityMention(models.Model):
    """Aresta entidade↔artigo: um artigo menciona uma entidade."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="mentions")
    article = models.ForeignKey(
        "articles.Article", on_delete=models.CASCADE, related_name="entity_mentions"
    )
    trecho = models.TextField("trecho", blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "menção de entidade"
        verbose_name_plural = "menções de entidade"
        constraints = [
            models.UniqueConstraint(fields=["entity", "article"], name="uniq_entity_article")
        ]

    def __str__(self):
        return f"{self.entity.nome} @ {self.article_id}"


class Term(models.Model):
    """Vocabulário controlado da área (glossário). A detecção determinística sinaliza
    variantes 'fora do glossário' e sugere o termo preferido — sem LLM (PROJETO §5c)."""

    area_slug = models.SlugField("slug da área", max_length=200)
    termo = models.CharField("termo preferido", max_length=200)
    variantes = models.TextField("variantes (uma por linha)", blank=True)
    definicao = models.TextField("definição", blank=True)

    class Meta:
        verbose_name = "termo do glossário"
        verbose_name_plural = "glossário"
        ordering = ["area_slug", "termo"]
        constraints = [
            models.UniqueConstraint(fields=["area_slug", "termo"], name="uniq_area_termo")
        ]

    def lista_variantes(self) -> list[str]:
        return [v.strip() for v in self.variantes.splitlines() if v.strip()]

    def __str__(self):
        return f"{self.termo} ({self.area_slug})"


class Reference(models.Model):
    """Fonte de um artigo (PROJETO.md §9). O banco é a fonte da verdade; a citação no
    texto é feita por marcador [[ref:ID]] (= pk), resolvido pelo sistema para ABNT.

    Só fontes `verificada=ok` podem ser citadas no texto final (regra de ouro §9.2).
    """

    article = models.ForeignKey(
        "articles.Article", on_delete=models.CASCADE, related_name="references"
    )
    tipo = models.CharField("tipo", max_length=20, choices=TipoFonte.choices, default=TipoFonte.SITE)
    titulo = models.CharField("título", max_length=400)
    autor = models.CharField("autor", max_length=300, blank=True)
    url = models.URLField("URL", max_length=800, blank=True)
    trecho = models.TextField("trecho citado", blank=True)
    data_pub = models.DateField("data de publicação", null=True, blank=True)
    data_acesso = models.DateField("data de acesso", null=True, blank=True)

    abnt = models.TextField("referência ABNT", blank=True)
    verificada = models.CharField(
        "status", max_length=20, choices=StatusVerif.choices, default=StatusVerif.PENDENTE
    )
    verificada_em = models.DateTimeField("verificada em", null=True, blank=True)
    nota_verificacao = models.TextField("nota da verificação", blank=True)

    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "referência"
        verbose_name_plural = "referências"
        ordering = ["article_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["article", "url"],
                condition=~models.Q(url=""),
                name="uniq_article_url",
            )
        ]

    def __str__(self):
        return f"[{self.pk}] {self.titulo[:60]} ({self.get_verificada_display()})"

    @property
    def ok(self) -> bool:
        return self.verificada == StatusVerif.OK

    def short_title(self) -> str:
        """Forma curta para citação inline (ex.: 'Lei nº 9.504/1997')."""
        import re
        m = re.search(r"(Lei|Decreto|Resolução|Súmula)[^,]*?n[ºo°]?\s*([\d.\-/]+)", self.titulo, re.I)
        if m:
            ano = re.search(r"(19|20)\d{2}", self.titulo)
            num = m.group(2).rstrip(".")
            return f"{m.group(1)} nº {num}" + (f"/{ano.group(0)}" if ano and '/' not in num else "")
        return self.titulo[:60]


class MemoryChunk(models.Model):
    """Trecho de um artigo vetorizado para busca semântica (RAG — PROJETO.md §5a).

    Cada parágrafo/bloco do artigo.md vira um embedding no pgvector. Antes de redigir,
    buscamos trechos semelhantes já escritos para evitar repetição e sugerir referências.
    """

    article = models.ForeignKey(
        "articles.Article", on_delete=models.CASCADE, related_name="chunks"
    )
    ordem = models.PositiveIntegerField("ordem no artigo", default=0)
    texto = models.TextField("texto")
    embedding = VectorField(dimensions=settings.EMBEDDING_DIMENSIONS)
    area = models.CharField("área", max_length=200)
    area_slug = models.SlugField("slug da área", max_length=200)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "trecho de memória"
        verbose_name_plural = "trechos de memória"
        ordering = ["article_id", "ordem"]
        indexes = [
            HnswIndex(
                name="memorychunk_emb_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            models.Index(fields=["area_slug"], name="memorychunk_area_idx"),
        ]

    def __str__(self):
        return f"chunk #{self.ordem} de {self.article_id} ({self.area_slug})"


class VideoSource(models.Model):
    """Um vídeo do YouTube usado como fonte de IDEIAS para complementar o artigo.

    A transcrição (legendas) é resumida pelo Redator em ideias (VideoIdea). O vídeo
    pode virar uma Reference citável (audiovisual) via ação "Usar como fonte".
    """

    article = models.ForeignKey(
        "articles.Article", on_delete=models.CASCADE, related_name="videos"
    )
    tipo = models.CharField("tipo", max_length=10, default="youtube")  # youtube | pdf
    url = models.URLField("URL", max_length=800, blank=True)
    video_id = models.CharField("ID da fonte", max_length=64)
    titulo = models.CharField("título", max_length=400, blank=True)
    canal = models.CharField("canal", max_length=300, blank=True)
    publicado_em = models.CharField("publicado em", max_length=40, blank=True)
    resumo = models.TextField("resumo", blank=True)
    tem_transcricao = models.BooleanField("tem transcrição", default=False)
    reference = models.ForeignKey(
        "memory.Reference", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="video", help_text="Reference criada quando vira fonte citável.",
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "vídeo (fonte)"
        verbose_name_plural = "vídeos (fontes)"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["article", "video_id"], name="uniq_article_video"),
        ]

    def __str__(self):
        return f"{self.titulo or self.video_id} ({self.article_id})"


class VideoIdea(models.Model):
    """Uma ideia extraída da transcrição de um vídeo. Se `selecionada`, entra no
    'banco de ideias' do artigo e é injetada como contexto na redação (Redator)."""

    video = models.ForeignKey(VideoSource, on_delete=models.CASCADE, related_name="ideias")
    texto = models.TextField("ideia")
    citavel = models.BooleanField("afirmação citável", default=False)
    selecionada = models.BooleanField("selecionada", default=False)
    ordem = models.PositiveIntegerField("ordem", default=0)

    class Meta:
        verbose_name = "ideia de vídeo"
        verbose_name_plural = "ideias de vídeo"
        ordering = ["video_id", "ordem"]

    def __str__(self):
        return f"ideia #{self.ordem} de {self.video_id}"
