import { expect, test } from "@playwright/test";

test("web shell renders operational navigation", async ({ page }) => {
  await page.route("**/v1/dataset/version", async (route) => {
    await route.fulfill({
      json: { hash: "dataset-1234567890", sources: ["silver.csv"], generated_at: "2026-01-01" }
    });
  });
  await page.route("**/v1/aggregations/**", async (route) => {
    await route.fulfill({
      json: {
        view_id: "overview",
        dataset_hash: "dataset-1234567890",
        filters: {},
        data: [
          {
            total_registros: 10,
            regioes: 2,
            topicos: 3,
            taxa_refaturamento: 0.2,
            volume_total: 10,
            regiao: "CE"
          }
        ]
      }
    });
  });

  await page.goto("/chat");

  await expect(page.getByText("ENEL Analytics")).toBeVisible();
  await expect(page.getByRole("link", { name: "MIS" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Chat conectado/ })).toBeVisible();
});
