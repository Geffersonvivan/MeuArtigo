"""Prompts do workspace (Fase 6): edição de UMA seção com contexto estável cacheado."""

from __future__ import annotations

EDITOR_SYSTEM = (
    "Você edita seções de artigos jurídicos. Reescreva SOMENTE a seção pedida, aplicando a "
    "instrução do autor e mantendo coerência com o restante do artigo e com o contexto/ideia. "
    "Regras: não invente citações, leis ou jurisprudência; preserve marcadores [[ref:ID]] "
    "existentes; escreva em português do Brasil, em Markdown. Devolva APENAS o Markdown da "
    "seção (com o mesmo nível de cabeçalho), sem comentários nem cercas de código."
)


REESCRITA_SYSTEM = (
    "Você é o Redator: reescreve UM parágrafo de um artigo jurídico, sob comando do autor. "
    "Aplique a instrução mantendo o sentido e a coerência com o artigo. Preserve os marcadores "
    "[[ref:ID]] existentes e NÃO invente citações. Devolva SOMENTE o parágrafo reescrito, em "
    "texto corrido, sem aspas, sem título e sem comentários."
)


def build_reescrita_prompt(*, contexto: str, secao_titulo: str, paragrafo: str,
                           instrucao: str) -> tuple[str, str]:
    ctx = (contexto or "").strip()
    user = (
        (f"CONTEXTO DO ARTIGO: {ctx}\n\n" if ctx else "")
        + f"SEÇÃO: {secao_titulo}\n\n"
        + f"PARÁGRAFO ATUAL:\n{paragrafo}\n\n"
        + f"INSTRUÇÃO: {instrucao}\n\n"
        + "Devolva apenas o parágrafo reescrito."
    )
    return REESCRITA_SYSTEM, user


def build_section_edit_prompt(*, contexto: str, artigo_md: str, memoria: list[dict] | None,
                              secao_texto: str, instrucao: str) -> tuple[list[dict], str]:
    """Devolve (system_blocks, user). O bloco estável (contexto + artigo + memória) leva
    cache_control para baratear iterações; a instrução volátil vai no user."""
    mem = ""
    if memoria:
        itens = "\n".join(f'- (de "{m["titulo"]}") {m["texto"]}' for m in memoria)
        mem = f"\n\nMEMÓRIA (outros artigos desta área — não repita):\n{itens}"

    estavel = (
        f"CONTEXTO/IDEIA DO AUTOR:\n{contexto or '(não informado)'}\n\n"
        f"ARTIGO ATUAL (referência; não reescreva o todo):\n{artigo_md}{mem}"
    )
    system = [
        {"type": "text", "text": EDITOR_SYSTEM},
        {"type": "text", "text": estavel, "cache_control": {"type": "ephemeral"}},
    ]
    user = (
        f"INSTRUÇÃO: {instrucao}\n\n"
        f"SEÇÃO ATUAL A REESCREVER:\n{secao_texto}\n\n"
        "Devolva apenas a seção reescrita em Markdown (com o mesmo cabeçalho)."
    )
    return system, user
