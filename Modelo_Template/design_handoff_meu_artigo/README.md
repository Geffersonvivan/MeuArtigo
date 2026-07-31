# Handoff: Meu Artigo — Ambiente de escrita assistida por IA

## Overview

**Meu Artigo** é uma plataforma de escrita de artigos para autores especialistas (protótipo em Direito Eleitoral). A IA não é a autora — é bancada de trabalho: pesquisa, propõe estrutura, redige rascunho e reescreve trechos **sob comando**. O texto pertence ao usuário: nada muda no documento sem aprovação explícita dele.

Diferencial: **edição cirúrgica** parágrafo a parágrafo, sem regenerar o artigo, com controle explícito de custo de LLM.

Este handoff cobre:
- Workspace principal (editor 3 colunas + régua de linhas + avisos de margem + balão de reescrita)
- Wizard de criação de artigo (2 passos)
- Gate de aprovação da estrutura
- Painel de fontes
- Comparação de versões (diff)
- Modal de fechamento (checklist + status: rascunho → em revisão → final)
- Tela de ajustes de modelos (3 papéis: Redator, Pesquisador, Revisor)
- Exportação (PDF, DOCX, Markdown)

## About the Design Files

Os arquivos deste bundle são **referências de design criadas em HTML/CSS/JS puro** — protótipos que mostram aparência e comportamento pretendidos, **não código de produção para colar**. A tarefa é **recriar esses designs no ambiente existente do codebase-alvo** (React/Vue/Svelte/etc.), respeitando os padrões e bibliotecas já estabelecidos. Se ainda não houver ambiente, escolher o framework mais adequado (recomendação: **React + TypeScript + Tailwind ou CSS Modules** — a UI é densa, com muita interação de estado local).

Toda a lógica de detecção que não usa LLM (contagem de linhas, similaridade, glossário, "sem fonte") deve ser **implementada no cliente ou em serviço rápido no backend** — não é uma chamada de LLM disfarçada. Isso é premissa do produto: essas verificações são grátis e instantâneas.

## Fidelity

**Alta-fidelidade (hifi).** Cores, tipografia, espaçamento, comportamento e microinterações estão todos definidos. Reproduzir pixel-a-pixel usando as bibliotecas do codebase.

Exceções que ainda são placeholder:
- Ícones inline SVG desenhados à mão dentro do HTML — substituir por biblioteca de ícones (Lucide, Phosphor, Heroicons) mantendo peso 1.5px e traço arredondado
- IDs de jurisprudência fictícios (`REspe nº 0600xxx-xx…`) — dados de mock, não literal

---

## Design System

### Colors

```
/* Superfícies */
--bg:            #fafaf9   /* fundo geral, off-white quente */
--surface:       #ffffff   /* superfícies elevadas */
--surface-2:     #f5f5f4   /* hover de linha, fundo sutil */
--surface-3:     #ebeae7

/* Bordas */
--border:        #e7e5e4   /* 1px, todas as divisórias */
--border-strong: #d6d3d1

/* Texto */
--text:          #1c1917   /* quase preto, corpo */
--text-muted:    #57534e
--text-faint:    #a8a29e

/* Acento — navy petróleo, sóbrio */
--accent:        #1e3a5f
--accent-hover:  #274b78
--accent-soft:   #eaf0f6   /* fundo de seleção */
--accent-line:   #c9d6e4

/* Semânticas */
--ok:            #15803d
--ok-soft:       #dcfce7
--warn:          #b45309
--warn-soft:     #fef3c7
--warn-line:     #fcd34d
--err:           #b91c1c
--err-soft:      #fee2e2
--err-line:      #fca5a5
```

Regra: **cor de acento única (navy)** para toda a UI ativa. Cores semânticas apenas para: verde (verificado), âmbar (atenção), vermelho (problema). Sem gradiente, sem sombra pesada.

### Typography

Duas famílias essenciais:
- **UI (sans):** `'IBM Plex Sans', system-ui, -apple-system, sans-serif` — 13–14px para chrome
- **Corpo do artigo (serif):** `'IBM Plex Serif', Georgia, serif` — **17px, line-height 1.75, max-width 640px**
- **Mono (custos, códigos):** `'IBM Plex Mono', ui-monospace, Menlo, monospace` — 11–12px

Regra dura: **corpo do artigo é serifado**. Interface é sans. Nada de trocar por Inter / Roboto — a assinatura do produto está no par Plex.

Escala aproximada:
- Corpo do artigo: 17 / 1.75 (essencial)
- Títulos de seção do artigo: 18 (serif, weight 500, letter-spacing -0.005em)
- UI padrão: 13 / 1.5
- Small (metadados): 11–12 / 1.4
- Labels uppercase: 10–11 / letter-spacing 0.06–0.08em
- Monospace (custo, versão, contadores): 11–12

### Spacing / Density

