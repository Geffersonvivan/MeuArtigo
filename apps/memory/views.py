import json

from django.shortcuts import render

from apps.articles.models import Article

from .graph import grafo_da_area
from .models import EntityTipo


def grafo_area(request, area_slug):
    """Página do grafo de entidades de uma área: nós + arestas de co-ocorrência."""
    nos, arestas = grafo_da_area(area_slug)
    art = Article.objects.filter(area_slug=area_slug).first()
    nome_area = art.area if art else area_slug

    grafo_json = json.dumps({
        "nodes": [{"id": n.id, "nome": n.nome, "tipo": n.tipo, "artigos": n.artigos} for n in nos],
        "edges": [{"a": e.a, "b": e.b, "peso": e.peso} for e in arestas],
    })

    return render(request, "memory/grafo.html", {
        "area_slug": area_slug,
        "nome_area": nome_area,
        "nos": sorted(nos, key=lambda n: (-n.artigos, n.nome)),
        "total_nos": len(nos),
        "total_arestas": len(arestas),
        "grafo_json": grafo_json,
    })
