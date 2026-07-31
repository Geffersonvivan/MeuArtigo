"""Papéis do pipeline → provedor/modelo, e estimativa de custo por ação (para os hints
contextuais e o painel Pipeline do design). Custo real vem do LLMCall; aqui é a ESTIMATIVA
mostrada ANTES da ação (README §"Contrato de ações e custos").

Roteamento (decisão do usuário): Pesquisa/Fontes=Perplexity · Arquiteto=Opus ·
Redator=Sonnet · Revisor=Perplexity(fato-check)+Haiku(estilo) · Editor=Opus.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings

#: preço aproximado por 1M tokens de saída (USD) — âncora só para ESTIMAR o hint.
_PRECO_SAIDA_USD = {
    "claude-opus-5": Decimal("25"),
    "claude-sonnet-5": Decimal("15"),
    "claude-haiku-4-5": Decimal("5"),
    "sonar": Decimal("15"),
}


def _papeis() -> dict:
    return {
        "pesquisador": {"label": "Pesquisador", "provider": "perplexity",
                        "model": getattr(settings, "PERPLEXITY_MODEL", "sonar"),
                        "tier": "médio", "dot": "ok",
                        "desc": "Levanta e verifica fontes. Não escreve."},
        "arquiteto": {"label": "Arquiteto", "provider": "anthropic",
                      "model": settings.MODELO_ARQUITETO, "tier": "forte", "dot": "accent",
                      "desc": "Propõe a estrutura em seções a partir da pesquisa."},
        "redator": {"label": "Redator", "provider": "anthropic",
                    "model": settings.MODELO_REDATOR, "tier": "médio", "dot": "accent",
                    "desc": "Escreve e reescreve o texto. Só ele toca no documento."},
        "revisor": {"label": "Revisor", "provider": "anthropic",
                    "model": settings.MODELO_REVISOR, "tier": "barato", "dot": "faint",
                    "desc": "Sinaliza estilo/coerência (avisos de margem). Nunca altera o texto."},
        "editor": {"label": "Editor", "provider": "anthropic",
                   "model": settings.MODELO_EDITOR, "tier": "forte", "dot": "accent",
                   "desc": "Edição final e ABNT."},
    }


#: custo-base por ação em "tokens de saída equivalentes" (milhões), para estimar o hint.
_ACOES = {
    "reescrever": ("redator", Decimal("0.0006")),
    "redigir_secao": ("redator", Decimal("0.006")),
    "propor_estrutura": ("arquiteto", Decimal("0.004")),
    "buscar_fonte": ("pesquisador", Decimal("0.0004")),
    "verificar_fonte": ("pesquisador", Decimal("0.0002")),
    "passada_revisor": ("revisor", Decimal("0.02")),
    "aviso_estilo": ("revisor", Decimal("0.0003")),
}


def papel(nome: str) -> dict:
    return _papeis()[nome]


def modelo_do_papel(nome: str) -> tuple[str, str]:
    p = papel(nome)
    return p["provider"], p["model"]


def estimar_custo_usd(acao: str) -> Decimal:
    nome_papel, base_mtok = _ACOES[acao]
    preco = _PRECO_SAIDA_USD.get(papel(nome_papel)["model"], Decimal("10"))
    return (base_mtok * preco).quantize(Decimal("0.0001"))


def estimar_custo_brl(acao: str) -> Decimal:
    taxa = Decimal(str(getattr(settings, "USD_BRL", 5.4)))
    return (estimar_custo_usd(acao) * taxa).quantize(Decimal("0.01"))


def hint(acao: str) -> dict:
    """Dados do hint contextual: ● <Papel> · <modelo> · ~R$ 0,04."""
    nome_papel = _ACOES[acao][0]
    p = papel(nome_papel)
    return {"papel": p["label"], "dot": p["dot"], "modelo": p["model"],
            "custo_brl": estimar_custo_brl(acao)}
