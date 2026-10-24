import { settleVisualLayout } from "./visual-layout";
import { test, expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots", { recursive: true });
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort(),
  );
});

test("reader keeps the latest selection and remains usable while another body is loading", async ({
  page,
}) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const rows = page.locator(".result-row");
  const slow = await rows.nth(0).getAttribute("data-bookmark-id");
  const fast = await rows.nth(1).getAttribute("data-bookmark-id");
  const fastTitle = await rows.nth(1).locator(".result-title").innerText();
  await page.route("**/bookmark/*?body=true", async (route) => {
    const response = await route.fetch();
    if (route.request().url().includes(`/bookmark/${slow}?`))
      await new Promise((resolve) => setTimeout(resolve, 900));
    await route.fulfill({ response });
  });
  await rows.nth(0).locator(".bookmark-preview").click();
  await expect(page.locator(".skeleton-article")).toBeVisible();
  await expect(page.getByRole("tab", { name: "阅读", exact: true })).toBeVisible();
  await rows.nth(1).locator(".bookmark-preview").click();
  await expect(page.locator(".preview-title h1")).toHaveText(fastTitle);
  await expect(page.locator(".body-text")).toBeVisible();
  await page.waitForTimeout(950);
  await expect(page.locator(".preview-title h1")).toHaveText(fastTitle);
  await expect(page.locator(`.result-row[data-bookmark-id="${fast}"] .bookmark-preview`)).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await rows.nth(0).locator(".bookmark-preview").click();
  await rows.nth(1).locator(".bookmark-preview").click();
  await expect(page.locator(".body-text")).toBeVisible();
  await expect(page.locator(".skeleton-article")).toHaveCount(0);
});