Densidade **média** (referência Linear/Notion). Padding padrão de container: 12–20px. Linhas de lista: 40–48px. Radius máximo **4px** (mais sóbrio que os 8–12px de SaaS). **Sem sombras**, exceto na tweaks panel e nos modais (sombra sutil apenas para elevação necessária).

### Iconography

- **Ícones de linha, stroke 1.5px, cor herdada** (`stroke: currentColor`)
- 14×14 padrão, 16×16 grande, 11–12 para inline em texto pequeno
- **Sem emoji**
- Substituir os SVGs inline do protótipo por Lucide ou Phosphor com mesmo peso

### Layout global (Workspace)

- **Grid 3 colunas fixas:** sidebar 240px · editor flexível · contexto 300px
- **Topbar:** 44px de altura, borda inferior 1px
- **Largura mínima:** 1280px (desktop-first — não responsivo por design)
- Aplicativo ocupa **100vh** com scroll interno em cada coluna independente

---

## Screens / Views

### 1. Workspace (tela principal)

**Purpose:** Ambiente de escrita e edição do artigo aberto. Coração do produto.

**Layout:**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ TOPBAR 44px                                                                  │
│ [Meu Artigo] | Nome do artigo · Área · [Status vN] | R$ | [Fechar] [Export] │
├──────────┬────────────────────────────────────────────────────┬──────────────┤
│ SIDEBAR  │ EDITOR (scroll independente)                       │ CONTEXTO     │
│ 240px    │ [Banner "Artigo final" quando status=final]        │ 300px        │
│          │ ┌──ruler──┬──corpo (max 560px)──┬──avisos 200px──┐│              │
│ [+ Novo] │ │ 24px    │ Serif 17/1.75       │ Etiquetas       ││ Tabs:        │
│ [Buscar] │ │ marca   │ 6 seções            │ posicionadas    ││ • Pipeline   │
│          │ │ progres │ Parágrafos como     │ absolutamente   ││ • Fontes     │
│ Árvore   │ │ so por  │  blocos             │ alinhadas ao    ││ • Memória    │
│ Área →   │ │ seção   │ Balão de reescrita  │ parágrafo       ││              │
│ Artigos  │ │         │ Diff atual×sugerida │                 ││              │
│          │ └─────────┴─────────────────────┴─────────────────┘│              │
│          │                                                    │              │
│ Rodapé:  │                                                    │              │
│ Fontes   │                                                    │              │
│ pend (3) │                                                    │              │
└──────────┴────────────────────────────────────────────────────┴──────────────┘
[Telas do protótipo ▾]  ← canto inferior esquerdo (menu de navegação)
```

#### 1a. Topbar

- Wordmark "Meu Artigo" (IBM Plex Serif 14, weight 500) com pequeno glifo `¶` em accent à esquerda
- Nome do artigo (Plex Sans 13, weight 500) + separador `·` + área em text-muted
- **Status pill:** borda 1px, radius 3px, uppercase 11px letter-spacing 0.06em, com bolinha 6px colorida:
  - `draft` → cinza `#a8a29e` + label "Rascunho"
  - `review` → âmbar var(--warn) + label "Em revisão"
  - `final` → verde var(--ok) + label "Final"
  - Sufixo de versão mono: ` v2` em text-faint 10px
- Custo da sessão: mono 12px, label "SESSÃO" em text-faint 10px uppercase, valor `R$ 3,42` em text-muted
- Botões `.icon-btn` (28px altura, radius 3px, gap 6px com ícone + texto):
  - **Fechar artigo** (some quando status=final)
  - **Exportar**
  - **Histórico** (icon-only)

#### 1b. Sidebar (240px)

- Header (padding 12px):
  - `Novo artigo` — botão largura total, altura 30px, borda `--border-strong`, ícone `+`
  - Campo de busca com ícone de lupa 14px absoluto à esquerda; placeholder "Buscar tema, termo ou fonte…"; borda `--border`, foco muda para `--accent-line` e background `--surface`
- Resultados de busca (aparecem no input): lista com título · trecho serifado com `<mark>` (background `--warn-soft`) · label da seção uppercase 11px `--text-faint`
- Árvore em 2 níveis:
  - Label uppercase 10px `--text-faint`: `DIREITO ELEITORAL`
  - Item de artigo: border-left 2px transparente (fica `--accent` quando ativo, com background `--accent-soft`); título 12.5px weight 500; meta `12 pág · rascunho · há 2 dias` em `--text-faint` 11px com bolinha de status
- Rodapé fixo (border-top): link "Fontes pendentes" com badge âmbar (bg `--warn-soft`, texto `--warn`, mono 10.5px weight 600, min-width 18px)

#### 1c. Editor (flexível)

- **Régua vertical à ESQUERDA (24px de largura, sticky top: 32px):**
  - Cada seção é um bloco proporcional à altura da seção real no doc
  - Border-right `--border`
  - Números mono 8.5–9.5px em `--text-faint` (label da seção + contador atual/meta)
  - Barra de preenchimento à direita da régua: 2px de largura, altura proporcional a `linhas_usadas / meta`; `--accent` normal, `--warn` quando excede a meta

