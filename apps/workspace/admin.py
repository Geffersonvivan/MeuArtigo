from django.contrib import admin

from .models import ChatTurn, Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("section", "texto", "resolvido", "criado_em")
    list_filter = ("resolvido",)


@admin.register(ChatTurn)
class ChatTurnAdmin(admin.ModelAdmin):
    """Painel interno de inspeção do chat de escrita — não é a UI do usuário."""

    list_display = ("article", "secao_heading", "aplicada", "cost_usd", "criado_em")
    list_filter = ("aplicada", "article")
    search_fields = ("instrucao", "article__titulo")
    readonly_fields = [f.name for f in ChatTurn._meta.fields]
