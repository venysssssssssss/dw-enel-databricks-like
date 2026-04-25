import { expect, test, type Route } from "@playwright/test";

const dataset = { hash: "dataset-sev-123", sources: ["silver.csv"], generated_at: "2026-01-01" };

function aggregationPayload(viewId: string) {
  const common = { view_id: viewId, dataset_hash: dataset.hash, filters: {} };
  if (viewId.endsWith("_overview")) {
    const critical = viewId.includes("critica");
    return {
      ...common,
      data: [
        {
          total: critical ? 1399 : 4223,
          procedentes: critical ? 1171 : 2867,
          improcedentes: critical ? 228 : 1356,
          pct_procedentes: critical ? 0.837 : 0.679,
          reincidentes_clientes: critical ? 298 : 624,
          valor_medio_fatura: critical ? 2847.6 : 487.3,
          categorias_count: critical ? 9 : 14,
          top3_share: critical ? 0.622 : 0.553,
          delta_trimestre: critical ? 0.118 : 0.072
        }
      ]
    };
  }
  if (viewId.endsWith("_mensal")) {
    return {
      ...common,
      data: [
        { mes_ingresso: "2026-01-01", qtd_erros: 310, procedentes: 180, improcedentes: 130 },
        { mes_ingresso: "2026-02-01", qtd_erros: 420, procedentes: 260, improcedentes: 160 },
        { mes_ingresso: "2026-03-01", qtd_erros: 510, procedentes: 310, improcedentes: 200 }
      ]
    };
  }
  if (viewId.endsWith("_categorias")) {
    return {
      ...common,
      data: [
        { categoria_id: "faturamento", categoria: "Faturamento por estimativa", vol: 982, pct: 23.3 },
        { categoria_id: "medidor", categoria: "Medidor com defeito", vol: 741, pct: 17.5 }
      ]
    };
  }
  if (viewId.endsWith("_causas")) {
    return {
      ...common,
      data: [
        { id: "c01", nome: "Digitação", vol: 782, proc: 71.2, reinc: 148, cat: "operacional" },
        { id: "c02", nome: "Estimativa prolongada", vol: 621, proc: 84.7, reinc: 132, cat: "estimativa" }
      ]
    };
  }
  if (viewId.endsWith("_ranking")) {
    return {
      ...common,
      data: [
        { inst: "INS-4782901", cat: "Faturamento por estimativa", causa: "Estimativa prolongada", reinc: 9, valor: 1284.4, spark: [2, 3, 4, 4, 5, 5, 6, 7, 9], cidade: "SP/SP" },
        { inst: "INS-3918205", cat: "Leitura divergente", causa: "Digitação", reinc: 8, valor: 987.12, spark: [1, 2, 3, 4, 4, 5, 6, 7, 8], cidade: "SP/SP" },
        { inst: "INS-5620144", cat: "Consumo atípico", causa: "Sensor TC/TP", reinc: 7, valor: 2104.88, spark: [1, 1, 2, 3, 4, 5, 5, 6, 7], cidade: "SP/SP" }
      ]
    };
  }
  return { ...common, data: [] };
}

async function mockApi(route: Route) {
  const url = new URL(route.request().url());
  if (url.pathname === "/v1/dataset/version") {
    await route.fulfill({ json: dataset });
    return;
  }
  const match = url.pathname.match(/\/v1\/aggregations\/([^/]+)/);
  if (match) {
    await route.fulfill({ json: aggregationPayload(match[1]) });
    return;
  }
  await route.continue();
}

test.beforeEach(async ({ page }) => {
  await page.route("**/v1/**", mockApi);
});

test("severity pages render, filter and navigate with keyboard shortcuts", async ({ page }) => {
  await page.goto("/bi/severidade-alta");

  await expect(page.getByText("ENEL Analytics")).toBeVisible();
  await expect(page.getByText("Severidade /")).toBeVisible();
  await expect(page.locator(".crumbs").getByText("Alta · SP")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Pressão operacional/ })).toBeVisible();
  await expect(page.getByText("4.223").first()).toBeVisible();

  const firstCategory = page.locator(".sev-hbar-row").first();
  await firstCategory.click();
  await expect(firstCategory).toHaveClass(/is-active/);
  await expect(page.getByRole("link", { name: "limpar filtro" })).toBeVisible();

  await page.locator(".sev-bar").first().hover();
  await expect(page.locator(".sev-tt.is-on")).toContainText("reclamações no mês");

  await expect(page.locator("tr.top-3")).toHaveCount(3);

  await page.keyboard.press("3");
  await expect(page).toHaveURL(/\/bi\/severidade-critica$/);
  await expect(page.locator(".crumbs").getByText("Crítica · SP")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Baixo volume/ })).toBeVisible();
});