test("reader tabs, expansion reversal and keyboard preserve query and scroll context", async ({
  page,
}) => {
  await page.goto("/app");
  const input = page.getByRole("textbox", { name: "搜索书签" });
  await input.fill("tag:demo");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.locator(".result-row").first().locator(".bookmark-preview").click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.getByLabel("跳转到章节").selectOption({ label: "从摘要回到原文" });
  await expect
    .poll(() => page.locator(".preview-scroll").evaluate((el) => el.scrollTop))
    .toBeGreaterThan(0);
  await page.getByRole("button", { name: "回到顶部" }).click();
  await expect.poll(() => page.locator(".preview-scroll").evaluate((el) => el.scrollTop)).toBe(0);
  const readerBefore = await page.locator(".preview-scroll").evaluate((el) => {
    el.scrollTop = Math.min(280, el.scrollHeight - el.clientHeight - 1);
    return { top: el.scrollTop, extent: el.scrollHeight - el.clientHeight };
  });
  expect(readerBefore.top).toBeGreaterThan(0);
  const before = await page.locator(".preview-tabs").boundingBox();
  await expect(page.locator(".reader-summary")).toBeVisible();
  await page.getByRole("tab", { name: "相关书签" }).click();
  await page.getByRole("tab", { name: "阅读", exact: true }).click();
  expect((await page.locator(".preview-tabs").boundingBox())?.y).toBe(before?.y);
  expect(await page.locator(".preview-scroll").evaluate((el) => el.scrollTop)).toBe(
    readerBefore.top,
  );
  await page.locator(".focus-reading").click();
  await expect(page.locator(".main-workspace")).toHaveClass(/focus-mode/);
  const header = await page.locator(".app-header").boundingBox();
  const workspace = await page.locator(".main-workspace").boundingBox();
  await expect
    .poll(() => page.locator(".preview-pane").evaluate(element => getComputedStyle(element).transform))
    .toBe("none");
  const focusedReader = await page.locator(".preview-pane").boundingBox();
  expect(focusedReader!.y).toBeGreaterThanOrEqual(header!.y + header!.height - 1);
  expect(focusedReader!.x).toBeGreaterThanOrEqual(workspace!.x - 1);
  expect(focusedReader!.x + focusedReader!.width).toBeLessThanOrEqual(workspace!.x + workspace!.width + 1);
  expect(focusedReader!.height).toBeGreaterThan(workspace!.height * .8);
  await expect(page.locator(".results-column")).toHaveAttribute("inert", "");
  // The focused button moves with the pane. Use real keyboard activation to
  // reverse mid-flight; a forced coordinate click can miss a moving target.
  await page.locator(".focus-reading").press("Enter");
  await expect(page.locator(".focus-reading")).toHaveAttribute("aria-pressed", "false");
  await page.locator(".focus-reading").press("Enter");
  await expect(page.locator(".focus-reading")).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Escape");
  await expect(page.locator(".main-workspace")).not.toHaveClass(/focus-mode/);
  await expect(page.locator(".body-text")).toBeVisible();
  await expect(input).toHaveValue("tag:demo");
  expect(await page.locator(".preview-scroll").evaluate((el) => el.scrollTop)).toBe(
    readerBefore.top,
  );
  await writeFile(
    "screenshots/scroll-context.json",
    JSON.stringify({ readerBefore, readerRestored: true }, null, 2),
  );
  await expect
    .poll(() => page.locator(".preview-pane").evaluate((el) => getComputedStyle(el).transform))
    .toBe("none");
  await page.keyboard.press("Escape");
  await expect(page.locator(".result-row").first().locator(".bookmark-preview")).toBeFocused();
  await expect(input).toHaveValue("tag:demo");

  // Keep a real, visible selection in a scrolled index so focus restoration
  // does not need to bring an offscreen row back into view.
  const list = page.locator(".result-list");
  const selectedRow = page.locator(".result-row").nth(24);
  await selectedRow.scrollIntoViewIfNeeded();
  const browsePosition = await list.evaluate((el) => el.scrollTop);
  await selectedRow.locator(".bookmark-preview").click();
  await expect(page.locator(".body-text")).toBeVisible();
  await settleVisualLayout(page);
  const listPosition = await list.evaluate((el) => el.scrollTop);
  expect(listPosition).toBeGreaterThan(0);
  await page.locator(".focus-reading").click();
  await page.locator(".focus-reading").click();
  await expect(page.locator(".main-workspace")).not.toHaveClass(/focus-mode/);
  await settleVisualLayout(page);
  expect(Math.abs((await list.evaluate((el) => el.scrollTop)) - listPosition)).toBeLessThanOrEqual(
    1,
  );
  await page.keyboard.press("Escape");
  await expect(selectedRow.locator(".bookmark-preview")).toBeFocused();
  expect(
    Math.abs((await list.evaluate((el) => el.scrollTop)) - browsePosition),
  ).toBeLessThanOrEqual(1);
  await expect(input).toHaveValue("tag:demo");
});

test("narrow reader reverses, contains focus and supports reduced motion", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 860 });
  await page.goto("/app");
  await page.locator(".result-row").first().locator(".bookmark-preview").click();
  await expect(page.locator(".body-text")).toBeVisible();
  await expect
    .poll(() => page.locator(".preview-drawer").evaluate((el) => getComputedStyle(el).transform))
    .toBe("none");
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/reader-zh-1024.png", animations: "disabled" });
  await page.getByRole("button", { name: "返回收藏" }).click();
  await expect(page.locator(".result-row").first().locator(".bookmark-preview")).toBeFocused();
  await page.locator(".result-row").nth(1).locator(".bookmark-preview").dispatchEvent("click");
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator(".preview-title h1")).toHaveText(
    await page.locator(".result-title").nth(1).innerText(),
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".result-row").nth(1).locator(".bookmark-preview")).toBeFocused();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.locator(".result-row").first().locator(".bookmark-preview").click();
  await page.locator(".focus-reading").click();
  await expect
    .poll(() => page.locator(".preview-pane").evaluate((el) => getComputedStyle(el).transform))
    .toBe("none");
  await page.getByRole("tab", { name: "相关书签" }).click();
  await page.getByRole("tab", { name: "阅读", exact: true }).click();
  const outline = page.getByRole("navigation", { name: "文章目录", exact: true });
  await expect(outline).toBeVisible();
  await outline.getByRole("button", { name: "从摘要回到原文", exact: true }).click();
  await expect(
    outline.getByRole("button", { name: "从摘要回到原文", exact: true }),
  ).toHaveAttribute("aria-current", "location");
  await expect
    .poll(() => page.locator(".preview-scroll").evaluate((el) => el.scrollTop))
    .toBeGreaterThan(0);
  await page.getByRole("button", { name: "回到顶部", exact: true }).click();
  await settleVisualLayout(page);
  await page.screenshot({
    path: "screenshots/focus-reading-reduced-motion.png",
    animations: "disabled",
  });
});