- **Corpo do artigo (max-width 560px, gap 24px da régua):**
  - IBM Plex Serif 17 / 1.75
  - Padding externo: 32px 32px 120px 40px
  - **Section head:** border-bottom 1px, padding-bottom 8px, mb 16px
    - `s-num` mono 11px `--text-faint` (ex: `02`)
    - `s-title` Plex Serif 18 weight 500 letter-spacing -0.005em
    - `s-count` mono 11px à direita: `<span class="used">22</span> / 40 linhas`; `.used` vira `--ok` (dentro) ou `--warn` (fora)
  - **Parágrafo (`.paragraph`):**
    - Padding 4px 8px, margin lateral negativo -8px, radius 2px
    - Hover: background `--surface` (leve destaque)
    - Selected (durante edição): background `--accent-soft`
    - **Locked:** background `--surface-2`, cor `--text-muted`, ícone cadeado 14px em `--text-faint` posicionado left: -20px, top: 8px
    - **Ações no hover (`.p-actions`):** stack vertical de 3 botões 26×26 à direita do parágrafo (right: -44px), aparecem via `opacity: 0 → 1` em .12s. Ícones: comentar, reescrever (lápis), travar (cadeado). Hover no botão: bg `--surface-2`, cor `--accent`
  - **Marcações inline dentro do texto:**
    - `.cite` — cor `--accent`, border-bottom 1px dotted `--accent-line`; hover → background `--accent-soft`, border sólida. Clicável, muda aba do painel direito para "Fontes"
    - `.no-source` — sublinhado ondulado âmbar via `linear-gradient` (background-image), padding-bottom 2px
    - `.similar` — background `--warn-soft`, padding 1px 2px, radius 2px

- **Balão de reescrita (`.rewrite`, ancorado abaixo do parágrafo):**
  - Aparece após clicar no ícone "reescrever"
  - Padding 14 · border 1px `--border-strong` · radius 4px · background `--surface`
  - Setinha de 10×10 rotate 45° na parte superior esquerda (::before), fingindo tail do balão
  - Header: label uppercase 11px "REESCREVER ESTE PARÁGRAFO" + botão fechar `×`
  - Textarea: min-height 36px, placeholder itálico "Instrução opcional…"
  - Chips: `encurtar · expandir · simplificar · endurecer tom · pedir fonte`
    - border 1px, radius 999px, padding 4px 10px, hover → borda `--accent-line` cor `--accent` bg `--accent-soft`
    - Estado selected: borda `--accent` cheia
  - Footer com border-top: hint contextual à esquerda + botão primary
    - **Hint contextual** (padrão do produto): `● Redator · opus-4 · ~R$ 0,04` (bolinha do papel + label + modelo mono + custo)

- **Diff atual × sugerida (`.diff`, substitui o balão após "Reescrever"):**
  - Grid 2 colunas dentro de um card com border `--border-strong`
  - Header em `--surface-2`: labels `ATUAL` e `SUGERIDA` em uppercase 10.5px, com bolinhas (`.dot` neutra e cor accent)
  - Body em Plex Serif 15 / 1.7; lado direito com bg quase branco `#fbfcfd`
  - `<ins>`: bg `--ok-soft`, cor `#14532d`, sem underline, padding 0 2px, radius 2px
  - `<del>`: bg `--err-soft`, cor `#7f1d1d`, line-through, padding 0 2px
  - Footer com border-top: nota mono à esquerda ("A sugestão só entra no documento se você aceitar.") + 3 botões: `Descartar` (ghost) · `Editar antes de aceitar` (secondary) · `Aceitar` (primary)

- **Avisos de margem (coluna DIREITA `.notes-col`, 200px):**
  - Cada `.margin-note` é `position: absolute`, alinhado por top ao parágrafo correspondente (JS calcula e evita colisão com gap mínimo 8px)
  - Border-left 2px na cor da severidade (âmbar padrão, `--err` para vermelho, `--accent` para info)
  - Padding 8 10; font-size 11.5px; hover → bg `--surface`
  - `.m-kind` uppercase 10px cor da severidade
  - `.m-body` 12/1.45 em `--text`; `<em>` destacado com bg `--warn-soft`
  - **`.m-source` (essencial):** origem do sinal, mono 9.5px:
    - `⚙ determinístico` (grátis, sem LLM) — cor `--text-muted`
    - `~ Revisor` (LLM) — cor `--accent`
  - `.m-actions`: dois botões uppercase 10px `CORRIGIR` (cor `--accent`) e `IGNORAR` (cor `--text-muted`); border-bottom 1px transparent que fica visível no hover
  - `.m-hint` (embaixo, quando "Corrigir" chama uma ação com custo): mono 9.5px cor `--text-faint` — ex: `Redator · opus-4 · ~R$ 0,04`
  - **Máximo 3 visíveis; o resto vira `.notes-overflow` no fim: "+2 avisos"**

