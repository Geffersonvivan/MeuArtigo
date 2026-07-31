/* =================================================================
   Meu Artigo — app.js
   Protótipo visual navegável. Sem framework, sem backend.

   REGRA DURA:
   Apenas o Redator escreve no documento — e só após o usuário aceitar.
   Pesquisador e Revisor produzem sinal (fontes, avisos), nunca texto.

   ORIGEM DOS SINAIS:
   Muito do que aparece na margem é DETERMINÍSTICO (contagem de linhas,
   similaridade com acervo, afirmação sem fonte, glossário). Custa R$ 0,00.
   O Revisor (LLM) entra só em estilo e coerência.
   ================================================================= */

// -------------------------------------------------------------------
// PAPÉIS — Redator (forte), Pesquisador (médio), Revisor (barato)
// -------------------------------------------------------------------
const MODEL_COST = { // multiplicador fictício por token
  'haiku-4':      { mult: 0.25, label: 'Haiku 4' },
  'sonnet-4':     { mult: 1.00, label: 'Sonnet 4' },
  'opus-4':       { mult: 4.00, label: 'Opus 4' },
  'gpt-5-mini':   { mult: 0.35, label: 'GPT-5 Mini' }
};

const ROLES = {
  redator: {
    key: 'redator',
    label: 'Redator',
    tier: 'forte',
    role: 'Escreve. Só ele toca no texto — e apenas após você aceitar.',
    defaultModel: 'opus-4',
    availableModels: ['opus-4', 'sonnet-4', 'gpt-5-mini'],
    writes: true
  },
  pesquisador: {
    key: 'pesquisador',
    label: 'Pesquisador',
    tier: 'médio',
    role: 'Levanta fontes e verifica se sustentam a afirmação. Não escreve.',
    defaultModel: 'sonnet-4',
    availableModels: ['sonnet-4', 'opus-4', 'gpt-5-mini'],
    writes: false
  },
  revisor: {
    key: 'revisor',
    label: 'Revisor',
    tier: 'barato',
    role: 'Estilo, glossário e coerência. Só produz avisos de margem.',
    defaultModel: 'haiku-4',
    availableModels: ['haiku-4', 'sonnet-4', 'gpt-5-mini'],
    writes: false
  }
};

// Ações que consomem LLM — custo base em R$, multiplicado pelo modelo do papel
const ACTIONS = {
  reescrever:      { role: 'redator',     base: 0.010, label: 'Reescrever parágrafo' },
  redigir_secao:   { role: 'redator',     base: 0.105, label: 'Redigir seção inteira' },
  propor_estrut:   { role: 'redator',     base: 0.070, label: 'Propor estrutura' },
  buscar_fonte:    { role: 'pesquisador', base: 0.060, label: 'Buscar fonte' },
  verificar_fonte: { role: 'pesquisador', base: 0.030, label: 'Verificar fonte' },
  passada_revisor: { role: 'revisor',     base: 4.800, label: 'Passada completa de revisão' },
  aviso_estilo:    { role: 'revisor',     base: 0.008, label: 'Detectar estilo/coerência' }
};

function costOf(actionKey, modelOverride){
  const a = ACTIONS[actionKey]; if (!a) return 0;
  const model = modelOverride || state.models[a.role];
  return a.base * (MODEL_COST[model]?.mult || 1);
}
function fmtBRL(v){
  return 'R$ ' + v.toFixed(2).replace('.', ',');
}


// -------------------------------------------------------------------
// DADOS — Direito Eleitoral, conforme briefing
// -------------------------------------------------------------------
const ARTICLES = {
  a1: {
    id: 'a1',
    title: 'Impulsionamento eleitoral em redes sociais',
    area: 'Direito Eleitoral',
    status: 'draft',
    sections: [
      { id: 's1', title: 'Introdução', target: 10, paragraphs: [
        { id: 'p1-1', html: 'O debate sobre a permeabilidade das redes sociais no processo eleitoral brasileiro deixou de ser especulativo. Desde 2018, a plataforma digital tornou-se palco central da disputa política — e, com ela, a compra de alcance passou a ser prática rotineira, ainda que juridicamente delicada.' }
      ]},
      { id: 's2', title: 'O marco legal do impulsionamento', target: 40, paragraphs: [
        { id: 'p2-1', html: 'A <span class="cite" data-src="lei-9504">Lei nº 9.504/1997</span>, com a redação dada pela <span class="cite" data-src="lei-13488">Lei nº 13.488/2017</span>, autorizou expressamente o impulsionamento de conteúdo eleitoral, desde que contratado por partido, coligação ou candidato, com identificação do responsável (BRASIL, 1997). A vedação recai sobre o impulsionamento por terceiros, prática que o Tribunal Superior Eleitoral tem tratado com rigor crescente.' },
        { id: 'p2-2', html: 'A <span class="cite" data-src="res-23610">Resolução TSE nº 23.610/2019</span> regulamentou a propaganda eleitoral em rede e detalhou o que se entende por "impulsionamento": o pagamento pela ampliação artificial do alcance de uma postagem, distinto do disparo em massa e da propaganda tradicional. <span class="similar" title="Alta similaridade com Propaganda antecipada §4">Essa distinção conceitual, embora sutil, é o que separa o lícito do ilícito na prática cotidiana das campanhas.</span>' },
        { id: 'p2-3', html: '<span class="no-source" title="Afirmação sem fonte atribuída">A doutrina tem convergido no sentido de que o impulsionamento é modalidade especial de propaganda paga, sujeita a regime próprio e não subsumível às regras gerais de arrecadação de recursos.</span> A tese, porém, ainda encontra resistência em parte da jurisprudência regional.' }
      ]},
      { id: 's3', title: 'Limites de gasto e prestação de contas', target: 35, paragraphs: [
        { id: 'p3-1', html: 'Os gastos com impulsionamento integram o teto de gastos da campanha e devem ser declarados na prestação de contas, sob pena de rejeição das contas e possível cassação. A comprovação exige nota fiscal do provedor da plataforma e identificação do CPF/CNPJ do beneficiário do pagamento.' },
          { id: 'p3-2', html: 'Na prática, contudo, muitas campanhas ainda subdeclaram esses valores, alegando confusão entre gasto com produção de conteúdo (permitido) e pagamento pelo alcance (obrigatoriamente declarado como propaganda paga).' }
      ]},
      { id: 's4', title: 'Jurisprudência do TSE', target: 45, paragraphs: [
        { id: 'p4-1', html: 'A partir das eleições de 2020, o TSE consolidou entendimento restritivo sobre o impulsionamento por terceiros. Em <span class="cite" data-src="respe-0600">REspe nº 0600xxx-xx.2020.6.16.0000</span>, a Corte manteve a cassação de mandato de vereador cujo comitê havia contratado impulsionamento em nome de pessoa física distinta do candidato.' }
      ]},
      { id: 's5', title: 'Zonas cinzentas e riscos práticos', target: 30, paragraphs: [
        { id: 'p5-1', html: 'Persiste indefinição sobre o tratamento de conteúdo impulsionado por apoiadores individuais em suas próprias contas — modalidade que a legislação não previu expressamente e que a jurisprudência ainda hesita em enquadrar como propaganda ilícita ou como manifestação legítima do eleitor.' }
      ]},
      { id: 's6', title: 'Considerações finais', target: 12, paragraphs: [
        { id: 'p6-1', html: 'O impulsionamento eleitoral é hoje ferramenta indispensável e, ao mesmo tempo, terreno de maior insegurança jurídica das campanhas. A resposta institucional passa menos por novas proibições e mais por critérios claros de rastreabilidade e responsabilização.' }
      ]}
    ]
  }
};

// Cada aviso tem `source`:
//   'det'      → determinístico (grátis, instantâneo, sem LLM)
//   'revisor'  → LLM Revisor (estilo/coerência)
// E `fixAction`: qual ação seria disparada ao clicar em Corrigir
const MARGIN_NOTES = [
  { id: 'n1', pid: 'p2-1', kind: 'warn', source: 'det',     label: 'Repetição', body: 'Repete o parágrafo 4 de <em>"Propaganda antecipada negativa"</em>.', fixAction: 'reescrever' },
  { id: 'n2', pid: 'p2-2', kind: 'warn', source: 'det',     label: 'Extensão', body: 'Esta seção está <em>6 linhas acima da meta</em>.', fixAction: 'reescrever' },
  { id: 'n3', pid: 'p2-3', kind: 'err',  source: 'det',     label: 'Sem fonte', body: 'Afirmação factual sem fonte atribuída.', fixAction: 'buscar_fonte' },
  { id: 'n4', pid: 'p3-1', kind: 'warn', source: 'det',     label: 'Glossário', body: '"boost" — o glossário da área usa <em>"impulsionamento pago"</em>.', fixAction: 'reescrever' },
  { id: 'n5', pid: 'p5-1', kind: 'warn', source: 'revisor', label: 'Ambiguidade', body: 'Termo <em>"apoiadores individuais"</em> foi definido de forma diferente em outro artigo.', fixAction: 'reescrever' }
];

// Sugestões pré-fabricadas para o balão de reescrita (por parágrafo)
const REWRITE_SUGGESTIONS = {
  'p2-1': 'A Lei nº 9.504/1997 (redação da Lei nº 13.488/2017) autoriza o impulsionamento de conteúdo eleitoral, desde que contratado por partido, coligação ou candidato e com identificação clara do responsável. Impulsionamento por terceiros é vedado — e o TSE tem tratado a hipótese com rigor crescente.',
  'p2-2': 'A Resolução TSE nº 23.610/2019 definiu impulsionamento como o pagamento pela ampliação artificial do alcance de uma postagem, distinguindo-o do disparo em massa e da propaganda tradicional. Essa fronteira conceitual é o que separa, na prática, o lícito do ilícito.',
  'p2-3': 'Parte relevante da doutrina — Gomes (2020), Salgado (2022) — sustenta que o impulsionamento é modalidade especial de propaganda paga, com regime próprio, não subsumível às regras gerais de arrecadação de recursos.',
  'p3-1': 'Os gastos com impulsionamento pago integram o teto de gastos da campanha e devem constar da prestação de contas. A comprovação exige nota fiscal do provedor e identificação do CPF/CNPJ do beneficiário.',
  'p3-2': 'Muitas campanhas, contudo, subdeclaram esses valores por confundir gasto com produção de conteúdo — permitido — e pagamento pelo alcance, que deve figurar obrigatoriamente como propaganda paga.',
  'p4-1': 'Desde 2020, o TSE firmou entendimento restritivo. Em REspe nº 0600xxx-xx.2020.6.16.0000, a Corte manteve a cassação de vereador cujo comitê contratou impulsionamento em nome de pessoa física distinta do candidato.',
  'p5-1': 'A jurisprudência ainda hesita quanto ao impulsionamento feito por apoiadores em suas próprias contas: hipótese não prevista na lei, que oscila entre propaganda ilícita e manifestação legítima do eleitor.',
  'p6-1': 'O impulsionamento é hoje ferramenta indispensável e, ao mesmo tempo, o terreno de maior insegurança jurídica das campanhas. A resposta institucional passa menos por novas proibições e mais por critérios claros de rastreabilidade.',
  'p1-1': 'Desde 2018, a plataforma digital tornou-se palco central da disputa eleitoral brasileira — e, com isso, a compra de alcance deixou de ser prática marginal para se instalar como rotina, ainda que juridicamente delicada.'
};

