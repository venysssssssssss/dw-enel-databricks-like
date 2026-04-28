/**
 * Pure analytics helpers shared across BI routes.
 * Data shapes match the aggregation contract returned by /v1/aggregations/*.
 */

export type Severity = "critical" | "high" | "medium" | "low";

/**
 * Display labels for canonical causes. The internal ID stays stable across
 * the data plane and tests; UIs render the friendly label, falling back to a
 * humanized version of the ID for unmapped causes.
 */
export const CAUSA_DISPLAY_LABEL: Record<string, string> = {
  autoleitura_cliente: "Erro leitura - com foto",
  consumo_elevado_revisao: "Erro leitura - sem foto"
};

export function formatCausa(id: string | null | undefined): string {
  if (!id) return "—";
  const trimmed = String(id).trim();
  if (!trimmed) return "—";
  if (CAUSA_DISPLAY_LABEL[trimmed]) return CAUSA_DISPLAY_LABEL[trimmed];
  if (trimmed.toLowerCase() === "indefinido") return "Indefinido";
  return trimmed.replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

export function formatCategoria(id: string | null | undefined): string {
  if (!id) return "—";
  const trimmed = String(id).trim();
  if (!trimmed) return "—";
  return trimmed.replace(/_/g, " ");
}

export const SEVERITY_ORDER: readonly Severity[] = ["critical", "high", "medium", "low"];

export const SEVERITY_LABEL_PT: Record<Severity, string> = {
  critical: "Crítica",
  high: "Alta",
  medium: "Média",
  low: "Baixa"
};

export type SeverityHeatmapRow = {
  regiao: string;
  severidade: Severity | string;
  qtd_erros: number;
  taxa_refaturamento: number;
};

export type SeverityBucket = {
  key: Severity;
  label: string;
  value: number;
  pct: number;
};

export type CategoryBreakdownRow = {
  categoria: string;
  regiao: string;
  qtd_erros: number;
  percentual: number;
};

export type ClassifierCoverageRow = {
  regiao: string;
  causa_canonica_confidence: "high" | "low" | "indefinido" | string;
  qtd_ordens: number;
  percentual: number;
  indefinidos: number;
  indefinido_pct: number;
};

export type MisMonthlyRow = {
  mes_ingresso: string;
  regiao: string;
  qtd_erros: number;
  mom: number;
  media_movel_3m: number;
};

export type RootCauseRow = {
  causa_canonica: string;
  qtd_erros: number;
  taxa_refaturamento: number;
  percentual: number;
};

export type TopAssuntoRow = {
  assunto: string;
  qtd_ordens: number;
  percentual: number;
};

export type AssuntoLiderRow = {
  regiao: string;
  assunto_lider: string;
  qtd_ordens: number;
  percentual: number;
  fat_reclamada_top: string;
  dias_emissao_ate_reclamacao_medio: number;
  tipo_medidor_dominante: string;
  valor_fatura_reclamada_medio: number;
  cobertura_fatura_pct: number;
  cobertura_medidor_pct: number;
};

export type MisRegionRow = {
  regiao: string;
  volume_total: number;
  taxa_refaturamento: number;
  cobertura_rotulo: number;
  causa_dominante: string;
  share_critico: number;
  instalacoes_reincidentes?: number;
  severidade_media?: number;
};

const NUM_FMT = new Intl.NumberFormat("pt-BR");
const MONEY_FMT = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

export function formatNumber(value: number | string | null | undefined): string {
  const n = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return NUM_FMT.format(Math.round(n));
}

export function formatPercent(value: number | string | null | undefined, digits = 1): string {
  const n = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits).replace(".", ",") + "%";
}

export function formatMoney(value: number | string | null | undefined): string {
  const n = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(n) || n === 0) return "R$ 0,00";
  return MONEY_FMT.format(n);
}

function isSeverity(value: string): value is Severity {
  return value === "critical" || value === "high" || value === "medium" || value === "low";
}

export function buildSeverityDistribution(
  rows: readonly SeverityHeatmapRow[],
  options: { regiao?: string } = {}
): SeverityBucket[] {
  const accum: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  const target = options.regiao?.toUpperCase();
  for (const row of rows) {
    if (target && String(row.regiao ?? "").toUpperCase() !== target) continue;
    const key = String(row.severidade ?? "").toLowerCase();
    if (isSeverity(key)) {
      accum[key] += Number(row.qtd_erros ?? 0);
    }
  }
  const total = SEVERITY_ORDER.reduce((sum, key) => sum + accum[key], 0);
  return SEVERITY_ORDER.map((key) => ({
    key,
    label: SEVERITY_LABEL_PT[key],
    value: accum[key],
    pct: total > 0 ? (accum[key] / total) * 100 : 0
  }));
}

