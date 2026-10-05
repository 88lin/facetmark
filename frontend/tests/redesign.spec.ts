import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

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
  await rows.nth(0).click();
  await expect(page.locator(".skeleton-article")).toBeVisible();
  await expect(page.getByRole("tab", { name: "正文", exact: true })).toBeVisible();
  await rows.nth(1).click();
  await expect(page.locator(".preview-title h1")).toHaveText(fastTitle);
  await expect(page.locator(".body-text")).toBeVisible();
  await page.waitForTimeout(950);
  await expect(page.locator(".preview-title h1")).toHaveText(fastTitle);
  await expect(page.locator(`.result-row[data-bookmark-id="${fast}"]`)).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await rows.nth(0).click();
  await rows.nth(1).click();
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
  await page.locator(".result-row").first().click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.getByLabel("跳转到章节").selectOption({ label: "从摘要回到原文" });
  await expect
    .poll(() => page.locator(".preview-scroll").evaluate((el) => el.scrollTop))
    .toBeGreaterThan(0);
  await page.getByRole("button", { name: "回到顶部" }).click();
  await expect.poll(() => page.locator(".preview-scroll").evaluate((el) => el.scrollTop)).toBe(0);
  await page.locator(".preview-scroll").evaluate((el) => {
    el.scrollTop = 280;
  });
  const before = await page.locator(".preview-tabs").boundingBox();
  await page.getByRole("tab", { name: "AI 摘要" }).click();
  await page.getByRole("tab", { name: "相关书签" }).click();
  await page.getByRole("tab", { name: "正文", exact: true }).click();
  expect((await page.locator(".preview-tabs").boundingBox())?.y).toBe(before?.y);
  expect(await page.locator(".preview-scroll").evaluate((el) => el.scrollTop)).toBe(280);
  await page.locator(".focus-reading").click();
  await expect(page.locator(".main-workspace")).toHaveClass(/focus-mode/);
  const toolbar = await page.locator(".workspace-toolbar").boundingBox();
  await expect
    .poll(async () => (await page.locator(".preview-pane").boundingBox())?.y)
    .toBe(toolbar!.y + toolbar!.height);
  await page.locator(".focus-reading").click({ force: true });
  await page.locator(".focus-reading").click({ force: true });
  await page.keyboard.press("Escape");
  await expect(page.locator(".main-workspace")).not.toHaveClass(/focus-mode/);
  await expect(page.locator(".body-text")).toBeVisible();
  await expect(input).toHaveValue("tag:demo");
  await expect
    .poll(() => page.locator(".preview-pane").evaluate((el) => getComputedStyle(el).transform))
    .toBe("none");
  await page.keyboard.press("Escape");
  await expect(page.locator(".result-row").first()).toBeFocused();
  await expect(input).toHaveValue("tag:demo");

  // Keep a real, visible selection in a scrolled index so focus restoration
  // does not need to bring an offscreen row back into view.
  const list = page.locator(".result-list");
  const selectedRow = page.locator(".result-row").nth(8);
  await selectedRow.click();
  await expect(page.locator(".body-text")).toBeVisible();
  const listPosition = await list.evaluate((el) => el.scrollTop);
  expect(listPosition).toBeGreaterThan(0);
  await page.locator(".focus-reading").click();
  await page.locator(".focus-reading").click();
  await expect(page.locator(".main-workspace")).not.toHaveClass(/focus-mode/);
  await page.keyboard.press("Escape");
  await expect(selectedRow).toBeFocused();
  expect(Math.abs((await list.evaluate((el) => el.scrollTop)) - listPosition)).toBeLessThanOrEqual(1);
  await expect(input).toHaveValue("tag:demo");
});

test("narrow reader reverses, contains focus and supports reduced motion", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 860 });
  await page.goto("/app");
  await page.locator(".result-row").first().click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.screenshot({ path: "screenshots/reader-zh-1024.png", animations: "disabled" });
  await page.keyboard.press("Escape");
  await page.locator(".result-row").nth(1).dispatchEvent("click");
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator(".preview-title h1")).toHaveText(
    await page.locator(".result-title").nth(1).innerText(),
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".result-row").nth(1)).toBeFocused();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.locator(".result-row").first().click();
  await page.locator(".focus-reading").click();
  await expect
    .poll(() => page.locator(".preview-pane").evaluate((el) => getComputedStyle(el).transform))
    .toBe("none");
  await page.getByRole("tab", { name: "AI 摘要" }).click();
  await page.getByRole("tab", { name: "正文", exact: true }).click();
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
  await page.locator(".result-row").first().click();
  await expect(page.locator(".preview-title h1")).toHaveText(title);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "screenshots/state-long-title.png", animations: "disabled" });
  await page.getByRole("textbox", { name: "搜索书签" }).fill("zzfacetmarknonexistent987654321");
  await expect(page.getByText("换一点线索试试")).toBeVisible();
  await page.screenshot({ path: "screenshots/state-empty.png", animations: "disabled" });
  await page.route("**/quick?**", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Synthetic failure: search temporarily unavailable" },
    }),
  );
  await page.getByRole("textbox", { name: "搜索书签" }).fill("controlled failure");
  await expect(page.locator(".search-error")).toBeVisible();
  await page.screenshot({ path: "screenshots/state-failure.png", animations: "disabled" });
  await page.unroute("**/quick?**");
  await page.getByRole("button", { name: "重试", exact: true }).click();
  await expect(page.locator(".search-error")).toHaveCount(0);
});

test("supporting views and small-window reader share the same system", async ({ page }) => {
  await page.goto("/app");
  await page.locator(".sidebar").getByRole("button", { name: "导入书签", exact: true }).click();
  await expect(page.locator(".dropzone")).toBeVisible();
  await page.screenshot({ path: "screenshots/import-zh-light.png", animations: "disabled" });
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.locator("input[name=chat_model]")).toBeVisible();
  await page.screenshot({ path: "screenshots/settings-zh-light.png", animations: "disabled" });
  await page.getByRole("button", { name: "任务", exact: true }).click();
  await expect(page.locator(".tasks")).toBeVisible();
  await page.screenshot({ path: "screenshots/tasks-zh-light.png", animations: "disabled" });
  await page.getByRole("button", { name: "全部书签", exact: false }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator(".result-row").first().click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.screenshot({ path: "screenshots/reader-zh-390.png", animations: "disabled" });
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
  await page.locator(".result-row").first().click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.waitForTimeout(1200);
  await page.locator(".preview-scroll").hover();
  await page.mouse.wheel(0, 360);
  await page.waitForTimeout(900);
  await page.getByRole("tab", { name: "AI 摘要" }).click();
  await page.waitForTimeout(700);
  await page.getByRole("tab", { name: "正文", exact: true }).click();
  await page.waitForTimeout(600);
  await page.locator(".focus-reading").click();
  await page.waitForTimeout(1100);
  await page.locator(".focus-reading").click();
  await page.waitForTimeout(650);
  await page.locator(".result-row").nth(1).click();
  await page.waitForTimeout(180);
  await page.locator(".result-row").nth(2).click();
  await page.waitForTimeout(180);
  await page.locator(".result-row").first().click();
  await page.waitForTimeout(900);
  await page.keyboard.press("Escape");
  await expect(page.locator(".result-row").first()).toBeFocused();
  await expect(page.getByRole("textbox", { name: "搜索书签" })).toHaveValue("tag:demo");
  await page.waitForTimeout(700);
  expect(errors).toEqual([]);
  const video = page.video();
  await context.close();
  await video?.saveAs("recordings/facetmark-reading.webm");
});