// Busca semântica fingida — resultados por termo
const SEARCH_INDEX = [
  { term: 'impulsionamento', article: 'Impulsionamento eleitoral em redes sociais', section: 'O marco legal', snippet: 'autorizou expressamente o <mark>impulsionamento</mark> de conteúdo eleitoral, desde que contratado por partido…' },
  { term: 'impulsionamento', article: 'Propaganda antecipada negativa', section: 'Zonas cinzentas', snippet: 'a fronteira entre <mark>impulsionamento</mark> lícito e propaganda paga negativa antecipada permanece indefinida…' },
  { term: 'impulsionamento', article: 'Prestação de contas de campanha', section: 'Gastos digitais', snippet: 'os gastos com <mark>impulsionamento</mark> integram o teto de gastos e devem constar da prestação de contas…' },
  { term: 'TSE', article: 'Impulsionamento eleitoral em redes sociais', section: 'Jurisprudência do TSE', snippet: 'o <mark>TSE</mark> consolidou entendimento restritivo sobre o impulsionamento por terceiros…' },
  { term: 'TSE', article: 'Uso de IA em campanhas eleitorais', section: 'Resolução 23.732', snippet: 'o <mark>TSE</mark>, em 2024, editou resolução específica sobre uso de IA generativa em propaganda…' },
  { term: '9.504', article: 'Impulsionamento eleitoral em redes sociais', section: 'O marco legal', snippet: 'A Lei nº <mark>9.504</mark>/1997, com a redação dada pela Lei nº 13.488/2017, autorizou expressamente…' },
  { term: 'ficha limpa', article: 'Propaganda antecipada negativa', section: 'Introdução', snippet: 'os precedentes construídos após a <mark>Ficha Limpa</mark> pavimentaram a atual sistemática de cassação…' }
];

// -------------------------------------------------------------------
// ESTADO
// -------------------------------------------------------------------
const state = {
  currentArticle: 'a1',
  openRewrite: null,     // paragraph id com balão aberto
  openDiff: null,        // paragraph id com diff aberto
  suggestion: null,      // texto sugerido (guardado enquanto diff aberto)
  activeTab: 'pipeline',
  contextTab: 'pipeline',

  // Status do artigo
  status: 'draft',       // 'draft' | 'review' | 'final'
  version: 'v2',         // string mostrada ao lado da pill
  ignoredNotes: new Set(),
  justifiedOverflow: false, // usuário justificou seção fora da meta

  // Modelo escolhido por papel (padrão = ROLES.*.defaultModel)
  models: {
    redator: 'opus-4',
    pesquisador: 'sonnet-4',
    revisor: 'haiku-4'
  },

  // Contadores para o modal de fechamento
  sourcesToDecide: 2,    // fontes duvidosas + não localizadas
  redFlags: 1,           // avisos vermelhos
  pendingDiffs: 0        // parágrafos com sugestão aberta ainda não resolvida
};

// -------------------------------------------------------------------
// UTIL
// -------------------------------------------------------------------
function $(sel, root=document){ return root.querySelector(sel); }
function $$(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }
function el(html){
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstChild;
}
function stripHTML(html){
  const d = document.createElement('div');
  d.innerHTML = html;
  return d.textContent || '';
}

// Aproxima nº de linhas do parágrafo com base na largura do container e no texto
// Usamos getClientRects() dividido pela altura de linha (é o método mais confiável em prod)
function measureLines(pEl){
  if (!pEl) return 0;
  const cs = getComputedStyle(pEl);
  const lh = parseFloat(cs.lineHeight);
  // usa scrollHeight menos padding
  const pt = parseFloat(cs.paddingTop) || 0;
  const pb = parseFloat(cs.paddingBottom) || 0;
  const h = pEl.getBoundingClientRect().height - pt - pb;
  return Math.max(1, Math.round(h / lh));
}

function updateSectionLines(sectionEl){
  const paragraphs = $$('.paragraph', sectionEl);
  let used = 0;
  paragraphs.forEach(p => used += measureLines(p));
  const target = parseInt(sectionEl.dataset.target, 10);
  const countEl = $('.s-count', sectionEl);
  countEl.querySelector('.used').textContent = used;
  countEl.classList.remove('ok', 'warn');
  if (used > target){ countEl.classList.add('warn'); }
  else { countEl.classList.add('ok'); }
  return { used, target };
}

// -------------------------------------------------------------------
// RENDER DO DOCUMENTO
// -------------------------------------------------------------------
function renderDoc(){
  const article = ARTICLES[state.currentArticle];
  const doc = $('#doc');
  doc.innerHTML = '';

  article.sections.forEach((sec, sIdx) => {
    const secEl = el(`
      <section class="section" id="${sec.id}" data-target="${sec.target}">
        <div class="section-head">
          <div>
            <span class="s-num">${String(sIdx+1).padStart(2,'0')}</span>
            <span class="s-title">${sec.title}</span>
          </div>
          <div class="s-count"><span class="used">0</span> / ${sec.target} linhas</div>
        </div>
      </section>
    `);
    sec.paragraphs.forEach(p => {
      const pEl = el(`
        <div class="paragraph" id="${p.id}" data-pid="${p.id}">
          <span class="p-lock-mark">
            <svg class="i" viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10" rx="1"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>
          </span>
          <div class="p-text">${p.html}</div>
          <div class="p-actions">
            <button class="p-action" data-act="comment" aria-label="Comentar">
              <svg class="i" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H8l-4 4V5a2 2 0 012-2h13a2 2 0 012 2v10z"/></svg>
            </button>
            <button class="p-action" data-act="rewrite" aria-label="Reescrever">
              <svg class="i" viewBox="0 0 24 24"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
            </button>
            <button class="p-action" data-act="lock" aria-label="Travar">
              <svg class="i" viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10" rx="1"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>
            </button>
          </div>
        </div>
      `);
      secEl.appendChild(pEl);

      // Slot para balão + diff (ancorados logo após o parágrafo)
      const rewriteSlot = el(`
        <div class="rewrite" data-for="${p.id}">
          <div class="rewrite-title">
            <span>Reescrever este parágrafo</span>
            <button class="close" aria-label="Fechar">×</button>
          </div>
          <textarea class="rewrite-input" placeholder="Instrução opcional (ex: deixe mais direto, tire o juridiquês…)"></textarea>
          <div class="chips">
            <button class="chip" data-chip="encurtar">encurtar</button>
            <button class="chip" data-chip="expandir">expandir</button>
            <button class="chip" data-chip="simplificar">simplificar</button>
            <button class="chip" data-chip="endurecer">endurecer tom</button>
            <button class="chip" data-chip="fonte">pedir fonte</button>
          </div>
          <div class="rewrite-foot">
            <span class="rewrite-hint role-hint">
              <span class="rh-dot redator"></span>
              Redator · <span class="rh-model">${state.models.redator}</span> · ~<span class="rh-cost">${fmtBRL(costOf('reescrever')).replace('R$ ','R$&nbsp;')}</span>
            </span>
            <button class="btn-primary" data-act="do-rewrite">
              <svg class="i" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>
              Reescrever
            </button>
          </div>
        </div>
      `);
      secEl.appendChild(rewriteSlot);

      const diffSlot = el(`
        <div class="diff" data-for="${p.id}">
          <div class="diff-head">
            <div class="side-cur"><span class="dot"></span>Atual</div>
            <div class="side-new"><span class="dot"></span>Sugerida</div>
          </div>
          <div class="diff-body">
            <div class="col-cur"></div>
            <div class="col-new"></div>
          </div>
          <div class="diff-foot">
            <span class="note">A sugestão só entra no documento se você aceitar.</span>
            <div class="actions">
              <button class="btn-ghost" data-act="discard">Descartar</button>
              <button class="btn-secondary" data-act="edit-before">Editar antes de aceitar</button>
              <button class="btn-primary" data-act="accept">Aceitar</button>
            </div>
          </div>
        </div>
      `);
      secEl.appendChild(diffSlot);
    });

    doc.appendChild(secEl);
  });

  // Estado inicial: hover simulado no p2-1 (visível on-load, mostra margem de ações)
  const demoP = $('#p2-1');
  if (demoP) demoP.classList.add('demo-hover');

  // Trava um parágrafo para mostrar o estado — p1-1 (introdução) fica visível
  const lockedP = $('#p6-1');
  if (lockedP) lockedP.classList.add('locked');
}

// -------------------------------------------------------------------
// RÉGUA VERTICAL — sincronizada com as seções
// -------------------------------------------------------------------
function renderRuler(){
  const article = ARTICLES[state.currentArticle];
  const ruler = $('#ruler');
  ruler.innerHTML = '';

  article.sections.forEach((sec, i) => {
    const rEl = el(`
      <div class="ruler-section" data-for="${sec.id}">
        <div class="r-label">${String(i+1).padStart(2,'0')}</div>
        <div class="r-count"><span class="used">0</span>/${sec.target}</div>
        <div class="r-fill"></div>
      </div>
    `);
    ruler.appendChild(rEl);
  });
}

function syncRuler(){
  const editor = $('.editor');
  const ruler = $('#ruler');
  const rulerRect = ruler.getBoundingClientRect();
  const editorRect = editor.getBoundingClientRect();

  // Distribui cada bloco da régua proporcional à altura da seção correspondente
  const sections = $$('.section', $('#doc'));
  const totalDocHeight = sections.reduce((s, sec) => s + sec.getBoundingClientRect().height, 0);
  const rulerHeight = ruler.clientHeight;

  sections.forEach((sec) => {
    const rBlock = $(`.ruler-section[data-for="${sec.id}"]`);
    if (!rBlock) return;
    const secH = sec.getBoundingClientRect().height;
    const share = secH / totalDocHeight;
    rBlock.style.flex = `0 0 ${share * rulerHeight}px`;

    // Preenchimento proporcional ao uso vs meta
    const target = parseInt(sec.dataset.target, 10);
    let used = 0;
    $$('.paragraph', sec).forEach(p => used += measureLines(p));
    const pct = Math.min(1, used / target);
    const fill = $('.r-fill', rBlock);
    fill.style.height = (share * rulerHeight * pct) + 'px';
    rBlock.classList.toggle('over', used > target);

    // Atualiza contador visível na régua
    $('.used', rBlock).textContent = used;
  });
}

// -------------------------------------------------------------------
// AVISOS DE MARGEM — posição absoluta alinhada aos parágrafos
// -------------------------------------------------------------------
function renderMarginNotes(){
  const col = $('#notes-col');
  col.innerHTML = '';

  const visible = MARGIN_NOTES.filter(n => !state.ignoredNotes.has(n.id));
  const active = visible.slice(0, 3);
  const overflow = visible.slice(3);

  active.forEach(n => {
    const act = ACTIONS[n.fixAction];
    const cost = act ? costOf(n.fixAction) : 0;
    const roleKey = act ? act.role : null;
    const roleLabel = roleKey ? ROLES[roleKey].label : '';
    const model = roleKey ? state.models[roleKey] : '';
    // Hint: "Redator · opus-4 · ~R$ 0,04"
    const hint = act ? `${roleLabel} · ${model} · ~${fmtBRL(cost)}` : '';

    // Origem do sinal
    const srcTag = n.source === 'det'
      ? `<span class="src-tag det" title="Detec\u00e7\u00e3o determin\u00edstica \u2014 R$ 0,00">\u2699 determin\u00edstico</span>`
      : `<span class="src-tag rev" title="Detectado pelo Revisor (LLM)">~ Revisor</span>`;

    const noteEl = el(`
      <div class="margin-note ${n.kind === 'err' ? 'err' : ''}" data-nid="${n.id}" data-pid="${n.pid}">
        <div class="m-kind">
          <span class="dot" style="width:5px;height:5px;border-radius:50%;background:currentColor;display:inline-block"></span>
          ${n.label}
        </div>
        <div class="m-body">${n.body}</div>
        <div class="m-source">${srcTag}</div>
        <div class="m-actions">
          <button class="fix" data-fix-action="${n.fixAction}" title="${hint}">Corrigir</button>
          <button class="ignore">Ignorar</button>
        </div>
        ${act ? `<div class="m-hint">${hint}</div>` : ''}
      </div>
    `);
    col.appendChild(noteEl);
  });

  if (overflow.length){
    const oEl = el(`<div class="notes-overflow">+ ${overflow.length} avisos</div>`);
    col.appendChild(oEl);
  }

  positionMarginNotes();
}