export type ScatterPoint = {
  id: string;
  label: string;
  x: number;
  y: number;
  size: number;
  group: string;
};

/**
 * Build a scatter focused on the volume × refaturamento dispersion of canonical causes.
 * Y is rendered as percentage in [0, 100] for legibility.
 */
export function buildCauseScatter(rows: readonly RootCauseRow[]): ScatterPoint[] {
  const points: ScatterPoint[] = [];
  for (const row of rows) {
    const causa = String(row.causa_canonica ?? "").trim();
    if (!causa || causa.toLowerCase() === "indefinido") continue;
    const vol = Number(row.qtd_erros ?? 0);
    const refat = Number(row.taxa_refaturamento ?? 0);
    if (vol <= 0) continue;
    points.push({
      id: causa,
      label: causa,
      x: vol,
      y: Math.max(0, Math.min(100, refat * 100)),
      size: vol,
      group: causa
    });
  }
  return points;
}

export type SubjectModelSummary = {
  subjectName: string;
  subjectFromFilter: boolean;
  totalSp: number;
  subjectTotal: number;
  subjectShare: number;
  evaluatedSp: number;
  evaluatedShareSp: number;
  evaluatedConfidenceNote: "high" | "high_low";
  categoriesFound: number;
  categoryDistribution: { categoria: string; value: number; pct: number }[];
  severityDistribution: SeverityBucket[];
  hasSubjectScopedEvaluation: boolean;
};

/**
 * Build the Subject/Model coverage summary for the MIS executive screen.
 *
 * Conservative interpretation of "avaliado pelo modelo": records with
 * causa_canonica_confidence in {high, low}. The current Web aggregation
 * contract does not expose evaluation counts joined to a specific assunto,
 * so subject-scoped evaluation rate is reported as a global SP coverage
 * proxy — flagged to the UI via `hasSubjectScopedEvaluation=false`.
 */
export function buildSubjectModelSummary(args: {
  topAssuntos: readonly TopAssuntoRow[];
  classifierCoverage: readonly ClassifierCoverageRow[];
  categoryBreakdown: readonly CategoryBreakdownRow[];
  severityHeatmap: readonly SeverityHeatmapRow[];
  misRegions: readonly MisRegionRow[];
  selectedAssunto?: string | null;
  scopeRegiao?: string;
}): SubjectModelSummary {
  const region = (args.scopeRegiao ?? "SP").toUpperCase();
  const totalSp = args.misRegions
    .filter((r) => String(r.regiao ?? "").toUpperCase() === region)
    .reduce((s, r) => s + Number(r.volume_total ?? 0), 0);

  const subjectsSorted = [...args.topAssuntos]
    .filter((row) => row.assunto && String(row.assunto).trim() !== "")
    .sort((a, b) => Number(b.qtd_ordens ?? 0) - Number(a.qtd_ordens ?? 0));
  const explicit = args.selectedAssunto?.trim();
  const fallback = subjectsSorted[0];
  const chosen = explicit
    ? subjectsSorted.find((r) => r.assunto === explicit) ?? fallback
    : fallback;

  const subjectName = chosen?.assunto ?? "—";
  const subjectTotal = Number(chosen?.qtd_ordens ?? 0);
  const subjectShare = totalSp > 0 ? (subjectTotal / totalSp) * 100 : 0;

  const spCoverage = args.classifierCoverage.filter(
    (r) => String(r.regiao ?? "").toUpperCase() === region
  );
  const totalSpCoverage = spCoverage.reduce(
    (s, r) => s + Number(r.qtd_ordens ?? 0),
    0
  );
  const evaluatedSp = spCoverage
    .filter((r) => {
      const k = String(r.causa_canonica_confidence ?? "").toLowerCase();
      return k === "high" || k === "low";
    })
    .reduce((s, r) => s + Number(r.qtd_ordens ?? 0), 0);
  const evaluatedShareSp =
    totalSpCoverage > 0 ? (evaluatedSp / totalSpCoverage) * 100 : 0;
  const hasLowBucket = spCoverage.some(
    (r) => String(r.causa_canonica_confidence ?? "").toLowerCase() === "low"
  );

  const spCategories = args.categoryBreakdown.filter(
    (r) => String(r.regiao ?? "").toUpperCase() === region
  );
  const totalSpCat = spCategories.reduce(
    (s, r) => s + Number(r.qtd_erros ?? 0),
    0
  );
  const categoryAccum = new Map<string, number>();
  for (const row of spCategories) {
    const key = String(row.categoria ?? "nao_classificada");
    categoryAccum.set(key, (categoryAccum.get(key) ?? 0) + Number(row.qtd_erros ?? 0));
  }
  const categoryDistribution = Array.from(categoryAccum.entries())
    .map(([categoria, value]) => ({
      categoria,
      value,
      pct: totalSpCat > 0 ? (value / totalSpCat) * 100 : 0
    }))
    .sort((a, b) => b.value - a.value);

  const severityDistribution = buildSeverityDistribution(args.severityHeatmap, {
    regiao: region
  });

  return {
    subjectName,
    subjectFromFilter: Boolean(explicit),
    totalSp,
    subjectTotal,
    subjectShare,
    evaluatedSp,
    evaluatedShareSp,
    evaluatedConfidenceNote: hasLowBucket ? "high_low" : "high",
    categoriesFound: categoryDistribution.length,
    categoryDistribution,
    severityDistribution,
    hasSubjectScopedEvaluation: false
  };
}