#### 1d. Painel de Contexto (300px)

Tabs no topo (`.tabs`): `Pipeline · Fontes · Memória`. Tab ativa: cor `--accent`, border-bottom 2px `--accent` (mb: -1px pra sobrepor a borda do tabs).

**Pipeline (agrupada por PAPEL):**

Cada `.role-block` (padding 14 14 12, border-bottom `--border`):
- Head: nome do papel (14px weight 500) com bolinha 8px (`--accent` redator, `--ok` pesquisador, `--text-faint` revisor, tracejado transparente para determinístico) + tier `· forte/médio/barato` uppercase 10px `--text-faint` → alinhado à direita: custo acumulado mono 12px weight 500
- Linha `Modelo: <name> (<id>)` em mono 11px
- Descrição do papel em Plex Serif itálico 11.5 `--text-muted`
- Lista de ações executadas por esse papel: `✓ nome · contador mono` (ícones: ✓ verde, ◐ accent com pulse para em execução, ○ faint aguardando)

Bloco especial `.role-det`:
- Background `--surface-2`, border-top dashed
- Custo destacado em verde: **`R$ 0,00`** com classe `.zero`
- Descrição: "Verificações instantâneas, sempre grátis. Alimentam os avisos de margem sem consumir tokens."
- Lista: Contagem de linhas · Similaridade com acervo · Afirmação sem fonte · Termos fora do glossário

Rodapé do painel:
- `.role-adjust`: botão link "Ajustar modelos" com ícone de engrenagem → abre modal de Ajustes
- `.pipe-cost-total`: label uppercase "CUSTO ACUMULADO" + valor mono grande à direita

**Fontes:**
- Lista `.src-item` (padding 12 14, border-bottom); duvidosas com bg `#fffdf5`
- Título 12.5 weight 500; meta mono 11 com badge de status
- Badges (`.badge`) com bolinha:
  - `verificada` → verde/`--ok-soft`
  - `duvidosa` → âmbar/`--warn-soft`
  - `nao-loc` → vermelho/`--err-soft`
- Botão "Decidir" uppercase 11 `--accent` (só nas duvidosas/não localizadas) → abre painel de fontes (tela 4)

**Memória:**
- `.mem-card` — título 12 weight 500, resumo Plex Serif itálico 12.5 `--text-muted`, botão uppercase "Referenciar em vez de repetir" em `--accent`
- **Nunca mostrar o texto completo anterior — apenas o resumo**

#### 1e. Menu de telas (`.screens-menu`, canto inferior esq)

- Botão pequeno "Telas do protótipo" com ícone grid 4-cell
- Ao clicar, expande lista com 5 telas + numeração mono
- Menu de navegação da demo; **não implementar em produção** (as demais telas devem abrir a partir de ações reais)

---

### 2. Wizard de criação (modal, 2 passos)

**Purpose:** Configurar um novo artigo e detectar sobreposição com o acervo antes de gerar.

**Passo 1 — Parâmetros:**
- Grid 2 colunas de campos:
  - Assunto (text), Área (select)
  - Tese em uma frase (opcional, largura total)
  - Nº de páginas (number), Linhas por página (number)
  - Estilo (select: aprofundado / raso / intelectual / popular / juridiquês / técnico-popular)
  - Perfil de layout (ABNT — Times 12, entrelinha 1,5 etc.)
  - Estilo de citação (Autor-data / Nota de rodapé)
  - Público-alvo (text)
- **Profundidade do rascunho** — 3 cartões seletores lado a lado:
  - `Esqueleto` — só títulos
  - `Frases-guia` (marcar como **recomendado** com badge verde)
  - `Rascunho completo` — texto inteiro
  - Cartão selecionado: borda `--accent`, bg `--accent-soft`
- Rodapé: meta calculada em mono `Meta: 8 páginas × 30 linhas = 240 linhas (~3.600 palavras)`
- Ações: Cancelar (ghost) · Continuar (primary)

**Passo 2 — Aviso de sobreposição:**
- Alerta âmbar (`.overlap-warn`, bg `--warn-soft`, border-left 3px `--warn`, ícone de alerta)
- Título: `Você já tratou de parte disso.`
- Lista de artigos com % em mono cor `--warn`, seções coincidentes listadas
- 3 botões de saída: `Novo artigo mesmo assim` (ghost) · `Continuação` (secondary) · `Atualizar o anterior` (primary)

---

### 3. Gate de aprovação da estrutura (modal amplo)

**Purpose:** Ritualizar a aprovação da estrutura antes que o Redator escreva.

- Título: `Aprove a estrutura antes de escrever`
- Lead serifado: "Cada linha é uma seção. Arraste para reordenar, ajuste as linhas alocadas e atribua fontes. Nada será redigido até você aprovar."
- Tabela `.struct-table`:
  - Header uppercase: `Seção · Linhas · Fontes`
  - Cada linha: alça `≡` (drag cursor) · input do título · input mono de linhas · contador de fontes · botão `Remover` (hover cor `--err`)
