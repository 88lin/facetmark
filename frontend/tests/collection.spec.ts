import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.addInitScript(() => {
    localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-collection-layout")) localStorage.setItem("fm-collection-layout", "grid");
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await mkdir("screenshots", { recursive: true });
});

test("a large collection leaves useful browsing space in short desktop and mobile windows", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  const measurements = [];
  for (const viewport of [{ width: 1440, height: 960 }, { width: 1366, height: 768 }, { width: 1280, height: 600 }, { width: 1024, height: 749 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await expect(page.locator(".result-count")).toHaveText("1892");
    const size = await page.locator(".result-list").evaluate(el => {
      const bounds = el.getBoundingClientRect();
      const fullyVisible = [...el.querySelectorAll(".result-row")].filter(row => {
        const box = row.getBoundingClientRect();
        return box.top >= bounds.top && box.bottom <= bounds.bottom;
      }).length;
      return { top: bounds.top, firstCardTop: el.querySelector(".result-row")!.getBoundingClientRect().top,
        height: bounds.height, viewport: innerHeight, fullyVisible,
        overflow: document.documentElement.scrollWidth > innerWidth + 1 };
    });
    expect(size.overflow).toBe(false);
    expect(size.top).toBeLessThanOrEqual(viewport.width < 720 ? 230 : 180);
    expect(size.height / size.viewport).toBeGreaterThanOrEqual(viewport.width < 720 ? .58 : .63);
    expect(size.fullyVisible).toBeGreaterThanOrEqual(viewport.width < 720 ? 2 : viewport.width < 1120 ? 4 : 6);
    if (viewport.width >= 960) {
      const directory = await page.locator(".collection-sidebar").boundingBox();
      const results = await page.locator(".result-list").boundingBox();
      expect(directory!.x + directory!.width).toBeLessThan(results!.x);
      expect(directory!.height).toBeGreaterThan(viewport.height * .65);
    }
    measurements.push({ width: viewport.width, viewportHeight: viewport.height,
      listTop: size.top, firstCardTop: size.firstCardTop, listHeight: size.height,
      fullyVisible: size.fullyVisible, horizontalOverflow: size.overflow });
    await page.screenshot({ path: `screenshots/collection-${viewport.width}x${viewport.height}.png`, animations: "disabled" });
  }
  expect(errors).toEqual([]);
  await writeFile("screenshots/collection-density.json", JSON.stringify({ data: "1892 synthetic bookmarks, over 240 folders", measurements }, null, 2));
  await page.evaluate(() => localStorage.setItem("fm-language", "en"));
  // Override this test's default language before checking expanded English actions.
  await page.addInitScript(() => localStorage.setItem("fm-language", "en"));
  await page.reload();
  await expect(page.getByRole("button", { name: "Add bookmark", exact: true })).toBeVisible();
  await expect(page.locator(".result-row")).toHaveCount(30);
  expect((await page.locator(".result-list").boundingBox())!.y).toBeLessThanOrEqual(230);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)).toBe(false);
  await page.screenshot({ path: "screenshots/collection-en-mobile.png", animations: "disabled" });
});