function positionMarginNotes(){
  const col = $('#notes-col');
  const colRect = col.getBoundingClientRect();
  const notes = $$('.margin-note', col);

  // Coleta posições-alvo (top do parágrafo relativo à coluna)
  let placements = notes.map(n => {
    const p = $('#' + n.dataset.pid);
    if (!p) return null;
    const pRect = p.getBoundingClientRect();
    const targetTop = pRect.top - colRect.top;
    return { note: n, target: targetTop, height: n.offsetHeight || 60 };
  }).filter(Boolean);

  // Empilha respeitando um gap mínimo (evita sobreposição)
  const GAP = 8;
  placements.sort((a,b) => a.target - b.target);
  let lastBottom = -Infinity;
  placements.forEach(pl => {
    let top = Math.max(pl.target, lastBottom + GAP);
    pl.note.style.top = top + 'px';
    lastBottom = top + pl.height;
  });

  // Posiciona o overflow no fim
  const ovf = $('.notes-overflow', col);
  if (ovf){
    ovf.style.top = (lastBottom + 20) + 'px';
  }
}

// -------------------------------------------------------------------
// INTERAÇÕES — parágrafo
// -------------------------------------------------------------------
function initParagraphInteractions(){
  const doc = $('#doc');

  doc.addEventListener('click', (e) => {
    // Ações do parágrafo
    const act = e.target.closest('.p-action');
    if (act){
      const p = act.closest('.paragraph');
      const kind = act.dataset.act;
      if (kind === 'lock'){
        p.classList.toggle('locked');
      } else if (kind === 'rewrite'){
        openRewrite(p.dataset.pid);
      } else if (kind === 'comment'){
        // stub — flash pra mostrar interação
        act.classList.add('active');
        setTimeout(() => act.classList.remove('active'), 800);
      }
      return;
    }

    // Fechar balão
    const closeBtn = e.target.closest('.rewrite .close');
    if (closeBtn){
      closeRewrite();
      return;
    }

    // Chip
    const chip = e.target.closest('.chip');
    if (chip){
      chip.classList.toggle('selected');
      return;
    }

    // Reescrever
    const rewriteBtn = e.target.closest('[data-act="do-rewrite"]');
    if (rewriteBtn){
      runRewrite();
      return;
    }

    // Diff actions
    const acceptBtn = e.target.closest('[data-act="accept"]');
    if (acceptBtn){
      acceptSuggestion();
      return;
    }
    const editBefore = e.target.closest('[data-act="edit-before"]');
    if (editBefore){
      editBeforeAccept();
      return;
    }
    const discardBtn = e.target.closest('[data-act="discard"]');
    if (discardBtn){
      discardSuggestion();
      return;
    }

    // Citação clicável → abre painel de fontes
    const cite = e.target.closest('.cite');
    if (cite){
      switchContextTab('fontes');
      return;
    }
  });
}

function openRewrite(pid){
  closeRewrite();
  const rewriteEl = $(`.rewrite[data-for="${pid}"]`);
  if (!rewriteEl) return;
  const p = $('#' + pid);
  if (p.classList.contains('locked')){
    // parágrafo travado — não abre. Feedback simples:
    p.animate([{ background: 'var(--warn-soft)'}, { background: 'transparent'}], { duration: 600 });
    return;
  }
  rewriteEl.classList.add('open');
  p.classList.add('selected');
  state.openRewrite = pid;
  // Foca no textarea
  setTimeout(() => rewriteEl.querySelector('.rewrite-input').focus(), 50);
  positionMarginNotes();
}

function closeRewrite(){
  if (state.openRewrite){
    const rewriteEl = $(`.rewrite[data-for="${state.openRewrite}"]`);
    if (rewriteEl) rewriteEl.classList.remove('open');
    const p = $('#' + state.openRewrite);
    if (p && state.openDiff !== state.openRewrite) p.classList.remove('selected');
    state.openRewrite = null;
  }
  positionMarginNotes();
}

function runRewrite(){
  const pid = state.openRewrite;
  if (!pid) return;
  const rewriteEl = $(`.rewrite[data-for="${pid}"]`);
  const diffEl = $(`.diff[data-for="${pid}"]`);
  const p = $('#' + pid);

  const currentText = $('.p-text', p).innerHTML;
  const suggestion = REWRITE_SUGGESTIONS[pid] || currentText;

  // Diff simples palavra a palavra (algoritmo LCS mínimo)
  const cur = stripHTML(currentText);
  const nxt = suggestion;
  const { curOut, nxtOut } = wordDiff(cur, nxt);

  $('.col-cur', diffEl).innerHTML = curOut;
  $('.col-new', diffEl).innerHTML = nxtOut;

  rewriteEl.classList.remove('open');
  diffEl.classList.add('open');
  state.openRewrite = null;
  state.openDiff = pid;
  state.suggestion = suggestion;
  positionMarginNotes();

  // Scroll gentil para o diff ficar visível
  diffEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function acceptSuggestion(){
  const pid = state.openDiff;
  if (!pid || !state.suggestion) return;
  const p = $('#' + pid);
  $('.p-text', p).textContent = state.suggestion;

  // Fecha diff, atualiza tudo
  closeDiff();

  // Recalcula seção — o contador e a régua devem mudar na hora
  const sec = p.closest('.section');
  requestAnimationFrame(() => {
    updateSectionLines(sec);
    syncRuler();
    positionMarginNotes();
  });

  // Micro feedback: flash verde no parágrafo
  p.animate(
    [{ background: 'var(--ok-soft)'}, { background: 'transparent'}],
    { duration: 700 }
  );
}

function editBeforeAccept(){
  const pid = state.openDiff;
  if (!pid || !state.suggestion) return;
  const p = $('#' + pid);
  const textEl = $('.p-text', p);
  textEl.textContent = state.suggestion;
  textEl.setAttribute('contenteditable', 'true');
  textEl.focus();
  // seleciona todo o texto
  const range = document.createRange();
  range.selectNodeContents(textEl);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);

  textEl.addEventListener('blur', () => {
    textEl.removeAttribute('contenteditable');
    const sec = p.closest('.section');
    updateSectionLines(sec);
    syncRuler();
    positionMarginNotes();
  }, { once: true });

  closeDiff();
}

function discardSuggestion(){ closeDiff(); }

function closeDiff(){
  if (state.openDiff){
    const diffEl = $(`.diff[data-for="${state.openDiff}"]`);
    if (diffEl) diffEl.classList.remove('open');
    const p = $('#' + state.openDiff);
    if (p) p.classList.remove('selected');
  }
  state.openDiff = null;
  state.suggestion = null;
  positionMarginNotes();
}

// -------------------------------------------------------------------
// DIFF palavra-a-palavra (LCS)
// -------------------------------------------------------------------
function wordDiff(a, b){
  const A = a.split(/(\s+)/);
  const B = b.split(/(\s+)/);
  const n = A.length, m = B.length;
  // LCS table
  const dp = Array.from({length:n+1}, () => new Uint16Array(m+1));
  for (let i=n-1;i>=0;i--){
    for (let j=m-1;j>=0;j--){
      dp[i][j] = A[i] === B[j] ? dp[i+1][j+1] + 1 : Math.max(dp[i+1][j], dp[i][j+1]);
    }
  }
  const curOut = [], nxtOut = [];
  let i=0, j=0;
  while (i<n && j<m){
    if (A[i] === B[j]){
      curOut.push(escapeHtml(A[i]));
      nxtOut.push(escapeHtml(B[j]));
      i++; j++;
    } else if (dp[i+1][j] >= dp[i][j+1]){
      curOut.push('<del>' + escapeHtml(A[i]) + '</del>');
      i++;
    } else {
      nxtOut.push('<ins>' + escapeHtml(B[j]) + '</ins>');
      j++;
    }
  }
  while (i<n){ curOut.push('<del>' + escapeHtml(A[i++]) + '</del>'); }
  while (j<m){ nxtOut.push('<ins>' + escapeHtml(B[j++]) + '</ins>'); }
  return { curOut: curOut.join(''), nxtOut: nxtOut.join('') };
}
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// -------------------------------------------------------------------
// PIPELINE — renderiza os 3 papéis + bloco determinístico
// -------------------------------------------------------------------
// Estado (fictício) de execução das ações por papel
const PIPELINE_DATA = {
  redator: [
    { name: 'Propor estrutura', status: 'done', count: '6 seções' },
    { name: 'Redigir seções',   status: 'done', count: '240 linhas' },
    { name: 'Reescrever parágrafo', status: 'idle', count: 'sob comando' }
  ],
  pesquisador: [
    { name: 'Levantar fontes', status: 'done', count: '12 fontes' },
    { name: 'Verificar fontes', status: 'done', count: '2 duvidosas · 1 não localizada', warn: true }
  ],
  revisor: [
    { name: 'Estilo', status: 'run', count: 'em execução' },
    { name: 'Glossário', status: 'wait', count: 'aguardando' },
    { name: 'Coerência entre seções', status: 'wait', count: 'aguardando' }
  ],
  det: [
    { name: 'Contagem de linhas por seção', status: 'done', count: '6/6 seções' },
    { name: 'Similaridade com acervo', status: 'done', count: '2 repetições' },
    { name: 'Afirmação sem fonte', status: 'done', count: '1 vermelho' },
    { name: 'Termos fora do glossário', status: 'done', count: '1 aviso' }
  ]
};

// Custos exibidos ao lado de cada papel — computados a partir do modelo escolhido
function roleAccumulatedCost(roleKey){
  const map = {
    redator: (m) => 0.070 * MODEL_COST[m].mult + 0.630 * MODEL_COST[m].mult, // estrutura + redação
    pesquisador: (m) => 0.030 * MODEL_COST[m].mult * 12,                     // 12 verificações
    revisor: (m) => 4.800 * MODEL_COST[m].mult * 0.20                        // parcial (em execução)
  };
  const model = state.models[roleKey];
  return map[roleKey] ? map[roleKey](model) : 0;
}