const PT_MONTH: Record<string, string> = {
  "01": "jan",
  "02": "fev",
  "03": "mar",
  "04": "abr",
  "05": "mai",
  "06": "jun",
  "07": "jul",
  "08": "ago",
  "09": "set",
  "10": "out",
  "11": "nov",
  "12": "dez"
};

export function labelMonthPt(iso: string): string {
  if (!iso) return "—";
  const m = iso.slice(5, 7);
  const y = iso.slice(2, 4);
  return (PT_MONTH[m] ?? m) + "/" + y;
}

export type MonthlyEvaluatedPoint = {
  iso: string;
  label: string;
  total: number;
};

/**
 * Monthly series for the SP scope. The Web contract currently does not split
 * "avaliados" per month, so this returns the SP total per month — the caller
 * should explain the limitation in the surrounding card text.
 */
export function buildMonthlyEvaluatedSeries(
  rows: readonly MisMonthlyRow[],
  options: { regiao?: string; maxMonths?: number } = {}
): MonthlyEvaluatedPoint[] {
  const region = (options.regiao ?? "SP").toUpperCase();
  const filtered = rows
    .filter((r) => String(r.regiao ?? "").toUpperCase() === region && r.mes_ingresso)
    .sort((a, b) => String(a.mes_ingresso).localeCompare(String(b.mes_ingresso)));
  const max = options.maxMonths ?? 12;
  const tail = filtered.slice(-max);
  return tail.map((r) => ({
    iso: String(r.mes_ingresso),
    label: labelMonthPt(String(r.mes_ingresso)),
    total: Number(r.qtd_erros ?? 0)
  }));
}

export function pickAssuntoLiderValor(rows: readonly AssuntoLiderRow[]): {
  valor: number;
  assunto: string;
  hasValue: boolean;
} {
  const sp = rows.find((r) => String(r.regiao ?? "").toUpperCase() === "SP");
  const valor = Number(sp?.valor_fatura_reclamada_medio ?? 0);
  return {
    valor,
    assunto: String(sp?.assunto_lider ?? ""),
    hasValue: valor > 0 && !!sp?.assunto_lider
  };
}

export type FaturaMedidorRow = {
  regiao: string;
  tipo_medidor_dominante: string;
  qtd_ordens: number;
  qtd_instalacoes: number;
  valor_fatura_reclamada_medio: number;
  valor_fatura_reclamada_max: number;
};

/**
 * Weighted mean of valor_fatura_reclamada_medio across rows, weighted by qtd_ordens.
 * Returns 0 when nothing weighable — caller chooses fallback rendering.
 */
export function weightedFaturaMedia(rows: readonly FaturaMedidorRow[]): {
  valor: number;
  qtdOrdens: number;
  qtdInstalacoes: number;
  totalReclamado: number;
} {
  let weight = 0;
  let weighted = 0;
  let installs = 0;
  for (const row of rows) {
    const w = Number(row.qtd_ordens ?? 0);
    const v = Number(row.valor_fatura_reclamada_medio ?? 0);
    if (!Number.isFinite(w) || !Number.isFinite(v) || w <= 0 || v <= 0) continue;
    weight += w;
    weighted += w * v;
    installs += Number(row.qtd_instalacoes ?? 0);
  }
  const valor = weight > 0 ? weighted / weight : 0;
  return {
    valor,
    qtdOrdens: weight,
    qtdInstalacoes: installs,
    totalReclamado: weighted
  };
}

export type CategoriaSubcausaTreeRow = {
  categoria_id: string;
  categoria_label: string;
  categoria_qtd: number;
  categoria_pct: number;
  subcausa_id: string;
  subcausa_label: string;
  qtd: number;
  percentual_na_categoria: number;
  procedentes: number;
  improcedentes: number;
  exemplo_id: string;
  exemplo_data: string;
  exemplo_descricao: string;
  exemplo_status: string;
  exemplo_valor_fatura: number;
  recomendacao_operacional: string;
};

