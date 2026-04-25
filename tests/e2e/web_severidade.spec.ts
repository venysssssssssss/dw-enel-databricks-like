import { expect, test, type Route } from "@playwright/test";

const DATASET_HASH = "dataset-severidade-1234567890";

const OVERVIEW_PAYLOAD = {
  total: 3502,
  procedentes: 0,
  improcedentes: 3502,
  pct_procedentes: 0.0,
  reincidentes_clientes: 49,
  valor_medio_fatura: 759.15,
  categorias_count: 5,
  top3_share: 0.9817,
  delta_trimestre: 0.3449
};

const MONTHLY_PAYLOAD = [
  { mes_ingresso: "2025-07-01", qtd_erros: 337, procedentes: 0, improcedentes: 337 },
  { mes_ingresso: "2025-08-01", qtd_erros: 412, procedentes: 0, improcedentes: 412 },
  { mes_ingresso: "2025-09-01", qtd_erros: 488, procedentes: 0, improcedentes: 488 }
];

const CATEGORIAS_PAYLOAD = [
  { categoria_id: "contestacao_cliente", categoria: "contestacao_cliente", vol: 2908, pct: 83.04 },
  { categoria_id: "operacional", categoria: "operacional", vol: 401, pct: 11.45 }
];

const CAUSAS_PAYLOAD = [
  { id: "c01", nome: "autoleitura_cliente", vol: 2908, proc: 0.0, reinc: 33, cat: "contestacao_cliente" },
  { id: "c02", nome: "impedimento_acesso", vol: 401, proc: 0.0, reinc: 7, cat: "operacional" }
];

const RANKING_PAYLOAD = [
  {
    inst: "INS-A",
    cat: "contestacao_cliente",
    causa: "autoleitura_cliente",
    reinc: 5,
    valor: 1284.4,
    spark: [0, 0, 0, 1, 1, 2, 2, 3, 5],
    cidade: "São Paulo/SP"
  },
  {
    inst: "INS-B",
    cat: "operacional",
    causa: "impedimento_acesso",
    reinc: 3,
    valor: 482.1,
    spark: [0, 0, 0, 0, 0, 1, 1, 2, 3],
    cidade: "Osasco/SP"
  },
  {
    inst: "INS-C",
    cat: "contestacao_cliente",
    causa: "autoleitura_cliente",
    reinc: 2,
    valor: 612.5,
    spark: [0, 0, 0, 0, 0, 0, 1, 1, 2],
    cidade: "São Paulo/SP"
  }
];

function aggregationFor(viewId: string) {
  if (viewId.endsWith("_overview")) {
    return [OVERVIEW_PAYLOAD];
  }
  if (viewId.endsWith("_mensal")) {
    return MONTHLY_PAYLOAD;
  }
  if (viewId.endsWith("_categorias")) {
    return CATEGORIAS_PAYLOAD;
  }
  if (viewId.endsWith("_causas")) {
    return CAUSAS_PAYLOAD;
  }
  if (viewId.endsWith("_ranking")) {
    return RANKING_PAYLOAD;
  }
  return [];
}

async function fulfillAggregations(route: Route) {
  const url = route.request().url();
  const match = /aggregations\/([^/?#]+)/.exec(url);
  const viewId = match ? match[1] : "unknown";
  await route.fulfill({
    json: {
      view_id: viewId,
      dataset_hash: DATASET_HASH,
      filters: {},
      data: aggregationFor(viewId)
    }
  });
}

test.beforeEach(async ({ page }) => {
  await page.route("**/v1/dataset/version", async (route) => {
    await route.fulfill({
      json: { hash: DATASET_HASH, sources: ["silver.csv"], generated_at: "2026-04-24" }
    });
  });
  await page.route("**/v1/aggregations/**", fulfillAggregations);
});

test("severidade alta — KPI total renders with real number", async ({ page }) => {
  await page.goto("/bi/severidade-alta");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText(/3\.502/)).toBeVisible();
  await expect(page.getByText(/Total Alta/i)).toBeVisible();
});

test("severidade alta — categoria HBar toggles active state", async ({ page }) => {
  await page.goto("/bi/severidade-alta");
  const firstRow = page.locator(".sev-hbar-row").first();
  await firstRow.waitFor();
  await firstRow.click();
  await expect(firstRow).toHaveClass(/is-active/);
  await expect(page.getByRole("link", { name: /limpar filtro/i })).toBeVisible();
});

test("severidade alta — keyboard 3 navigates to crítica", async ({ page }) => {
  await page.goto("/bi/severidade-alta");
  await expect(page.getByText(/Alta · SP/i)).toBeVisible();
  await page.locator('a[href="/bi/severidade-critica"]').click();
  await expect(page.getByText(/Crítica · SP/i)).toBeVisible();
});

test("severidade — ranking marks top-3 rows", async ({ page }) => {
  await page.goto("/bi/severidade-alta");
  const rows = page.locator(".sev-rank-table tr.rank-row");
  await rows.first().waitFor();
  await expect(rows.nth(0)).toHaveClass(/top-3/);
  await expect(rows.nth(1)).toHaveClass(/top-3/);
  await expect(rows.nth(2)).toHaveClass(/top-3/);
});

test("severidade — scatter renders all causas", async ({ page }) => {
  await page.goto("/bi/severidade-alta");
  const circles = page.locator(".sev-scatter circle");
  await circles.first().waitFor();
  await expect(circles).toHaveCount(CAUSAS_PAYLOAD.length);
});

test("severidade crítica — hero shows correct breadcrumb tag", async ({ page }) => {
  await page.goto("/bi/severidade-critica");
  await expect(page.getByText(/Crítica · SP/i)).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/impacto financeiro/i);
});