function renderPipeline(){
  const panel = $('#pipeline-panel');
  if (!panel) return;

  const roleBlock = (roleKey, data) => {
    const r = ROLES[roleKey];
    const cost = roleAccumulatedCost(roleKey);
    const model = state.models[roleKey];
    const modelLabel = MODEL_COST[model]?.label || model;

    return `
      <div class="role-block" data-role="${roleKey}">
        <div class="role-head">
          <div class="role-name">
            <span class="r-dot ${roleKey}"></span>
            ${r.label}
            <span class="role-tier">· ${r.tier}</span>
          </div>
          <div class="role-cost">${fmtBRL(cost)}</div>
        </div>
        <div class="role-model">Modelo: <span class="m-name">${modelLabel}</span> <span style="color:var(--text-faint)">(${model})</span></div>
        <div class="role-desc">${r.role}</div>
        <div class="role-lines">
          ${data.map(item => {
            const icon = item.status === 'done' ? '<span class="rl-check">✓</span>'
                       : item.status === 'run'  ? '<span class="rl-run">◐</span>'
                       : item.status === 'wait' ? '<span class="rl-wait">○</span>'
                       :                          '<span class="rl-wait">·</span>';
            return `
              <div class="rl-item">
                ${icon}
                <span class="rl-name ${item.warn ? 'rl-warn' : ''}">${item.name}</span>
                <span class="rl-count">${item.count}</span>
              </div>`;
          }).join('')}
        </div>
      </div>
    `;
  };

  const detBlock = `
    <div class="role-block role-det">
      <div class="role-head">
        <div class="role-name">
          <span class="r-dot det"></span>
          Determinístico
          <span class="role-tier">· sem LLM</span>
        </div>
        <div class="role-cost zero">R$ 0,00</div>
      </div>
      <div class="role-desc">
        Verificações instantâneas, sempre grátis. Alimentam os avisos de margem sem consumir tokens.
      </div>
      <div class="role-lines">
        ${PIPELINE_DATA.det.map(item => `
          <div class="rl-item">
            <span class="rl-check">✓</span>
            <span class="rl-name">${item.name}</span>
            <span class="rl-count">${item.count}</span>
          </div>`).join('')}
      </div>
    </div>
  `;

  const totalCost = ['redator','pesquisador','revisor'].reduce((s,k) => s + roleAccumulatedCost(k), 0);

  panel.innerHTML =
    roleBlock('redator', PIPELINE_DATA.redator) +
    roleBlock('pesquisador', PIPELINE_DATA.pesquisador) +
    roleBlock('revisor', PIPELINE_DATA.revisor) +
    detBlock +
    `<div class="role-adjust">
       <button class="btn-link" id="open-model-settings">
         <svg class="i" style="width:11px;height:11px" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
         Ajustar modelos
       </button>
       <span style="font-size:11px;color:var(--text-faint);font-family:var(--font-mono)">3 papéis · 4 modelos</span>
     </div>
     <div class="pipe-cost-total">
       <span class="lbl">Custo acumulado</span>
       <span class="val">${fmtBRL(totalCost)}</span>
     </div>`;

  // Wire do botão de ajustes
  const btn = $('#open-model-settings');
  if (btn) btn.addEventListener('click', () => openScreen('modelSettings'));

  // Reflete no session-cost do topbar também
  const sc = $('.session-cost');
  if (sc) sc.innerHTML = '<span class="label">sessão</span>' + fmtBRL(totalCost);
}

// -------------------------------------------------------------------
// TABS DO PAINEL DIREITO
// -------------------------------------------------------------------
function initTabs(){
  $$('.tab').forEach(t => {
    t.addEventListener('click', () => switchContextTab(t.dataset.tab));
  });
}
function switchContextTab(name){
  state.contextTab = name;
  $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  $$('.tab-panel').forEach(p => p.classList.toggle('active', p.dataset.panel === name));
}

// -------------------------------------------------------------------
// SIDEBAR — busca semântica + árvore
// -------------------------------------------------------------------
function initSidebar(){
  const search = $('#search');
  const results = $('#search-results');

  search.addEventListener('input', () => {
    const q = search.value.trim().toLowerCase();
    if (!q){ results.classList.remove('open'); results.innerHTML = ''; return; }
    const matches = SEARCH_INDEX.filter(r => r.term.toLowerCase().includes(q) || r.article.toLowerCase().includes(q) || r.snippet.toLowerCase().includes(q));
    if (!matches.length){
      results.innerHTML = `<div style="padding:16px 12px;color:var(--text-faint);font-size:12px">Nenhum resultado para "<em>${escapeHtml(q)}</em>"</div>`;
      results.classList.add('open');
      return;
    }
    results.innerHTML = matches.map(m => `
      <button class="search-result">
        <div class="title">${m.article}</div>
        <div class="snippet">${m.snippet}</div>
        <div class="section">${m.section}</div>
      </button>
    `).join('');
    results.classList.add('open');
  });
  search.addEventListener('blur', () => {
    setTimeout(() => results.classList.remove('open'), 200);
  });
  search.addEventListener('focus', () => {
    if (search.value.trim()) results.classList.add('open');
  });

  // Árvore — seleção visual apenas
  $$('.tree-item').forEach(item => {
    item.addEventListener('click', () => {
      $$('.tree-item').forEach(t => t.classList.remove('active'));
      item.classList.add('active');
      // apenas o a1 tem conteúdo real
      if (item.dataset.article !== 'a1'){
        showToast('Artigo apenas visual no protótipo — o conteúdo real é do "Impulsionamento".');
      }
    });
  });

  // Fontes pendentes → tela 4
  $('#btn-sources-pending').addEventListener('click', () => openScreen('sources'));
}

