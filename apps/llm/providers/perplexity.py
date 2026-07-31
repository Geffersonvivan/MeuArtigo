"""Provedor Perplexity — pesquisa (fontes reais/atuais) e revisão/fato-check.

API compatível com OpenAI (POST /chat/completions). Além do texto, devolve `citations`
e `search_results` (fontes reais com URL), que alimentam as referências na Fase 5.
O próprio `usage.cost.total_cost` traz o custo em USD.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings

from .base import LLMProvider, LLMProviderError, LLMResult

API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = "sonar"


class PerplexityProvider(LLMProvider):
    name = "perplexity"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = (api_key or getattr(settings, "PERPLEXITY_API_KEY", "") or "").strip()
        self.default_model = model or getattr(settings, "PERPLEXITY_MODEL", DEFAULT_MODEL)

    def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int,
        model: str | None = None,
        search_recency: str | None = None,
        **kwargs: Any,
    ) -> LLMResult:
        if not self.api_key:
            raise LLMProviderError("PERPLEXITY_API_KEY ausente. Configure no .env.")

        model_id = model or self.default_model
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": ([{"role": "system", "content": system}] if system else []) + messages,
            "max_tokens": max_tokens,
        }
        if search_recency:
            payload["search_recency_filter"] = search_recency  # hour/day/week/month/year

        try:
            resp = httpx.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Falha de conexão com a Perplexity: {exc}") from exc

        if resp.status_code != 200:
            raise LLMProviderError(f"Erro da API Perplexity ({resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content", "") or ""
        usage = data.get("usage") or {}
        cost = Decimal(str((usage.get("cost") or {}).get("total_cost", 0)))

        return LLMResult(
            text=text,
            provider=self.name,
            model=data.get("model", model_id),
            input_tokens=usage.get("prompt_tokens", 0) or 0,
            output_tokens=usage.get("completion_tokens", 0) or 0,
            cost_usd=cost,
            stop_reason=choice.get("finish_reason", "") or "",
            sources=data.get("search_results") or [],
            citations=data.get("citations") or [],
            raw=data,
        )
