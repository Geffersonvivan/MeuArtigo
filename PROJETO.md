# Meu Artigo — Plataforma de Escrita Assistida por LLMs

> Documento de projeto e arquitetura. Ponto de partida para o desenvolvimento.
> Última atualização: 2026-07-29

---

## 1. Visão geral

Aplicação web em **Python + Django** para escrever artigos com apoio de múltiplas LLMs,
onde cada artigo vive em sua própria pasta física, mas todos ficam **conectados por uma
camada de memória** que registra o que já foi dito, os conceitos tratados e as fontes usadas.

**Problema que resolve:** escrever vários artigos numa mesma área (ex.: Direito Eleitoral)
sem repetir conteúdo, mantendo consistência terminológica e reaproveitando pesquisa/fontes.

**Diferencial:** a memória é cidadã de primeira classe — não é um log, é o que orienta cada
nova redação.

---

## 2. Decisões já tomadas

| Tema | Decisão |
|---|---|
| **Backend** | Python + Django |
| **Banco** | PostgreSQL + extensão `pgvector` (dados relacionais + busca vetorial num só lugar) |
| **Armazenamento** | **Híbrido** — pastas físicas `.md` (versionáveis com Git) + metadados/embeddings no Postgres |
| **LLMs** | **Claude** (estrutura+redação+edição), **Perplexity** (pesquisa+fontes **e** revisão/fato-check). OpenAI/GPT descartado. |
| **Memória** | Começar por RAG (busca semântica); grafo de entidades como evolução |

---

## 3. Papéis das LLMs (pipeline de escrita)

Cada LLM entra onde é mais forte. O artigo passa por um **pipeline de papéis**:

```
[1] PESQUISA        Perplexity   → levanta leis, jurisprudência, fontes reais e atuais
        ↓
[V] VERIFICAÇÃO     sistema+Perplexity → confere se cada fonte existe e sustenta a alegação (seção 9)
        ↓
[2] ESTRUTURA       Claude       → propõe esqueleto/roteiro do artigo a partir dos parâmetros
        ↓
[3] REDAÇÃO         Claude       → escreve citando SÓ fontes verificadas via [[ref:ID]]
        ↓
[4] REVISÃO         Perplexity   → critica, fato-checa contra as fontes (web-grounded), aponta repetições
        ↓
[5] EDIÇÃO FINAL    Claude       → ajusta linhas/páginas/estilo + gera referências ABNT
```

Antes da etapa [3], o sistema **consulta a memória** e injeta no prompt:
"você já abordou X no artigo Y — não repita, referencie."

> A camada de abstração `LLMProvider` garante que trocar/adicionar modelo seja configuração,
> nunca reescrita de código de negócio.

---

## 4. Parâmetros de cada novo artigo

Ao criar um artigo, o sistema solicita os **pontos base**:

| Parâmetro | Exemplo | Observação |
|---|---|---|
| **Assunto** | Impulsionamento eleitoral | tema central |
| **Área** | Direito eleitoral | filtra a memória relevante |
| **Nº de páginas** | 1 | meta de extensão |
| **Nº de linhas** | 10 | meta fina de extensão |
| **Modo/Estilo** | técnico/popular | ver tabela abaixo |

### Estilos suportados (mapeiam para instruções de prompt)

- `aprofundado` — denso, com desenvolvimento e nuances
- `raso` — direto, superficial, panorâmico
- `intelectual` — sofisticado, referências, vocabulário elevado
- `popular` — linguagem acessível ao leigo
- `juridiquês` — terminologia técnica jurídica plena
- `técnico/popular` — técnico mas explicado de forma acessível (híbrido)

---

## 5. Camadas de memória

Três camadas distintas (não confundir):

### (a) Memória factual / semântica — RAG *(implementar primeiro)*
Cada seção/parágrafo vira um *embedding* no `pgvector`. Antes de redigir, busca trechos
semelhantes já escritos → evita repetição, sugere referências cruzadas.

### (b) Memória de entidades / grafo *(evolução)*
Conceitos do domínio (`impulsionamento pago`, `Lei 9.504/97`, `propaganda antecipada`)
viram nós conectados aos artigos que os citam. Conversa com a skill `/graphify`.

### (c) Memória de estilo / perfil *(configuração simples)*
Guarda decisões de tom, glossário jurídico preferido e exemplos de parágrafos aprovados.

---

## 6. Estrutura de armazenamento híbrido

**Banco** guarda metadados + embeddings. **Disco** guarda o texto versionável.

```
artigos/
└── direito-eleitoral/                        # = Área (slug)
    └── impulsionamento-eleitoral/            # = Assunto (slug)
        ├── artigo.md                         # texto final
        ├── params.json                       # parâmetros do artigo
        ├── referencias.md                    # fontes (via Perplexity)
        └── rascunhos/                        # versões intermediárias do pipeline
            ├── 01-estrutura.md
            ├── 02-redacao.md
            └── 03-revisao.md
```

