import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.skip(process.env.FACETMARK_LARGE_VALIDATION !== "1", "Runs in the separate 200k cloud matrix");

test("200k actual records stay paginated and all matching selection survives deep paging", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.locator(".library-manage > summary").click();
  await page.getByRole("button", { name: "批量管理", exact: true }).click();
  await expect(page.getByRole("button", { name: "全选 200,000 条用于摘要", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "全选 200,000 条用于摘要", exact: true }).click();
  await page.locator(".bookmark-check").first().uncheck();
  await page.locator(".bookmark-check").nth(1).uncheck();
  await expect(page.locator(".collection-selection")).toContainText("已选 199,998 条");
  const jump = page.getByRole("spinbutton", { name: "跳转页码" });
  await jump.fill("6667");
  await jump.press("Enter");
  await expect(page.locator(".results-footer")).toContainText("199981–200000");
  await expect(page.locator(".result-row")).toHaveCount(20);
  await expect(page.locator(".bookmark-check:checked")).toHaveCount(20);
  await expect(page.locator(".collection-selection")).toContainText("已选 199,998 条");
  const request = page.waitForRequest(r => r.url().includes("/admin/jobs/preview"));
  await page.getByRole("button", { name: "生成所选摘要", exact: true }).click();
  const body = (await request).postDataJSON();
  expect(body.bookmark_ids).toBeUndefined();
  expect(body.scope.exclude_ids).toHaveLength(2);
  expect(JSON.stringify(body).length).toBeLessThan(1000);
  const dialog = page.getByRole("dialog", { name: "生成 AI 摘要", exact: true });
  await expect(dialog.locator(".processing-count")).toContainText("本次将处理");
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await page.locator(".collection-selection").getByRole("button", { name: "清空", exact: true }).click();
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill("needle");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await expect(page.locator(".result-title").first()).toContainText("needle");
  expect(await page.locator(".result-row").count()).toBeLessThanOrEqual(30);
  await mkdir("screenshots", { recursive: true });
  await page.screenshot({ path: "screenshots/collection-200k.png", animations: "disabled" });
});
