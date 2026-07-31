from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # UI única: o workspace é a home. As páginas fragmentadas antigas foram removidas.
    path("", RedirectView.as_view(url="/workspace/app/", permanent=False)),
    path("workspace/", include("apps.workspace.urls")),
    path("grafo/", include("apps.memory.urls")),
    path("admin/", admin.site.urls),
]
