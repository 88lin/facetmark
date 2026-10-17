import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await mkdir("screenshots", { recursive: true });
});

test("settings categories preserve drafts and support keyboard and narrow layouts", async ({ page }) => {
  await page.goto("/app#settings");
  const model = page.locator("input[name=chat_model]");
  await expect(model).toBeVisible();
  await model.fill("unsaved-model-draft");
  const ai = page.getByRole("tab", { name: "AI 连接", exact: true });
  await ai.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "设备同步", exact: true })).toBeFocused();
  await expect(page.locator(".sync-settings")).toBeVisible();
  await expect(model).toBeHidden();
  await page.screenshot({ path: "screenshots/support-sync-desktop.png", animations: "disabled" });
  await page.keyboard.press("Home");
  await expect(ai).toBeFocused();
  await expect(model).toHaveValue("unsaved-model-draft");
  await expect(page.getByRole("tabpanel")).toHaveCount(1);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "screenshots/support-settings-mobile.png", animations: "disabled" });
  await page.getByRole("tab", { name: "浏览器扩展", exact: true }).click();
  await expect(page.getByRole("heading", { name: "连接浏览器扩展" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: "screenshots/support-extension-mobile.png", animations: "disabled" });
  await ai.click();
  await expect(model).toHaveValue("unsaved-model-draft");
});

test("idle and paused tasks show truthful status and recover failed saved-task requests", async ({ page }) => {
  let failed = true;
  let current: Record<string, unknown> = { state: "idle" };
  await page.route("**/admin/job", route => route.fulfill({ json: current }));
  await page.route("**/admin/jobs", route => failed
    ? route.fulfill({ status: 503, json: { detail: "Synthetic saved-task failure" } })
    : route.fulfill({ json: { items: [] } }));
  await page.goto("/app");
  await page.getByRole("button", { name: "任务", exact: true }).click();
  await expect(page.locator(".tasks h2")).toHaveText("尚未开始");
  await expect(page.locator(".stages")).toHaveCount(0);
  await expect(page.locator(".index-consent")).not.toHaveAttribute("open", "");
  await expect(page.getByRole("alert")).toContainText("无法读取已保存的任务");
  failed = false;
  await page.getByRole("button", { name: "重试读取任务", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.screenshot({ path: "screenshots/support-tasks-idle.png", animations: "disabled" });
  current = { id: "synthetic-paused", state: "paused", resumable: true, current: "enrich", planned: ["enrich"], params: { mode: "summarize" }, items: { done: 24, total: 80, failed: 2 } };
  await expect(page.locator(".tasks h2")).toHaveText("任务已暂停", { timeout: 10000 });
  await expect(page.locator(".stages .spin")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "继续上次任务", exact: true })).toBeVisible();
  await expect(page.locator(".task-progress")).toContainText("2 条处理失败");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await expect(page.locator(".task-current")).toContainText("进度已保存");
  await expect(page.locator(".task-current")).not.toContainText("后台继续");
  const resume = page.getByRole("button", { name: "继续上次任务", exact: true });
  await expect(resume).toBeInViewport({ ratio: 1 });
  const resumeBounds = await resume.boundingBox();
  const newWorkBounds = await page.locator(".task-shortcuts").boundingBox();
  expect(resumeBounds!.y + resumeBounds!.height).toBeLessThanOrEqual(newWorkBounds!.y);
  await page.screenshot({ path: "screenshots/support-tasks-paused-mobile.png", animations: "disabled" });
  current = { ...current, params: { mode: "fetch" }, current: "fetch", planned: ["fetch"] };
  await expect(page.locator(".task-progress")).toContainText("2 条正文抓取失败", { timeout: 10000 });
  await expect(page.locator(".task-progress")).not.toContainText("筛选「失败」");
});

test("partial task recovery resumes the saved scope without starting broad work", async ({ page }) => {
  const current = { id: "original-scoped-task", state: "partial", resumable: true, params: { mode: "summarize", scope: { folder: "Research", status: "pending" } }, items: { done: 4, total: 5, failed: 1 } };
  let resumed: unknown;
  let started = false;
  await page.route("**/admin/job", route => route.fulfill({ json: current }));
  await page.route("**/admin/jobs", route => route.fulfill({ json: { items: [current] } }));
  await page.route("**/admin/jobs/resume", route => { resumed = route.request().postDataJSON(); return route.fulfill({ json: {} }); });
  await page.route("**/admin/jobs/start", route => { started = true; return route.fulfill({ json: {} }); });
  await page.goto("/app#tasks");
  await expect(page.locator(".task-scope")).toContainText("Research");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "screenshots/support-tasks-partial-mobile.png", animations: "disabled" });
  await page.getByRole("button", { name: "重试此任务失败项", exact: true }).click();
  await expect.poll(() => resumed).toEqual({ resume_id: current.id, confirmed: true });
  expect(started).toBe(false);
});

