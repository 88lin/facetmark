import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

const report = { pages_attempted: 2, pages_fetched: 1, inserted: 1, already_known: 0, bodies_stored: 1,
  errors: 1, skipped: 0, robots_denied: 0, privacy_skipped: 0, off_domain_skipped: 1, notes: ["Synthetic HTTP 404"] };
async function fixture(page: Page) {
  const control = { job: { state: "idle" } as Record<string, unknown>, starts: [] as Record<string, unknown>[],
    stops: 0, reads: 0, conflict: false, readFailure: false, stopWait: null as Promise<void> | null };
  await page.route("**/admin/crawl", async route => {
    if (route.request().method() === "POST") {
      const options = route.request().postDataJSON(); control.starts.push(options);
      if (control.conflict) return route.fulfill({ status: 409, json: { detail: "Synthetic active task conflict" } });
      control.job = { id: "synthetic-site-job", state: "running", params: options, report, cancel_requested: false };
    } else {
      control.reads++;
      if (control.readFailure) return route.fulfill({ status: 503, json: { detail: "Synthetic site status unavailable" } });
    }
    return route.fulfill({ json: control.job });
  });
  await page.route("**/admin/crawl/cancel", async route => {
    control.stops++;
    if (control.stopWait) await control.stopWait;
    control.job = { ...control.job, state: "cancelled", retryable: true, cancel_requested: true };
    return route.fulfill({ json: control.job });
  });
  return control;
}
async function enter(page: Page) {
  await page.goto("/app");
  await page.getByRole("button", { name: "导入书签", exact: true }).click();
  const panel = page.locator(".site-import");
  await panel.locator(":scope > summary").click();
  await expect(panel.getByRole("button", { name: "刷新状态", exact: true })).toBeEnabled();
  return panel;
}
test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test("site import defaults to a small same-site budget and shows real outcomes", async ({ page }) => {
  const control = await fixture(page), panel = await enter(page);
  await expect(panel.getByLabel("最多扫描页数", { exact: true })).toHaveValue("25");
  await expect(panel.getByLabel("只跟随同站点链接", { exact: true })).toBeChecked();
  await panel.getByLabel("起始网址", { exact: true }).fill("https://docs.synthetic.invalid/guide/");
  await panel.getByLabel("最多扫描页数", { exact: true }).fill("8");
  await panel.getByRole("button", { name: "开始网站导入", exact: true }).click();
  await expect.poll(() => control.starts[0]).toEqual({ start_url: "https://docs.synthetic.invalid/guide/", max_pages: 8, same_domain: true });
  await expect(panel.getByRole("progressbar")).toHaveAttribute("max", "8");
  await expect(panel.getByRole("progressbar")).toHaveAttribute("value", "2");
  control.job = { ...control.job, state: "partial", retryable: true };
  await panel.getByRole("button", { name: "刷新状态", exact: true }).click();
  await expect(panel.locator(".site-import-result > strong")).toHaveText("扫描完成，部分页面未能导入");
  await expect(panel.locator(".site-import-result dl")).toContainText("新增收藏1");
  await expect(panel.locator(".site-import-result dl")).toContainText("获取失败1");
  await panel.locator(".site-import-notes > summary").click();
  await expect(panel.locator(".site-import-notes")).toContainText("Synthetic HTTP 404");
  await expect(panel.getByRole("button", { name: "重新导入这个网站", exact: true })).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/polish-site-import-partial.png", fullPage: true });
});

test("Stop joins the active task once and retains imported pages and the rerun parameters", async ({ page }) => {
  const control = await fixture(page), panel = await enter(page);
  await panel.getByLabel("起始网址", { exact: true }).fill("https://docs.synthetic.invalid/");
  await panel.getByRole("button", { name: "开始网站导入", exact: true }).click();
  const stop = panel.getByRole("button", { name: "停止网站导入", exact: true });
  await expect(stop).toBeVisible();
  let release!: () => void;
  control.stopWait = new Promise(resolve => { release = resolve; });
  await stop.click();
  await expect(panel.getByRole("button", { name: "正在停止…", exact: true })).toBeDisabled();
  release();
  await expect(panel.locator(".site-import-result > strong")).toContainText("已保存的页面仍可使用");
  expect(control.stops).toBe(1);
  await expect(panel.locator(".site-import-result dl")).toContainText("新增收藏1");
  await panel.getByRole("button", { name: "重新导入这个网站", exact: true }).click();
  await expect.poll(() => control.starts.length).toBe(2);
  expect(control.starts[1]).toEqual(control.starts[0]);
});

test("reopening the import page finds a background task without starting it again", async ({ page }) => {
  const control = await fixture(page), panel = await enter(page);
  await panel.getByLabel("起始网址", { exact: true }).fill("https://docs.synthetic.invalid/");
  await panel.getByRole("button", { name: "开始网站导入", exact: true }).click();
  await expect(panel.getByRole("button", { name: "停止网站导入", exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "导入书签", exact: true }).click();
  await page.locator(".site-import > summary").click();
  await expect(page.locator(".site-import").getByRole("button", { name: "停止网站导入", exact: true })).toBeVisible();
  expect(control.starts).toHaveLength(1);
  await expect(page.locator(".site-import").getByLabel("起始网址", { exact: true })).toHaveValue("https://docs.synthetic.invalid/");
});

test("a start conflict and invalid credentials keep the draft and do not report completion", async ({ page }) => {
  const control = await fixture(page), panel = await enter(page);
  await panel.getByLabel("起始网址", { exact: true }).fill("https://user:password@docs.synthetic.invalid/");
  await panel.getByRole("button", { name: "开始网站导入", exact: true }).click();
  await expect(panel.getByRole("alert")).toContainText("有效的 HTTP(S)");
  expect(control.starts).toHaveLength(0);
  await panel.getByLabel("起始网址", { exact: true }).fill("https://docs.synthetic.invalid/");
  control.conflict = true;
  await panel.getByRole("button", { name: "开始网站导入", exact: true }).click();
  await expect(panel.getByRole("alert")).toContainText("Synthetic active task conflict");
  await expect(panel.getByLabel("起始网址", { exact: true })).toHaveValue("https://docs.synthetic.invalid/");
  await expect(panel.locator(".site-import-result > strong")).toHaveText("按需导入一个网站");
  control.conflict = false;
  await panel.getByRole("button", { name: "开始网站导入", exact: true }).click();
  await expect(panel.getByRole("button", { name: "停止网站导入", exact: true })).toBeVisible();
});

test("status recovery, narrow dark layout and reduced motion keep the optional form usable", async ({ page }) => {
  const control = await fixture(page);
  control.readFailure = true;
  const panel = await enter(page);
  await expect(panel.getByRole("alert")).toContainText("Synthetic site status unavailable");
  control.readFailure = false;
  control.job = { id: "interrupted", state: "interrupted", retryable: true, report,
    params: { start_url: "https://docs.synthetic.invalid/", max_pages: 25, same_domain: true } };
  await panel.getByRole("button", { name: "刷新状态", exact: true }).click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("button", { name: "切换主题", exact: true }).click();
  await expect(panel.getByRole("button", { name: "重新导入这个网站", exact: true })).toBeVisible();
  await settleVisualLayout(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
  await page.screenshot({ path: "screenshots/collection-review/polish-site-import-mobile-dark.png", fullPage: true });
});
