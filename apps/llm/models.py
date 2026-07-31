from django.db import models


class Papel(models.TextChoices):
    """Etapa/papel da chamada no pipeline (PROJETO.md §3)."""

    PESQUISA = "pesquisa", "Pesquisa"
    ESTRUTURA = "estrutura", "Estrutura"
    REDACAO = "redacao", "Redação"
    REVISAO = "revisao", "Revisão"
    EDICAO = "edicao", "Edição final"
    VERIFICACAO = "verificacao", "Verificação"
    ENTIDADES = "entidades", "Extração de entidades"


class LLMCall(models.Model):
    """Registro de cada chamada a uma LLM — tokens e custo por etapa.

    Convenção do projeto: logar tokens/custo por etapa do pipeline (Perplexity/Claude
    somam custo). Serve de auditoria e base para relatórios de gasto por artigo.
    """

    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.CASCADE,
        related_name="llm_calls",
        null=True,
        blank=True,
    )
    papel = models.CharField("papel", max_length=20, choices=Papel.choices)
    provider = models.CharField("provedor", max_length=30)
    model = models.CharField("modelo", max_length=80)

    input_tokens = models.PositiveIntegerField("tokens de entrada", default=0)
    output_tokens = models.PositiveIntegerField("tokens de saída", default=0)
    cost_usd = models.DecimalField("custo (USD)", max_digits=10, decimal_places=6, default=0)

    ok = models.BooleanField("sucesso", default=True)
    erro = models.TextField("erro", blank=True)

    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "chamada de LLM"
        verbose_name_plural = "chamadas de LLM"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.provider}/{self.model} · {self.get_papel_display()} · ${self.cost_usd}"
