"""Templates de prompt por papel/estilo (PROJETO.md §3 e §4).

Nesta fase cobrimos o papel de REDAÇÃO (Claude). A regra de ouro (§9) já entra aqui:
a LLM não inventa citações — só cita fontes verificadas via marcador [[ref:ID]].
Como ainda não há fontes verificadas (Fase 5), instruímos a NÃO fabricar citações.
"""

from __future__ import annotations

#: Instrução de tom por estilo (chave = valor de Estilo.value).
ESTILO_INSTRUCTIONS: dict[str, str] = {
    "aprofundado": "Denso e analítico: desenvolva nuances, contrapontos e implicações.",
    "raso": "Direto e panorâmico: visão geral objetiva, sem aprofundar.",
    "intelectual": "Sofisticado: vocabulário elevado, articulação conceitual refinada.",
    "popular": "Acessível ao leigo: linguagem simples, exemplos do cotidiano.",
    "juridiques": "Terminologia jurídica plena e técnica, próprio de peças e doutrina.",
    "tecnico_popular": "Técnico, mas explicado de forma acessível ao leitor não especialista.",
}

REDACAO_SYSTEM = """\
Você é um redator jurídico especializado, responsável pela REDAÇÃO de artigos.

Regras invioláveis:
1. NUNCA invente citações, leis, números de processo, jurisprudência ou doutrina.
2. Só é permitido citar fontes pelo marcador [[ref:ID]], usando SOMENTE os IDs da lista
   "FONTES VERIFICADAS DISPONÍVEIS" quando fornecida. Se nenhuma lista for fornecida, NÃO
   cite fontes específicas: escreva de forma geral e, se preciso, marque "[carece de fonte]".
3. Respeite o estilo e a extensão pedidos.
4. Escreva em português do Brasil, em Markdown, com títulos e parágrafos.
5. Não escreva a seção "Referências" — o sistema a gera a partir dos marcadores [[ref:ID]].
"""


def _refs_block(referencias: list[dict] | None) -> str:
    if not referencias:
        return ""
    linhas = "\n".join(f'- [[ref:{r["id"]}]] {r["titulo"]}' for r in referencias)
    return (
        "\n\nFONTES VERIFICADAS DISPONÍVEIS — cite SOMENTE estas, pelo marcador [[ref:ID]] "
        "correspondente, onde a afirmação exigir fonte. NÃO invente nem cite outras:\n"
        f"{linhas}\n"
    )


def _mem_block(memoria: list[dict] | None) -> str:
    if not memoria:
        return ""
    itens = "\n".join(f'- (do artigo "{m["titulo"]}") {m["texto"]}' for m in memoria)
    return (
        "\n\nMEMÓRIA — trechos que você já escreveu em OUTROS artigos desta área.\n"
        "NÃO repita o que já foi dito; quando fizer sentido, referencie que o tema já\n"
        "foi tratado, em vez de reescrever:\n"
        f"{itens}\n"
    )


def _ctx_block(titulo: str, conteudo: str | None) -> str:
    if not conteudo:
        return ""
    return f"\n\n{titulo}:\n{conteudo.strip()}\n"


def build_redacao_prompt(*, titulo: str, assunto: str, area: str,
                         num_paginas: int, num_linhas: int, estilo: str,
                         memoria: list[dict] | None = None,
                         estrutura: str | None = None,
                         pesquisa: str | None = None,
                         referencias: list[dict] | None = None) -> tuple[str, str]:
    """Monta (system, user) para a redação de um artigo.

    `memoria`: trechos já escritos (RAG). `estrutura`/`pesquisa`: contexto das etapas
    anteriores. `referencias`: fontes VERIFICADAS [{id, titulo}] citáveis via [[ref:ID]].
    Todos opcionais (PROJETO.md §3/§9).
    """
    estilo_desc = ESTILO_INSTRUCTIONS.get(estilo, estilo)
    user = f"""\
Escreva a primeira versão de um artigo com os parâmetros abaixo.

- Título: {titulo}
- Assunto: {assunto}
- Área: {area}
- Estilo: {estilo_desc}
- Extensão-alvo: aproximadamente {num_paginas} página(s) / {num_linhas} linha(s).\
{_ctx_block("ROTEIRO A SEGUIR", estrutura)}\
{_ctx_block("PESQUISA DE APOIO (contexto; não copie)", pesquisa)}\
{_refs_block(referencias)}\
{_mem_block(memoria)}

Produza o texto em Markdown, começando por um título de nível 1 (#) e organizado
em seções. Cite via [[ref:ID]] apenas onde houver fonte na lista. Não escreva a seção
"Referências" — o sistema a gera.
"""
    return REDACAO_SYSTEM, user


# --- Papéis adicionais do pipeline (Fase 4) ---