---

## 7. Estrutura do projeto Django

Monolito modular — apps bem separados, simples de começar e fácil de evoluir.

```
meu_artigo/
├── manage.py
├── requirements.txt
├── .env                          # chaves de API (NUNCA no Git)
├── .gitignore
├── config/                       # projeto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── articles/                 # o artigo em si
│   │   ├── models.py             # Article, Section, Version
│   │   ├── services.py           # cria pasta física + registro no BD
│   │   ├── forms.py              # formulário dos parâmetros base
│   │   └── views.py
│   │
│   ├── llm/                      # orquestração das LLMs
│   │   ├── providers/
│   │   │   ├── base.py           # interface LLMProvider
│   │   │   ├── anthropic.py      # Claude
│   │   │   ├── openai.py         # GPT
│   │   │   └── perplexity.py     # pesquisa + fontes
│   │   ├── pipeline.py           # pesquisa→estrutura→redação→revisão→edição
│   │   └── prompts.py            # templates de prompt por estilo/papel
│   │
│   ├── memory/                   # a memória / conhecimento
│   │   ├── models.py             # MemoryChunk, Entity, Reference
│   │   ├── embeddings.py         # geração de embeddings
│   │   ├── retrieval.py          # busca semântica (RAG)
│   │   └── graph.py              # (evolução) grafo de entidades
│   │
│   └── workspace/                # UI de escrita
│       ├── views.py
│       └── templates/
│
└── artigos/                      # PASTAS FÍSICAS (ver seção 6)
```

---

## 8. Modelo de dados inicial (esqueleto)

```python
# apps/articles/models.py
class Article(models.Model):
    titulo      = models.CharField(max_length=300)
    assunto     = models.CharField(max_length=300)          # "Impulsionamento eleitoral"
    area        = models.CharField(max_length=200)          # "Direito eleitoral"
    num_paginas = models.PositiveIntegerField()             # 1
    num_linhas  = models.PositiveIntegerField()             # 10
    estilo      = models.CharField(max_length=50, choices=ESTILOS)
    pasta       = models.CharField(max_length=500)          # caminho físico
    status      = models.CharField(max_length=30)           # rascunho/revisão/final
    criado_em   = models.DateTimeField(auto_now_add=True)

# apps/memory/models.py
class MemoryChunk(models.Model):
    article   = models.ForeignKey("articles.Article", on_delete=models.CASCADE)
    texto     = models.TextField()
    embedding = VectorField(dimensions=1024)                # pgvector (Voyage voyage-3.5)
    area      = models.CharField(max_length=200)            # filtra memória por área
    criado_em = models.DateTimeField(auto_now_add=True)

class Reference(models.Model):                              # fontes (via Perplexity)
    article     = models.ForeignKey("articles.Article", on_delete=models.CASCADE)
    tipo        = models.CharField(max_length=30, choices=TIPOS_FONTE)  # lei/jurisprudência/doutrina/notícia/site
    titulo      = models.CharField(max_length=400)
    autor       = models.CharField(max_length=300, blank=True)
    url         = models.URLField(blank=True)
    trecho      = models.TextField(blank=True)                # citação direta usada
    data_pub    = models.DateField(null=True, blank=True)     # data da publicação/fonte
    data_acesso = models.DateField(null=True, blank=True)     # exigido pela ABNT p/ fontes online
    abnt        = models.TextField(blank=True)                # referência formatada em ABNT
    verificada  = models.CharField(max_length=20, choices=STATUS_VERIF)  # ok/duvidosa/inexistente
    verificada_em = models.DateTimeField(null=True, blank=True)
```

---

## 9. Fontes e citações (ABNT)

Em Direito Eleitoral, **fonte errada ou inventada é inaceitável**. Esta camada garante que
toda afirmação factual (lei, jurisprudência, doutrina, dado) tenha fonte rastreável,
verificada e formatada em ABNT.

### 9.1 Fluxo de citação (integrado ao pipeline)

```
[1] Perplexity levanta fontes          → cria registros Reference (com URL + trecho)
        ↓
[VERIFICAÇÃO] cada fonte é conferida    → status: ok / duvidosa / inexistente
        ↓
[3] Claude redige citando marcadores    → usa [[ref:ID]] no texto, nunca "inventa" citação
        ↓
[FORMATAÇÃO ABNT] gera referências      → nota de rodapé/autor-data + lista final
        ↓
referencias.md + seção "Referências" no artigo.md
```

> **Regra de ouro:** a LLM de redação (Claude) só pode citar fontes que **já existem** como
> `Reference` verificada. Ela referencia por marcador `[[ref:ID]]`; o sistema resolve o
> marcador para a citação ABNT. Isso elimina a "alucinação" de citações.

### 9.2 Verificação de fontes (anti-alucinação)

Três níveis, do mais barato ao mais rigoroso:

1. **Existência da URL** — checar HTTP 200 e que o domínio bate (site oficial: `planalto.gov.br`,
   `tse.jus.br`, `stf.jus.br`, etc.).
