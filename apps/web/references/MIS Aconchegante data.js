// ───── Synthetic yet realistic MIS data ─────
window.MIS = (function(){
  const months = ['Abr 25','Mai 25','Jun 25','Jul 25','Ago 25','Set 25','Out 25','Nov 25','Dez 25','Jan 26','Fev 26','Mar 26'];

  // Macrotemas (qtd)
  const macroTemas = [
    {name:'Refaturamento & Cobrança',     qtd:91891, pct:54.9, delta:+18.2},
    {name:'Religação & Multas',           qtd:22310, pct:13.3, delta:+4.1},
    {name:'Geração Distribuída (GD)',     qtd:16240, pct:9.7,  delta:+22.7},
    {name:'Ouvidoria & Jurídico',         qtd:12108, pct:7.2,  delta:+3.3},
    {name:'Variação de Consumo',          qtd:9830,  pct:5.9,  delta:-2.1},
    {name:'Faturamento por Média/Estim.', qtd:7412,  pct:4.4,  delta:+41.0},
    {name:'Outros',                       qtd:4690,  pct:2.8,  delta:+1.0},
    {name:'Entrega da Fatura',            qtd:3152,  pct:1.9,  delta:-5.4},
  ];

  // Monthly trend per macrotema
  const macroTrend = {
    'Refaturamento & Cobrança':   [5400,6200,7300,8200,8800,8400,8100,7900,7400,7100,6800,6200],
    'Religação & Multas':         [1200,1800,5400,3200,2600,2200,2000,2100,2400,2600,2100,1800],
    'Geração Distribuída (GD)':   [600, 720, 950, 1150,1300,1420,1500,1550,1700,1800,1900,1950],
    'Ouvidoria & Jurídico':       [800, 820, 860, 1000,1040,1080,1100,1120,1130,1120,1100,1100],
    'Variação de Consumo':        [650, 700, 820, 900, 920, 880, 830, 810, 800, 820, 840, 860],
    'Faturamento por Média/Estim.':[220, 260, 310, 380, 440, 520, 620, 720, 820, 920,1020,1180],
    'Outros':                     [300, 310, 330, 360, 380, 400, 410, 420, 430, 440, 440, 450],
  };

  // Regional monthly MIS (erro leitura)
  const regionMonthly = {
    'CE': [490,510,520,500,470,450,510,460,470,560,600,380],
    'SP': [540,560,580,1080,1180,1220,1440,1340,1380,2180,2627,560]
  };

  // Causas canônicas (Pareto)
  const causas = [
    {name:'digitacao',                  v:4974, refat:0.3, regiao:'CE'},
    {name:'consumo_elevado_revisao',    v:3930, refat:16.2,regiao:'SP'},
    {name:'indefinido',                 v:3678, refat:0.0, regiao:'SP'},
    {name:'autoleitura_cliente',        v:2939, refat:9.1, regiao:'SP'},
    {name:'refaturamento_corretivo',    v:668,  refat:3.6, regiao:'CE'},
    {name:'impedimento_acesso',         v:234,  refat:0.5, regiao:'SP'},
    {name:'leitura_estimada_media',     v:197,  refat:0.2, regiao:'CE'},
    {name:'compensacao_gd',             v:140,  refat:0.1, regiao:'SP'},
    {name:'leitura_confirmada_improced.',v:78,  refat:-0.1,regiao:'CE'},
    {name:'art_113_regulatorio',        v:57,   refat:0.0, regiao:'CE'},
    {name:'medidor_danificado',         v:51,   refat:0.4, regiao:'CE'},
    {name:'troca_titularidade',         v:38,   refat:0.0, regiao:'SP'},
    {name:'endereco_tipologia',         v:30,   refat:0.1, regiao:'CE'},
    {name:'cobranca_indevida',          v:23,   refat:20.5,regiao:'CE'},
  ];

  // Severidade por região (ordens)
  const severidade = {
    CE: {critical:29,  high:5719, medium:75,   low:112},
    SP: {critical:365, high:3502, medium:4061, low:5564}
  };

  // Region × Cause heatmap
  const regCausa = [];
  ['CE','SP'].forEach((r,ri)=>causas.slice(0,10).forEach((c,ci)=>{
    const bias = (r==='CE' && c.name==='digitacao')?4974:
                 (r==='SP' && c.name==='indefinido')?3631:
                 (r==='SP' && c.name==='consumo_elevado_revisao')?3925:
                 (r==='SP' && c.name==='autoleitura_cliente')?2908:
                 (r==='CE' && c.name==='leitura_confirmada_improced.')?68:
                 (r==='CE' && c.name==='refaturamento_corretivo')?43:
                 Math.round(c.v * (r==='CE'?0.12:0.88) * (0.6+Math.random()*0.8));
    regCausa.push([ci, ri, bias]);
  }));

  // Topics descobertos (BERTopic)
  const topics = [
    {id:0, name:'medidor_relogio_loja',      size:7381, keywords:['medidor','relogio','loja','troca','visita'], refat:0.4,  ex:'Cliente solicita visita técnica ao medidor da loja; [USUARIO] [ID_INTERNO] relata oscilação.'},
    {id:1, name:'corrigido_ajuste_ajustado', size:2181, keywords:['corrigido','ajuste','ajustado','fatura'],     refat:11.2, ex:'01.07.2025 13:09 gmtuk [USUARIO] ([br/ID_INTERNO]) revisar fatura com ajuste.'},
    {id:2, name:'consumo_variacao_dias',     size:2181, keywords:['consumo','variacao','dias','icms'],            refat:8.4,  ex:'Celular: [TELEFONE]. Informacoes: cliente com variacao de consumo em dias frios.'},
    {id:3, name:'consumo_dias_variacao',     size:1821, keywords:['consumo','dias','variacao','dias_consumo'],    refat:7.1,  ex:'Celular: [TELEFONE]. Demais informacoes: cliente relata variacao...'},
    {id:4, name:'ajuste_leit_ajustada',      size:1296, keywords:['ajuste','leit','ajustada','consumidor'],       refat:9.9,  ex:'04.02.2026 14:12 gmtuk [USUARIO] ([br/ID_INTERNO]) trata-se de erro de leitura ajustado.'},
    {id:5, name:'anexo_mail_mail_anexo',     size:1132, keywords:['anexo','mail','mail_anexo','segue','foto'],    refat:2.1,  ex:'Segue anexo com foto do relogio; cliente [USUARIO] pede retorno por mail.'},
    {id:6, name:'ajuste_corrigida_ficou',    size:890,  keywords:['ajuste','corrigida','ficou','consumo'],        refat:6.2,  ex:'Ajuste aplicado, fatura corrigida ficou [USUARIO] sem pendencia.'},
    {id:7, name:'tecnico_telefone_visita',   size:310,  keywords:['tecnico','telefone','visita','agenda'],        refat:0.9,  ex:'Tecnico vai ligar no [TELEFONE] para agendar visita.'},
  ];

  // Category impact (taxonomia)
  const categoriasTax = [
    {cat:'processo_leitura',          CE:4680, SP:420},
    {cat:'relocacao',                 CE:120,  SP:230},
    {cat:'nao_classificada',          CE:3700, SP:620},
    {cat:'consertacao',               CE:40,   SP:6870},
    {cat:'cadastro',                  CE:360,  SP:510},
    {cat:'faturamento_por_media',     CE:200,  SP:980},
    {cat:'equipamento',               CE:140,  SP:180},
    {cat:'geracao_distribuida',       CE:300,  SP:260},
    {cat:'regulatorio',               CE:80,   SP:160},
    {cat:'acesso_fisico',             CE:220,  SP:320},
  ];

  // Reincidência (histograma)
  const reincidencia = {
    CE: [4780, 360, 48, 12, 4, 1],
    SP: [10950, 890, 140, 28, 9, 3]
  };

  // Quadrant: causa x refaturamento
  const quadrant = causas.map(c=>({
    name:c.name, x:c.v, y:c.refat, z: Math.max(80, c.v * Math.max(c.refat,0.3))
  }));

  // Cobertura
  const coverage = [
    {cat:'Refaturamento', rot:38, ia:32, ind:30},
    {cat:'Religação',     rot:25, ia:48, ind:27},
    {cat:'GD',            rot:44, ia:34, ind:22},
    {cat:'Ouvidoria',     rot:18, ia:50, ind:32},
    {cat:'V. Consumo',    rot:41, ia:36, ind:23},
    {cat:'Fat. Média',    rot:12, ia:38, ind:50},
  ];

  // Governance risk heatmap
  const govHeat = [
    [0,0, 0.12],[1,0,0.22],[2,0,0.07],[3,0,0.02],
    [0,1, 0.18],[1,1,0.34],[2,1,0.28],[3,1,0.04],
  ];

  return {months, macroTemas, macroTrend, regionMonthly, causas, severidade, regCausa, topics, categoriasTax, reincidencia, quadrant, coverage, govHeat};
})();