- Link "+ Adicionar seção" em `--accent`
- Rodapé:
  - Meta ao vivo: `172 / 240 linhas alocadas` (vermelho se estourar, verde se == 240, texto muted se sobra)
  - Botões: `Salvar como molde` (ghost) · `Gerar outra proposta` (secondary) · `Aprovar e escrever` (primary)

---

### 4. Painel de fontes (modal amplo)

**Purpose:** Auditar todas as fontes do artigo; decidir sobre as duvidosas.

Layout 2 colunas (`.src-panel`): tabela à esquerda + detalhe à direita (320px).

**Esquerda:**
- Filtros por status no topo (`.src-filter`): pills "Todas 5 · Duvidosas 1 · Não localizadas 1 · Verificadas 3"
- Tabela: colunas Fonte · Tipo · Status · Citações
- Linha selecionada: bg `--accent-soft`

**Direita (detalhe da fonte selecionada):**
- Título + badge de status
- Blocos: `Afirmação do artigo`, `Trecho da fonte encontrada`, `Link informado`
  - Blockquotes serifadas com border-left 2px, padding 8 12
- Ações no rodapé: `Rejeitar` (ghost) · `Aceitar mesmo assim` (secondary) · `Buscar fonte melhor` (primary)

---

### 5. Comparação de versões (modal amplo)

**Purpose:** Comparar duas versões do mesmo artigo com diff colorido.

Layout 2 colunas (`.ver-compare`). Cada coluna:
- Header com selector `<select class="ver-sel">` mono (ex: `02-redacao`) + meta "há 3h · redação inicial"
- Coluna direita tem botão `Restaurar esta versão` uppercase 10.5 `--accent`
- Body Plex Serif 15 / 1.7 com diff colorido (mesmas classes `<ins>` / `<del>` do balão)

---

### 6. Modal de Fechamento

**Purpose:** Ritual de encerramento com checklist + 4 ações. Trigger: botão "Fechar artigo" no topbar.

**Estrutura:**

Summary no topo (bg `--surface-2`):
- `ARTIGO` uppercase + nome serifado
- `STATUS ATUAL` uppercase + pill com bolinha e versão

**Seção CHECKLIST:**
- Contador à direita do heading: `2 bloqueadores pendentes` (mono, `--text-muted`)
- Lista `.check-list` (border, radius, sem sombra):
  - Cada `.ck-item`: grid `32px 1fr`, padding 12 14, border-bottom
  - Background por severidade: `ok` verde-claro `#f6fbf7`, `warn` amarelo-claro `#fffdf5`, `block` vermelho-claro `#fdf5f5`
  - Ícone circular 22×22:
    - OK: fundo `--ok-soft`, ✓ em `--ok`
    - Warn: fundo `--warn-soft`, `!` em `--warn`
    - Block: fundo `--err-soft`, `✕` em `--err`
  - Corpo: label 13 weight 500 com contador mono muted à direita
  - Meta linha: badge `.ck-sev` (uppercase 10, padding 1 6, radius 2 na cor da severidade) + link `→ Ver ...` em `--accent`

- **Itens do checklist:**
  1. Fontes duvidosas ou não localizadas decididas — **BLOQUEIA**
  2. Avisos vermelhos em aberto (afirmação sem fonte) — **BLOQUEIA**
  3. Sugestões de reescrita não resolvidas — **BLOQUEIA**
  4. Seções fora da meta de linhas — **AVISO** (permite seguir, pode justificar)

**Seção AÇÕES:**
- 4 rows (`.ca-row`, grid `1fr auto`, border-bottom):
  1. **Passar para revisão** — desc + hint `● Revisor · haiku-4 · ~R$ 1,20` — botão secondary "Passar para revisão"; disabled quando já em revisão
  2. **Aprovar revisão** — desc "Trava o artigo. Nada mais pode ser editado sem clicar em Reabrir." + hint `⚙ Sem LLM · ~R$ 0,00` — botão secondary; disabled quando status !== 'review'
  3. **Gerar versão final** — desc "Salva snapshot numerado no histórico" — botão primary. Fica disabled se houver bloqueadores; hint muda para `.block-hint` em vermelho: `N bloqueadores pendentes — resolva no checklist acima.`
  4. **Exportar** — desc dinâmica (fora do status final: "Sai com cabeçalho **RASCUNHO — não citar**") — botão secondary "Exportar…" → abre modal de exportação

**Comportamento:**
- Ao clicar em `→ Ver ...`: fecha modal, `scrollIntoView` até o alvo, flash `--warn-soft` no elemento por 1200ms
- Após `Passar para revisão`: status muda para `review`, toast "Revisor (haiku-4) iniciou passada completa. Custo estimado ~R$ 1,20."; modal se re-renderiza com o novo estado
- Após `Aprovar revisão`: status vira `final`, versão bumpa (v2→v3), modal fecha, banner "Artigo final" aparece
- Após `Gerar versão final`: status vira `final`, versão bumpa, snapshot conceitual salvo

