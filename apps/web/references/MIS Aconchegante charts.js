// ───── Chart rendering ─────
(function(){
  const D = window.MIS;

  // Shared palette
  const P = {
    ink:       getCSS('--ink'),
    ink2:      getCSS('--ink-2'),
    ink3:      getCSS('--ink-3'),
    inkFaint:  getCSS('--ink-faint'),
    line:      getCSS('--line'),
    terra:     getCSS('--terra'),
    terraDeep: getCSS('--terra-deep'),
    plum:      getCSS('--plum'),
    plumDeep:  getCSS('--plum-deep'),
    amber:     getCSS('--amber'),
    sage:      getCSS('--sage'),
    ocean:     getCSS('--ocean'),
    card:      getCSS('--card'),
    paper2:    getCSS('--paper-2'),
    paper3:    getCSS('--paper-3'),
  };
  function getCSS(v){ return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }

  const CAT = [P.terra, P.plum, P.sage, P.amber, P.ocean, '#b3736a', '#7a5b82', '#9e8a44'];

  const baseGrid = {left:48, right:24, top:28, bottom:36, containLabel:true};
  const tooltipStyle = {
    backgroundColor:P.card,
    borderColor:P.line,
    textStyle:{color:P.ink, fontFamily:'Inter', fontSize:12},
    extraCssText:'box-shadow:0 8px 24px rgba(30,20,12,.10);border-radius:8px;padding:10px 12px;',
    padding:0,
  };
  const axisStyle = {
    axisLine:{lineStyle:{color:P.line}},
    axisTick:{show:false},
    axisLabel:{color:P.ink3, fontFamily:'JetBrains Mono', fontSize:10.5},
    splitLine:{lineStyle:{color:P.line, type:'dashed'}},
  };

  const charts = {};
  function mk(id, opt){
    const el = document.getElementById(id);
    if(!el) return;
    if(charts[id]) charts[id].dispose();
    const c = echarts.init(el, null, {renderer:'canvas'});
    c.setOption(opt);
    charts[id] = c;
    return c;
  }

  // ───── Hero spark ─────
  mk('heroSpark', {
    grid:{left:0,right:0,top:4,bottom:0},
    xAxis:{type:'category',show:false,data:D.months},
    yAxis:{type:'value',show:false},
    series:[{
      type:'line', smooth:true, symbol:'none',
      data:D.regionMonthly.CE.map((v,i)=>v+D.regionMonthly.SP[i]),
      lineStyle:{width:2, color:P.terra},
      areaStyle:{color:{
        type:'linear', x:0,y:0,x2:0,y2:1,
        colorStops:[{offset:0,color:'rgba(180,70,50,.30)'},{offset:1,color:'rgba(180,70,50,0)'}]
      }},
    }]
  });

  // ───── Macro Pareto (custom DOM bars) ─────
  (function renderPareto(){
    const el = document.getElementById('macroPareto');
    const max = Math.max(...D.macroTemas.map(d=>d.qtd));
    el.innerHTML = D.macroTemas.map((d,i)=>`
      <div class="pareto-row ${i===0?'active':''}" data-theme="${d.name}">
        <div class="pareto-name" title="${d.name}">${d.name}</div>
        <div class="pareto-bar"><div class="fill" style="width:${(d.qtd/max*100).toFixed(1)}%"></div></div>
        <div class="pareto-val">${d.qtd.toLocaleString('pt-BR')}</div>
        <div class="pareto-pct">${d.pct.toFixed(1)}%</div>
      </div>
    `).join('');
    el.querySelectorAll('.pareto-row').forEach(r=>{
      r.onclick=()=>{
        el.querySelectorAll('.pareto-row').forEach(x=>x.classList.remove('active'));
        r.classList.add('active');
      };
    });
  })();

  // ───── Macro trend (multi-line) ─────
  const macroTrendSeries = Object.entries(D.macroTrend).map(([name, data], i)=>({
    name, type:'line', smooth:true, symbol:'circle', symbolSize:5,
    lineStyle:{width: name==='Refaturamento & Cobrança'? 3: 1.8, color:CAT[i]},
    itemStyle:{color:CAT[i]},
    emphasis:{focus:'series'},
    data
  }));
  mk('macroTrend', {
    tooltip:{trigger:'axis', ...tooltipStyle},
    legend:{type:'scroll', textStyle:{color:P.ink3, fontSize:11}, top:4, icon:'roundRect'},
    grid:{...baseGrid, top:48},
    xAxis:{type:'category', data:D.months, ...axisStyle, boundaryGap:false},
    yAxis:{type:'value', ...axisStyle, name:'ordens', nameTextStyle:{color:P.ink3, fontSize:10, fontFamily:'JetBrains Mono'}},
    series: macroTrendSeries
  });

  // ───── Region stacked area ─────
  mk('regionStack', {
    tooltip:{trigger:'axis', ...tooltipStyle},
    legend:{top:4, icon:'roundRect', textStyle:{color:P.ink3, fontSize:11}},
    grid:{...baseGrid, top:36},
    xAxis:{type:'category', data:D.months, ...axisStyle, boundaryGap:false},
    yAxis:{type:'value', ...axisStyle},
    series:[
      {name:'CE', type:'line', stack:'r', smooth:true, symbol:'none',
       lineStyle:{color:P.terra, width:2},
       areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(180,70,50,.55)'},{offset:1,color:'rgba(180,70,50,.10)'}]}},
       data:D.regionMonthly.CE},
      {name:'SP', type:'line', stack:'r', smooth:true, symbol:'none',
       lineStyle:{color:P.plum, width:2},
       areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(100,30,50,.55)'},{offset:1,color:'rgba(100,30,50,.10)'}]}},
       data:D.regionMonthly.SP},
    ]
  });

  // ───── Severity heatmap (executivo) ─────
  function sevHeat(id){
    const sevs = ['critical','high','medium','low'];
    const regs = ['CE','SP'];
    const data = [];
    regs.forEach((r,ri)=>sevs.forEach((s,si)=>data.push([si, ri, D.severidade[r][s]])));
    const max = Math.max(...data.map(d=>d[2]));
    mk(id,{
      tooltip:{position:'top', ...tooltipStyle, formatter:(p)=>`<b>${regs[p.data[1]]}</b> · ${sevs[p.data[0]]}<br>${p.data[2].toLocaleString('pt-BR')} ordens`},
      grid:{left:56, right:16, top:10, bottom:40},
      xAxis:{type:'category', data:sevs, ...axisStyle, splitArea:{show:false}},
      yAxis:{type:'category', data:regs, ...axisStyle, splitArea:{show:false}},
      visualMap:{min:0, max, show:false, inRange:{color:['#faeee4','#f4c2a0','#d67a56','#893730','#3b1a1f']}},
      series:[{
        type:'heatmap', data,
        label:{show:true, color:'#fff', fontFamily:'JetBrains Mono', fontWeight:600, fontSize:11,
          formatter:p=> p.data[2] >= 1000 ? (p.data[2]/1000).toFixed(1)+'k' : p.data[2]},
        itemStyle:{borderRadius:4, borderColor:P.card, borderWidth:3},
      }]
    });
  }
  sevHeat('sevHeatExec');

  // ───── Ritmo trend (area) ─────
  mk('ritmoTrend', {
    tooltip:{trigger:'axis', ...tooltipStyle},
    legend:{top:4, textStyle:{color:P.ink3, fontSize:11}, icon:'roundRect'},
    grid:{...baseGrid, top:36},
    xAxis:{type:'category', data:D.months, ...axisStyle, boundaryGap:false},
    yAxis:{type:'value', ...axisStyle},
    series:[
      {name:'CE', type:'line', smooth:true, symbol:'circle', symbolSize:5,
       data:D.regionMonthly.CE, lineStyle:{color:P.terra, width:2},
       areaStyle:{color:'rgba(180,70,50,.18)'}},
      {name:'SP', type:'line', smooth:true, symbol:'circle', symbolSize:5,
       data:D.regionMonthly.SP, lineStyle:{color:P.plum, width:2.5},
       areaStyle:{color:'rgba(100,30,50,.22)'},
       markPoint:{symbol:'pin', symbolSize:44, itemStyle:{color:P.plumDeep},
         label:{color:'#fff',fontSize:10},
         data:[{type:'max', name:'pico'}]},
      },
    ]
  });

  // ───── Ritmo Pareto (bars + cumulative line) ─────
  (function(){
    const sorted=[...D.causas].sort((a,b)=>b.v-a.v).slice(0,12);
    const total=sorted.reduce((a,c)=>a+c.v,0);
    let acc=0;const cum=sorted.map(c=>{acc+=c.v;return +(acc/total*100).toFixed(1)});
    mk('ritmoPareto',{
      tooltip:{trigger:'axis', ...tooltipStyle, axisPointer:{type:'shadow'}},
      grid:{left:130, right:48, top:16, bottom:32},
      xAxis:[{type:'value', ...axisStyle}, {type:'value', max:100, ...axisStyle, axisLabel:{...axisStyle.axisLabel,formatter:'{value}%'}}],
      yAxis:{type:'category', inverse:true, data:sorted.map(c=>c.name), ...axisStyle,
        axisLabel:{...axisStyle.axisLabel, fontSize:10.5, overflow:'truncate', width:120}},
      series:[
        {type:'bar', data:sorted.map(c=>c.v), barWidth:16,
          itemStyle:{borderRadius:[0,4,4,0], color:(p)=>{
            const c=['#4a1725','#6a1f36','#892644','#a22a48','#b93a50','#c85454','#cf6a58','#d8805d','#dfa37a','#e6bb96','#edc9a8','#f0d6b4'];
            return c[p.dataIndex]||P.terra;
          }},
          label:{show:true, position:'right', color:P.ink2, fontFamily:'JetBrains Mono', fontSize:11,
            formatter:p=>p.value.toLocaleString('pt-BR')},
        },
        {type:'line', data:cum, smooth:true, xAxisIndex:1, symbol:'circle', symbolSize:6,
          lineStyle:{color:P.ink, width:1.5}, itemStyle:{color:P.ink},
          markLine:{symbol:'none', lineStyle:{color:P.amber, type:'dashed'}, label:{formatter:'80%', color:P.ink3},
            data:[{xAxis:80}]},
        }
      ]
    });
  })();

  // ───── Sankey: causa → ação → resolução ─────
  mk('sankey', {
    tooltip:{...tooltipStyle, trigger:'item'},
    series:[{
      type:'sankey', left:24, right:120, top:18, bottom:18,
      nodeAlign:'justify', nodeGap:10, nodeWidth:14,
      label:{fontFamily:'Inter', fontSize:11, color:P.ink2},
      lineStyle:{color:'gradient', curveness:0.5, opacity:0.55},
      data:[
        {name:'digitacao', itemStyle:{color:P.terra}},
        {name:'consumo_elevado', itemStyle:{color:P.plum}},
        {name:'autoleitura', itemStyle:{color:P.amber}},
        {name:'refat_corretivo', itemStyle:{color:P.sage}},
        {name:'Revisão humana', itemStyle:{color:'#8a6a52'}},
        {name:'Ajuste automático', itemStyle:{color:'#6a8a72'}},
        {name:'Visita técnica', itemStyle:{color:'#8a7a4a'}},
        {name:'Resolvida', itemStyle:{color:P.sage}},
        {name:'Refaturamento', itemStyle:{color:P.terra}},
        {name:'Reaberta', itemStyle:{color:P.plumDeep}},
      ],
      links:[
        {source:'digitacao',       target:'Revisão humana',     value:3200},
        {source:'digitacao',       target:'Ajuste automático',  value:1774},
        {source:'consumo_elevado', target:'Revisão humana',     value:1820},
        {source:'consumo_elevado', target:'Visita técnica',     value:2110},
        {source:'autoleitura',     target:'Ajuste automático',  value:1440},
        {source:'autoleitura',     target:'Visita técnica',     value:1499},
        {source:'refat_corretivo', target:'Revisão humana',     value:668},
        {source:'Revisão humana',   target:'Resolvida',      value:3400},
        {source:'Revisão humana',   target:'Refaturamento',  value:2100},
        {source:'Revisão humana',   target:'Reaberta',       value:188},
        {source:'Ajuste automático',target:'Resolvida',      value:2700},
        {source:'Ajuste automático',target:'Refaturamento',  value:514},
        {source:'Visita técnica',   target:'Resolvida',      value:2400},
        {source:'Visita técnica',   target:'Refaturamento',  value:980},
        {source:'Visita técnica',   target:'Reaberta',       value:229},
      ]
    }]
  });

  // ───── Heatmap região × causa ─────
  (function(){
    const causaNames = D.causas.slice(0,10).map(c=>c.name);
    const regs=['CE','SP'];
    const max = Math.max(...D.regCausa.map(d=>d[2]));
    mk('heatRegCausa',{
      tooltip:{...tooltipStyle, position:'top',
        formatter:p=>`<b>${regs[p.data[1]]}</b> · ${causaNames[p.data[0]]}<br>${p.data[2].toLocaleString('pt-BR')} ordens`},
      grid:{left:16, right:40, top:12, bottom:130, containLabel:true},
      xAxis:{type:'category', data:causaNames, ...axisStyle,
        axisLabel:{...axisStyle.axisLabel, rotate:45, fontSize:10}},
      yAxis:{type:'category', data:regs, ...axisStyle},
      visualMap:{min:0, max, orient:'horizontal', right:0, bottom:0,
        itemWidth:10, itemHeight:80,
        textStyle:{color:P.ink3, fontFamily:'JetBrains Mono', fontSize:10},
        inRange:{color:['#fdecee','#f7c8b8','#e89478','#c8543f','#7a2030','#3a1017']}},
      series:[{
        type:'heatmap', data:D.regCausa,
        label:{show:true, color:'#fff', fontFamily:'JetBrains Mono', fontWeight:600, fontSize:10,
          formatter:p=>p.data[2]>=1000?(p.data[2]/1000).toFixed(1)+'k':p.data[2]},
        itemStyle:{borderRadius:3, borderColor:P.card, borderWidth:2},
      }]
    });
  })();

  // ───── Radar por região ─────
  (function(){
    const cs = D.causas.slice(0,6).map(c=>c.name);
    // normalize within region
    function norm(r){
      const total = D.causas.slice(0,6).reduce((a,c)=>a+(c.regiao===r?c.v:c.v*(r==='CE'?0.12:0.88)),0);
      return cs.map(n=>{
        const c = D.causas.find(x=>x.name===n);
        const v = c.regiao===r?c.v:c.v*(r==='CE'?0.12:0.88);
        return +(v/total*100).toFixed(1);
      });
    }
    mk('radarRegion',{
      tooltip:{...tooltipStyle},
      legend:{top:4, textStyle:{color:P.ink3, fontSize:11}, icon:'roundRect'},
      radar:{
        indicator: cs.map(n=>({name:n, max:60})),
        axisName:{color:P.ink3, fontFamily:'JetBrains Mono', fontSize:10},
        splitLine:{lineStyle:{color:P.line}},
        splitArea:{areaStyle:{color:[P.card, P.paper2]}},
        axisLine:{lineStyle:{color:P.line}},
        radius:'64%',
      },
      series:[{
        type:'radar', areaStyle:{opacity:0.25},
        data:[
          {name:'CE', value:norm('CE'), itemStyle:{color:P.terra}, lineStyle:{color:P.terra, width:2}, areaStyle:{color:P.terra}},
          {name:'SP', value:norm('SP'), itemStyle:{color:P.plum}, lineStyle:{color:P.plum, width:2}, areaStyle:{color:P.plum}},
        ]
      }]
    });
  })();

  // ───── Topic pills ─────
  (function(){
    const el = document.getElementById('topicPills');
    el.innerHTML = D.topics.map(t=>`
      <span class="topic-pill" data-id="${t.id}">
        <span>${t.name}</span>
        <span class="n">${t.size.toLocaleString('pt-BR')}</span>
      </span>`).join('');
  })();

  // ───── Quadrant scatter ─────
  (function(){
    const pts = D.quadrant.map((d,i)=>{
      // classify
      let color = P.sage;
      if(d.x>=2000 && d.y>=5) color = P.terra;
      else if(d.x>=2000 && d.y<5) color = P.amber;
      else if(d.x<2000 && d.y>=5) color = P.ocean;
      return {value:[d.x, d.y, d.z], name:d.name, itemStyle:{color, opacity:0.85, borderColor:'#fff', borderWidth:1}};
    });
    mk('quadrant',{
      tooltip:{...tooltipStyle, formatter:p=>`<b>${p.data.name}</b><br>volume: ${p.data.value[0].toLocaleString('pt-BR')}<br>refat: ${p.data.value[1].toFixed(1)}%`},
      grid:{left:50, right:80, top:24, bottom:48},
      xAxis:{type:'value', name:'volume de ordens', ...axisStyle,
        nameGap:26, nameTextStyle:{color:P.ink3, fontSize:10.5, fontFamily:'JetBrains Mono'}},
      yAxis:{type:'value', name:'% refaturamento', ...axisStyle,
        nameGap:26, nameTextStyle:{color:P.ink3, fontSize:10.5, fontFamily:'JetBrains Mono'}},
      series:[{
        type:'scatter', data:pts, symbolSize:(v)=>Math.max(14, Math.sqrt(v[2])/6),
        label:{show:true, formatter:p=>p.data.name, position:'top', color:P.ink3, fontSize:10, fontFamily:'JetBrains Mono'},
        emphasis:{focus:'self', label:{color:P.ink, fontWeight:600}},
        markLine:{symbol:'none', lineStyle:{type:'dashed', color:P.line, width:1},
          data:[{xAxis:2000}, {yAxis:5}],
          label:{show:false}},
      }]
    });
  })();

  // ───── Category impact ─────
  mk('catImpact', {
    tooltip:{trigger:'axis', ...tooltipStyle, axisPointer:{type:'shadow'}},
    legend:{top:4, textStyle:{color:P.ink3, fontSize:11}, icon:'roundRect'},
    grid:{left:40, right:16, top:36, bottom:60},
    xAxis:{type:'category', data:D.categoriasTax.map(c=>c.cat), ...axisStyle,
      axisLabel:{...axisStyle.axisLabel, rotate:40, fontSize:9.5}},
    yAxis:{type:'value', ...axisStyle},
    series:[
      {name:'CE', type:'bar', data:D.categoriasTax.map(c=>c.CE),
        itemStyle:{color:P.terra, borderRadius:[3,3,0,0]}, barGap:'8%'},
      {name:'SP', type:'bar', data:D.categoriasTax.map(c=>c.SP),
        itemStyle:{color:P.plum, borderRadius:[3,3,0,0]}},
    ]
  });

  // ───── Reincidência histograma ─────
  mk('reincHist', {
    tooltip:{trigger:'axis', ...tooltipStyle, axisPointer:{type:'shadow'}},
    legend:{top:4, textStyle:{color:P.ink3, fontSize:11}, icon:'roundRect'},
    grid:{...baseGrid, top:36},
    xAxis:{type:'category', data:['1','2','3','4','5','6+'], ...axisStyle,
      name:'recorrências', nameTextStyle:{color:P.ink3, fontSize:10, fontFamily:'JetBrains Mono'}},
    yAxis:{type:'value', ...axisStyle, name:'instalações'},
    series:[
      {name:'CE', type:'bar', data:D.reincidencia.CE, itemStyle:{color:'#edc9a8', borderRadius:[3,3,0,0]}},
      {name:'SP', type:'bar', data:D.reincidencia.SP, itemStyle:{color:'#e6bb96', borderRadius:[3,3,0,0]}},
    ]
  });

  // ───── Treemap (topics) ─────
  mk('treemap', {
    tooltip:{...tooltipStyle,
      formatter:p=>`<b>${p.data.name}</b><br>${p.value.toLocaleString('pt-BR')} doc<br>refat: ${p.data.refat.toFixed(1)}%`},
    series:[{
      type:'treemap', data: D.topics.map(t=>({
        name:t.name, value:t.size, refat:t.refat,
        itemStyle:{
          color: t.refat>8 ? P.terra : t.refat>3 ? P.amber : P.sage,
          borderColor:P.card, borderWidth:2, gapWidth:2,
        },
      })),
      roam:false, nodeClick:false, breadcrumb:{show:false},
      label:{fontFamily:'Inter', fontSize:12, fontWeight:500, color:'#fff',
        formatter:p=>`{b|${p.name}}\n{v|${(p.value/1000).toFixed(1)}k}`,
        rich:{b:{fontSize:12, fontWeight:600}, v:{fontSize:11, fontFamily:'JetBrains Mono', opacity:0.85, padding:[2,0,0,0]}}
      },
      top:4,left:4,right:4,bottom:4,
    }]
  });

  // ───── Keywords bars ─────
  (function(){
    const kw = D.topics.slice(0,6).flatMap(t=>t.keywords.slice(0,3).map(k=>({
      k, t:t.name, v: Math.round(t.size*(0.6+Math.random()*0.3))
    })));
    kw.sort((a,b)=>b.v-a.v);
    mk('kwBars',{
      tooltip:{...tooltipStyle, formatter:p=>`<b>${p.data.k}</b><br>tópico: ${p.data.t}<br>contagem: ${p.data.v.toLocaleString('pt-BR')}`},
      grid:{left:130, right:24, top:8, bottom:16},
      xAxis:{type:'value', ...axisStyle},
      yAxis:{type:'category', data:kw.map(x=>x.k), inverse:true, ...axisStyle,
        axisLabel:{...axisStyle.axisLabel, fontSize:11}},
      series:[{
        type:'bar', data:kw.map(x=>({value:x.v, k:x.k, t:x.t})),
        barWidth:12,
        itemStyle:{borderRadius:[0,4,4,0], color:(p)=>{
          const c=[P.terra, P.plum, P.amber, P.sage, P.ocean, '#8a6a52'];
          return c[p.dataIndex%c.length];
        }},
        label:{show:true, position:'right', color:P.ink3, fontFamily:'JetBrains Mono', fontSize:10.5,
          formatter:p=>p.value.toLocaleString('pt-BR')},
      }]
    });
  })();

  // ───── Topic table ─────
  (function(){
    const tbody = document.querySelector('#topicTable tbody');
    tbody.innerHTML = D.topics.map((t,i)=>`
      <tr>
        <td class="mono" style="color:var(--ink-faint)">${String(i).padStart(2,'0')}</td>
        <td><b style="font-family:var(--f-mono);color:var(--ink)">${t.name}</b></td>
        <td class="num">${t.size.toLocaleString('pt-BR')}</td>
        <td>${t.keywords.map(k=>`<span class="topic-pill" style="padding:2px 8px;font-size:10.5px;margin:1px">${k}</span>`).join('')}</td>
        <td style="max-width:340px;font-size:12px;color:var(--ink-3)">${t.ex}</td>
        <td class="num"><span class="tag ${t.refat>8?'terra':t.refat>3?'amber':'sage'}">${t.refat.toFixed(1)}%</span></td>
      </tr>
    `).join('');
  })();

  // ───── Governance heatmap ─────
  (function(){
    const sevs=['critical','high','medium','low'];
    const regs=['CE','SP'];
    mk('govHeat',{
      tooltip:{...tooltipStyle, position:'top',
        formatter:p=>`<b>${regs[p.data[1]]}</b> · ${sevs[p.data[0]]}<br>taxa refat: ${(p.data[2]*100).toFixed(1)}%`},
      grid:{left:56, right:16, top:10, bottom:40},
      xAxis:{type:'category', data:sevs, ...axisStyle},
      yAxis:{type:'category', data:regs, ...axisStyle},
      visualMap:{show:false, min:0, max:0.4,
        inRange:{color:['#faeee4','#f4c2a0','#d67a56','#893730','#3b1a1f']}},
      series:[{type:'heatmap', data:D.govHeat,
        label:{show:true, color:'#fff', fontFamily:'JetBrains Mono', fontWeight:600, fontSize:11,
          formatter:p=>(p.data[2]*100).toFixed(0)+'%'},
        itemStyle:{borderRadius:4, borderColor:P.card, borderWidth:3},
      }]
    });
  })();

  // ───── Coverage stacked ─────
  mk('covBars', {
    tooltip:{trigger:'axis', ...tooltipStyle, axisPointer:{type:'shadow'},
      formatter:ps=>{
        return `<b>${ps[0].axisValue}</b><br>`+ps.map(p=>`<span style="color:${p.color}">●</span> ${p.seriesName}: ${p.value}%`).join('<br>');
      }},
    legend:{top:4, textStyle:{color:P.ink3, fontSize:11}, icon:'roundRect'},
    grid:{...baseGrid, top:36, bottom:44},
    xAxis:{type:'category', data:D.coverage.map(c=>c.cat), ...axisStyle,
      axisLabel:{...axisStyle.axisLabel, rotate:20}},
    yAxis:{type:'value', max:100, ...axisStyle, axisLabel:{...axisStyle.axisLabel, formatter:'{value}%'}},
    series:[
      {name:'Rotulado', type:'bar', stack:'c', data:D.coverage.map(c=>c.rot),
        itemStyle:{color:P.sage}},
      {name:'Auto-IA', type:'bar', stack:'c', data:D.coverage.map(c=>c.ia),
        itemStyle:{color:P.amber}},
      {name:'Indefinido', type:'bar', stack:'c', data:D.coverage.map(c=>c.ind),
        itemStyle:{color:P.terra, borderRadius:[3,3,0,0]}},
    ]
  });

  // ───── NAV + SCREENS ─────
  const screens = document.querySelectorAll('.screen');
  const navBtns = document.querySelectorAll('.nav-item');
  function show(id){
    screens.forEach(s=>s.classList.toggle('on', s.dataset.id===id));
    navBtns.forEach(b=>b.classList.toggle('active', b.dataset.screen===id));
    const label = document.querySelector(`.nav-item[data-screen="${id}"]`);
    document.getElementById('crumbScreen').textContent = label ? label.textContent.replace(/\d+$/,'').trim() : '';
    // resize charts in case container was hidden
    setTimeout(()=>Object.values(charts).forEach(c=>c && c.resize()), 40);
    localStorage.setItem('mis.screen', id);
  }
  navBtns.forEach(b=>b.onclick=()=>show(b.dataset.screen));
  // keyboard
  document.addEventListener('keydown',e=>{
    const map={'1':'exec','2':'ritmo','3':'padroes','4':'refat','5':'tax','6':'gov'};
    if(map[e.key]) show(map[e.key]);
    if(e.key==='Escape') document.getElementById('tweaks').classList.remove('open');
  });
  // restore
  const saved = localStorage.getItem('mis.screen');
  if(saved) show(saved);

  // Region toggle
  document.querySelectorAll('.seg').forEach(seg=>{
    seg.querySelectorAll('button').forEach(b=>{
      b.onclick=()=>{
        seg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
        b.classList.add('on');
      };
    });
  });
  // region chips
  document.querySelectorAll('#regChips .chip').forEach(c=>{
    c.onclick=()=>c.classList.toggle('on');
  });

  // Tweaks
  const tw = document.getElementById('tweaks');
  document.getElementById('tweaksBtn').onclick=()=>tw.classList.add('open');
  document.getElementById('tweaksClose').onclick=()=>tw.classList.remove('open');
  document.getElementById('twPalette').onchange=(e)=>{
    const v = e.target.value;
    const r = document.documentElement;
    if(v==='mono'){
      r.style.setProperty('--terra', 'oklch(36% 0.018 40)');
      r.style.setProperty('--plum',  'oklch(22% 0.018 40)');
    } else if(v==='ink'){
      r.style.setProperty('--terra', 'oklch(58% 0.18 30)');
      r.style.setProperty('--plum',  'oklch(20% 0.02 30)');
    } else {
      r.style.setProperty('--terra', 'oklch(60% 0.17 28)');
      r.style.setProperty('--plum',  'oklch(36% 0.14 12)');
    }
    location.reload();
  };
  document.getElementById('twFont').onchange=(e)=>{
    document.documentElement.style.setProperty('--f-serif', e.target.value==='sans'?"'Inter',sans-serif":"'Fraunces',serif");
  };
  document.getElementById('twDensity').onchange=(e)=>{
    document.body.style.fontSize = e.target.value==='compact' ? '13px' : '14px';
    setTimeout(()=>Object.values(charts).forEach(c=>c && c.resize()), 40);
  };

  // Resize
  window.addEventListener('resize',()=>Object.values(charts).forEach(c=>c && c.resize()));
})();