test("loading, empty, failure and long-title states have real rendered evidence", async ({
  page,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/bookmarks?**", async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto("/app");
  await expect(page.locator(".skeleton-list")).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/state-loading.png", animations: "disabled" });
  release();
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.unroute("**/bookmarks?**");
  const title =
    "当收藏越来越多，我们如何在碎片化的信息中重新找到值得深入阅读的内容：关于个人知识管理、检索上下文与长期思考的一份合成测试笔记";
  await page.route("**/bookmark/*?body=true", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.title = title;
    await route.fulfill({ json: data });
  });
  await page.locator(".result-row").first().locator(".bookmark-preview").click();
  await expect(page.locator(".preview-title h1")).toHaveText(title);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/state-long-title.png", animations: "disabled" });
  await page.getByRole("textbox", { name: "搜索书签" }).fill("zzfacetmarknonexistent987654321");
  await expect(page.getByText("换一点线索试试")).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/state-empty.png", animations: "disabled" });
  await page.route("**/bookmarks?**", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Synthetic failure: search temporarily unavailable" },
    }),
  );
  await page.getByRole("textbox", { name: "搜索书签" }).fill("controlled failure");
  await expect(page.locator(".search-error")).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/state-failure.png", animations: "disabled" });
  await page.unroute("**/bookmarks?**");
  await page.getByRole("button", { name: "重试", exact: true }).click();
  await expect(page.locator(".search-error")).toHaveCount(0);
});

test("supporting views and small-window reader share the same system", async ({ page }) => {
  // Earlier suites can legitimately leave the first record without fetched
  // text. This render journey uses a saved excerpt fixture, preserving metadata
  // and original links while keeping extraction tests independent.
  await page.route("**/bookmark/*?body=true", async route => {
    const response = await route.fetch();
    const record = await response.json();
    await route.fulfill({ json: { ...record, body_text: record.body_text ||
      "## 收藏与阅读\n\n把网页保存下来，是为了在需要时回到当时的问题与来源。A saved excerpt keeps its original source and reading context.\n\n## 回到原文\n\n读完摘要后，可以打开原始链接，继续查阅完整材料。" } });
  });
  await page.goto("/app");
  await expect(page.locator(".result-row").first()).toBeVisible();
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
  await expect(page.locator(".preview-pane")).toHaveCount(0);
  const search = await page.locator(".app-header .workspace-search").boundingBox();
  const collection = await page.locator(".results-column").boundingBox();
  const categories = await page.locator(".collection-sidebar").boundingBox();
  const header = await page.locator(".app-header").boundingBox();
  expect(search!.x).toBeGreaterThanOrEqual(header!.x);
  expect(search!.y).toBeGreaterThanOrEqual(header!.y);
  expect(search!.x + search!.width).toBeLessThanOrEqual(header!.x + header!.width);
  expect(search!.y + search!.height).toBeLessThanOrEqual(header!.y + header!.height);
  expect(Math.abs(categories!.y - header!.y)).toBeLessThanOrEqual(1);
  expect(categories!.height).toBeGreaterThanOrEqual(960 * .9);
  expect(collection!.y).toBeGreaterThanOrEqual(header!.y + header!.height - 1);
  await expect(page.locator(".app-header .collection-sidebar")).toHaveCount(0);
  expect(categories!.x + categories!.width).toBeLessThan(collection!.x);
  const rows = await page.locator(".result-row").all();
  for (const row of rows.slice(0, 8)) {
    const bounds = await row.boundingBox();
    const meta = await row.locator(".result-meta").boundingBox();
    expect(meta!.y + meta!.height).toBeLessThanOrEqual(bounds!.y + bounds!.height);
  }
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-zh-light.png", animations: "disabled" });
  await page.locator(".result-row").first().locator(".bookmark-preview").focus();
  await settleVisualLayout(page);
  await page.screenshot({
    path: "screenshots/collection-keyboard-focus.png",
    animations: "disabled",
  });
  await page.locator(".app-header").getByRole("button", { name: "导入书签", exact: true }).click();
  await expect(page.locator(".dropzone")).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/import-zh-light.png", animations: "disabled" });
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.locator("input[name=chat_model]")).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/settings-zh-light.png", animations: "disabled" });
  await page.getByRole("button", { name: "任务", exact: true }).click();
  await expect(page.locator(".tasks")).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/tasks-zh-light.png", animations: "disabled" });
  await page.getByRole("button", { name: "全部书签", exact: false }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator(".result-row").first().locator(".bookmark-preview").click();
  await expect(page.locator(".body-text")).toBeVisible();
  await expect
    .poll(() => page.locator(".preview-drawer").evaluate((el) => getComputedStyle(el).transform))
    .toBe("none");
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/reader-zh-390.png", animations: "disabled" });
  await page.getByRole("button", { name: "返回收藏" }).click();
  await expect(page.locator(".result-row").first().locator(".bookmark-preview")).toBeFocused();
  await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.locator("input[name=chat_model]")).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/settings-zh-390.png", animations: "disabled" });
});

