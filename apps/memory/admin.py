from django.contrib import admin

from .models import Entity, EntityMention, MemoryChunk, Reference, Term


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("termo", "area_slug")
    list_filter = ("area_slug",)
    search_fields = ("termo", "variantes")


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "area_slug", "criado_em")
    list_filter = ("tipo", "area_slug")
    search_fields = ("nome",)


@admin.register(EntityMention)
class EntityMentionAdmin(admin.ModelAdmin):
    list_display = ("entity", "article", "criado_em")
    search_fields = ("entity__nome", "article__titulo")


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    """Painel interno de inspeção das fontes — não é a UI do usuário."""

    list_display = ("id", "titulo", "tipo", "verificada", "verificada_em", "article")
    list_filter = ("verificada", "tipo", "article")
    search_fields = ("titulo", "url", "article__titulo")
    readonly_fields = ("verificada_em", "abnt", "nota_verificacao", "criado_em")


@admin.register(MemoryChunk)
class MemoryChunkAdmin(admin.ModelAdmin):
    """Painel interno de inspeção do índice RAG — não é a UI do usuário."""

    list_display = ("article", "ordem", "area_slug", "criado_em")
    list_filter = ("area_slug",)
    search_fields = ("texto", "article__titulo")
    readonly_fields = ("article", "ordem", "texto", "area", "area_slug", "criado_em")
    ordering = ("article_id", "ordem")

    def has_add_permission(self, request):
        return False
