import { expect, test } from "@playwright/test";

test("walletless visitors can choose an explicit local replay", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Gold vs Silver" })).toBeVisible();
  await expect(page.getByText("Synthetic evidence demo")).toBeVisible();

  await page.getByRole("button", { name: "Start local replay" }).first().click();

  await expect(page.getByRole("button", { name: "Exit local replay" })).toBeVisible();
  await expect(page.locator(".entry-status")).toContainText("OPEN");
  await expect(page.getByRole("button", { name: /Place (GOLD|SILVER) position/ })).toBeVisible();
});

test("entry landmark and quick stake controls remain accessible", async ({ page }) => {
  await page.goto("/");
  const entryPanel = page.locator('aside[aria-labelledby="entry-heading"]');
  await expect(entryPanel).toHaveCount(1);
  await expect(page.locator("#entry-heading")).toHaveCount(1);

  for (const amount of ["10", "25", "50", "100"]) {
    await expect(page.getByRole("button", { name: amount, exact: true })).toHaveCSS("min-height", "44px");
  }
});

test("future synthetic evidence is withheld until the market closes", async ({ request }) => {
  const response = await request.get("/evidence/market-2030-01-01T00:00:00Z.json");
  expect(response.ok()).toBeTruthy();
  const evidence = await response.json();
  expect(evidence.status).toBe("PENDING_EVIDENCE");
  expect(evidence.reason_code).toBe("EVIDENCE_NOT_AVAILABLE");
  expect(evidence.outcome).toBeUndefined();
  expect(evidence.gold_closing_price).toBe(0);
});

test("closed historical synthetic evidence still has a canonical record", async ({ request }) => {
  const response = await request.get("/evidence/market-2020-01-01T00:00:00Z.json");
  expect(response.ok()).toBeTruthy();
  const evidence = await response.json();
  expect(evidence.status).toBe("FINALIZED");
  expect(evidence.evidence_hash).toMatch(/^sha256:[0-9a-f]{64}$/);
});

test("wallet-free comparison proofs expose alignment, arithmetic, and settlement state", async ({ page }) => {
  await page.goto("/comparison/metalswap-synthetic-2026-09-14-07-30-00z");
  await expect(page.getByRole("heading", { name: "Gold vs Silver settlement proof" })).toBeVisible();
  await expect(page.getByText("SYNTHETIC DEMO")).toBeVisible();
  await expect(page.getByText("FINALIZED", { exact: true })).toBeVisible();
  await expect(page.getByText("Duplicate claim rejected", { exact: false })).toBeVisible();
  await expect(page.getByText("Delayed publication does not make this outcome unpredictable.")).toBeVisible();
});

test("wallet-free XAUS replay shows real source references without presenting a wager", async ({ page }) => {
  await page.goto("/comparison/xaus-2026-09-14-09-00-00z");
  await expect(page.getByRole("heading", { name: "Gold vs Silver real-observation replay" })).toBeVisible();
  await expect(page.getByText("HISTORICAL REPLAY")).toBeVisible();
  await expect(page.getByText("Comparison-only replay")).toBeVisible();
  await expect(page.getByText("XAUUSD", { exact: true })).toBeVisible();
  await expect(page.getByText("XAGUSD", { exact: true })).toBeVisible();
});

test("wallet-free live XAUS case exposes observations, finality, and claims", async ({ page }) => {
  await page.goto("/comparison/xaus-live-2026-09-16-12-15-00z");
  await expect(page.getByRole("heading", { name: "Gold vs Silver live-interval proof" })).toBeVisible();
  await expect(page.getByText("INDICATIVE LIVE INTERVAL")).toBeVisible();
  await expect(page.getByText("SILVER outperformed")).toBeVisible();
  await expect(page.getByText("FINALIZED", { exact: true })).toBeVisible();
  await expect(page.getByText("Gate acknowledgment", { exact: false })).toBeVisible();
  await expect(page.getByText("Rotation / historical access", { exact: false })).toBeVisible();
});