test("a mouse can scroll and page the category directory, then search beyond the old 200-item ceiling", async ({ page, request }) => {
  await page.goto("/app");
  const rail = page.locator(".collection-sidebar");
  const options = rail.locator(".facet-options");
  await expect(options.locator("button[title]")).toHaveCount(50);
  await options.hover();
  await page.mouse.wheel(0, 2400);
  await expect.poll(() => options.evaluate(el => el.scrollTop)).toBeGreaterThan(100);
  await rail.getByRole("button", { name: "显示更多分类" }).click();
  await expect(options.locator("button[title]")).toHaveCount(100);

  const boot = await (await request.get("/app/boot")).json();
  const late = await (await request.get("/bookmarks/facets/folders?offset=220&limit=1", {
    headers: { Authorization: `Bearer ${boot.token}` },
  })).json();
  expect(late.total).toBeGreaterThan(240);
  const name: string = late.items[0].value;
  await rail.getByRole("textbox", { name: "查找分类" }).fill(name);
  const target = options.getByTitle(name, { exact: true });
  await expect(target).toBeVisible();
  await target.click();
  await expect(target).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  const folders = await page.locator(".result-folder").allTextContents();
  expect(folders.length).toBeGreaterThan(0);
  expect(folders.every(value => value.trim() === name)).toBe(true);
  await page.screenshot({ path: "screenshots/collection-category-search.png", animations: "disabled" });

  // The same directory is usable without a pointer or a horizontal gesture.
  await options.getByRole("button", { name: "全部文件夹", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".result-count")).toHaveText("1892");
  await rail.getByRole("textbox", { name: "查找分类" }).fill("知识管理");
  await rail.getByRole("textbox", { name: "查找分类" }).press("Tab");
  await expect(rail.getByRole("button", { name: "清空分类搜索" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(options).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(options.getByRole("button", { name: "全部文件夹", exact: true })).toBeFocused();
  await options.getByTitle("知识管理", { exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".result-row").first()).toBeVisible();
  expect((await page.locator(".result-folder").allTextContents()).every(value => value.trim() === "知识管理")).toBe(true);
});

test("a large library can jump to its last page without stepping through every page", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const jump = page.getByRole("spinbutton", { name: "跳转页码" });
  await jump.fill("64");
  await page.getByRole("button", { name: "跳转", exact: true }).click();
  await expect(page.locator(".results-footer")).toContainText("1891–1892");
  await expect(page.locator(".result-row")).toHaveCount(2);
  await expect(page.getByRole("button", { name: "下一页", exact: true })).toBeDisabled();
  await expect(jump).toHaveValue("64");
  await jump.fill("65");
  await jump.press("Enter");
  expect(await jump.evaluate((el: HTMLInputElement) => el.validity.rangeOverflow)).toBe(true);
  await expect(page.locator(".results-footer")).toContainText("1891–1892");
  await jump.fill("1");
  await jump.press("Enter");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await expect(page.locator(".results-footer")).toContainText("1–30");
  await page.screenshot({ path: "screenshots/collection-page-jump.png", animations: "disabled" });
});

test("deselecting this page preserves selections from other pages", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.getByRole("button", { name: "批量管理", exact: true }).click();
  await page.getByRole("button", { name: "选择本页", exact: true }).click();
  await expect(page.locator(".selection-total")).toHaveText("已选择 30 条");
  await page.getByRole("button", { name: "下一页", exact: true }).click();
  await expect(page.locator(".results-footer")).toContainText("31–60");
  await page.getByRole("button", { name: "选择本页", exact: true }).click();
  await expect(page.locator(".selection-total")).toHaveText("已选择 60 条");
  await page.getByRole("button", { name: "取消本页选择", exact: true }).click();
  await expect(page.locator(".selection-total")).toHaveText("已选择 30 条");
  await expect(page.locator(".result-row[aria-pressed=true]")).toHaveCount(0);
  await page.getByRole("button", { name: "上一页", exact: true }).click();
  await expect(page.locator(".result-row[aria-pressed=true]")).toHaveCount(30);
  await page.getByRole("button", { name: "取消本页选择", exact: true }).click();
  await expect(page.locator(".selection-total")).toHaveText("已选择 0 条");
  await expect(page.getByRole("button", { name: "批量操作", exact: true })).toBeDisabled();
});

test("filter labels explain unfiled and clearing filters keeps the keyword query", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const rail = page.locator(".collection-sidebar");
  await rail.getByRole("textbox", { name: "查找分类" }).fill("开发工具");
  await rail.getByTitle("开发工具", { exact: true }).click();
  const search = page.getByRole("textbox", { name: "搜索书签", exact: true });
  await search.fill("SQLite");
  await expect(page.locator(".result-title").first()).toContainText("SQLite");
  await expect(page.getByRole("button", { name: "移除文件夹筛选：开发工具", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "清除筛选", exact: true }).click();
  await expect(page.locator(".filter-chips")).toHaveCount(0);
  await expect(search).toHaveValue("SQLite");
  await expect(page.locator(".result-title").first()).toContainText("SQLite");
  await rail.getByRole("textbox", { name: "查找分类" }).fill("");
  await rail.getByRole("button", { name: "未分类", exact: true }).click();
  const remove = page.getByRole("button", { name: "移除文件夹筛选：未分类", exact: true });
  await expect(remove).toBeVisible();
  await expect(page.locator(".filter-value")).toHaveText("未分类");
  await remove.click();
  await expect(search).toHaveValue("SQLite");
  await expect(page.locator(".result-title").first()).toContainText("SQLite");
});

test("collection typography stays readable across views and larger user text settings", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const typography = await page.evaluate(() => {
    const size = (selector: string) => parseFloat(getComputedStyle(document.querySelector(selector)!).fontSize);
    return { title: size(".result-title"), summary: size(".result-summary"), source: size(".result-source"),
      category: size(".collection-sidebar .facet-option"), action: size(".library-tools .primary"),
      search: size(".search-box input"), weight: getComputedStyle(document.querySelector(".result-title")!).fontWeight,
      tracking: getComputedStyle(document.querySelector(".toolbar-location h1")!).letterSpacing };
  });
  expect(typography.title).toBeGreaterThanOrEqual(18);
  expect(typography.summary).toBeGreaterThanOrEqual(14);
  expect(typography.source).toBeGreaterThanOrEqual(12);
  expect(typography.category).toBeGreaterThanOrEqual(14);
  expect(typography.action).toBeGreaterThanOrEqual(14);
  expect(typography.search).toBeGreaterThanOrEqual(16);
  expect(Number(typography.weight)).toBeGreaterThanOrEqual(700);
  expect(["normal", "0px"]).toContain(typography.tracking);
  const categoryLabelsStayOnOneLine = () => page.locator(".collection-sidebar .facet-types button span").evaluateAll(labels =>
    labels.every(label => label.getBoundingClientRect().height <= parseFloat(getComputedStyle(label).lineHeight) + 1));
  expect(await categoryLabelsStayOnOneLine()).toBe(true);
  await page.getByRole("button", { name: "列表视图", exact: true }).click();
  expect(await page.locator(".result-title").first().evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(18);
  await page.evaluate(() => { document.documentElement.style.fontSize = "125%"; });
  expect(await page.locator(".result-title").first().evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(22.5);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)).toBe(false);
  expect(await categoryLabelsStayOnOneLine()).toBe(true);
  await page.screenshot({ path: "screenshots/collection-text-125.png", animations: "disabled" });
  await page.evaluate(() => { document.documentElement.style.fontSize = ""; });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.locator(".result-title").first().evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(18);
  await page.screenshot({ path: "screenshots/collection-readable-mobile-list.png", animations: "disabled" });
  await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
  const option = page.locator(".sidebar .facet-option").first();
  expect(await option.evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(14);
  await writeFile("screenshots/collection-typography.json", JSON.stringify(typography, null, 2));
});

test("repeating the active category during a slow request does not leave loading stuck", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const target = page.locator(".collection-sidebar .facet-option[title]").first();
  await expect(target).toBeVisible();
  const name = await target.getAttribute("title");
  let calls = 0;
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/bookmarks?**", async route => {
    if (new URL(route.request().url()).searchParams.get("folder") !== name) return route.continue();
    calls++;
    const response = await route.fetch();
    await gate;
    await route.fulfill({ response });
  });
  try {
    await target.click();
    await expect.poll(() => calls).toBe(1);
    await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "true");
    await expect(page.locator(".result-row")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "导出", exact: true })).toBeDisabled();
    await target.click();
    release();
    await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
    await expect(page.locator(".result-row").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "导出", exact: true })).toBeEnabled();
    expect(calls).toBe(1);
  } finally { release(); }
});

