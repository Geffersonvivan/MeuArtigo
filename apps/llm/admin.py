from django.contrib import admin

from .models import LLMCall


@admin.register(LLMCall)
class LLMCallAdmin(admin.ModelAdmin):
    """Painel interno de auditoria de custo/tokens — não é a UI do usuário."""

    list_display = ("criado_em", "provider", "model", "papel", "input_tokens",
                    "output_tokens", "cost_usd", "ok", "article")
    list_filter = ("provider", "papel", "ok", "model")
    search_fields = ("article__titulo", "model")
    readonly_fields = [f.name for f in LLMCall._meta.fields]
    ordering = ("-criado_em",)
