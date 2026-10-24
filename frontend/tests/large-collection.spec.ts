import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.skip(process.env.FACETMARK_LARGE_VALIDATION !== "1", "Runs in the separate 200k cloud matrix");

test("200k actual records stay paginated and all matching selection survives deep paging", async ({ page }) => {
  let started: Record<string, unknown> | null = null;
  await page.route("**/admin/jobs/start", route => {
    started = route.request().postDataJSON();
    return route.fulfill({ json: { id: "synthetic-summary", state: "done", params: started } });
  });
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const selectAll = page.getByRole("checkbox", { name: "全选当前结果", exact: true });
  await expect(selectAll).toBeVisible();
  await selectAll.check();
  await page.locator(".bookmark-check").first().uncheck();
  await page.locator(".bookmark-check").nth(1).uncheck();
  await expect(page.locator(".library-selection-count")).toHaveText("已选 199,998");
  await expect(selectAll).toHaveJSProperty("indeterminate", true);
  await expect(page.locator(".collection-selection")).toHaveCount(0);
  const jump = page.getByRole("spinbutton", { name: "跳转页码" });
  await jump.fill("6667");
  await jump.press("Enter");
  await expect(page.locator(".results-footer")).toContainText("199981–200000");
  await expect(page.locator(".result-row")).toHaveCount(20);
  await expect(page.locator(".bookmark-check:checked")).toHaveCount(20);
  await expect(page.locator(".library-selection-count")).toHaveText("已选 199,998");
  const request = page.waitForRequest(r => r.url().includes("/admin/jobs/preview"));
  await page.getByRole("button", { name: "生成摘要", exact: true }).click();
  const body = (await request).postDataJSON();
  expect(body.bookmark_ids).toBeUndefined();
  expect(body.scope.exclude_ids).toHaveLength(2);
  expect(body.force).toBe(true);
  expect(JSON.stringify(body).length).toBeLessThan(1000);
  await expect.poll(() => started).toEqual(expect.objectContaining({
    mode: "summarize", scope: body.scope, force: true, confirmed: true, summary_language: "zh",
  }));
  await expect(page.getByRole("dialog", { name: "生成 AI 摘要", exact: true })).toHaveCount(0);
  await expect(selectAll).not.toBeChecked();
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill("needle");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await expect(page.locator(".result-title").first()).toContainText("needle");
  expect(await page.locator(".result-row").count()).toBeLessThanOrEqual(30);
  await mkdir("screenshots", { recursive: true });
  await page.screenshot({ path: "screenshots/collection-200k.png", animations: "disabled" });
});
