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
  for (const viewport of [{ width: 1366, height: 768 }, { width: 1280, height: 600 }, { width: 390, height: 844 }]) {
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
      return { top: bounds.top, height: bounds.height, viewport: innerHeight, fullyVisible,
        overflow: document.documentElement.scrollWidth > innerWidth + 1 };
    });
    expect(size.overflow).toBe(false);
    expect(size.top).toBeLessThanOrEqual(viewport.width < 720 ? 280 : 180);
    expect(size.height / size.viewport).toBeGreaterThanOrEqual(viewport.width < 720 ? .58 : .63);
    expect(size.fullyVisible).toBeGreaterThanOrEqual(viewport.width < 720 ? 2 : 6);
    measurements.push({ ...viewport, ...size });
    await page.screenshot({ path: `screenshots/collection-${viewport.width}x${viewport.height}.png`, animations: "disabled" });
  }
  expect(errors).toEqual([]);
  await writeFile("screenshots/collection-density.json", JSON.stringify({ data: "1892 synthetic bookmarks, over 240 folders", measurements }, null, 2));
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
