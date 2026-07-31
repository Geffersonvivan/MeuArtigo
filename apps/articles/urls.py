from django.urls import path

from . import views

app_name = "articles"

urlpatterns = [
    path("", views.article_list, name="list"),
    path("novo/", views.article_create, name="create"),
    path("<int:pk>/", views.article_detail, name="detail"),
    path("<int:pk>/redigir/", views.article_write, name="write"),
    path("<int:pk>/pipeline/", views.article_pipeline, name="pipeline"),
    path("<int:pk>/verificar-fontes/", views.article_verify_sources, name="verify_sources"),
    path("<int:pk>/extrair-entidades/", views.article_extract_entities, name="extract_entities"),
]