2. **Conferência de conteúdo** — buscar o `trecho` citado dentro da página (via fetch) para
   confirmar que a fonte *realmente diz aquilo*.
3. **Cross-check por 2ª LLM** — GPT recebe fonte + afirmação e responde se a fonte sustenta a
   alegação (`ok` / `duvidosa` / `inexistente`). Divergência → marcar para revisão humana.

Fontes `duvidosa`/`inexistente` **não entram** no texto final — ficam sinalizadas para você decidir.

### 9.3 Formatação ABNT

Referências formatadas conforme **NBR 6023** (referências) e **NBR 10520** (citações).
Modelos por tipo de fonte:

| Tipo | Modelo ABNT (NBR 6023) |
|---|---|
| **Lei / norma** | BRASIL. *Lei nº 9.504, de 30 de setembro de 1997*. Estabelece normas para as eleições. Brasília, DF: Presidência da República, 1997. Disponível em: `<url>`. Acesso em: DD mmm. AAAA. |
| **Jurisprudência** | BRASIL. Tribunal Superior Eleitoral. *Recurso Especial Eleitoral nº XXXX*. Relator: Min. Fulano. Brasília, DF, DD mmm. AAAA. Disponível em: `<url>`. Acesso em: DD mmm. AAAA. |
| **Doutrina (livro)** | SOBRENOME, Nome. *Título da obra*. ed. Cidade: Editora, ano. |
| **Artigo/site** | SOBRENOME, Nome. Título do texto. *Nome do site*, ano. Disponível em: `<url>`. Acesso em: DD mmm. AAAA. |

**Estilo de citação no corpo** (configurável por artigo):
- **Autor-data** (NBR 10520): `(BRASIL, 1997)` — recomendado para estilo acadêmico.
- **Nota de rodapé**: numeração sequencial com a referência ao pé da página.

### 9.4 Onde fica no armazenamento

- `referencias.md` — lista completa em ABNT, por artigo.
- Seção **"Referências"** ao final do `artigo.md`, gerada a partir dos `Reference` verificados.
- Banco (`Reference`) — fonte da verdade; o `.md` é renderizado a partir dela.

### 9.5 Componentes de código envolvidos

```
apps/memory/
├── models.py          # Reference (com campos ABNT + verificação)
├── citations.py       # formata Reference → string ABNT (por tipo de fonte)
└── verify.py          # verificação de fontes (URL, conteúdo, cross-check LLM)

apps/llm/
├── providers/perplexity.py   # retorna fontes estruturadas, não texto solto
└── prompts.py                # instrui Claude a citar SÓ via [[ref:ID]]
```

---

## 10. Roadmap sugerido

| Fase | Entrega | Objetivo |
|---|---|---|
| **0** | Esqueleto Django + Postgres/pgvector + `.env` | base rodando |
| **1** | Fluxo de criação de artigo (form → pasta + registro) | criar artigos com parâmetros |
| **2** | Camada `LLMProvider` + 1 provedor (Claude) | primeira redação funcionando |
| **3** | Motor de memória RAG (embeddings + busca) | "o que já foi dito" |
| **4** | Pipeline completo (Perplexity + GPT + Claude) | qualidade multi-LLM |
| **5** | Fontes + citação ABNT + verificação (seção 9) | rastreabilidade e anti-alucinação |
| **6** | UI de workspace (editor + histórico) | experiência de escrita |
| **7** | Grafo de entidades / `/graphify` | evolução da memória |

---

## 11. Stack técnica

| Camada | Escolha |
|---|---|
| Backend | Django 5.x |
| Banco | PostgreSQL 16 + `pgvector` |
| LLMs | `anthropic` (Claude), Perplexity API (pesquisa+revisão). OpenAI descartado. |
| Embeddings | Voyage AI `voyage-3.5` (1024 dims) — Claude/Perplexity não fazem embeddings |
| Async (opcional) | Celery + Redis (para pipeline longo) |
| Frontend | Django Templates + HTMX (simples) — evoluir depois se preciso |

---

## 12. Riscos e cuidados

- **Chaves de API** — sempre em `.env`, nunca no Git (`.gitignore` desde o commit 1).
- **Custo** — Perplexity/Claude por artigo somam; logar tokens/custo por etapa.
- **Sincronização disco ↔ banco** — uma única `service` responsável por escrever nos dois.
- **Consistência da memória** — reindexar embeddings quando o `artigo.md` mudar.
- **Direito Eleitoral muda rápido** — Perplexity ajuda a manter fontes atuais; datar tudo.
- **Alucinação de citações** — LLM jamais cita fonte não verificada; só via marcador `[[ref:ID]]`
  resolvido pelo sistema. Toda citação passa pela verificação da seção 9 antes do texto final.
- **ABNT correta** — validar formato por tipo de fonte (NBR 6023/10520) e sempre registrar
  `data de acesso` para fontes online.
