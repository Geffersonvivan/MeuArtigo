"""Interface de abstração das LLMs.

Convenção do projeto: o código de negócio NUNCA fala com a API de um provedor
direto — sempre através desta interface. Trocar/adicionar modelo vira configuração,
não reescrita (PROJETO.md §3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class LLMResult:
    """Resultado normalizado de uma chamada a uma LLM, com tokens e custo.

    `sources`/`citations` são preenchidos por provedores com busca web (Perplexity)
    e servem de matéria-prima para as referências (Fase 5). Vazios nos demais.
    """

    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Decimal = Decimal("0")
    stop_reason: str = ""
    sources: list[dict] = field(default_factory=list)   # [{title, url, snippet, date}]
    citations: list[str] = field(default_factory=list)  # URLs
    raw: Any = field(default=None, repr=False)


class LLMProviderError(Exception):
    """Falha ao chamar um provedor de LLM (credenciais, rede, API)."""


class LLMProvider(ABC):
    """Contrato mínimo que todo provedor (Claude, GPT, Perplexity) deve cumprir."""

    #: identificador curto do provedor ("anthropic", "openai", "perplexity")
    name: str = "base"

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Executa uma chamada de completude e devolve um LLMResult normalizado."""
        raise NotImplementedError

    def generate(self, *, system: str, prompt: str, max_tokens: int, **kwargs: Any) -> LLMResult:
        """Atalho para o caso comum de um único turno de usuário."""
        return self.complete(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            **kwargs,
        )

    def stream_generate(self, *, system, prompt: str, max_tokens: int,
                        on_done=None, **kwargs: Any):
        """Gera texto em streaming (yield de pedaços). `on_done(LLMResult)` é chamado
        ao final. Nem todo provedor implementa — o padrão levanta NotImplementedError."""
        raise NotImplementedError(f"{self.name} não suporta streaming.")
