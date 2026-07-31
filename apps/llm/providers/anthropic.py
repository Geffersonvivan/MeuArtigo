"""Provedor Claude (Anthropic) — papel de redação/edição final (PROJETO.md §3).

Usa o SDK oficial `anthropic` com streaming (redação é saída longa) e thinking
adaptativo. Normaliza a resposta para LLMResult com contagem de tokens e custo.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import anthropic
from django.conf import settings

from .base import LLMProvider, LLMProviderError, LLMResult

#: Preço por 1M de tokens (USD), por modelo: (input, output).
#: Verificar contra a tabela de preços vigente da Anthropic ao ajustar modelos.
PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "claude-opus-5": (Decimal("5"), Decimal("25")),
    "claude-opus-4-8": (Decimal("5"), Decimal("25")),
    "claude-sonnet-5": (Decimal("3"), Decimal("15")),
    "claude-sonnet-4-6": (Decimal("3"), Decimal("15")),
    "claude-haiku-4-5": (Decimal("1"), Decimal("5")),
}

DEFAULT_MODEL = "claude-opus-5"


def _cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    in_price, out_price = PRICING.get(model, (Decimal("0"), Decimal("0")))
    million = Decimal("1000000")
    return (
        Decimal(input_tokens) / million * in_price
        + Decimal(output_tokens) / million * out_price
    )


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or getattr(settings, "ANTHROPIC_API_KEY", "") or None
        # Se `key` for None, o SDK ainda resolve credenciais do ambiente / perfil `ant`.
        self._client = anthropic.Anthropic(api_key=key)
        self.default_model = model or getattr(settings, "ANTHROPIC_MODEL", DEFAULT_MODEL)

    def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int,
        model: str | None = None,
        thinking: bool = True,
        **kwargs: Any,
    ) -> LLMResult:
        model_id = model or self.default_model
        params: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if thinking:
            params["thinking"] = {"type": "adaptive"}

        try:
            with self._client.messages.stream(**params) as stream:
                # Consome o stream (protege contra timeouts em saídas longas)
                for _ in stream.text_stream:
                    pass
                final = stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise LLMProviderError(
                "Credencial da Anthropic inválida ou ausente. Configure ANTHROPIC_API_KEY no .env."
            ) from exc
        except anthropic.APIStatusError as exc:
            raise LLMProviderError(f"Erro da API Anthropic ({exc.status_code}): {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMProviderError("Falha de conexão com a API Anthropic.") from exc

        text = "".join(b.text for b in final.content if b.type == "text")
        usage = final.usage
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0

        return LLMResult(
            text=text,
            provider=self.name,
            model=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_cost(model_id, input_tokens, output_tokens),
            stop_reason=final.stop_reason or "",
            raw=final,
        )

    def stream_generate(self, *, system, prompt, max_tokens, model=None,
                        thinking: bool = False, on_done=None, **kwargs):
        """Streama a resposta token a token (yield de str). Chama on_done(LLMResult)
        ao final, com tokens/custo. `system` pode ser str ou blocos (p/ cache_control)."""
        model_id = model or self.default_model
        params: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        if thinking:
            params["thinking"] = {"type": "adaptive"}

        try:
            with self._client.messages.stream(**params) as stream:
                for text in stream.text_stream:
                    yield text
                final = stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise LLMProviderError("Credencial da Anthropic inválida ou ausente.") from exc
        except anthropic.APIStatusError as exc:
            raise LLMProviderError(f"Erro da API Anthropic ({exc.status_code}): {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMProviderError("Falha de conexão com a API Anthropic.") from exc

        if on_done:
            txt = "".join(b.text for b in final.content if b.type == "text")
            u = final.usage
            it, ot = getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0
            on_done(LLMResult(
                text=txt, provider=self.name, model=model_id,
                input_tokens=it, output_tokens=ot,
                cost_usd=_cost(model_id, it, ot),
                stop_reason=final.stop_reason or "", raw=final,
            ))
