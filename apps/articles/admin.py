from django.contrib import admin

from .models import Article, Folder, Paragraph, Section, Snapshot


class ParagraphInline(admin.TabularInline):
    model = Paragraph
    extra = 0
    fields = ("ordem", "texto", "locked")


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("article", "versao", "label", "criado_em")
    list_filter = ("article",)


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ordem")
    prepopulated_fields = {"slug": ("nome",)}


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ("ordem", "titulo", "status", "meta_linhas")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    inlines = [ParagraphInline]
    list_display = ("article", "ordem", "titulo", "status", "meta_linhas")
    list_filter = ("status", "article")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Painel interno de inspeção — NÃO é a interface do usuário (essa é o frontend)."""

    inlines = [SectionInline]
    list_display = ("titulo", "area", "folder", "estilo", "status", "versao", "criado_em")
    list_filter = ("status", "estilo", "area")
    search_fields = ("titulo", "assunto", "area")
    readonly_fields = ("area_slug", "assunto_slug", "pasta", "criado_em", "atualizado_em")
    ordering = ("-criado_em",)
