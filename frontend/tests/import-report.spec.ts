import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

const fullReport = { parsed: 6, inserted: 4, updated: 2, merged_duplicates: 0, privacy_skipped: 0,
  non_indexable: 0, missing_dates: 0, folders: 2, max_depth: 2, warnings: [],
  restored_bodies: 3, restored_summaries: 2, restored_conversations: 1, restored_messages: 4 };
async function openImporter(page: Page) {
  await page.goto("/app");
  await page.getByRole("button", { name: "导入书签", exact: true }).click();
  await expect(page.locator(".importer")).toBeVisible();
  return page.locator(".importer");
}
async function upload(page: Page, name = "synthetic-bookmarks.json") {
  const panel = page.locator(".importer");
  await expect(panel.getByRole("button", { name: "选择文件", exact: true })).toBeEnabled();
  await panel.locator('input[type="file"]').setInputFiles({ name, mimeType: "application/json",
    buffer: Buffer.from('{"format":"synthetic","bookmarks":[]}') });
}
test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test("file import reports parsed and restored content without opening optional site import", async ({ page }) => {
  let requests = 0, crawls = 0;
  await page.route("**/admin/import", route => { requests++; return route.fulfill({ json: fullReport }); });
  await page.route("**/admin/crawl", route => { crawls++; return route.fulfill({ json: { state: "idle" } }); });
  const panel = await openImporter(page);
  await expect(panel.locator(".site-import")).not.toHaveAttribute("open", "");
  await upload(page);
  const result = panel.locator(".import-result");
  await expect(result).toHaveAttribute("data-outcome", "complete");
  await expect(result.locator('[data-metric="parsed"] dd')).toHaveText("6");
  await expect(result.locator('[data-metric="inserted"] dd')).toHaveText("4");
  await expect(result.locator('[data-metric="updated"] dd')).toHaveText("2");
  for (const [key, count] of Object.entries({ restored_bodies: 3, restored_summaries: 2, restored_conversations: 1, restored_messages: 4 }))
    await expect(result.locator(`[data-metric="${key}"] dd`)).toHaveText(String(count));
  await expect(result.locator('[data-metric="errors"]')).toHaveCount(0);
  await expect(result.locator('[data-metric="skipped"]')).toHaveCount(0);
  expect(requests).toBe(1); expect(crawls).toBe(0);
  await result.scrollIntoViewIfNeeded(); await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/import-report-restored-1280.png", animations: "disabled" });
  await page.setViewportSize({ width: 320, height: 640 });
  await result.scrollIntoViewIfNeeded(); await settleVisualLayout(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "screenshots/collection-review/import-report-restored-320.png", animations: "disabled" });
});

test("zero and partial imports remain distinct and metadata exclusions are not import failures", async ({ page }) => {
  const reports = [
    { parsed: 0, inserted: 0, updated: 0, warnings: ["Synthetic empty export"] },
    { total_parsed: 8, inserted: 5, updated: 1, merged_duplicates: 2, privacy_skipped: 2,
      non_indexable: 1, missing_dates: 3, warnings: ["Synthetic item https://fixture.invalid/page has no date", "Synthetic folder C:\\fixture\\export has incomplete saved text"],
      restored_bodies: 1, restored_summaries: 0, restored_conversations: 0, restored_messages: 0 },
    { parsed: 5, inserted: 2, updated: 0, merged_duplicates: 1, skipped: 1, errors: 1, warnings: ["Synthetic partial report"] },
  ];
  await page.route("**/admin/import", route => route.fulfill({ json: reports.shift() }));
  const panel = await openImporter(page), result = panel.locator(".import-result");
  await upload(page);
  await expect(result).toHaveAttribute("data-outcome", "empty");
  await expect(result.locator(".import-result-heading")).toHaveText("没有新增或更新的收藏");
  await expect(panel.getByRole("button", { name: "查看已导入的收藏", exact: true })).toHaveCount(0);
  await upload(page);
  await expect(result).toHaveAttribute("data-outcome", "review");
  await expect(result.locator('[data-metric="parsed"] dd')).toHaveText("8");
  await expect(result.locator('[data-metric="inserted"] dd')).toHaveText("5");
  await expect(result.locator('[data-metric="privacy_skipped"] dd')).toHaveText("2");
  await expect(result.locator('[data-metric="non_indexable"] dd')).toHaveText("1");
  await expect(result.locator(".import-warnings")).toContainText("https://fixture.invalid/page");
  await expect(result.locator(".import-warnings")).toContainText("C:\\fixture\\export");
  await expect(result.locator('[data-metric="errors"]')).toHaveCount(0);
  await upload(page);
  await expect(result).toHaveAttribute("data-outcome", "partial");
  await expect(result.locator('[data-metric="skipped"] dd')).toHaveText("1");
  await expect(result.locator('[data-metric="errors"] dd')).toHaveText("1");
  await expect(result.locator(".import-result-heading")).toContainText("部分内容未能导入");
});

test("failed upload supports a single keyboard retry and validates the file before sending", async ({ page }) => {
  let requests = 0, release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/admin/import", async route => {
    requests++;
    if (requests === 1) return route.fulfill({ status: 503, json: { detail: "Synthetic import service unavailable" } });
    await gate; return route.fulfill({ json: { parsed: 1, inserted: 1, updated: 0, warnings: [] } });
  });
  const panel = await openImporter(page);
  await upload(page, "synthetic.txt");
  await expect(panel.locator(".import-error")).toContainText("请选择 HTML 或 JSON");
  expect(requests).toBe(0);
  await upload(page);
  await expect(panel.locator(".import-error")).toContainText("Synthetic import service unavailable");
  const retry = panel.getByRole("button", { name: "重试导入", exact: true });
  await retry.focus(); await retry.press("Enter");
  await expect.poll(() => requests).toBe(2);
  await expect(panel.getByRole("button", { name: "正在导入…", exact: true })).toBeDisabled();
  await page.keyboard.press("Enter"); expect(requests).toBe(2);
  release();
  await expect(panel.locator(".import-result")).toHaveAttribute("data-outcome", "complete");
  await expect(panel.locator(".import-error")).toHaveCount(0);
  const done = panel.getByRole("button", { name: "查看已导入的收藏", exact: true });
  await expect(done).toBeEnabled();
  await done.focus(); await done.press("Space");
  await expect(page.locator(".workspace-search")).toBeVisible();
});