test("repeated Enter and unchanged IME completion always settle the current search", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  let calls = 0;
  await page.route("**/quick?**", async route => {
    calls++;
    const response = await route.fetch();
    await new Promise(resolve => setTimeout(resolve, 450));
    await route.fulfill({ response });
  });
  const input = page.getByRole("textbox", { name: "搜索书签", exact: true });
  await input.fill("SQLite");
  await expect.poll(() => calls).toBe(1);
  await input.press("Enter");
  await expect.poll(() => calls).toBe(2);
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".result-title").first()).toContainText("SQLite");
  await input.press("Enter");
  await expect.poll(() => calls).toBe(3);
  await input.dispatchEvent("compositionstart");
  await input.dispatchEvent("compositionend");
  await expect.poll(() => calls).toBe(4);
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(input).toHaveValue("SQLite");
  await expect(page.locator(".result-title").first()).toContainText("SQLite");
});

test("changing a category closes the old reader and fails closed until the new scope loads", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.getByRole("button", { name: "下一页", exact: true }).click();
  await expect(page.locator(".results-footer")).toContainText("31–60");
  await page.locator(".result-row").first().click();
  await expect(page.locator(".body-text")).toBeVisible();
  await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
  const menu = page.locator(".sidebar");
  await menu.getByRole("textbox", { name: "查找分类" }).fill("知识管理");
  await expect(menu.getByTitle("知识管理", { exact: true })).toBeVisible();
  await page.route("**/bookmarks?**", route => route.fulfill({ status: 503, json: { detail: "Synthetic delayed collection failure" } }));
  await menu.getByTitle("知识管理", { exact: true }).click();
  await expect(page.locator(".preview-pane")).toHaveCount(0);
  await expect(page.locator(".search-error")).toBeVisible();
  await expect(page.locator(".result-row")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "批量管理", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "导出", exact: true })).toBeDisabled();
  await page.unroute("**/bookmarks?**");
  await page.locator(".search-error").getByRole("button", { name: "重试", exact: true }).click();
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".result-row").first()).toBeVisible();
  await expect(page.locator(".results-footer")).toContainText("1–");
  expect(await page.locator(".result-list").evaluate(el => el.scrollTop)).toBe(0);
  expect((await page.locator(".result-folder").allTextContents()).every(value => value.trim() === "知识管理")).toBe(true);
});