---

### 7. Tela de Ajustes de modelos

**Purpose:** Trocar o modelo LLM usado por cada papel; ver o impacto de custo por ação.

**Estrutura:**
- Lead: "Cada papel usa um modelo diferente. Trocar aqui muda o custo de todas as ações daquele papel. A detecção determinística é sempre grátis e não aparece nesta tela."
- 3 cards `.ms-role` (Redator, Pesquisador, Revisor):
  - Head: nome com bolinha do papel + tier · select mono à direita (`min-width 180px`)
  - Descrição do papel serifada itálica
  - Tabela de ações `.ms-actions` (border-top dashed):
    - Header uppercase: `Ação · Com <modelo atual> · Delta`
    - Cada ação: nome · custo mono · delta vs. modelo mais barato disponível (âmbar quando > 0.001; verde/`—` quando já é o mais barato)
- 4º card `.ms-role-det` (bg `--surface-2`):
  - Título "Determinístico · sem LLM" · valor fixo `Sempre R$ 0,00` em `--ok`
  - Descrição sobre verificações grátis
- Rodapé: `Restaurar padrões` (ghost) · `Fechar` (primary)

**Comportamento:**
- Trocar select recalcula todos os custos daquele papel na hora
- Também atualiza: painel Pipeline (todos os custos e o total), avisos de margem (hints contextuais), balão de reescrita (hint no botão)

---

### 8. Modal de Exportação

**Purpose:** Escolher formato de exportação. Sempre disponível.

- Warning âmbar no topo (quando status !== 'final'): "Este artigo ainda não foi finalizado. O arquivo exportado terá um cabeçalho **RASCUNHO — não citar** na primeira página."
- Grid 3 colunas com 3 opções (`.ex-opt`): PDF · DOCX · Markdown
  - Cada opção: chip mono do formato (bg `--surface-2` → `--accent` no hover) + nome 14 weight 500 + descrição

---

## Interactions & Behavior

### O modelo mental dos 3 papéis (crítico)

```
Redator (LLM forte, default opus-4)      → ESCREVE. Só ele toca no texto.
                                            Ações: propor estrutura, redigir seção, reescrever parágrafo.
                                            SEMPRE após aceite explícito do usuário.

Pesquisador (LLM médio, default sonnet-4) → LEVANTA e VERIFICA fontes. Não escreve.
                                            Ações: buscar fonte, verificar fonte, auditar citações.

Revisor (LLM barato, default haiku-4)     → SINAL sobre estilo/glossário/coerência.
                                            Produz avisos de margem. Nunca altera o texto.

Determinístico (sem LLM, R$ 0,00)         → Contagem de linhas, similaridade com acervo,
                                            afirmação sem fonte, glossário. Instantâneo, grátis.
```

**Regra dura a implementar:** funções que alteram o texto do documento ficam encapsuladas em um módulo que só aceita chamadas originadas do papel `redator`. Pesquisador e Revisor recebem `readonly` do documento — nunca `mutate`.

**Regra do custo:** os avisos determinísticos NUNCA aparecem como custo no painel Pipeline. Existe uma linha dedicada `R$ 0,00` para deixar explícito que essas checagens não usam LLM.

### Hint contextual (padrão de UI que se repete)

Sempre que um botão dispara uma ação que gasta LLM, mostrar logo abaixo/ao lado:

```
● <Papel> · <modelo> · ~R$ 0,04
```

Bolinha na cor do papel (accent/ok/faint), papel weight 500, modelo mono, custo mono. Alternativa `.det`: bolinha tracejada + `Sem LLM · ~R$ 0,00`.

Aplicar em:
- Botão "Reescrever" do balão
- Botão "Corrigir" nos avisos (se a ação chama LLM)
- Cada ação no modal de fechamento
- Cada opção na tela de ajustes de modelos

### Comportamento do parágrafo (essencial — a "bancada")

1. **Hover:** margem de ações (3 ícones) aparece à direita do bloco com `opacity 0 → 1` em .12s
2. **Clique em "reescrever":** balão ancorado abre logo abaixo do parágrafo (variantes possíveis: ancorado / lateral / overlay, controlável via tweaks). Parágrafo ganha classe `.selected` com bg `--accent-soft`
3. **Chips + textarea:** usuário monta a instrução
4. **Clique em "Reescrever":** balão fecha, `.diff` abre no mesmo lugar com atual × sugerida (diff palavra a palavra via LCS)
5. **Aceitar:** substitui o texto do parágrafo pelo sugerido. **Na hora:**
   - Recalcula linhas de todos os parágrafos daquela seção
   - Atualiza contador do cabeçalho da seção (verde/âmbar)
   - Altera a altura preenchida da barra na régua vertical
   - Flash verde `--ok-soft` no parágrafo por 700ms
