from django.urls import path

from . import views

app_name = "workspace"

urlpatterns = [
    path("app/", views.app_workspace, name="app"),
    path("app/<int:pk>/", views.app_workspace, name="app_article"),
    path("paragraph/<int:pk>/rewrite/", views.paragraph_rewrite, name="paragraph_rewrite"),
    path("section/<int:pk>/write/", views.section_write, name="section_write"),
    path("paragraph/<int:pk>/accept/", views.paragraph_accept, name="paragraph_accept"),
    path("paragraph/<int:pk>/ignore-note/", views.paragraph_ignore_note, name="paragraph_ignore_note"),
    path("paragraph/<int:pk>/comment/", views.paragraph_comment, name="paragraph_comment"),
    path("paragraph/<int:pk>/comments/", views.paragraph_comments, name="paragraph_comments"),
    path("search/", views.workspace_search, name="workspace_search"),
    path("article/<int:pk>/snapshots/", views.article_snapshots, name="article_snapshots"),
    path("article/<int:pk>/export/<str:fmt>/", views.article_export, name="article_export"),
    path("article/create/", views.workspace_create, name="workspace_create"),
    path("overlap/", views.workspace_overlap, name="workspace_overlap"),
    path("article/<int:pk>/status/", views.article_status, name="article_status"),
    path("reference/<int:pk>/verify/", views.reference_verify, name="reference_verify"),
    path("reference/<int:pk>/decide/", views.reference_decide, name="reference_decide"),
    path("reference/<int:pk>/buscar/", views.reference_buscar, name="reference_buscar"),
]