export type CategoriaTreeNode = {
  categoria_id: string;
  categoria_label: string;
  categoria_qtd: number;
  categoria_pct: number;
  procedentes: number;
  improcedentes: number;
  subcausas: CategoriaSubcausaTreeRow[];
};

/**
 * Group flat tree rows by categoria, summing exact procedente/improcedente
 * counts from the data plane (no proxy). Sorted by categoria volume desc.
 */
export function groupCategoriaSubcausaTree(
  rows: readonly CategoriaSubcausaTreeRow[]
): CategoriaTreeNode[] {
  const map = new Map<string, CategoriaTreeNode>();
  for (const row of rows) {
    const id = String(row.categoria_id ?? "nao_classificada");
    const node = map.get(id) ?? {
      categoria_id: id,
      categoria_label: row.categoria_label || formatCategoria(id),
      categoria_qtd: Number(row.categoria_qtd ?? 0),
      categoria_pct: Number(row.categoria_pct ?? 0),
      procedentes: 0,
      improcedentes: 0,
      subcausas: []
    };
    node.procedentes += Number(row.procedentes ?? 0);
    node.improcedentes += Number(row.improcedentes ?? 0);
    node.subcausas.push(row);
    map.set(id, node);
  }
  for (const node of map.values()) {
    node.subcausas.sort((a, b) => Number(b.qtd ?? 0) - Number(a.qtd ?? 0));
  }
  return Array.from(map.values()).sort((a, b) => b.categoria_qtd - a.categoria_qtd);
}

export type CauseRankingRow = {
  id: string;
  label: string;
  vol: number;
  proc: number;
  improc: number;
  pctProcedentes: number;
  reinc: number;
  categoria: string;
};

export type CauseRankingSourceRow = {
  id?: string;
  nome?: string;
  vol?: number;
  proc?: number;
  reinc?: number;
  cat?: string;
};

/**
 * Convert the sp_severidade_*_causas scatter payload into a ranked,
 * UI-friendly model. proc on the wire is `% procedência`. We re-derive
 * absolute counts (procedentes/improcedentes) from the volume so the
 * surface stays exact rather than presenting a percentage as a raw number.
 */
export function buildCauseRanking(
  rows: readonly CauseRankingSourceRow[]
): CauseRankingRow[] {
  return rows
    .map((row) => {
      const vol = Math.max(0, Number(row.vol ?? 0));
      const pctProc = Math.max(0, Math.min(100, Number(row.proc ?? 0)));
      const procedentes = Math.round((pctProc / 100) * vol);
      const improcedentes = Math.max(0, vol - procedentes);
      const id = String(row.id ?? row.nome ?? "");
      const nome = String(row.nome ?? row.id ?? "");
      return {
        id,
        label: formatCausa(nome),
        vol,
        proc: procedentes,
        improc: improcedentes,
        pctProcedentes: pctProc,
        reinc: Math.max(0, Number(row.reinc ?? 0)),
        categoria: String(row.cat ?? "nao_classificada")
      };
    })
    .filter((r) => r.vol > 0)
    .sort((a, b) => b.vol - a.vol);
}

/**
 * Weighted procedência share for the focused severities in SP using
 * severity_heatmap rows. taxa_refaturamento ≈ procedência operacional.
 *
 * @deprecated Substituído por contagens exatas das views
 *   sp_severidade_demais_overview / sp_severidade_demais_causas. Mantido
 *   somente para compatibilidade com chamadores antigos — não usar em UI.
 */
export function buildProcedenciaSplit(
  rows: readonly SeverityHeatmapRow[],
  options: { regiao?: string; severities?: readonly Severity[] } = {}
): {
  total: number;
  procedentes: number;
  improcedentes: number;
  pctProcedentes: number;
} {
  const target = (options.regiao ?? "SP").toUpperCase();
  const filterSet = new Set(options.severities ?? SEVERITY_ORDER);
  let total = 0;
  let weightedRefat = 0;
  for (const row of rows) {
    if (String(row.regiao ?? "").toUpperCase() !== target) continue;
    const sev = String(row.severidade ?? "").toLowerCase();
    if (!isSeverity(sev) || !filterSet.has(sev)) continue;
    const vol = Number(row.qtd_erros ?? 0);
    if (vol <= 0) continue;
    total += vol;
    weightedRefat += vol * Number(row.taxa_refaturamento ?? 0);
  }
  const procedentes = total > 0 ? weightedRefat : 0;
  const improcedentes = Math.max(0, total - procedentes);
  return {
    total,
    procedentes,
    improcedentes,
    pctProcedentes: total > 0 ? (procedentes / total) * 100 : 0
  };
}
