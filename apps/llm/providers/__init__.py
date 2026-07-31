"""Registro/fábrica de provedores de LLM.

Uso: `get_provider("anthropic")` no código de negócio — nunca instanciar SDK direto.
"""

from __future__ import annotations

from .base import LLMProvider, LLMProviderError, LLMResult

_REGISTRY: dict[str, type[LLMProvider]] = {}


def register(cls: type[LLMProvider]) -> type[LLMProvider]:
    _REGISTRY[cls.name] = cls
    return cls


def get_provider(name: str = "anthropic", **kwargs) -> LLMProvider:
    """Devolve uma instância do provedor pedido. Importa sob demanda para evitar
    exigir SDKs de provedores não usados."""
    if name not in _REGISTRY:
        if name == "anthropic":
            from .anthropic import AnthropicProvider

            register(AnthropicProvider)
        elif name == "perplexity":
            from .perplexity import PerplexityProvider

            register(PerplexityProvider)
        else:
            raise LLMProviderError(f"Provedor de LLM desconhecido: {name!r}")
    return _REGISTRY[name](**kwargs)


__all__ = ["LLMProvider", "LLMProviderError", "LLMResult", "get_provider", "register"]
