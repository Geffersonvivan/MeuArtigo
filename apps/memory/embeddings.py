"""Geração de embeddings — abstração `Embedder` (mesma filosofia do LLMProvider).

Claude e Perplexity não geram embeddings; usamos a Voyage AI (parceiro recomendado
pela Anthropic). Ver PROJETO.md §5/§11.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    tokens: int
    model: str
    provider: str


class EmbedderError(Exception):
    """Falha ao gerar embeddings (credencial, rede, API)."""


class Embedder(ABC):
    name: str = "base"
    dimensions: int = 0

    @abstractmethod
    def embed(self, texts: Iterable[str], *, input_type: str = "document") -> EmbeddingResult:
        """Vetoriza textos. `input_type`: 'document' para indexar, 'query' para buscar."""
        raise NotImplementedError

    def embed_one(self, text: str, *, input_type: str = "document") -> list[float]:
        return self.embed([text], input_type=input_type).vectors[0]


class VoyageEmbedder(Embedder):
    name = "voyage"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        import voyageai

        self._client = voyageai.Client(api_key=api_key or getattr(settings, "VOYAGE_API_KEY", "") or None)
        self.model = model or getattr(settings, "EMBEDDING_MODEL", "voyage-3.5")
        self.dimensions = getattr(settings, "EMBEDDING_DIMENSIONS", 1024)

    def embed(self, texts: Iterable[str], *, input_type: str = "document") -> EmbeddingResult:
        batch = [t for t in texts]
        if not batch:
            return EmbeddingResult(vectors=[], tokens=0, model=self.model, provider=self.name)
        try:
            r = self._client.embed(batch, model=self.model, input_type=input_type)
        except Exception as exc:  # SDK levanta tipos próprios (auth, rate, conexão)
            raise EmbedderError(f"Falha na Voyage AI: {exc}") from exc
        return EmbeddingResult(
            vectors=r.embeddings, tokens=r.total_tokens, model=self.model, provider=self.name
        )


def get_embedder(name: str | None = None, **kwargs) -> Embedder:
    name = name or getattr(settings, "EMBEDDING_PROVIDER", "voyage")
    if name == "voyage":
        return VoyageEmbedder(**kwargs)
    raise EmbedderError(f"Provedor de embeddings desconhecido: {name!r}")
