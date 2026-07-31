# CLAUDE.md — Meu Artigo

> Memória de projeto para o Claude Code. Carregado em toda sessão neste diretório.
> Detalhes completos de arquitetura em [`PROJETO.md`](./PROJETO.md).

## O que é este projeto
Aplicação web **Python + Django** para escrever artigos com apoio de **múltiplas LLMs**.
Cada artigo vive em sua **pasta física** (`.md` versionável), mas todos ficam conectados
por uma **camada de memória** (RAG) que registra o que já foi dito, os conceitos tratados
e as fontes usadas. Caso de uso inicial: artigos de **Direito Eleitoral**.

## Decisões fixas (não reabrir sem pedido explícito)
- **Backend:** Django 5.x · **Banco:** PostgreSQL 16 + `pgvector`
- **Armazenamento:** híbrido — pastas físicas `.md` (Git) + metadados/embeddings no Postgres
- **LLMs e papéis** (OpenAI/GPT foi descartado — ver memória do projeto):
  - **Perplexity** → pesquisa + fontes reais/atuais **e** revisão/fato-check (2ª família, web-grounded)
  - **Claude** → estrutura, redação e edição final (estilo/juridiquês)
- **Embeddings:** Voyage AI `voyage-3.5` (1024 dims) — parceiro recomendado pela Anthropic.
  (Claude e Perplexity não geram embeddings.) OpenAI/GPT segue só para brainstorm/revisão.
- **Memória:** começar por RAG; grafo de entidades é evolução (integra com `/graphify`)

## Pipeline de escrita (papéis)
```
Perplexity(pesquisa) → [Verificação] → Claude(estrutura) → Claude(redação)
    → Perplexity(revisão/fato-check) → Claude(edição final + ABNT)
```
Antes da redação, o sistema consulta a **memória RAG** e injeta "o que já foi dito naquela área".

## Parâmetros de cada artigo
`assunto` · `área` · `nº de páginas` · `nº de linhas` · `estilo`
Estilos: `aprofundado` · `raso` · `intelectual` · `popular` · `juridiquês` · `técnico/popular`

## Regras de ouro (invioláveis)
1. **Nunca inventar citação.** A LLM de redação só cita fontes que já existem como
   `Reference` **verificada**, via marcador `[[ref:ID]]`; o sistema resolve para ABNT.
2. **Toda fonte passa por verificação** antes do texto final: existência da URL
   (domínios oficiais `planalto.gov.br`, `tse.jus.br`, `stf.jus.br`) → conferência do trecho
   na página → cross-check por 2ª LLM. Fontes `duvidosa`/`inexistente` não entram no texto.
3. **Citação em ABNT** (NBR 6023 referências, NBR 10520 citações); registrar sempre
   `data de acesso` para fontes online.
4. **Chaves de API** só em `.env`, nunca no Git.
5. **Sincronização disco ↔ banco** feita por uma única `service`; banco é a fonte da verdade,
   o `.md` é renderizado a partir dele. Reindexar embeddings quando o `artigo.md` mudar.

## Estrutura do projeto
```
config/                  # projeto Django
apps/
  articles/   # Article, Section, Version · services (cria pasta+registro) · forms · views
  llm/        # providers/{base,anthropic,openai,perplexity} · pipeline.py · prompts.py
  memory/     # MemoryChunk, Reference · embeddings.py · retrieval.py · citations.py · verify.py · graph.py
  workspace/  # UI de escrita (views + templates)
artigos/                 # pastas físicas: <area-slug>/<assunto-slug>/{artigo.md, params.json, referencias.md, rascunhos/}
```

## Roadmap (fases 0–7 concluídas)
0. Esqueleto Django + Postgres/pgvector + `.env`
1. Fluxo de criação de artigo (form → pasta + registro)
2. `LLMProvider` + Claude (primeira redação)
3. Motor de memória RAG (embeddings + busca)
4. Pipeline completo multi-LLM
5. Fontes + citação ABNT + verificação
6. UI de workspace
7. Grafo de entidades / `/graphify`

## Convenções
- Nunca chamar API de provedor direto no código de negócio — sempre via interface `LLMProvider`.
- Slugs de área/assunto definem o caminho da pasta física.
- Logar tokens/custo por etapa do pipeline (Perplexity/Claude somam custo).
- Datar tudo — Direito Eleitoral muda rápido.