test("mobile category errors recover and list view is a persistent alternative", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.route("**/bookmarks/facets/folders?**", route => route.fulfill({ status: 503, json: { detail: "Synthetic category failure" } }));
  await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
  const menu = page.locator(".sidebar");
  await expect(menu.getByRole("alert")).toContainText("分类暂时无法加载");
  await page.unroute("**/bookmarks/facets/folders?**");
  await menu.getByRole("button", { name: "重试", exact: true }).click();
  await expect(menu.locator(".facet-option[title]")).toHaveCount(50);
  await menu.getByRole("textbox", { name: "查找分类" }).fill("知识管理");
  await expect(menu.getByTitle("知识管理", { exact: true })).toBeVisible();
  await page.screenshot({ path: "screenshots/collection-mobile-categories.png", animations: "disabled" });
  await menu.getByTitle("知识管理", { exact: true }).click();
  await expect(menu).toHaveAttribute("inert", "");
  await expect(page.locator(".result-row").first()).toBeVisible();
  await page.getByRole("button", { name: "列表视图", exact: true }).click();
  await expect(page.locator(".main-workspace")).toHaveClass(/list-mode/);
  await page.screenshot({ path: "screenshots/collection-list-390.png", animations: "disabled" });
  expect(await page.evaluate(() => localStorage.getItem("fm-collection-layout"))).toBe("list");
  await page.reload();
  await expect(page.locator(".main-workspace")).toHaveClass(/list-mode/);
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.screenshot({ path: "screenshots/collection-list-1366.png", animations: "disabled" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
});