test("long excerpts remain expandable after changing display without changing text", async ({ page }) => {
  await page.route("**/bookmarks?**", async route => {
    const response = await route.fetch();
    const data = await response.json();
    data.items[0].summary = "";
    data.items[0].snippet = "没有摘要时仍然需要展开这段很长的网页摘录。".repeat(30);
    await route.fulfill({ response, json: data });
  });
  await page.goto("/app");
  const entry = page.locator(".result-row").first();
  await expect(entry.getByRole("button", { name: "展开全文", exact: true })).toBeVisible();
  await page.locator(".collection-options-menu > summary").click();
  await page.getByRole("button", { name: "原文摘录", exact: true }).click();
  await entry.getByRole("button", { name: "展开全文", exact: true }).click();
  expect(await entry.locator(".result-summary").evaluate(el => el.scrollHeight <= el.clientHeight + 1)).toBe(true);
  await page.getByRole("button", { name: "摘要", exact: true }).click();
  await expect(entry.getByRole("button", { name: "展开全文", exact: true })).toBeVisible();
});

test("desktop reader return and tabs have separate space in English dark mode", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("fm-language", "en");
    localStorage.setItem("fm-theme", "dark");
  });
  await page.setViewportSize({ width: 1120, height: 800 });
  await page.goto("/app");
  await page.locator(".result-row").first().locator(".bookmark-preview").click();
  const back = page.getByRole("button", { name: "Back to collection", exact: true });
  await expect(back).toBeVisible();
  const bounds = await page.locator(".preview-heading").boundingBox();
  const tabs = await page.locator(".preview-tabs").boundingBox();
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(tabs!.y + 1);
  await page.getByRole("tab", { name: "Related", exact: true }).click();
  await page.getByRole("tab", { name: "Page text", exact: true }).click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.screenshot({ path: "screenshots/support-reader-en-dark-1120.png", animations: "disabled" });
  await back.click();
  await expect(page.locator(".result-row").first().locator(".bookmark-preview")).toBeFocused();
});

test("an import can retry the same file and returns directly to the collection", async ({ page }) => {
  let attempts = 0;
  await page.route("**/admin/import", route => ++attempts === 1
    ? route.fulfill({ status: 503, json: { detail: "Synthetic import interruption" } })
    : route.fulfill({ json: { inserted: 2, updated: 0 } }));
  await page.goto("/app");
  await page.locator(".app-header").getByRole("button", { name: "导入书签", exact: true }).click();
  const upload = page.locator("input[type=file]");
  const file = { name: "retry.html", mimeType: "text/html", buffer: Buffer.from("synthetic export") };
  await upload.setInputFiles(file);
  await expect(page.getByRole("alert")).toContainText("Synthetic import interruption");
  await upload.setInputFiles(file);
  await expect(page.locator(".import-result")).toContainText("新增 2");
  expect(attempts).toBe(2);
  await page.screenshot({ path: "screenshots/support-import-success.png", animations: "disabled" });
  await page.getByRole("button", { name: "查看已导入的收藏", exact: true }).click();
  await expect(page.locator(".result-row")).toHaveCount(30);
});

test("editing a collection entry keeps search context without opening the reader", async ({ page }) => {
  await page.goto("/app");
  const search = page.getByRole("textbox", { name: "搜索书签", exact: true });
  await search.fill("知识");
  const row = page.locator(".result-row").first();
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: /^编辑：/ }).click();
  const dialog = page.getByRole("dialog", { name: "编辑收藏", exact: true });
  await expect(dialog).toBeVisible();
  await expect(page.locator(".preview-pane")).toHaveCount(0);
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await expect(search).toHaveValue("知识");
  await expect(row.getByRole("button", { name: /^编辑：/ })).toBeFocused();
  await expect(page.getByRole("combobox", { name: "排序", exact: true })).toBeVisible();
});
