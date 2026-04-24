// ENEL Severidade — app principal
(function(){
  'use strict';

  const DATA = window.ENEL_DATA;
  const $ = (s, el=document) => el.querySelector(s);
  const $$ = (s, el=document) => [...el.querySelectorAll(s)];

  // ─────────────────────────────────────────────────────────
  // State
  // ─────────────────────────────────────────────────────────
  const state = {
    screen: 'alta',
    tweaks: { ...(window.TWEAK_DEFAULTS || {}) },
    filter: { category: null, causaId: null },
    sort: { key: 'reinc', dir: 'desc' },
    openDesc: null,
  };

  // ─────────────────────────────────────────────────────────
  // Utils
  // ─────────────────────────────────────────────────────────
  const fmtN = n => n.toLocaleString('pt-BR');
  const fmtMoney = n => 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtPct = n => n.toFixed(1).replace('.', ',') + '%';

  const tt = $('#tt');
  function showTT(e, html){
    tt.innerHTML = html;
    tt.classList.add('is-on');
    const pad = 14;
    const w = tt.offsetWidth, h = tt.offsetHeight;
    let x = e.clientX + pad, y = e.clientY + pad;
    if (x + w > innerWidth) x = e.clientX - w - pad;
    if (y + h > innerHeight) y = e.clientY - h - pad;
    tt.style.left = x + 'px';
    tt.style.top = y + 'px';
  }
  function hideTT(){ tt.classList.remove('is-on'); }

  function sparkPath(values, w, h){
    if (!values || !values.length) return '';
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const range = Math.max(max - min, 1);
    return values.map((v,i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return (i===0?'M':'L') + x.toFixed(1) + ',' + y.toFixed(1);
    }).join(' ');
  }

  // ─────────────────────────────────────────────────────────
  // Chart renderers (SVG, no lib)
  // ─────────────────────────────────────────────────────────

  function renderVolumeBars(container, mesesData, values, sevLabel){
    const W = container.clientWidth || 640;
    const H = 320;
    const M = { t: 24, r: 16, b: 40, l: 48 };
    const iw = W - M.l - M.r;
    const ih = H - M.t - M.b;
    const max = Math.max(...values);
    const yMax = Math.ceil(max / 50) * 50 + 50;
    const bw = iw / values.length * 0.64;
    const gap = iw / values.length * 0.36;

    const grids = [0, 0.25, 0.5, 0.75, 1].map(p => {
      const v = yMax * p;
      const y = M.t + ih - (v / yMax) * ih;
      return `<line class="grid-line" x1="${M.l}" x2="${W - M.r}" y1="${y}" y2="${y}"/>
              <text x="${M.l - 8}" y="${y + 3}" text-anchor="end">${fmtN(Math.round(v))}</text>`;
    }).join('');

    const bars = values.map((v, i) => {
      const bh = (v / yMax) * ih;
      const x = M.l + i * (bw + gap) + gap/2;
      const y = M.t + ih - bh;
      return `<rect class="bar" x="${x}" y="${y}" width="${bw}" height="${bh}" rx="3"
        fill="url(#barGrad)" data-idx="${i}" data-val="${v}" data-label="${mesesData[i]}"/>
        <text class="bar-label" x="${x + bw/2}" y="${y - 6}" text-anchor="middle">${fmtN(v)}</text>`;
    }).join('');

    const xLabels = mesesData.map((m, i) => {
      const x = M.l + i * (bw + gap) + gap/2 + bw/2;
      return `<text x="${x}" y="${H - M.b + 18}" text-anchor="middle">${m}</text>`;
    }).join('');

    container.innerHTML = `
      <svg class="chart-svg" viewBox="0 0 ${W} ${H}">
        <defs>
          <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--sev-primary)" stop-opacity="0.95"/>
            <stop offset="100%" stop-color="var(--sev-secondary)" stop-opacity="0.70"/>
          </linearGradient>
        </defs>
        ${grids}
        ${bars}
        ${xLabels}
        <line class="axis-line" x1="${M.l}" x2="${W - M.r}" y1="${M.t + ih}" y2="${M.t + ih}"/>
      </svg>`;

    $$('.bar', container).forEach(el => {
      el.addEventListener('mousemove', e => {
        const v = el.dataset.val, l = el.dataset.label;
        showTT(e, `<div class="tt-label">${l} · ${sevLabel}</div>
          <div class="tt-val">${fmtN(+v)}</div>
          <div class="tt-row"><span>reclamações no mês</span></div>`);
      });
      el.addEventListener('mouseleave', hideTT);
    });
  }

  function renderHBars(container, categorias, onClick){
    const max = Math.max(...categorias.map(c => c.vol));
    container.innerHTML = `<div class="hbar-list">${categorias.map(c => {
      const w = (c.vol / max * 100).toFixed(1);
      const active = state.filter.category === c.id ? 'is-active' : '';
      return `<div class="hbar-row ${active}" data-id="${c.id}" data-name="${c.nome}" data-vol="${c.vol}" data-pct="${c.pct}">
        <div class="hbar-name" title="${c.nome}">${c.nome}</div>
        <div class="hbar-track"><div class="hbar-fill" style="width:${w}%"></div></div>
        <div class="hbar-val">${fmtN(c.vol)}</div>
        <div class="hbar-pct">${c.pct.toFixed(1)}%</div>
      </div>`;
    }).join('')}</div>`;

    $$('.hbar-row', container).forEach(row => {
      row.addEventListener('mousemove', e => {
        showTT(e, `<div class="tt-label">${row.dataset.name}</div>
          <div class="tt-val">${fmtN(+row.dataset.vol)}</div>
          <div class="tt-row"><span>% do total</span><b>${(+row.dataset.pct).toFixed(1)}%</b></div>`);
      });
      row.addEventListener('mouseleave', hideTT);
      row.addEventListener('click', () => onClick(row.dataset.id));
    });
  }

  function renderScatter(container, causas, onClick){
    const W = container.clientWidth || 640;
    const H = 340;
    const M = { t: 20, r: 24, b: 52, l: 56 };
    const iw = W - M.l - M.r;
    const ih = H - M.t - M.b;
    const xMax = Math.max(...causas.map(c => c.vol));
    const xMaxRound = Math.ceil(xMax / 100) * 100;
    const yMax = 100;
    const rMax = Math.max(...causas.map(c => c.reinc));

    const CAT_COLORS = {
      operacional: 'var(--terra)',
      estimativa: 'var(--amber-deep)',
      medidor: 'var(--plum)',
      cadastral: 'var(--sage)',
      tarifa: 'var(--ocean)',
      fraude: 'var(--wine)',
      faturamento: 'var(--terra-deep)',
      juridico: 'var(--plum-deep)',
      rede: 'var(--amber)',
      social: 'var(--sage)',
    };

    const gridsY = [0, 25, 50, 75, 100].map(p => {
      const y = M.t + ih - (p/yMax) * ih;
      return `<line class="grid-line" x1="${M.l}" x2="${W - M.r}" y1="${y}" y2="${y}"/>
              <text x="${M.l - 8}" y="${y + 3}" text-anchor="end">${p}%</text>`;
    }).join('');

    const gridsX = 5;
    const gx = Array.from({length: gridsX + 1}, (_, i) => {
      const v = (xMaxRound / gridsX) * i;
      const x = M.l + (v / xMaxRound) * iw;
      return `<text x="${x}" y="${H - M.b + 18}" text-anchor="middle">${fmtN(Math.round(v))}</text>`;
    }).join('');

    // quadrant divider
    const midX = M.l + iw/2;
    const midY = M.t + ih/2;

    const circles = causas.map(c => {
      const cx = M.l + (c.vol / xMaxRound) * iw;
      const cy = M.t + ih - (c.proc / yMax) * ih;
      const r = 6 + (c.reinc / rMax) * 22;
      const color = CAT_COLORS[c.cat] || 'var(--sev-primary)';
      const active = state.filter.causaId === c.id;
      return `<circle cx="${cx}" cy="${cy}" r="${r}"
        fill="${color}" fill-opacity="${active?0.9:0.52}"
        stroke="${color}" stroke-width="${active?2:1.25}"
        data-id="${c.id}" data-name="${c.nome}" data-vol="${c.vol}" data-proc="${c.proc}" data-reinc="${c.reinc}" data-cat="${c.cat}"/>
        <text x="${cx}" y="${cy - r - 5}" text-anchor="middle" fill="var(--ink-2)" style="font-size:10px;font-family:var(--f-sans);font-weight:500">${c.nome.length > 22 ? c.nome.slice(0, 22)+'…' : c.nome}</text>`;
    }).join('');

    container.innerHTML = `
      <svg class="chart-svg scatter-svg" viewBox="0 0 ${W} ${H}">
        ${gridsY}
        ${gx}
        <line class="grid-line" x1="${midX}" x2="${midX}" y1="${M.t}" y2="${M.t + ih}" stroke-dasharray="1 4" opacity="0.6"/>
        <line class="grid-line" x1="${M.l}" x2="${W-M.r}" y1="${midY}" y2="${midY}" stroke-dasharray="1 4" opacity="0.6"/>
        <text class="quadrant-label" x="${W - M.r - 4}" y="${M.t + 14}" text-anchor="end">alto vol · alta proc.</text>
        <text class="quadrant-label" x="${M.l + 4}" y="${M.t + 14}">baixo vol · alta proc.</text>
        <text class="quadrant-label" x="${W - M.r - 4}" y="${M.t + ih - 6}" text-anchor="end">alto vol · baixa proc.</text>
        <text class="quadrant-label" x="${M.l + 4}" y="${M.t + ih - 6}">baixo vol · baixa proc.</text>
        <line class="axis-line" x1="${M.l}" x2="${W - M.r}" y1="${M.t + ih}" y2="${M.t + ih}"/>
        <line class="axis-line" x1="${M.l}" x2="${M.l}" y1="${M.t}" y2="${M.t + ih}"/>
        <text x="${M.l - 40}" y="${M.t + ih/2}" transform="rotate(-90, ${M.l - 40}, ${M.t + ih/2})" text-anchor="middle" style="font-size:10.5px">% procedência →</text>
        <text x="${M.l + iw/2}" y="${H - 6}" text-anchor="middle" style="font-size:10.5px">volume de ordens →</text>
        ${circles}
      </svg>`;

    const cats = [...new Set(causas.map(c=>c.cat))];
    const legend = document.createElement('div');
    legend.className = 'scatter-legend';
    legend.innerHTML = cats.map(cat => `<span><span class="dot" style="background:${CAT_COLORS[cat]||'var(--sev-primary)'}"></span>${cat}</span>`).join('')
      + `<span style="margin-left:12px;color:var(--ink-faint)">tamanho do círculo = reincidências</span>`;
    container.appendChild(legend);

    $$('circle', container).forEach(el => {
      el.addEventListener('mousemove', e => {
        showTT(e, `<div class="tt-label">causa canônica</div>
          <div class="tt-val">${el.dataset.name}</div>
          <div class="tt-row"><span>volume</span><b>${fmtN(+el.dataset.vol)}</b></div>
          <div class="tt-row"><span>procedência</span><b>${(+el.dataset.proc).toFixed(1)}%</b></div>
          <div class="tt-row"><span>reincidências</span><b>${fmtN(+el.dataset.reinc)}</b></div>
          <div class="tt-row"><span>categoria</span><b>${el.dataset.cat}</b></div>`);
      });
      el.addEventListener('mouseleave', hideTT);
      el.addEventListener('click', () => onClick(el.dataset.id));
    });
  }

  // ─────────────────────────────────────────────────────────
  // Page templates
  // ─────────────────────────────────────────────────────────

  function pageExecutivo(){
    const d = DATA.executivo;
    const sevDist = d.sev_total;
    const sevTotal = sevDist.critica + sevDist.alta + sevDist.medium + sevDist.low;
    return `
      <section class="screen is-on" data-screen-label="01 Executivo">
        <div class="hero" data-sev="executivo" style="--sev-primary:var(--terra-deep);--sev-secondary:var(--plum);--sev-wash:var(--warm-wash);--sev-soft:oklch(60% 0.17 28/.14);--sev-gradient:linear-gradient(135deg,var(--terra),var(--plum))">
          <div class="hero-grid">
            <div>
              <div class="eyebrow">MIS · Executivo · ABR 2026</div>
              <h1>Volume, cobertura e <em>severidade</em> por região</h1>
              <p class="hero-lede">Visão cruzada de <b>17.057 ordens</b> de erro de leitura nos últimos 12 meses. Refaturamento concentra 54,9% do volume. A severidade <b>crítica</b> representa apenas 8,2% mas responde por <b>78% do valor financeiro reclamado</b>.</p>
            </div>
            <div class="hero-metric">
              <div class="mini">Ordens · últimos 12m</div>
              <div class="big">${fmtN(d.total_ordens)}</div>
              <div class="delta">↑ 54,9% vs. ano anterior</div>
            </div>
          </div>
        </div>

        <div class="kpis">
          <div class="kpi">
            <div class="kpi-head"><span class="kpi-label">Reclamações CE</span><span class="kpi-tag">12m</span></div>
            <div class="kpi-val">${fmtN(d.reclamacoes_ce)}</div>
            <div class="kpi-sub"><span class="d-up">↑ 18,2%</span> · 131.809 inst. únicas</div>
          </div>
          <div class="kpi">
            <div class="kpi-head"><span class="kpi-label">Reincidentes</span><span class="kpi-tag">≥ 2 ordens</span></div>
            <div class="kpi-val">${fmtN(d.reincidentes)}</div>
            <div class="kpi-sub"><span class="d-up">↑ 6,1%</span> · 17,6% do total</div>
          </div>
          <div class="kpi dominant">
            <div class="kpi-head"><span class="kpi-label">Tema dominante</span><span class="kpi-tag">IA+regra</span></div>
            <div class="kpi-val sm" style="color:var(--terra-deep)">${d.tema_dominante}</div>
            <div class="kpi-sub">54,9% · 91.891 ordens</div>
          </div>
          <div class="kpi">
            <div class="kpi-head"><span class="kpi-label">Causa #1</span><span class="kpi-tag">canônica</span></div>
            <div class="kpi-val sm">${d.causa_dominante}</div>
            <div class="kpi-sub">4.974 ordens · 29% op.</div>
          </div>
          <div class="kpi">
            <div class="kpi-head"><span class="kpi-label">Cobertura rótulo</span><span class="kpi-tag">nl</span></div>
            <div class="kpi-val">87,3%</div>
            <div class="kpi-sub"><span class="d-up">↑ 4,1 pp</span> · meta 90%</div>
          </div>
        </div>

        <div class="story">
          <div class="story-icon">?</div>
          <div class="story-body">
            <span class="lead">Onde está o volume — e onde ele pesa?</span>
            Regiões com maior <b>volume absoluto</b> nem sempre são as mais críticas. Cruze a taxa de refaturamento e o share de severidade <b>crítica</b> para priorizar revisão. As páginas de severidade aprofundam cada faixa.
            <div class="story-steps">
              <div class="story-step"><span class="n">→</span>Abra <b>Severidade Alta</b> para ver o fluxo operacional</div>
              <div class="story-step"><span class="n">→</span>Abra <b>Severidade Crítica</b> para casos de maior impacto</div>
            </div>
          </div>
        </div>

        <div class="grid-2">
          <div class="card">
            <div class="c-head">
              <div>
                <div class="c-title">Volume mensal · todas severidades</div>
                <div class="c-sub">Série histórica 12 meses · base dataset 15e753a</div>
              </div>
            </div>
            <div id="execVolume"></div>
          </div>

          <div class="card">
            <div class="c-head">
              <div>
                <div class="c-title">Distribuição por severidade</div>
                <div class="c-sub">Participação do volume total</div>
              </div>
            </div>
            <div style="display:grid;gap:14px;padding:12px 4px">
              ${[
                ['Crítica', sevDist.critica, 'var(--plum)', 'critica'],
                ['Alta', sevDist.alta, 'var(--amber-deep)', 'alta'],
                ['Média', sevDist.medium, 'var(--sage)', 'medium'],
                ['Baixa', sevDist.low, 'var(--ink-faint)', 'low'],
              ].map(([name, v, c, cls]) => {
                const pct = (v/sevTotal*100).toFixed(1);
                const w = (v/sevTotal*100).toFixed(1);
                const clickable = cls === 'alta' || cls === 'critica';
                return `<div class="sev-dist-row" data-sev="${cls}" style="display:grid;grid-template-columns:90px 1fr 64px 50px;gap:12px;align-items:center;${clickable?'cursor:pointer;':''}">
                  <div style="font-size:12.5px;color:var(--ink);font-weight:500">${name}${clickable?' →':''}</div>
                  <div style="height:26px;background:var(--paper-3);border-radius:4px;overflow:hidden">
                    <div style="height:100%;background:${c};width:${w}%;border-radius:4px;transition:width .5s var(--ease)"></div>
                  </div>
                  <div style="font-family:var(--f-mono);font-size:12.5px;color:var(--ink);text-align:right;font-weight:600">${fmtN(v)}</div>
                  <div style="font-family:var(--f-mono);font-size:11px;color:var(--ink-3);text-align:right">${pct}%</div>
                </div>`;
              }).join('')}
            </div>
          </div>
        </div>
      </section>`;
  }

  function pageSeveridade(key){
    const d = DATA[key];
    const label = key === 'alta' ? 'Alta' : 'Crítica';
    const sevPrimary = key === 'alta' ? 'var(--amber-deep)' : 'var(--plum)';
    const pctProc = (d.procedentes / d.total * 100);
    const urgency = key === 'critica' ? `
      <div class="urgency-strip">
        <span class="tick">ATENÇÃO</span>
        <span><b>Severidade Crítica</b> concentra apenas <b>8,2% do volume</b>, mas <b>R$ ${fmtN(Math.round(d.procedentes * d.valor_medio_fatura))}</b> em valor reclamado procedente. Impacto desproporcional — priorização imediata.</span>
      </div>` : '';

    return `
      <section class="screen is-on" data-screen-label="${key==='alta'?'02 Severidade Alta':'03 Severidade Critica'}" data-sev="${key}">

        <div class="hero">
          <div class="hero-grid">
            <div>
              <div class="eyebrow">MIS · Severidade ${label} · leitura executiva</div>
              <h1>${key==='alta'
                ? `Pressão operacional <em>contida</em>, mas em <em>aceleração</em>.`
                : `Baixo volume, <em>alto impacto financeiro</em>.`}</h1>
              <p class="hero-lede">${key==='alta'
                ? `<b>${fmtN(d.total)}</b> reclamações de severidade <b>alta</b> em 12 meses, distribuídas em <b>${d.categorias_count} categorias</b>. ${fmtPct(pctProc)} confirmadas como procedentes, com valor médio de <b>${fmtMoney(d.valor_medio_fatura)}</b>. Tendência: pico em jan/26, arrefecendo em mar/26.`
                : `<b>${fmtN(d.total)}</b> ocorrências <b>críticas</b>, ${fmtPct(pctProc)} procedentes. Valor médio reclamado <b>5,8×</b> acima da média geral. Concentração em fraude, medidores queimados e faturas anômalas — exige resposta operacional e jurídica coordenada.`}
              </p>
              ${urgency}
            </div>
            <div class="hero-metric">
              <div class="mini">Total de reclamações · ${label}</div>
              <div class="big" id="hero-big">${fmtN(d.total)}</div>
              <div class="delta">${key==='alta'?'↑ 12,4% vs. trimestre anterior':'↑ 31,7% vs. trimestre anterior'}</div>
            </div>
          </div>
        </div>

        <div class="kpis">
          <div class="kpi dominant">
            <div class="kpi-head"><span class="kpi-label">Total ${label}</span><span class="kpi-tag">12m</span></div>
            <div class="kpi-val" style="color:${sevPrimary}">${fmtN(d.total)}</div>
            <div class="kpi-sub"><span class="d-up">${key==='alta'?'↑ 12,4%':'↑ 31,7%'}</span> · ${fmtPct(d.total/DATA.executivo.total_ordens*100)} do universo</div>
          </div>
          <div class="kpi">
            <div class="kpi-head"><span class="kpi-label">Categorias</span><span class="kpi-tag">taxonomia</span></div>
            <div class="kpi-val">${d.categorias_count}</div>
            <div class="kpi-sub">top-3 = ${((d.categorias[0].pct + d.categorias[1].pct + d.categorias[2].pct)).toFixed(1)}% do vol.</div>
          </div>
          <div class="kpi">
            <div class="kpi-head"><span class="kpi-label">Procedência</span><span class="kpi-tag">proc/improc</span></div>
            <div class="kpi-split">
              <div class="col proc">
                <div class="tiny">procedentes</div>
                <div class="num">${fmtN(d.procedentes)}</div>
                <div class="pct">${fmtPct(pctProc)}</div>
              </div>
              <div class="col improc">
                <div class="tiny">improcedentes</div>
                <div class="num">${fmtN(d.improcedentes)}</div>
                <div class="pct">${fmtPct(100-pctProc)}</div>
              </div>
            </div>
            <div class="kpi-mini-bar"><span style="width:${pctProc}%"></span></div>
          </div>
          <div class="kpi">
            <div class="kpi-head"><span class="kpi-label">Clientes reincidentes</span><span class="kpi-tag">≥ 2 ord.</span></div>
            <div class="kpi-val">${fmtN(d.reincidentes_clientes)}</div>
            <div class="kpi-sub">${fmtPct(d.reincidentes_clientes/d.total*100)} · ver ranking abaixo</div>
          </div>
          <div class="kpi">
            <div class="kpi-head"><span class="kpi-label">Valor médio fatura</span><span class="kpi-tag">procedentes</span></div>
            <div class="kpi-val">${fmtMoney(d.valor_medio_fatura)}</div>
            <div class="kpi-sub">total reclamado ${fmtMoney(d.procedentes*d.valor_medio_fatura)}</div>
          </div>
        </div>

        <div class="story">
          <div class="story-icon">${key==='alta'?'◆':'●'}</div>
          <div class="story-body">
            <span class="lead">${key==='alta'
              ? 'O que a severidade alta diz ao operacional?'
              : 'Por que a severidade crítica muda a prioridade?'}</span>
            ${key==='alta'
              ? `Concentração em <b>estimativa prolongada</b> e <b>digitação</b>. Quadrante "alto volume × alta procedência" sinaliza <b>ajuste de processo</b>, não auditoria individual. A curva mensal atinge pico em janeiro e arrefece — padrão sazonal confirmado.`
              : `Apesar do volume menor, cada caso tem valor médio <b>R$ ${fmtN(Math.round(d.valor_medio_fatura))}</b> e risco reputacional elevado. Fraude confirmada e corte indevido são as duas causas que mais exigem escalonamento.`}
            <div class="story-steps">
              <div class="story-step"><span class="n">1</span>Analise a sazonalidade mensal</div>
              <div class="story-step"><span class="n">2</span>Confronte categoria × causa canônica</div>
              <div class="story-step"><span class="n">3</span>Priorize instalações do ranking</div>
            </div>
          </div>
        </div>

        <div class="grid-12">
          <div class="card col-7">
            <div class="c-head">
              <div>
                <div class="c-title">Volume de reclamações · ${label} · mês × ano</div>
                <div class="c-sub">Série mensal 12m · hover para detalhes · pico em ${key==='alta'?'jan/26 (552 ord.)':'jan/26 (188 ord.)'}</div>
              </div>
              <div class="c-actions">
                <button class="c-btn is-on">mensal</button>
                <button class="c-btn">trimestral</button>
              </div>
            </div>
            <div id="volumeChart" style="min-height:320px"></div>
          </div>

          <div class="card col-5">
            <div class="c-head">
              <div>
                <div class="c-title">Categorias identificadas</div>
                <div class="c-sub">Clique para cross-filtrar ranking e tabela</div>
              </div>
            </div>
            <div id="categoriasChart"></div>
            <div class="insight-box">
              <b>Insight:</b> As ${key==='alta'?'3':'2'} primeiras categorias respondem por <b>${((d.categorias[0].pct + d.categorias[1].pct + (d.categorias[2]?.pct||0)).toFixed(1))}%</b> do volume ${label.toLowerCase()}.
              ${state.filter.category ? `Filtro ativo: <b>${d.categorias.find(c=>c.id===state.filter.category)?.nome}</b>. <a href="#" id="clearFilter" style="color:var(--sev-primary);text-decoration:underline;margin-left:6px">limpar</a>` : ''}
            </div>
          </div>
        </div>

        <div class="card">
          <div class="c-head">
            <div>
              <div class="c-title">Causas canônicas · dispersão</div>
              <div class="c-sub">X: volume de ordens · Y: % de procedência · tamanho: nº de reincidências · cor: categoria técnica · clique para filtrar</div>
            </div>
          </div>
          <div id="scatterChart" class="scatter-wrap" style="min-height:360px"></div>
        </div>

        <div class="card" style="margin-top:18px">
          <div class="c-head">
            <div>
              <div class="c-title">Descrições identificadas pelo assistente</div>
              <div class="c-sub">Somente severidade ${label.toLowerCase()} · expandir linha para ver análise e sugestão de ação</div>
            </div>
            <div class="c-actions">
              <button class="c-btn is-on">todas</button>
              <button class="c-btn">procedentes</button>
              <button class="c-btn">improcedentes</button>
            </div>
          </div>
          <table class="desc-table"><thead>
            <tr>
              <th style="width:140px">ID</th>
              <th>Categoria · causa canônica</th>
              <th style="width:100px">Data</th>
              <th style="width:110px">Status</th>
              <th style="width:120px" class="num">Valor fatura</th>
              <th style="width:28px"></th>
            </tr>
          </thead><tbody id="descBody"></tbody></table>
        </div>

        <div class="card" style="margin-top:18px">
          <div class="c-head">
            <div>
              <div class="c-title">Ranking · Top 10 instalações reincidentes</div>
              <div class="c-sub">Ordenado por reincidência ${label.toLowerCase()} · categoria predominante e causa canônica associada · clique em coluna para ordenar</div>
            </div>
            <div class="c-actions">
              <button class="c-btn ${state.tweaks.ranking_style==='table'?'is-on':''}" data-rs="table">tabela</button>
              <button class="c-btn ${state.tweaks.ranking_style==='cards'?'is-on':''}" data-rs="cards">cards</button>
            </div>
          </div>
          <div id="rankingWrap"></div>
        </div>
      </section>`;
  }

  // Render descriptions table body (filterable)
  function renderDescBody(key){
    const d = DATA[key];
    let rows = d.descricoes;
    if (state.filter.category) {
      const catName = d.categorias.find(c=>c.id===state.filter.category)?.nome;
      if (catName) rows = rows.filter(r => r.cat.toLowerCase().includes(catName.toLowerCase().slice(0,12)));
    }
    if (state.filter.causaId) {
      const causaName = d.causas.find(c=>c.id===state.filter.causaId)?.nome;
      if (causaName) rows = rows.filter(r => r.causa.toLowerCase().includes(causaName.toLowerCase().slice(0,10)));
    }
    if (!rows.length) rows = d.descricoes.slice(0,3);

    const body = $('#descBody');
    if (!body) return;
    body.innerHTML = rows.map(r => {
      const isOpen = state.openDesc === r.id;
      return `<tr class="desc-row ${isOpen?'is-open':''}" data-id="${r.id}">
          <td><span class="id">${r.id}</span></td>
          <td>
            <div class="cat">${r.cat}</div>
            <div style="font-size:11.5px;color:var(--ink-3);font-family:var(--f-mono);margin-top:3px">${r.causa}</div>
          </td>
          <td class="mono" style="font-size:11.5px;color:var(--ink-3)">${r.data}</td>
          <td><span class="tag ${r.proc?'proc':'improc'}">${r.proc?'procedente':'improcedente'}</span></td>
          <td class="mono num" style="font-weight:600;color:var(--ink)">${fmtMoney(r.valor)}</td>
          <td class="chevron" style="font-size:12px">▶</td>
        </tr>
        ${isOpen ? `<tr class="desc-detail"><td colspan="6">
          <div class="desc-detail">
            <div class="detail-quote">"${r.resumo}"</div>
            <div class="detail-grid" style="margin-top:14px">
              <div class="detail-block">
                <div class="detail-label">Ação sugerida (IA)</div>
                <div class="detail-value">${r.sugestao}</div>
              </div>
              <div class="detail-block">
                <div class="detail-label">Área responsável</div>
                <div class="detail-value">${r.area}</div>
              </div>
              <div class="detail-block">
                <div class="detail-label">Causa · categoria</div>
                <div class="detail-value">${r.causa} · <span style="color:var(--ink-3)">${r.cat}</span></div>
              </div>
            </div>
          </div>
        </td></tr>` : ''}`;
    }).join('');

    $$('.desc-row', body).forEach(row => {
      row.addEventListener('click', () => {
        state.openDesc = state.openDesc === row.dataset.id ? null : row.dataset.id;
        renderDescBody(key);
      });
    });
  }

  function renderRanking(key){
    const d = DATA[key];
    let rows = [...d.ranking];
    // filter by category if active
    if (state.filter.category) {
      const catName = d.categorias.find(c=>c.id===state.filter.category)?.nome;
      if (catName) {
        const first = catName.split(' ')[0].toLowerCase();
        rows = rows.filter(r => r.cat.toLowerCase().includes(first.slice(0,6)));
        if (!rows.length) rows = [...d.ranking];
      }
    }
    const dir = state.sort.dir === 'asc' ? 1 : -1;
    const key2 = state.sort.key;
    rows.sort((a,b) => {
      if (typeof a[key2] === 'number') return (a[key2]-b[key2])*dir;
      return String(a[key2]).localeCompare(String(b[key2]))*dir;
    });

    const wrap = $('#rankingWrap');
    if (!wrap) return;

    if (state.tweaks.ranking_style === 'cards') {
      wrap.innerHTML = `<div class="rank-cards-wrap">${rows.map((r, i) => {
        const top = i < 3 ? 'top-3' : '';
        return `<div class="rank-card ${top}">
          <div class="pos-lg">${i+1}</div>
          <div class="meta">
            <div class="meta-inst">${r.inst} <span style="color:var(--ink-3);font-weight:400">· ${r.cidade}</span></div>
            <div class="meta-sub"><b>${r.cat}</b> · causa: <span style="font-family:var(--f-mono);color:var(--ink-2)">${r.causa}</span></div>
          </div>
          <div style="text-align:right">
            <div class="reinc-badge">${r.reinc}× reinc.</div>
          </div>
          <div style="text-align:right;min-width:100px">
            <div style="font-family:var(--f-mono);font-size:11px;color:var(--ink-3);letter-spacing:.06em;text-transform:uppercase">fatura</div>
            <div style="font-family:var(--f-serif);font-size:17px;font-weight:500;color:var(--ink);letter-spacing:-.01em">${fmtMoney(r.valor)}</div>
          </div>
        </div>`;
      }).join('')}</div>`;
      return;
    }

    const cols = [
      { key: 'pos', label: '#', sortable: false },
      { key: 'inst', label: 'Instalação' },
      { key: 'cat', label: 'Categoria' },
      { key: 'causa', label: 'Causa canônica' },
      { key: 'reinc', label: 'Reinc.', num: true },
      { key: 'valor', label: 'Valor fatura', num: true },
      { key: 'spark', label: 'Histórico', sortable: false, num: true },
    ];
    wrap.innerHTML = `
      <table class="rank-table"><thead><tr>
        ${cols.map(c => `<th ${c.num?'class="num"':''}>
          ${c.sortable===false ? c.label : `<span class="rank-head-sort ${state.sort.key===c.key?'is-sorted':''}" data-sort="${c.key}">${c.label}<span class="arrow">${state.sort.key===c.key?(state.sort.dir==='asc'?'▲':'▼'):'◆'}</span></span>`}
        </th>`).join('')}
      </tr></thead><tbody>
        ${rows.map((r, i) => {
          const top = i < 3 ? 'top-3' : '';
          const path = sparkPath(r.spark, 70, 18);
          const last = r.spark.length-1;
          const max = Math.max(...r.spark, 1);
          const lx = (last/(r.spark.length-1))*70;
          const ly = 18 - (r.spark[last]/max)*18;
          return `<tr class="rank-row ${top}">
            <td><span class="pos">${i+1}</span></td>
            <td><span class="inst">${r.inst}</span><div style="font-size:11px;color:var(--ink-3);margin-top:2px">${r.cidade}</div></td>
            <td style="font-size:12.5px;color:var(--ink-2)">${r.cat}</td>
            <td style="font-family:var(--f-mono);font-size:11.5px;color:var(--ink-3)">${r.causa}</td>
            <td class="num"><span class="reinc-badge">${r.reinc}×</span></td>
            <td class="num" style="color:var(--ink);font-weight:600">${fmtMoney(r.valor)}</td>
            <td class="num"><svg class="spark" viewBox="0 0 70 18"><path d="${path}"/><circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="2"/></svg></td>
          </tr>`;
        }).join('')}
      </tbody></table>`;

    $$('.rank-head-sort', wrap).forEach(h => {
      h.addEventListener('click', () => {
        const k = h.dataset.sort;
        if (state.sort.key === k) state.sort.dir = state.sort.dir === 'asc' ? 'desc' : 'asc';
        else { state.sort.key = k; state.sort.dir = 'desc'; }
        renderRanking(key);
      });
    });
  }

  // ─────────────────────────────────────────────────────────
  // Render screen
  // ─────────────────────────────────────────────────────────

  function applySurface(){
    document.body.setAttribute('data-sev', state.screen);
    const shell = $('#shell');
    shell.setAttribute('data-layout', state.tweaks.layout || 'editorial');
    shell.setAttribute('data-density', state.tweaks.density || 'comfortable');
    shell.setAttribute('data-theme', state.tweaks.theme === 'dark' ? 'dark' : 'paper');
  }

  function render(){
    applySurface();
    const main = $('#main');
    const crumb = $('#crumbScreen');
    const crumbSev = $('#crumbSev');

    if (state.screen === 'executivo') {
      main.innerHTML = pageExecutivo();
      crumb.textContent = 'MIS Executivo';
      crumbSev.className = 'sev-tag';
      crumbSev.textContent = '';
      crumbSev.style.display = 'none';
      // render exec volume bars
      requestAnimationFrame(() => {
        const cont = $('#execVolume');
        if (cont) renderVolumeBars(cont, DATA.meses, DATA.executivo.volume_mensal, 'todas sev.');
      });
      // sev dist clickable
      $$('.sev-dist-row').forEach(r => {
        r.addEventListener('click', () => {
          const s = r.dataset.sev;
          if (s === 'alta' || s === 'critica') { state.screen = s; syncNav(); render(); }
        });
      });
    } else {
      main.innerHTML = pageSeveridade(state.screen);
      crumb.textContent = state.screen === 'alta' ? 'Severidade Alta' : 'Severidade Crítica';
      crumbSev.className = 'sev-tag ' + state.screen;
      crumbSev.textContent = state.screen === 'alta' ? 'Alta' : 'Crítica';
      crumbSev.style.display = 'inline-flex';

      requestAnimationFrame(() => {
        const d = DATA[state.screen];
        const label = state.screen === 'alta' ? 'alta' : 'crítica';
        renderVolumeBars($('#volumeChart'), DATA.meses, d.volume_mensal, label);
        renderHBars($('#categoriasChart'), d.categorias, id => {
          state.filter.category = state.filter.category === id ? null : id;
          state.filter.causaId = null;
          state.openDesc = null;
          render();
        });
        renderScatter($('#scatterChart'), d.causas, id => {
          state.filter.causaId = state.filter.causaId === id ? null : id;
          render();
        });
        renderDescBody(state.screen);
        renderRanking(state.screen);

        const cf = $('#clearFilter');
        if (cf) cf.addEventListener('click', e => { e.preventDefault(); state.filter.category = null; state.filter.causaId = null; render(); });

        // Ranking style toggle
        $$('[data-rs]').forEach(b => b.addEventListener('click', () => {
          state.tweaks.ranking_style = b.dataset.rs;
          $('#tw-ranking').value = b.dataset.rs;
          persistTweaks();
          render();
        }));
      });
    }
  }

  function syncNav(){
    $$('.nav-item[data-screen]').forEach(b => {
      b.classList.toggle('is-active', b.dataset.screen === state.screen);
    });
  }

  // ─────────────────────────────────────────────────────────
  // Wire up
  // ─────────────────────────────────────────────────────────

  $$('.nav-item[data-screen]').forEach(b => {
    b.addEventListener('click', () => {
      state.screen = b.dataset.screen;
      state.filter = { category: null, causaId: null };
      state.openDesc = null;
      syncNav();
      render();
    });
  });

  // Keyboard 1/2/3
  window.addEventListener('keydown', e => {
    if (e.target.matches('input, textarea, select')) return;
    if (e.key === '1') { state.screen = 'executivo'; syncNav(); render(); }
    else if (e.key === '2') { state.screen = 'alta'; syncNav(); render(); }
    else if (e.key === '3') { state.screen = 'critica'; syncNav(); render(); }
  });

  // Theme toggle
  $('#themeToggle').addEventListener('click', () => {
    state.tweaks.theme = state.tweaks.theme === 'dark' ? 'paper' : 'dark';
    $('#tw-theme').value = state.tweaks.theme;
    persistTweaks();
    render();
  });

  // Tweaks panel
  const tweaksPanel = $('#tweaksPanel');
  $('#tweaksToggle').addEventListener('click', () => tweaksPanel.classList.toggle('is-open'));
  $('#tweaksClose').addEventListener('click', () => tweaksPanel.classList.remove('is-open'));

  function persistTweaks(){
    try { parent.postMessage({ type: '__edit_mode_set_keys', edits: state.tweaks }, '*'); } catch(_){}
  }
  ['layout','density','theme','ranking','hero'].forEach(k => {
    const map = { ranking:'ranking_style', hero:'hero_metric' };
    const sk = map[k] || k;
    const el = $('#tw-' + k);
    if (el) {
      el.value = state.tweaks[sk] || el.value;
      el.addEventListener('change', () => {
        state.tweaks[sk] = el.value;
        persistTweaks();
        render();
      });
    }
  });

  // Host edit-mode protocol
  window.addEventListener('message', e => {
    const d = e.data || {};
    if (d.type === '__activate_edit_mode') tweaksPanel.classList.add('is-open');
    else if (d.type === '__deactivate_edit_mode') tweaksPanel.classList.remove('is-open');
  });
  try { parent.postMessage({ type: '__edit_mode_available' }, '*'); } catch(_){}

  // Initial render
  render();

  // Re-render on resize (SVG sizes)
  let rz;
  window.addEventListener('resize', () => {
    clearTimeout(rz);
    rz = setTimeout(render, 180);
  });
})();