test("folder directory filters the real collection and returns to all folders", async ({
  page,
}) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const folders = page.getByRole("navigation", { name: "按文件夹浏览", exact: true });
  const folder = folders.locator("button[title]").first();
  const label = await folder.getAttribute("title");
  expect(label).toBeTruthy();
  await folder.click();
  await expect(folder).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".filter-chips")).toContainText(label!);
  await expect
    .poll(async () => {
      const values = await page.locator(".result-folder").allTextContents();
      return values.length > 0 && values.every((value) => value.trim() === label);
    })
    .toBe(true);
  await folders.getByRole("button", { name: "全部文件夹", exact: true }).click();
  await expect(page.locator(".filter-chips")).toHaveCount(0);
  await expect(page.locator(".result-row")).toHaveCount(30);
});

test("record the search-to-reading interaction on the actual shared frontend", async ({
  browser,
}) => {
  await mkdir("recordings", { recursive: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    recordVideo: { dir: "recordings/raw", size: { width: 1440, height: 960 } },
  });
  const page = await context.newPage();
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort(),
  );
  await page.goto("http://127.0.0.1:8791/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.waitForTimeout(700);
  await page
    .getByRole("textbox", { name: "搜索书签" })
    .pressSequentially("tag:demo", { delay: 95 });
  await page.waitForTimeout(500);
  await page.locator(".result-row").first().locator(".bookmark-preview").click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.waitForTimeout(1200);
  await page.locator(".preview-scroll").hover();
  await page.mouse.wheel(0, 360);
  await page.waitForTimeout(900);
  await page.getByRole("tab", { name: "相关书签" }).click();
  await page.waitForTimeout(700);
  await page.getByRole("tab", { name: "阅读", exact: true }).click();
  await page.waitForTimeout(600);
  await page.locator(".focus-reading").click();
  await page.waitForTimeout(1100);
  await page.locator(".focus-reading").click();
  await page.waitForTimeout(650);
  await page.locator(".result-row").nth(1).locator(".bookmark-preview").click();
  await page.waitForTimeout(180);
  await page.locator(".result-row").nth(2).locator(".bookmark-preview").click();
  await page.waitForTimeout(180);
  await page.locator(".result-row").first().locator(".bookmark-preview").click();
  await page.waitForTimeout(900);
  await page.keyboard.press("Escape");
  await expect(page.locator(".result-row").first().locator(".bookmark-preview")).toBeFocused();
  await expect(page.getByRole("textbox", { name: "搜索书签" })).toHaveValue("tag:demo");
  await page.waitForTimeout(700);
  expect(errors).toEqual([]);
  const video = page.video();
  await context.close();
  await video?.saveAs("recordings/facetmark-reading.webm");
});
