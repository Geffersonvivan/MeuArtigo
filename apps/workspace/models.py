from django.db import models


class Comment(models.Model):
    """Comentário do autor ancorado a uma seção do artigo (revisão por seção)."""

    section = models.ForeignKey(
        "articles.Section", on_delete=models.CASCADE, related_name="comments"
    )
    texto = models.TextField("comentário")
    resolvido = models.BooleanField("resolvido", default=False)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "comentário"
        verbose_name_plural = "comentários"
        ordering = ["criado_em"]

    def __str__(self):
        return f"comentário @ seção {self.section_id}"


class ChatTurn(models.Model):
    """Um turno do chat de escrita (Fase 6): instrução do autor → proposta do Claude
    para uma seção, aplicada ou não. Serve de histórico e auditoria (com custo)."""

    article = models.ForeignKey(
        "articles.Article", on_delete=models.CASCADE, related_name="chat_turns"
    )
    instrucao = models.TextField("instrução")
    secao_index = models.IntegerField("índice da seção", null=True, blank=True)
    secao_heading = models.CharField("título da seção", max_length=300, blank=True)

    proposta = models.TextField("proposta gerada", blank=True)
    aplicada = models.BooleanField("aplicada", default=False)

    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "turno de chat"
        verbose_name_plural = "turnos de chat"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.article_id} · {self.instrucao[:40]} ({'aplicada' if self.aplicada else 'proposta'})"