PESQUISA_SYSTEM = """\
Você é pesquisador jurídico especializado em Direito brasileiro. Levante o estado atual
do tema: legislação vigente (com nº e ano), jurisprudência relevante e pontos controversos.
Priorize fontes oficiais (planalto.gov.br, tse.jus.br, stf.jus.br). Seja objetivo e estruturado;
não redija o artigo, apenas reúna o material e as fontes.
"""

ESTRUTURA_SYSTEM = """\
Você estrutura artigos jurídicos. A partir dos parâmetros e da pesquisa, proponha um
ROTEIRO (seções e sub-tópicos, em Markdown com títulos), coerente com a extensão-alvo.
Não escreva o conteúdo — apenas o esqueleto comentado do que cada seção deve cobrir.
"""

REVISAO_SYSTEM = """\
Você revisa artigos jurídicos com apoio de busca web atual. Fato-cheque as afirmações
contra fontes reais e atuais; aponte imprecisões, afirmações sem base, erros de norma
(lei/artigo/ano) e repetições. Responda com uma lista objetiva de correções e observações,
citando as fontes. Não reescreva o artigo inteiro.
"""

EDICAO_SYSTEM = """\
Você faz a EDIÇÃO FINAL de artigos jurídicos. Aplique as correções da revisão, ajuste ao
estilo e à extensão-alvo, melhore a fluidez e a coesão. Regras invioláveis: NÃO invente
citações; PRESERVE os marcadores [[ref:ID]] já presentes e só use IDs da lista de fontes
verificadas; se a revisão apontou algo sem fonte, generalize ou marque "[carece de fonte]".
Não escreva a seção "Referências" (o sistema gera). Devolva o Markdown final completo (com título #).
"""


ENTIDADES_SYSTEM = """\
Você extrai entidades do domínio jurídico de um texto. Identifique leis/normas (com nº e ano),
jurisprudência, conceitos jurídicos, órgãos/instituições e pessoas relevantes.
Responda SOMENTE com JSON válido, sem comentários nem cercas de código, no formato:
{"entidades": [{"nome": "...", "tipo": "lei|jurisprudencia|conceito|orgao|pessoa|outro", "descricao": "curta"}]}
Não invente entidades que não estejam no texto. Normalize nomes (ex.: "Lei nº 9.504/1997").
"""


def build_entidades_prompt(*, texto: str) -> tuple[str, str]:
    return ENTIDADES_SYSTEM, f"Extraia as entidades do texto abaixo.\n\n--- TEXTO ---\n{texto}"


def build_pesquisa_prompt(*, assunto: str, area: str) -> tuple[str, str]:
    user = (
        f"Tema: {assunto}\nÁrea: {area}\n\n"
        "Levante os principais pontos, normas vigentes, jurisprudência e controvérsias atuais "
        "sobre esse tema, com as fontes, para embasar um artigo."
    )
    return PESQUISA_SYSTEM, user


def build_estrutura_prompt(*, titulo: str, assunto: str, area: str, num_paginas: int,
                           num_linhas: int, estilo: str, pesquisa: str | None = None,
                           memoria: list[dict] | None = None) -> tuple[str, str]:
    estilo_desc = ESTILO_INSTRUCTIONS.get(estilo, estilo)
    user = f"""\
Proponha o roteiro de um artigo:

- Título: {titulo}
- Assunto: {assunto}
- Área: {area}
- Estilo: {estilo_desc}
- Extensão-alvo: ~{num_paginas} página(s) / {num_linhas} linha(s).\
{_ctx_block("PESQUISA DE APOIO", pesquisa)}\
{_mem_block(memoria)}

Devolva só o roteiro (seções e o que cada uma deve cobrir), em Markdown.
"""
    return ESTRUTURA_SYSTEM, user


def build_revisao_prompt(*, texto: str) -> tuple[str, str]:
    user = (
        "Revise e fato-cheque o artigo abaixo. Aponte erros factuais, normas incorretas, "
        "afirmações sem base e repetições, com as fontes. Não reescreva o artigo.\n\n"
        f"--- ARTIGO ---\n{texto}"
    )
    return REVISAO_SYSTEM, user


def build_edicao_prompt(*, titulo: str, estilo: str, num_paginas: int, num_linhas: int,
                        redacao: str, revisao: str,
                        referencias: list[dict] | None = None) -> tuple[str, str]:
    estilo_desc = ESTILO_INSTRUCTIONS.get(estilo, estilo)
    user = f"""\
Produza a versão FINAL do artigo "{titulo}", aplicando as observações da revisão.

- Estilo: {estilo_desc}
- Extensão-alvo: ~{num_paginas} página(s) / {num_linhas} linha(s).\
{_refs_block(referencias)}

--- REDAÇÃO ATUAL (preserve os marcadores [[ref:ID]]) ---
{redacao}

--- OBSERVAÇÕES DA REVISÃO ---
{revisao}

Devolva o Markdown final completo (começando por # título), sem seção de "Referências".
"""
    return EDICAO_SYSTEM, user
