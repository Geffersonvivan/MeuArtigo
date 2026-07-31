from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    """Habilita a extensão pgvector no PostgreSQL (base do RAG, ver PROJETO.md §5)."""

    initial = True

    dependencies = []

    operations = [
        VectorExtension(),
    ]