// -------------------------------------------------------------------
// NAVEGAÇÃO — Screens
// -------------------------------------------------------------------
function initScreens(){
  const menu = $('#screens-menu');
  $('#screens-toggle').addEventListener('click', (e) => {
    e.stopPropagation();
    menu.classList.toggle('open');
  });
  document.addEventListener('click', () => menu.classList.remove('open'));

  $$('.screens-list button').forEach(b => {
    b.addEventListener('click', (e) => {
      e.stopPropagation();
      openScreen(b.dataset.screen);
      menu.classList.remove('open');
    });
  });

  // Novo artigo → wizard
  $('#btn-new-article').addEventListener('click', () => openScreen('wizard'));

  // "Decidir" nas fontes duvidosas → painel de fontes
  $$('[data-open="sources-view"]').forEach(b => b.addEventListener('click', () => openScreen('sources')));

  // Histórico → comparação de versões
  $('#btn-history').addEventListener('click', () => openScreen('diff'));

  // Fechar artigo
  const closeBtn = $('#btn-close-article');
  if (closeBtn) closeBtn.addEventListener('click', () => openScreen('close'));

  // Exportar (topbar)
  const exportBtn = $('#btn-export');
  if (exportBtn) exportBtn.addEventListener('click', () => openScreen('export'));

  // Reabrir (banner)
  const reopenBtn = $('#btn-reopen');
  if (reopenBtn) reopenBtn.addEventListener('click', () => {
    state.status = 'draft';
    bumpVersion();
    updateStatusUI();
    showToast(`Artigo reaberto para edição. Nova versão: ${state.version}.`);
  });

  // Fechar modal ao clicar fora ou Esc
  $('#modal-back').addEventListener('click', (e) => {
    if (e.target.id === 'modal-back') closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
}

function openScreen(name){
  if (name === 'workspace'){ closeModal(); return; }
  const modal = $('#modal');
  // Telas dinâmicas (dependem do estado)
  let markup;
  if (name === 'close') markup = SCREENS_DYN.close();
  else if (name === 'modelSettings') markup = SCREENS_DYN.modelSettings();
  else if (name === 'export') markup = SCREENS_DYN.export();
  else markup = SCREENS[name] || '<div class="modal-body">Tela não encontrada.</div>';

  modal.innerHTML = markup;
  modal.classList.toggle('wide', ['structure', 'diff', 'sources', 'close', 'modelSettings'].includes(name));
  $('#modal-back').classList.add('open');

  // Wire-up de botões específicos da tela
  modal.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', closeModal));
  if (name === 'wizard') wireWizard();
  if (name === 'structure') wireStructure();
  if (name === 'sources') wireSources();
  if (name === 'close') wireCloseArticle();
  if (name === 'modelSettings') wireModelSettings();
  if (name === 'export') wireExport();
}
function closeModal(){
  $('#modal-back').classList.remove('open');
  $('#modal').innerHTML = '';
}

// -------------------------------------------------------------------
// TELAS 2-5 (markup completo)
// -------------------------------------------------------------------
const SCREENS = {
  wizard: `
    <div class="modal-head">
      <h2>Novo artigo</h2>
      <span class="step-info">Passo 1 de 2 · Parâmetros</span>
    </div>
    <div class="modal-body">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px 20px">
        <label class="fld">
          <div class="fld-label">Assunto</div>
          <input class="fld-input" value="Impulsionamento eleitoral em redes sociais"/>
        </label>
        <label class="fld">
          <div class="fld-label">Área</div>
          <select class="fld-input">
            <option>Direito Eleitoral</option>
            <option>Direito Constitucional</option>
            <option>Direito Administrativo</option>
          </select>
        </label>
        <label class="fld" style="grid-column:1/-1">
          <div class="fld-label">Tese em uma frase <span class="fld-hint">(opcional)</span></div>
          <input class="fld-input" placeholder="Ex: o impulsionamento é modalidade especial de propaganda paga, sujeita a regime próprio."/>
        </label>
        <label class="fld">
          <div class="fld-label">Nº de páginas</div>
          <input class="fld-input" type="number" value="8" min="1"/>
        </label>
        <label class="fld">
          <div class="fld-label">Linhas por página</div>
          <input class="fld-input" type="number" value="30" min="10"/>
        </label>
        <label class="fld">
          <div class="fld-label">Estilo</div>
          <select class="fld-input">
            <option>Aprofundado</option><option>Raso</option><option>Intelectual</option>
            <option>Popular</option><option>Juridiquês</option><option>Técnico/popular</option>
          </select>
        </label>
        <label class="fld">
          <div class="fld-label">Perfil de layout</div>
          <select class="fld-input">
            <option>ABNT — Times 12, entrelinha 1,5</option>
            <option>Editorial — Serif 11, entrelinha 1,4</option>
            <option>Web — Sans 14, entrelinha 1,6</option>
          </select>
        </label>
        <label class="fld">
          <div class="fld-label">Estilo de citação</div>
          <select class="fld-input">
            <option>Autor-data</option>
            <option>Nota de rodapé</option>
          </select>
        </label>
        <label class="fld">
          <div class="fld-label">Público-alvo</div>
          <input class="fld-input" placeholder="Ex: advogados eleitorais em atuação prática"/>
        </label>
      </div>

      <div class="fld" style="margin-top:20px">
        <div class="fld-label">Profundidade do rascunho</div>
        <div class="depth-cards">
          <label class="depth-card">
            <input type="radio" name="depth" value="skeleton"/>
            <div class="d-title">Esqueleto</div>
            <div class="d-desc">Apenas títulos das seções, sem parágrafos.</div>
          </label>
          <label class="depth-card selected">
            <input type="radio" name="depth" value="frases" checked/>
            <div class="d-title">Frases-guia <span class="d-rec">recomendado</span></div>
            <div class="d-desc">A primeira frase de cada parágrafo, para você continuar.</div>
          </label>
          <label class="depth-card">
            <input type="radio" name="depth" value="completo"/>
            <div class="d-title">Rascunho completo</div>
            <div class="d-desc">Texto inteiro gerado, para editar.</div>
          </label>
        </div>
      </div>
    </div>
    <div class="modal-foot">
      <span class="meta">Meta: 8 páginas × 30 linhas = <b>240 linhas</b> (~3.600 palavras)</span>
      <div class="actions">
        <button class="btn-ghost" data-close>Cancelar</button>
        <button class="btn-primary" data-next-wizard>Continuar</button>
      </div>
    </div>
  `,

  wizardStep2: `
    <div class="modal-head">
      <h2>Novo artigo</h2>
      <span class="step-info">Passo 2 de 2 · Sobreposição detectada</span>
    </div>
    <div class="modal-body">
      <div class="overlap-warn">
        <svg class="i i-lg" viewBox="0 0 24 24"><path d="M12 9v4m0 4h.01M4.93 19h14.14a2 2 0 001.75-2.97l-7.07-12.5a2 2 0 00-3.5 0L3.18 16.03A2 2 0 004.93 19z"/></svg>
        <div>
          <div class="ow-title">Você já tratou de parte disso.</div>
          <div class="ow-body">Encontrei 2 artigos seus com trechos que provavelmente se repetem. Vale decidir agora.</div>
        </div>
      </div>

      <div class="overlap-list">
        <div class="overlap-item">
          <div class="ol-head">
            <div class="ol-title">Propaganda antecipada negativa</div>
            <div class="ol-pct">32% de sobreposição</div>
          </div>
          <div class="ol-sections">
            Seções coincidentes: <b>"Marco legal"</b>, <b>"Distinção entre impulsionamento e propaganda paga"</b>
          </div>
        </div>
        <div class="overlap-item">
          <div class="ol-head">
            <div class="ol-title">Prestação de contas de campanha</div>
            <div class="ol-pct">18% de sobreposição</div>
          </div>
          <div class="ol-sections">
            Seções coincidentes: <b>"Gastos com impulsionamento no teto de campanha"</b>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-foot">
      <span class="meta">O que você quer fazer?</span>
      <div class="actions">
        <button class="btn-ghost" data-close>Novo artigo mesmo assim</button>
        <button class="btn-secondary" data-close>Continuação</button>
        <button class="btn-primary" data-close>Atualizar o anterior</button>
      </div>
    </div>
  `,

  structure: `
    <div class="modal-head">
      <h2>Aprove a estrutura antes de escrever</h2>
      <span class="step-info">Impulsionamento eleitoral em redes sociais</span>
    </div>
    <div class="modal-body">
      <p class="modal-lede">Cada linha é uma seção. Arraste para reordenar, ajuste as linhas alocadas e atribua fontes. Nada será redigido até você aprovar.</p>
      <div class="struct-table">
        <div class="st-head">
          <div></div>
          <div>Seção</div>
          <div>Linhas</div>
          <div>Fontes</div>
          <div></div>
        </div>
        <div class="st-row"><span class="drag">≡</span><input value="Introdução"/><input type="number" value="10" data-lines/><span class="src-count">2</span><button class="rm">Remover</button></div>
        <div class="st-row"><span class="drag">≡</span><input value="O marco legal do impulsionamento"/><input type="number" value="40" data-lines/><span class="src-count">4</span><button class="rm">Remover</button></div>
        <div class="st-row"><span class="drag">≡</span><input value="Limites de gasto e prestação de contas"/><input type="number" value="35" data-lines/><span class="src-count">3</span><button class="rm">Remover</button></div>
        <div class="st-row"><span class="drag">≡</span><input value="Jurisprudência do TSE"/><input type="number" value="45" data-lines/><span class="src-count">5</span><button class="rm">Remover</button></div>
        <div class="st-row"><span class="drag">≡</span><input value="Zonas cinzentas e riscos práticos"/><input type="number" value="30" data-lines/><span class="src-count">2</span><button class="rm">Remover</button></div>
        <div class="st-row"><span class="drag">≡</span><input value="Considerações finais"/><input type="number" value="12" data-lines/><span class="src-count">0</span><button class="rm">Remover</button></div>
      </div>
      <button class="add-section">+ Adicionar seção</button>
    </div>
    <div class="modal-foot">
      <span class="meta"><span id="struct-sum">172</span> / <b>240</b> linhas alocadas <span id="struct-status" class="muted">— sobram 68 para redistribuir</span></span>
      <div class="actions">
        <button class="btn-ghost" data-close>Salvar como molde</button>
        <button class="btn-secondary" data-close>Gerar outra proposta</button>
        <button class="btn-primary" data-close>Aprovar e escrever</button>
      </div>
    </div>
  `,

  sources: `
    <div class="modal-head">
      <h2>Painel de fontes</h2>
      <button class="btn-ghost" data-close>Fechar</button>
    </div>
    <div class="modal-body" style="padding:0">
      <div class="src-panel">
        <aside class="src-side">
          <div class="src-filter">
            <button class="sf active" data-filter="todas">Todas <span>5</span></button>
            <button class="sf" data-filter="duvidosa">Duvidosas <span>1</span></button>
            <button class="sf" data-filter="nao-loc">Não localizadas <span>1</span></button>
            <button class="sf" data-filter="verificada">Verificadas <span>3</span></button>
          </div>
          <table class="src-table">
            <thead><tr><th>Fonte</th><th>Tipo</th><th>Status</th><th>Citações</th></tr></thead>
            <tbody>
              <tr class="src-row selected" data-src="respe"><td>REspe nº 0600xxx-xx.2020.6.16.0000</td><td>Jurisprudência</td><td><span class="badge duvidosa">Duvidosa</span></td><td>1</td></tr>
              <tr class="src-row" data-src="blog"><td>Blog jurídico — "Tudo sobre impulsionamento"</td><td>Site</td><td><span class="badge nao-loc">Não localizada</span></td><td>0</td></tr>
              <tr class="src-row" data-src="l9504"><td>Lei nº 9.504/1997</td><td>Lei federal</td><td><span class="badge verificada">Verificada</span></td><td>3</td></tr>
              <tr class="src-row" data-src="res23610"><td>Resolução TSE nº 23.610/2019</td><td>Norma</td><td><span class="badge verificada">Verificada</span></td><td>2</td></tr>
              <tr class="src-row" data-src="l13488"><td>Lei nº 13.488/2017</td><td>Lei federal</td><td><span class="badge verificada">Verificada</span></td><td>1</td></tr>
            </tbody>
          </table>
        </aside>
        <div class="src-detail">
          <div class="sd-head">
            <div class="sd-title">REspe nº 0600xxx-xx.2020.6.16.0000</div>
            <span class="badge duvidosa">Duvidosa</span>
          </div>
          <div class="sd-block">
            <div class="sd-label">Afirmação do artigo</div>
            <blockquote class="sd-quote">O TSE manteve a cassação de mandato de vereador cujo comitê havia contratado impulsionamento em nome de pessoa física distinta do candidato.</blockquote>
          </div>
          <div class="sd-block">
            <div class="sd-label">Trecho da fonte encontrada</div>
            <blockquote class="sd-quote">— <em>Não foi possível localizar o inteiro teor com esta numeração no repositório oficial do TSE. A busca retorna acórdãos com numeração próxima, porém em matéria distinta (prestação de contas).</em></blockquote>
          </div>
          <div class="sd-block">
            <div class="sd-label">Link informado</div>
            <a href="#" class="sd-link">tse.jus.br/…/REspe-0600xxx</a>
          </div>
          <div class="sd-actions">
            <button class="btn-ghost">Rejeitar</button>
            <button class="btn-secondary">Aceitar mesmo assim</button>
            <button class="btn-primary">Buscar fonte melhor</button>
          </div>
        </div>
      </div>
    </div>
  `,

  diff: `
    <div class="modal-head">
      <h2>Comparação de versões</h2>
      <button class="btn-ghost" data-close>Fechar</button>
    </div>
    <div class="modal-body" style="padding:0">
      <div class="ver-compare">
        <div class="ver-col">
          <div class="ver-head">
            <select class="ver-sel"><option>02-redacao</option><option>01-estrutura</option></select>
            <span class="ver-meta">há 3h · redação inicial</span>
          </div>
          <div class="ver-body">
            <h3>O marco legal do impulsionamento</h3>
            <p>A Lei nº 9.504/1997 <del>autorizou</del> o impulsionamento de conteúdo eleitoral, desde que contratado por partido, coligação ou candidato.</p>
            <p><del>A vedação recai sobre o impulsionamento por terceiros.</del></p>
            <p>A Resolução TSE nº 23.610/2019 <del>trata do tema</del>.</p>
          </div>
        </div>
        <div class="ver-col">
          <div class="ver-head">
            <select class="ver-sel"><option>03-revisao</option><option>02-redacao</option></select>
            <span class="ver-meta">agora · após revisão</span>
            <button class="restore">Restaurar esta versão</button>
          </div>
          <div class="ver-body">
            <h3>O marco legal do impulsionamento</h3>
            <p>A Lei nº 9.504/1997, <ins>com a redação dada pela Lei nº 13.488/2017,</ins> <ins>autorizou expressamente</ins> o impulsionamento de conteúdo eleitoral, desde que contratado por partido, coligação ou candidato<ins>, com identificação do responsável</ins>.</p>
            <p><ins>A vedação recai sobre o impulsionamento por terceiros, prática que o Tribunal Superior Eleitoral tem tratado com rigor crescente.</ins></p>
            <p>A Resolução TSE nº 23.610/2019 <ins>regulamentou a propaganda eleitoral em rede e detalhou o que se entende por "impulsionamento"</ins>.</p>
          </div>
        </div>
      </div>
    </div>
  `
};

// -------------------------------------------------------------------
// TELAS DINÂMICAS — dependem do estado (Fechamento, Ajustes de modelos, Exportar)
// -------------------------------------------------------------------
function getChecklistItems(){
  const overSections = $$('.section').filter(sec => {
    const target = parseInt(sec.dataset.target, 10);
    let used = 0;
    $$('.paragraph', sec).forEach(p => used += measureLines(p));
    return used > target;
  }).length;

  return [
    {
      id: 'sources',
      severity: 'block',
      label: 'Fontes duvidosas ou não localizadas decididas',
      count: state.sourcesToDecide,
      ok: state.sourcesToDecide === 0,
      action: 'Ver fontes',
      goto: 'sources'
    },
    {
      id: 'red',
      severity: 'block',
      label: 'Avisos vermelhos em aberto (afirmação sem fonte)',
      count: MARGIN_NOTES.filter(n => n.kind === 'err' && !state.ignoredNotes.has(n.id)).length,
      ok: MARGIN_NOTES.filter(n => n.kind === 'err' && !state.ignoredNotes.has(n.id)).length === 0,
      action: 'Ver no artigo',
      goto: 'p2-3'
    },
    {
      id: 'diffs',
      severity: 'block',
      label: 'Sugestões de reescrita não resolvidas',
      count: state.pendingDiffs + $$('.diff.open').length,
      ok: (state.pendingDiffs + $$('.diff.open').length) === 0,
      action: 'Ver no artigo',
      goto: 'first-diff'
    },
    {
      id: 'overflow',
      severity: 'warn',
      label: 'Seções fora da meta de linhas',
      count: overSections,
      ok: overSections === 0 || state.justifiedOverflow,
      action: 'Ver seção',
      goto: 'first-over'
    }
  ];
}

const SCREENS_DYN = {
  close(){
    const items = getChecklistItems();
    const blockers = items.filter(i => i.severity === 'block' && !i.ok);
    const canFinalize = blockers.length === 0;
    const revisorCost = costOf('passada_revisor');

    return `
      <div class="modal-head">
        <h2>Fechar artigo</h2>
        <button class="btn-ghost" data-close>Cancelar</button>
      </div>

      <div class="modal-body close-body">

        <div class="close-summary">
          <div>
            <div class="cs-label">Artigo</div>
            <div class="cs-value">Impulsionamento eleitoral em redes sociais</div>
          </div>
          <div>
            <div class="cs-label">Status atual</div>
            <div class="cs-value cs-status status-${state.status}">${statusLabel(state.status)} <span class="v">${state.version}</span></div>
          </div>
        </div>

        <div class="close-section">
          <div class="cs-heading">
            <span>Checklist</span>
            <span class="cs-sub">${blockers.length === 0 ? 'Tudo verde. Pronto para finalizar.' : `${blockers.length} bloqueador${blockers.length>1?'es':''} pendente${blockers.length>1?'s':''}`}</span>
          </div>

          <ul class="check-list">
            ${items.map(item => {
              const iconMark = item.ok
                ? '<span class="ck-icon ok">✓</span>'
                : item.severity === 'block'
                  ? '<span class="ck-icon block">✕</span>'
                  : '<span class="ck-icon warn">!</span>';
              const sev = item.ok
                ? '<span class="ck-sev ok">OK</span>'
                : item.severity === 'block'
                  ? '<span class="ck-sev block">BLOQUEIA</span>'
                  : '<span class="ck-sev warn">AVISO — pode seguir</span>';
              return `
                <li class="ck-item ${item.ok ? 'ok' : item.severity}">
                  ${iconMark}
                  <div class="ck-body">
                    <div class="ck-label">${item.label}
                      ${item.count > 0 && !item.ok ? `<span class="ck-count">(${item.count})</span>` : ''}
                    </div>
                    <div class="ck-meta">
                      ${sev}
                      ${!item.ok ? `<button class="ck-link" data-goto="${item.goto}">→ ${item.action}</button>` : ''}
                    </div>
                  </div>
                </li>
              `;
            }).join('')}
          </ul>
        </div>

        <div class="close-section">
          <div class="cs-heading"><span>Ações</span></div>

          <div class="close-actions">

            <div class="ca-row">
              <div class="ca-info">
                <div class="ca-title">Passar para revisão</div>
                <div class="ca-desc">O Revisor faz uma passada completa em estilo, glossário e coerência.</div>
                <div class="ca-hint role-hint">
                  <span class="rh-dot revisor"></span>
                  Revisor · <span class="rh-model">${state.models.revisor}</span> · ~<span class="rh-cost">${fmtBRL(revisorCost)}</span>
                </div>
              </div>
              <button class="btn-secondary" data-close-act="review" ${state.status === 'final' ? 'disabled' : ''}>
                ${state.status === 'review' ? 'Já em revisão' : 'Passar para revisão'}
              </button>
            </div>

            <div class="ca-row">
              <div class="ca-info">
                <div class="ca-title">Aprovar revisão</div>
                <div class="ca-desc">Trava o artigo. Nada mais pode ser editado sem clicar em <b>Reabrir</b>.</div>
                <div class="ca-hint role-hint">
                  <span class="rh-dot det"></span>
                  Sem LLM · ~R$&nbsp;0,00
                </div>
              </div>
              <button class="btn-secondary" data-close-act="approve" ${state.status !== 'review' ? 'disabled' : ''}>
                Aprovar revisão
              </button>
            </div>

            <div class="ca-row ${canFinalize ? '' : 'disabled'}">
              <div class="ca-info">
                <div class="ca-title">Gerar versão final</div>
                <div class="ca-desc">Salva snapshot numerado no histórico. Marca o artigo como final.</div>
                ${!canFinalize
                  ? `<div class="ca-hint block-hint">${blockers.length} bloqueador${blockers.length>1?'es':''} pendente${blockers.length>1?'s':''} — resolva no checklist acima.</div>`
                  : `<div class="ca-hint role-hint"><span class="rh-dot det"></span>Sem LLM · ~R$&nbsp;0,00</div>`
                }
              </div>
              <button class="btn-primary" data-close-act="finalize" ${canFinalize ? '' : 'disabled'}>
                Gerar versão final
              </button>
            </div>

            <div class="ca-row">
              <div class="ca-info">
                <div class="ca-title">Exportar</div>
                <div class="ca-desc">PDF, DOCX ou Markdown. ${state.status !== 'final' ? 'Sai com cabeçalho <b>RASCUNHO — não citar</b>.' : 'Versão limpa, sem carimbo.'}</div>
              </div>
              <button class="btn-secondary" data-close-act="export">Exportar…</button>
            </div>

          </div>
        </div>

      </div>
    `;
  },

  modelSettings(){
    const roleRow = (roleKey) => {
      const r = ROLES[roleKey];
      const current = state.models[roleKey];
      const roleActions = Object.entries(ACTIONS).filter(([, a]) => a.role === roleKey);

      return `
        <div class="ms-role">
          <div class="ms-role-head">
            <div class="ms-role-name">
              <span class="r-dot ${roleKey}"></span>
              ${r.label}
              <span class="role-tier">· ${r.tier}</span>
            </div>
            <select class="ms-select" data-role="${roleKey}">
              ${r.availableModels.map(m => `
                <option value="${m}" ${m === current ? 'selected' : ''}>${MODEL_COST[m].label} — ${m}</option>
              `).join('')}
            </select>
          </div>
          <div class="ms-role-desc">${r.role}</div>
          <div class="ms-actions">
            <div class="ms-act-head">
              <span>Ação</span>
              <span>Com ${current}</span>
              <span>Delta</span>
            </div>
            ${roleActions.map(([k, a]) => {
              const cur = a.base * MODEL_COST[current].mult;
              // "delta" mostra vs. o modelo mais barato disponível para esse papel
              const cheapest = r.availableModels.reduce((min, m) =>
                MODEL_COST[m].mult < MODEL_COST[min].mult ? m : min, r.availableModels[0]);
              const cheapCost = a.base * MODEL_COST[cheapest].mult;
              const delta = cur - cheapCost;
              return `
                <div class="ms-act">
                  <span class="ms-a-name">${a.label}</span>
                  <span class="ms-a-cost">${fmtBRL(cur)}</span>
                  <span class="ms-a-delta ${delta > 0 ? 'up' : ''}">
                    ${delta > 0.001
                      ? `+${fmtBRL(delta)} vs. ${MODEL_COST[cheapest].label}`
                      : `— já é o mais barato`}
                  </span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    };

    return `
      <div class="modal-head">
        <h2>Ajustes de modelos</h2>
        <span class="step-info">3 papéis · Redator, Pesquisador, Revisor</span>
      </div>
      <div class="modal-body ms-body">
        <p class="modal-lede">
          Cada papel usa um modelo diferente. Trocar aqui muda o custo de todas as ações daquele papel.
          A detecção determinística é sempre grátis e não aparece nesta tela.
        </p>

        ${roleRow('redator')}
        ${roleRow('pesquisador')}
        ${roleRow('revisor')}

        <div class="ms-role ms-role-det">
          <div class="ms-role-head">
            <div class="ms-role-name">
              <span class="r-dot det"></span>
              Determinístico
              <span class="role-tier">· sem LLM</span>
            </div>
            <span class="ms-fixed">Sempre R$ 0,00</span>
          </div>
          <div class="ms-role-desc">
            Contagem de linhas, similaridade com artigos anteriores, afirmação sem fonte, glossário.
            Verificações instantâneas e gratuitas. Não usam LLM.
          </div>
        </div>

      </div>
      <div class="modal-foot">
        <span class="meta">As mudanças se aplicam imediatamente às próximas ações.</span>
        <div class="actions">
          <button class="btn-ghost" data-ms-restore>Restaurar padrões</button>
          <button class="btn-primary" data-close>Fechar</button>
        </div>
      </div>
    `;
  },

  export(){
    const rascunho = state.status !== 'final';
    return `
      <div class="modal-head">
        <h2>Exportar artigo</h2>
        <button class="btn-ghost" data-close>Fechar</button>
      </div>
      <div class="modal-body">
        ${rascunho ? `
          <div class="overlap-warn" style="background:var(--warn-soft);border-left-color:var(--warn)">
            <svg class="i i-lg" viewBox="0 0 24 24"><path d="M12 9v4m0 4h.01M4.93 19h14.14a2 2 0 001.75-2.97l-7.07-12.5a2 2 0 00-3.5 0L3.18 16.03A2 2 0 004.93 19z"/></svg>
            <div>
              <div class="ow-title">Este artigo ainda não foi finalizado.</div>
              <div class="ow-body">O arquivo exportado terá um cabeçalho <b>"RASCUNHO — não citar"</b> na primeira página.</div>
            </div>
          </div>
        ` : ''}

        <div class="export-grid">
          <button class="ex-opt" data-fmt="pdf">
            <div class="ex-icon">PDF</div>
            <div class="ex-name">PDF</div>
            <div class="ex-desc">Layout ABNT · Times 12 · entrelinha 1,5</div>
          </button>
          <button class="ex-opt" data-fmt="docx">
            <div class="ex-icon">DOCX</div>
            <div class="ex-name">Word</div>
            <div class="ex-desc">Editável, mantém estilos e comentários.</div>
          </button>
          <button class="ex-opt" data-fmt="md">
            <div class="ex-icon">MD</div>
            <div class="ex-name">Markdown</div>
            <div class="ex-desc">Texto puro, citações em footnotes.</div>
          </button>
        </div>
      </div>
    `;
  }
};

function statusLabel(s){
  return s === 'draft' ? 'Rascunho' : s === 'review' ? 'Em revisão' : 'Final';
}

// -------------------------------------------------------------------
// WIRE-UP das telas dinâmicas
// -------------------------------------------------------------------
function wireCloseArticle(){
  const modal = $('#modal');
  modal.querySelectorAll('[data-close-act]').forEach(btn => {
    btn.addEventListener('click', () => {
      const act = btn.dataset.closeAct;
      if (act === 'review'){
        state.status = 'review';
        state.pendingDiffs = 0;
        updateStatusUI();
        showToast(`Revisor (${state.models.revisor}) iniciou passada completa. Custo estimado ~${fmtBRL(costOf('passada_revisor'))}.`);
        openScreen('close'); // rerender com novo status
      } else if (act === 'approve'){
        state.status = 'final';
        bumpVersion();
        updateStatusUI();
        showToast('Revisão aprovada. Artigo travado.');
        closeModal();
      } else if (act === 'finalize'){
        state.status = 'final';
        bumpVersion();
        updateStatusUI();
        showToast(`Versão final salva no histórico: ${state.version}.`);
        closeModal();
      } else if (act === 'export'){
        openScreen('export');
      }
    });
  });
  modal.querySelectorAll('[data-goto]').forEach(a => {
    a.addEventListener('click', () => {
      const target = a.dataset.goto;
      closeModal();
      if (target === 'sources'){ openScreen('sources'); return; }
      // rola até parágrafo/aviso
      let el;
      if (target === 'first-diff'){ el = $('.diff.open'); }
      else if (target === 'first-over'){
        el = $$('.section').find(sec => {
          const target = parseInt(sec.dataset.target, 10);
          let used = 0;
          $$('.paragraph', sec).forEach(p => used += measureLines(p));
          return used > target;
        });
      } else {
        el = document.getElementById(target);
      }
      if (el){
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.animate([{ background: 'var(--warn-soft)' }, { background: 'transparent' }], { duration: 1200 });
      }
    });
  });
}

function wireModelSettings(){
  const modal = $('#modal');
  modal.querySelectorAll('.ms-select').forEach(sel => {
    sel.addEventListener('change', () => {
      const role = sel.dataset.role;
      state.models[role] = sel.value;
      renderPipeline();
      renderMarginNotes(); // hints recalculados
      // Rerender modal com novos custos
      $('#modal').innerHTML = SCREENS_DYN.modelSettings();
      wireModelSettings();
      $$('[data-close]', modal).forEach(b => b.addEventListener('click', closeModal));
    });
  });
  const restore = modal.querySelector('[data-ms-restore]');
  if (restore) restore.addEventListener('click', () => {
    Object.keys(ROLES).forEach(k => state.models[k] = ROLES[k].defaultModel);
    renderPipeline();
    renderMarginNotes();
    $('#modal').innerHTML = SCREENS_DYN.modelSettings();
    wireModelSettings();
    $$('[data-close]', modal).forEach(b => b.addEventListener('click', closeModal));
    showToast('Modelos restaurados aos padrões.');
  });
}

function wireExport(){
  const modal = $('#modal');
  modal.querySelectorAll('.ex-opt').forEach(b => b.addEventListener('click', () => {
    const fmt = b.dataset.fmt;
    showToast(`Exportando ${fmt.toUpperCase()}${state.status !== 'final' ? ' com carimbo "RASCUNHO — não citar"' : ''}…`);
    closeModal();
  }));
}

function updateStatusUI(){
  const pill = $('#status-pill');
  pill.className = `status-pill ${state.status}`;
  pill.innerHTML = statusLabel(state.status) + ` <span class="v">${state.version}</span>`;
  document.body.classList.toggle('status-final', state.status === 'final');
  const banner = $('#final-banner');
  if (banner) banner.classList.toggle('on', state.status === 'final');
}

function bumpVersion(){
  const m = /^v(\d+)$/.exec(state.version);
  const n = m ? parseInt(m[1],10) : 1;
  state.version = 'v' + (n + 1);
}

function updateChecklistCounts(){
  // Chamada quando ações mudam contadores; se o modal de fechamento estiver
  // aberto, rerender.
  if ($('.modal-back.open') && $('#modal').innerHTML.includes('Fechar artigo')){
    $('#modal').innerHTML = SCREENS_DYN.close();
    wireCloseArticle();
  }
}

// CSS adicional para telas 2-5 (injetado dinamicamente)
const MODAL_CSS = `
.fld{ display:flex; flex-direction:column; gap:4px; }
.fld-label{ font-size:11px; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-muted); }
.fld-hint{ text-transform:none; letter-spacing:0; color:var(--text-faint); font-weight:400; }
.fld-input{ height:32px; padding:0 10px; border:1px solid var(--border); border-radius:3px; background:var(--surface); font-size:13px; outline:none; color:var(--text); }
.fld-input:focus{ border-color:var(--accent-line); }
select.fld-input{ padding: 0 8px; }
.depth-cards{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:8px; }
.depth-card{ padding:14px; border:1px solid var(--border); border-radius:3px; cursor:pointer; background:var(--surface); }
.depth-card:hover{ border-color:var(--border-strong); }
.depth-card.selected, .depth-card:has(input:checked){ border-color:var(--accent); background:var(--accent-soft); }
.depth-card input{ position:absolute; opacity:0; pointer-events:none; }
.depth-card .d-title{ font-size:13px; font-weight:500; color:var(--text); margin-bottom:4px; display:flex; align-items:center; gap:8px; }
.depth-card .d-rec{ font-size:9.5px; text-transform:uppercase; letter-spacing:0.06em; padding:1px 6px; border-radius:2px; background:var(--ok-soft); color:var(--ok); font-weight:500; }
.depth-card .d-desc{ font-size:12px; color:var(--text-muted); line-height:1.4; }

.overlap-warn{ display:flex; gap:12px; padding:14px; background:var(--warn-soft); border-left:3px solid var(--warn); border-radius:3px; margin-bottom:16px; align-items:flex-start; color:var(--warn); }
.overlap-warn .ow-title{ font-weight:500; color:var(--text); margin-bottom:3px; font-size:13.5px; }
.overlap-warn .ow-body{ font-size:12.5px; color:var(--text-muted); }
.overlap-list{ display:flex; flex-direction:column; }
.overlap-item{ padding:14px 0; border-bottom:1px solid var(--border); }
.overlap-item:last-child{ border-bottom:0; }
.ol-head{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:4px; }
.ol-title{ font-family:var(--font-serif); font-size:15px; color:var(--text); font-weight:500; }
.ol-pct{ font-family:var(--font-mono); font-size:12px; color:var(--warn); }
.ol-sections{ font-size:12.5px; color:var(--text-muted); }
.ol-sections b{ color:var(--text); font-weight:500; }

.modal-lede{ font-family:var(--font-serif); font-size:13.5px; color:var(--text-muted); margin:0 0 16px; line-height:1.5; }
.struct-table{ border:1px solid var(--border); border-radius:3px; overflow:hidden; }
.struct-table .st-head, .struct-table .st-row{ display:grid; grid-template-columns:24px 1fr 80px 60px 80px; align-items:center; gap:10px; padding:8px 12px; }
.struct-table .st-head{ background:var(--surface-2); font-size:10.5px; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-muted); border-bottom:1px solid var(--border); }
.struct-table .st-row{ border-bottom:1px solid var(--border); }
.struct-table .st-row:last-child{ border-bottom:0; }
.struct-table .drag{ color:var(--text-faint); cursor:grab; font-size:16px; user-select:none; text-align:center; }
.struct-table input{ height:26px; padding:0 8px; border:1px solid transparent; border-radius:3px; background:transparent; font-size:13px; color:var(--text); outline:none; }
.struct-table input:hover{ border-color:var(--border); }
.struct-table input:focus{ border-color:var(--accent-line); background:var(--surface); }
.struct-table input[type=number]{ font-family:var(--font-mono); text-align:center; }
.struct-table .src-count{ font-family:var(--font-mono); font-size:12px; color:var(--text-muted); text-align:center; }
.struct-table .rm{ font-size:10.5px; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-faint); }
.struct-table .rm:hover{ color:var(--err); }
.add-section{ margin-top:10px; font-size:12px; color:var(--accent); padding:6px 0; }
.add-section:hover{ color:var(--accent-hover); }
.muted{ color:var(--text-faint); }
#struct-status.over{ color:var(--err); }

.src-panel{ display:grid; grid-template-columns:1fr 320px; min-height:480px; }
.src-side{ border-right:1px solid var(--border); }
.src-filter{ display:flex; gap:2px; padding:12px 14px; border-bottom:1px solid var(--border); background:var(--surface-2); }
.src-filter .sf{ padding:5px 10px; font-size:11.5px; color:var(--text-muted); border-radius:3px; display:inline-flex; align-items:center; gap:6px; }
.src-filter .sf span{ font-family:var(--font-mono); font-size:10.5px; color:var(--text-faint); }
.src-filter .sf.active{ background:var(--surface); color:var(--text); border:1px solid var(--border); }
.src-filter .sf:hover{ color:var(--text); }
.src-table{ width:100%; border-collapse:collapse; }
.src-table thead th{ text-align:left; font-weight:500; font-size:10.5px; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-muted); padding:10px 14px; border-bottom:1px solid var(--border); background:var(--surface); }
.src-table tbody td{ padding:12px 14px; border-bottom:1px solid var(--border); font-size:12.5px; color:var(--text); }
.src-table tbody tr{ cursor:pointer; }
.src-table tbody tr:hover{ background:var(--surface-2); }
.src-table tbody tr.selected{ background:var(--accent-soft); }
.src-detail{ padding:16px 18px; background:var(--surface); }
.sd-head{ display:flex; align-items:center; gap:10px; padding-bottom:12px; border-bottom:1px solid var(--border); margin-bottom:14px; }
.sd-title{ font-family:var(--font-serif); font-size:14.5px; font-weight:500; }
.sd-block{ margin-bottom:14px; }
.sd-label{ font-size:10px; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-faint); margin-bottom:5px; }
.sd-quote{ font-family:var(--font-serif); font-size:13px; margin:0; padding:8px 12px; border-left:2px solid var(--border-strong); color:var(--text); line-height:1.55; }
.sd-quote em{ color:var(--text-muted); font-style:italic; }
.sd-link{ font-family:var(--font-mono); font-size:12px; color:var(--accent); text-decoration:none; }
.sd-link:hover{ text-decoration:underline; }
.sd-actions{ display:flex; gap:6px; justify-content:flex-end; margin-top:16px; padding-top:12px; border-top:1px solid var(--border); flex-wrap:wrap; }
.sd-actions button{ white-space:nowrap; padding:0 10px; }

.ver-compare{ display:grid; grid-template-columns:1fr 1fr; min-height:480px; }
.ver-col{ display:flex; flex-direction:column; }
.ver-col:first-child{ border-right:1px solid var(--border); background:var(--bg); }
.ver-head{ padding:12px 16px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:10px; background:var(--surface); }
.ver-sel{ height:26px; padding:0 8px; border:1px solid var(--border); border-radius:3px; background:var(--surface); font-family:var(--font-mono); font-size:12px; }
.ver-meta{ font-size:11px; color:var(--text-faint); font-family:var(--font-mono); flex:1; }
.restore{ font-size:10.5px; text-transform:uppercase; letter-spacing:0.06em; color:var(--accent); font-weight:500; }
.ver-body{ padding:18px 24px; font-family:var(--font-serif); font-size:15px; line-height:1.7; color:var(--text); overflow-y:auto; }
.ver-body h3{ font-size:17px; font-weight:500; margin:0 0 14px; letter-spacing:-0.005em; }
.ver-body p{ margin:0 0 14px; }
.ver-body ins{ background:var(--ok-soft); color:#14532d; text-decoration:none; padding:0 2px; border-radius:2px; }
.ver-body del{ background:var(--err-soft); color:#7f1d1d; text-decoration:line-through; padding:0 2px; border-radius:2px; }

/* ---- Fechamento do artigo ---- */
.close-body{ padding:0; }
.close-summary{
  display:grid; grid-template-columns:1fr auto;
  gap:16px;
  padding:16px 22px;
  border-bottom:1px solid var(--border);
  background:var(--surface-2);
}
.cs-label{ font-size:10px; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-faint); margin-bottom:4px; }
.cs-value{ font-family:var(--font-serif); font-size:14.5px; color:var(--text); font-weight:500; }
.cs-value .v{ margin-left:6px; color:var(--text-faint); font-family:var(--font-mono); font-size:11px; font-weight:400; }
.cs-status{ display:inline-flex; align-items:center; gap:8px; }
.cs-status::before{ content:""; width:8px; height:8px; border-radius:50%; background:var(--text-faint); }
.cs-status.status-draft::before{ background:#a8a29e; }
.cs-status.status-review::before{ background:var(--warn); }
.cs-status.status-final::before{ background:var(--ok); }

.close-section{ padding:16px 22px; border-bottom:1px solid var(--border); }
.close-section:last-child{ border-bottom:0; }
.cs-heading{
  display:flex; justify-content:space-between; align-items:baseline;
  margin-bottom:12px;
}
.cs-heading > span:first-child{
  font-size:10.5px; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); font-weight:500;
}
.cs-heading .cs-sub{ font-size:12px; color:var(--text-muted); font-family:var(--font-mono); }

.check-list{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:0; border:1px solid var(--border); border-radius:3px; overflow:hidden; }
.ck-item{ display:grid; grid-template-columns:32px 1fr; gap:12px; align-items:start; padding:12px 14px; border-bottom:1px solid var(--border); background:var(--surface); }
.ck-item:last-child{ border-bottom:0; }
.ck-item.ok{ background:#f6fbf7; }
.ck-item.warn{ background:#fffdf5; }
.ck-item.block{ background:#fdf5f5; }
.ck-icon{ width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:600; margin-top:1px; }
.ck-icon.ok{ background:var(--ok-soft); color:var(--ok); }
.ck-icon.block{ background:var(--err-soft); color:var(--err); }
.ck-icon.warn{ background:var(--warn-soft); color:var(--warn); }
.ck-label{ font-size:13px; color:var(--text); font-weight:500; }
.ck-label .ck-count{ margin-left:6px; font-family:var(--font-mono); font-size:11.5px; color:var(--text-muted); font-weight:400; }
.ck-meta{ margin-top:4px; display:flex; align-items:center; gap:14px; }
.ck-sev{ font-size:10px; text-transform:uppercase; letter-spacing:0.06em; font-weight:500; padding:1px 6px; border-radius:2px; }
.ck-sev.ok{ color:var(--ok); background:var(--ok-soft); }
.ck-sev.block{ color:var(--err); background:var(--err-soft); }
.ck-sev.warn{ color:var(--warn); background:var(--warn-soft); }
.ck-link{ font-size:11.5px; color:var(--accent); background:none; border:0; padding:0; cursor:pointer; }
.ck-link:hover{ color:var(--accent-hover); text-decoration:underline; }

.close-actions{ display:flex; flex-direction:column; }
.ca-row{ display:grid; grid-template-columns:1fr auto; gap:16px; align-items:center; padding:14px 0; border-bottom:1px solid var(--border); }
.ca-row:last-child{ border-bottom:0; }
.ca-row.disabled .ca-title{ color:var(--text-muted); }
.ca-title{ font-size:13.5px; font-weight:500; color:var(--text); margin-bottom:2px; }
.ca-desc{ font-size:12px; color:var(--text-muted); line-height:1.45; margin-bottom:5px; }
.ca-desc b{ color:var(--text); }
.ca-hint{ font-size:11px; }
.ca-hint.block-hint{ color:var(--err); font-family:var(--font-mono); }

/* ---- Ajustes de modelos ---- */
.ms-body{ display:flex; flex-direction:column; gap:16px; }
.ms-role{ border:1px solid var(--border); border-radius:3px; padding:14px 16px; background:var(--surface); }
.ms-role.ms-role-det{ background:var(--surface-2); }
.ms-role-head{
  display:flex; justify-content:space-between; align-items:center;
  gap:12px;
  margin-bottom:6px;
}
.ms-role-name{ display:flex; align-items:center; gap:8px; font-size:14px; font-weight:500; }
.ms-select{
  height:28px; padding:0 8px;
  border:1px solid var(--border-strong); border-radius:3px;
  background:var(--surface);
  font-family:var(--font-mono); font-size:12px; color:var(--text);
  min-width:180px;
}
.ms-fixed{ font-family:var(--font-mono); font-size:12px; color:var(--ok); font-weight:500; }
.ms-role-desc{ font-family:var(--font-serif); font-style:italic; font-size:12.5px; color:var(--text-muted); line-height:1.5; margin-bottom:10px; }
.ms-actions{ border-top:1px dashed var(--border); padding-top:8px; }
.ms-act-head, .ms-act{
  display:grid; grid-template-columns:1.5fr 90px 1fr;
  gap:12px; align-items:center;
  font-size:11.5px;
}
.ms-act-head{ font-size:10px; text-transform:uppercase; letter-spacing:0.06em; color:var(--text-faint); padding:6px 0 4px; }
.ms-act{ padding:5px 0; border-top:1px solid var(--border); }
.ms-act:first-of-type{ border-top:0; }
.ms-a-name{ color:var(--text); }
.ms-a-cost{ font-family:var(--font-mono); color:var(--text); text-align:right; }
.ms-a-delta{ font-family:var(--font-mono); color:var(--text-faint); font-size:10.5px; }
.ms-a-delta.up{ color:var(--warn); }

/* ---- Export ---- */
.export-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:10px; }
.ex-opt{ padding:16px; border:1px solid var(--border); border-radius:3px; background:var(--surface); text-align:left; }
.ex-opt:hover{ border-color:var(--accent); background:var(--accent-soft); }
.ex-icon{
  display:inline-block; padding:2px 8px;
  background:var(--surface-2); color:var(--text-muted);
  font-family:var(--font-mono); font-size:10px; font-weight:600;
  border-radius:2px;
  margin-bottom:10px;
}
.ex-opt:hover .ex-icon{ background:var(--accent); color:#fff; }
.ex-name{ font-size:14px; font-weight:500; color:var(--text); margin-bottom:4px; }
.ex-desc{ font-size:11.5px; color:var(--text-muted); line-height:1.4; }
`;

function injectModalCSS(){
  if ($('#modal-css')) return;
  const style = document.createElement('style');
  style.id = 'modal-css';
  style.textContent = MODAL_CSS;
  document.head.appendChild(style);
}

function wireWizard(){
  const nextBtn = $('[data-next-wizard]');
  if (nextBtn){
    nextBtn.addEventListener('click', () => {
      const modal = $('#modal');
      modal.innerHTML = SCREENS.wizardStep2;
      modal.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', closeModal));
    });
  }
}

function wireStructure(){
  const rows = $$('.struct-table [data-lines]');
  const sum = () => {
    let total = 0;
    rows.forEach(r => total += parseInt(r.value, 10) || 0);
    $('#struct-sum').textContent = total;
    const status = $('#struct-status');
    if (total > 240){
      status.textContent = `— excede em ${total-240} linhas`;
      status.classList.add('over');
    } else if (total < 240){
      status.textContent = `— sobram ${240-total} para redistribuir`;
      status.classList.remove('over');
    } else {
      status.textContent = `— distribuição completa`;
      status.classList.remove('over');
    }
  };
  rows.forEach(r => r.addEventListener('input', sum));
  sum();
}

function wireSources(){
  $$('.src-row').forEach(r => {
    r.addEventListener('click', () => {
      $$('.src-row').forEach(x => x.classList.remove('selected'));
      r.classList.add('selected');
    });
  });
  $$('.sf').forEach(b => {
    b.addEventListener('click', () => {
      $$('.sf').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
    });
  });
}

// -------------------------------------------------------------------
// TOAST
// -------------------------------------------------------------------
function showToast(msg){
  let toast = $('#toast');
  if (!toast){
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--text);color:#fff;padding:8px 14px;border-radius:3px;font-size:12px;z-index:3000;opacity:0;transition:opacity .2s;pointer-events:none;';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { toast.style.opacity = '0'; }, 2400);
}

// -------------------------------------------------------------------
// AVISOS DE MARGEM — ações
// -------------------------------------------------------------------
function initMarginActions(){
  $('#notes-col').addEventListener('click', (e) => {
    const fix = e.target.closest('.fix');
    const ignore = e.target.closest('.ignore');
    if (fix){
      const note = fix.closest('.margin-note');
      const pid = note.dataset.pid;
      const action = fix.dataset.fixAction;
      if (action === 'buscar_fonte'){
        switchContextTab('fontes');
        showToast(`Pesquisador (${state.models.pesquisador}) buscando fonte…`);
      } else {
        openRewrite(pid);
        showToast(`Redator (${state.models.redator}) reescrevendo este par\u00e1grafo…`);
      }
      note.style.opacity = '0.5';
      return;
    }
    if (ignore){
      const note = ignore.closest('.margin-note');
      const nid = note.dataset.nid;
      state.ignoredNotes.add(nid);
      note.style.transition = 'opacity .2s, transform .2s';
      note.style.opacity = '0';
      note.style.transform = 'translateX(20px)';
      setTimeout(() => { renderMarginNotes(); updateChecklistCounts(); }, 200);
      return;
    }
  });
}

// -------------------------------------------------------------------
// TWEAKS PROTOCOL
// -------------------------------------------------------------------
function initTweaks(){
  const tweaks = $('#tweaks');
  const values = { ...window.__tweaks };

  function apply(){
    document.documentElement.dataset.accent = values.accent;
    document.documentElement.dataset.typography = values.typography;
    document.documentElement.dataset.rewriteVariant = values.rewriteVariant;
    // reflete no UI
    $$('.tweak-options').forEach(g => {
      const key = g.dataset.tweak;
      $$('.tweak-opt', g).forEach(o => o.classList.toggle('active', o.dataset.val === values[key]));
    });
    // Aplica variante do balão (CSS já ancorado; overlay/lateral são ajustes)
    applyRewriteVariant(values.rewriteVariant);
  }

  // Listeners para o protocolo do host
  window.addEventListener('message', (e) => {
    const d = e.data || {};
    if (d.type === '__activate_edit_mode'){ tweaks.classList.add('open'); }
    else if (d.type === '__deactivate_edit_mode'){ tweaks.classList.remove('open'); }
  });

  // Anuncia disponibilidade
  try{
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
  } catch(_){}

  // Fechar
  $('#tweaks-close').addEventListener('click', () => tweaks.classList.remove('open'));

  // Trocar valor
  $$('.tweak-options').forEach(g => {
    g.addEventListener('click', (e) => {
      const opt = e.target.closest('.tweak-opt');
      if (!opt) return;
      const key = g.dataset.tweak;
      values[key] = opt.dataset.val;
      apply();
      try{
        window.parent.postMessage({ type: '__edit_mode_set_keys', edits: { [key]: opt.dataset.val } }, '*');
      } catch(_){}
    });
  });

  apply();
}

function applyRewriteVariant(v){
  // Injeta ajustes de estilo via classe no body
  document.body.classList.remove('rw-anchored', 'rw-side', 'rw-overlay');
  document.body.classList.add('rw-' + v);
}

// Estilos extras para as variantes do balão de reescrita
const REWRITE_VARIANT_CSS = `
/* Lateral: encaixa à direita, mais estreito */
body.rw-side .rewrite{
  position:absolute; right:-260px; top:0; width:240px;
  margin:0;
}
body.rw-side .rewrite::before{ left: -6px; top: 16px; transform: rotate(-45deg); }
body.rw-side .paragraph.selected{ position: relative; }

/* Overlay: sobre o parágrafo, com fundo semitransparente */
body.rw-overlay .paragraph.selected + .rewrite,
body.rw-overlay .rewrite.open{
  position:absolute; left:0; right:0; top:0;
  margin:0;
  background:var(--surface);
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}
body.rw-overlay .rewrite::before{ display:none; }
body.rw-overlay .paragraph.selected{ position:relative; }
body.rw-overlay .paragraph.selected .p-text{ opacity:0.15; }
`;
const rvStyle = document.createElement('style');
rvStyle.textContent = REWRITE_VARIANT_CSS;
document.head.appendChild(rvStyle);

// -------------------------------------------------------------------
// BOOT
// -------------------------------------------------------------------
function setAppHeight(){
  const app = document.querySelector('.app');
  if (!app) return;
  let h = window.innerHeight;
  if (!h || h < 200){
    // preview iframe pode reportar 0 — usa altura do parent frame ou fallback
    try {
      h = window.parent.innerHeight || document.documentElement.getBoundingClientRect().height;
    } catch(_){}
    if (!h || h < 200) h = 900;
  }
  app.style.height = h + 'px';
}

function boot(){
  setAppHeight();
  window.addEventListener('resize', setAppHeight);
  // Poll a cada 500ms caso o iframe cresça mais tarde
  let pollTries = 0;
  const poll = setInterval(() => {
    setAppHeight();
    if (++pollTries > 20) clearInterval(poll);
  }, 500);

  renderRuler();
  renderDoc();
  renderMarginNotes();
  renderPipeline();
  initParagraphInteractions();
  initTabs();
  initSidebar();
  initScreens();
  initMarginActions();
  injectModalCSS();
  initTweaks();

  // primeira medição — precisa de fontes carregadas
  const doMeasure = () => {
    $$('.section').forEach(s => updateSectionLines(s));
    syncRuler();
    positionMarginNotes();
  };
  doMeasure();

  // remede quando as web-fonts terminam
  if (document.fonts && document.fonts.ready){
    document.fonts.ready.then(doMeasure);
  }

  // resposta a resize
  let rt;
  window.addEventListener('resize', () => {
    clearTimeout(rt);
    rt = setTimeout(doMeasure, 100);
  });
}

if (document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