6. **Editar antes:** aplica sugestão + torna parágrafo `contenteditable`; blur recalcula
7. **Descartar:** volta ao original, nada muda
8. **Travar parágrafo:** aplica classe `.locked`. Balão de reescrita não abre em parágrafos travados (feedback: flash âmbar). Clique de novo destrava.

### Avisos de margem

- **Máximo 3 visíveis simultaneamente**; extras vão para `.notes-overflow` (`+N avisos`, clicável)
- Cada aviso é posicionado por JS: coletar top do parágrafo relativo à coluna, ordenar por posição, empilhar respeitando gap mínimo de 8px (impede sobreposição)
- **Ignorar:** remove da lista com fade + slide 20px, adiciona ao Set `ignoredNotes` (impacta o checklist de fechamento)
- **Corrigir:** dispara a ação correspondente (reescrever → abre balão; buscar_fonte → muda aba para Fontes); mostra toast com papel + modelo
- Recalcular posições em: resize, load, aceitar sugestão, ignorar aviso, abrir/fechar balão ou diff

### Busca semântica na sidebar

- Não é filtro de título — mostra artigos onde o **termo aparece dentro do corpo**, com trecho contextualizado (`<mark>`) + label da seção
- No protótipo é mockado. Em produção: embeddings + top-k + rerank leve

### Régua vertical

- Sticky top: 32px, altura `calc(100vh - topbar - 64px)`
- Blocos proporcionais à altura de cada seção no doc (recalcular no load, resize, aceite de sugestão)
- Barra de preenchimento: `min(1, used/target)` da altura do bloco
- Cor: `--accent` normal, `--warn` se excedeu meta

### Fluxo de status do artigo

```
[draft "Rascunho vN"]
     │
     │  "Passar para revisão"
     ▼
[review "Em revisão vN"]  ── Revisor faz passada completa (~R$ 1,20 no haiku)
     │
     │  "Aprovar revisão"  OU  "Gerar versão final" (com bloqueadores resolvidos)
     ▼
[final "Final vN+1"]  ── banner âmbar, ações no parágrafo somem, botão "Fechar" some
     │
     │  "Reabrir para edição"
     ▼
[draft "Rascunho vN+2"]  ── ciclo pode recomeçar
```

Cada transição bumpa versão (v2 → v3 → v4…). Se possível, persistir snapshots por versão para o modal de "Comparação de versões" (tela 5).

### Tweaks (opcional em produção)

O protótipo tem um painel de Tweaks (bottom-right) com 3 knobs. Em produção, esconder ou converter em preferências do usuário:
- Cor de acento: Navy / Grafite
- Par tipográfico: Plex / Source / Editorial (Newsreader)
- Variante do balão de reescrita: Ancorado / Lateral / Overlay

Protocolo do protótipo: escuta `__activate_edit_mode` / `__deactivate_edit_mode` via `postMessage` e persiste via `__edit_mode_set_keys`. **Remover em produção** — usar sistema de preferências do app.

### Animações e transições

- Aparição de ações no parágrafo: `opacity .12s`
- Preenchimento da régua: `height .18s ease`
- Fade de aviso ignorado: `opacity .2s + transform .2s`
- Flash pós-aceite (verde no parágrafo): 700ms
- Flash de "→ Ver..." no checklist: 1200ms
- Pulse do dot "em execução" no Pipeline: 1.6s ease-in-out infinite
- **Sem** micro-animações "decorativas". Sem skeleton loaders. Sem "brilho de pensando".

---

## State Management

### Estado global do artigo

```ts
type Status = 'draft' | 'review' | 'final';

type State = {
  currentArticleId: string;
  status: Status;
  version: string;                    // ex: 'v2'

  // Modelo escolhido por papel
  models: {
    redator: string;                  // default 'opus-4'
    pesquisador: string;              // default 'sonnet-4'
    revisor: string;                  // default 'haiku-4'
  };

  // Sinal
  ignoredNoteIds: Set<string>;
  justifiedOverflow: boolean;

  // Contadores para o checklist de fechamento
  sourcesToDecide: number;            // duvidosa + não-localizada
  redFlags: number;                   // avisos kind=err ativos
  pendingDiffs: number;               // diffs abertos por aceitar

  // Interação
  openRewritePid: string | null;
  openDiffPid: string | null;
  currentSuggestion: string | null;
  contextTab: 'pipeline' | 'fontes' | 'memoria';

  // Custo acumulado por papel (para o painel Pipeline)
  accumulatedCost: { redator: number; pesquisador: number; revisor: number };
};
```

### Modelo de dados (artigo)

```ts
type Article = {
  id: string;
  title: string;
  area: string;
  status: Status;
  sections: Section[];
};

type Section = {
  id: string;
  title: string;
  target: number;                     // meta de linhas
  paragraphs: Paragraph[];
};

type Paragraph = {
  id: string;
  html: string;                       // pode conter <span class="cite" data-src="…">, <span class="no-source">, <span class="similar">
  locked?: boolean;
};

type MarginNote = {
  id: string;
  paragraphId: string;
  kind: 'warn' | 'err' | 'info';
  source: 'det' | 'revisor';          // origem do sinal
  label: string;                      // ex: "Repetição", "Sem fonte"
  body: string;                       // HTML pequeno com <em>
  fixAction: keyof typeof ACTIONS;    // qual ação disparar em "Corrigir"
};
```

