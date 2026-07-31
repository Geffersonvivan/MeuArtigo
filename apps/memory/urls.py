from django.urls import path

from . import views

app_name = "memory"

urlpatterns = [
    path("<slug:area_slug>/", views.grafo_area, name="grafo_area"),
]