### Contrato de ações e custos (a preservar na implementação real)

```ts
const MODEL_COST = {
  'haiku-4':   { mult: 0.25, label: 'Haiku 4' },
  'sonnet-4':  { mult: 1.00, label: 'Sonnet 4' },
  'opus-4':    { mult: 4.00, label: 'Opus 4' },
  'gpt-5-mini':{ mult: 0.35, label: 'GPT-5 Mini' },
};

const ACTIONS = {
  reescrever:      { role: 'redator',     base: 0.010 },
  redigir_secao:   { role: 'redator',     base: 0.105 },
  propor_estrut:   { role: 'redator',     base: 0.070 },
  buscar_fonte:    { role: 'pesquisador', base: 0.060 },
  verificar_fonte: { role: 'pesquisador', base: 0.030 },
  passada_revisor: { role: 'revisor',     base: 4.800 },
  aviso_estilo:    { role: 'revisor',     base: 0.008 },
};

costOf(action, modelOverride?) = base × multiplicador do modelo do papel
```

Em produção, substituir os multiplicadores fictícios pelos preços reais dos modelos. A estrutura é o que importa: **cada papel tem seu modelo, cada ação sabe seu papel, custo é multiplicativo.**

### Detecções determinísticas (implementar no cliente)

Não usam LLM. Devem rodar em milissegundos ao carregar o doc, ao aceitar uma sugestão, ou ao editar manualmente.

- **Contagem de linhas por parágrafo:** medir via `getClientRects()` ou dividir `boundingRect.height` pelo `lineHeight` computado. Somar por seção. Comparar com meta.
- **Similaridade com acervo:** comparar embeddings de parágrafos do artigo aberto com parágrafos dos outros artigos. Threshold para sinalizar. (No protótipo, hardcoded — em produção, calcular no ingest e cachear.)
- **Afirmação sem fonte:** parágrafos com sentenças fáticas mas sem `<span class="cite">`. Regra simples de heurística (frases com anos, números, quantificadores + ausência de cite).
- **Glossário:** vocabulário controlado da área; scan por termos fora dele.

---

## Design Tokens (resumo referencial)

Já detalhados na seção **Design System** acima. Extração recomendada como CSS custom properties ou como tokens tipados (`theme.ts`) — todos os valores estão pinados exatamente lá.

---

## Assets

Todos os assets do protótipo são inline (SVG, sem imagens externas). Nada de mídia binária.

- Ícones: SVGs inline dentro do HTML. Substituir por **Lucide** (recomendado) mantendo `stroke-width: 1.5`, `stroke-linecap: round`, `stroke-linejoin: round`.
- Fontes: **IBM Plex Sans**, **IBM Plex Serif**, **IBM Plex Mono** via Google Fonts. Também carregadas: Source Sans 3, Source Serif 4, Newsreader (apenas para os tweaks alternativos — remover em produção se os tweaks forem eliminados).
- Nenhum PNG, JPG, WebP ou vídeo.

---

## Files

Arquivos incluídos neste handoff (referência de design):

- `Meu Artigo.html` — Arquivo principal do protótipo. Contém a estrutura HTML, todos os tokens CSS em `:root`, todo o styling, e o carregamento das fontes. É o ponto de entrada.
- `app.js` — Toda a lógica: dados fictícios de Direito Eleitoral (artigos, seções, parágrafos, avisos, fontes, memória), rendering das colunas, interações do parágrafo (hover, reescrita, diff, aceite), régua vertical, avisos de margem, tabs, telas 2–5 (wizard, gate, fontes, comparação), telas dinâmicas de fechamento e ajustes de modelos, protocolo de tweaks, status/versão/reabrir, custo por papel.

Ambos são referência de design. Reimplementar no framework do projeto respeitando o design system deste README.

---

## Notas de implementação para Genspark Code / desenvolvedor

- **Não implementar** integração externa (publicar em blog/revista), configuração de chave de API, ou autenticação — não estão no escopo deste design
- **Priorizar** o comportamento do parágrafo e os avisos de margem — é onde está o valor do produto
- **Preservar** a regra "só o Redator toca no texto" no nível de tipo/interface, não só no comportamento
- **Preservar** a linha "Determinístico · R$ 0,00" no painel Pipeline — é uma escolha de produto que precisa estar visível
- **Preservar** os hints contextuais em toda ação que gasta LLM — deixa o custo tangível e ensina o usuário sobre a arquitetura
- Se o codebase tiver um sistema de comandos slash ou paleta de ações, considerar mapear as ações principais (Reescrever, Buscar fonte, Passar para revisão, Aprovar revisão, Gerar versão final) para atalhos de teclado
