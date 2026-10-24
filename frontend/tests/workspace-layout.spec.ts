import { expect, test, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

const output = "screenshots/collection-review";
test.beforeEach(async ({ page }) => {
  await mkdir(output, { recursive: true });
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});
async function capture(page: Page, name: string) {
  await settleVisualLayout(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: `${output}/polish-layout-${name}.png`, animations: "disabled" });
}

async function savedTextFixture(page: Page) {
  const paragraph = "收藏需要把问题、来源与当时的想法放在一起。A saved page keeps its reading context and native source link. ";
  const body = ["## 阅读与上下文", ...Array.from({ length: 16 }, () => paragraph.repeat(4)),
    "## 文章末尾", "最后一段仍然完整可见，阅读进度和返回顶部不会遮挡正文。"].join("\n\n");
  await page.route("**/bookmark/*?body=true", async route => {
    const response = await route.fetch();
    const record = await response.json();
    await route.fulfill({ json: { ...record, body_text: body } });
  });
}

test("desktop uses its height for the directory and collection, with search in the header", async ({ page }) => {
  const evidence = [];
  for (const { width, height } of [{ width: 1440, height: 900 }, { width: 1280, height: 720 }, { width: 1024, height: 768 }]) {
    await page.setViewportSize({ width, height });
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await settleVisualLayout(page);
    const geometry = await page.evaluate(() => {
      const bounds = (selector: string) => {
        const box = document.querySelector(selector)!.getBoundingClientRect();
        return { x: box.x, y: box.y, width: box.width, height: box.height, bottom: box.bottom };
      };
      const list = document.querySelector(".result-list")!.getBoundingClientRect();
      const visible = [...document.querySelectorAll(".result-row")].filter(row => {
        const box = row.getBoundingClientRect();
        return box.top >= list.top && box.bottom <= list.bottom + 1;
      }).length;
      return { search: bounds(".search-box"), rail: bounds(".collection-sidebar"), directory: bounds(".collection-sidebar .facet-options"),
        results: bounds(".result-list"), header: bounds(".app-header"), visible };
    });
    expect(geometry.search.bottom).toBeLessThanOrEqual(geometry.header.bottom + 1);
    expect(geometry.rail.height).toBeGreaterThan(height * .9);
    expect(geometry.directory.height).toBeGreaterThan(height * .7);
    expect(geometry.results.height).toBeGreaterThan(height * .62);
    if (width === 1440) expect(geometry.visible).toBeGreaterThanOrEqual(6);
    evidence.push({ width, height, ...geometry });
    await capture(page, `collection-${width}-${height}`);
  }
  await writeFile(`${output}/layout-geometry.json`, JSON.stringify(evidence, null, 2));
});

test("card blank areas open the reader while native links, selection and expansion keep their own behavior", async ({ page }) => {
  await savedTextFixture(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const cards = page.locator(".result-row");
  const first = cards.first(), second = cards.nth(1);
  const secondTitle = (await second.locator(".result-title").innerText()).trim();
  await first.click({ position: { x: 7, y: 7 } });
  await expect(page.locator(".body-text")).toBeVisible();
  await expect(first).toHaveClass(/selected/);
  await expect(first.locator(".bookmark-description")).toBeHidden();
  await second.click({ position: { x: 7, y: 7 } });
  await expect(page.locator(".preview-title h1")).toHaveText(secondTitle);
  await expect(second).toHaveClass(/selected/);
  await capture(page, "compact-reader-index");
  await page.keyboard.press("Escape");
  await expect(second.locator(".bookmark-preview")).toBeFocused();
  await expect(first.locator(".bookmark-description")).toBeVisible();
  await first.locator(".bookmark-check").click();
  await expect(first.locator(".bookmark-check")).toBeChecked();
  await expect(page.locator(".preview-title")).toHaveCount(0);
  await first.locator(".bookmark-check").press("Space");
  await page.getByRole("button", { name: "完成选择", exact: true }).click();
  const expand = first.locator(".summary-expand");
  if (await expand.count()) {
    await expand.click();
    await expect(expand).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".preview-title")).toHaveCount(0);
  }
  const text = first.locator(".result-summary");
  const box = (await text.boundingBox())!;
  await page.mouse.move(box.x + 3, box.y + 8);
  await page.mouse.down(); await page.mouse.move(box.x + Math.min(box.width - 10, 190), box.y + 8, { steps: 10 }); await page.mouse.up();
  expect(await page.evaluate(() => Boolean(getSelection()?.toString()))).toBe(true);
  await expect(page.locator(".preview-title")).toHaveCount(0);
  await page.evaluate(() => getSelection()?.removeAllRanges());
  const popupPromise = page.waitForEvent("popup");
  await first.locator("a.result-title").click();
  const original = await popupPromise;
  await expect(page.locator(".preview-title")).toHaveCount(0);
  await original.close();
});

test("reading text has a clear scale, progress stays below the article and missing text has no progress box", async ({ page }) => {
  await savedTextFixture(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/app");
  const first = page.locator(".result-row").first();
  await first.locator(".bookmark-preview").click();
  await expect(page.locator(".body-text")).toBeVisible();
  const sizes = await page.evaluate(() => ({
    title: parseFloat(getComputedStyle(document.querySelector(".preview-title h1")!).fontSize),
    body: parseFloat(getComputedStyle(document.querySelector(".reading")!).fontSize),
    heading: parseFloat(getComputedStyle(document.querySelector(".body-text h2")!).fontSize),
  }));
  expect(sizes.body).toBe(17); expect(sizes.title).toBeGreaterThan(sizes.body * 1.5);
  expect(sizes.heading).toBeGreaterThan(sizes.body); expect(sizes.heading).toBeLessThan(sizes.title);
  await page.locator(".preview-scroll").evaluate(element => element.scrollTo({ top: element.scrollHeight, behavior: "instant" }));
  await expect(page.locator(".reading-percent")).toHaveText("100%");
  const final = (await page.locator(".body-text p").last().boundingBox())!;
  const footer = (await page.locator(".reading-position").boundingBox())!;
  expect(final.y + final.height).toBeLessThanOrEqual(footer.y + 1);
  const top = page.getByRole("button", { name: "回到顶部", exact: true });
  await expect(top).toHaveClass(/fm-button/);
  await top.press("Enter");
  await expect.poll(() => page.locator(".preview-scroll").evaluate(element => element.scrollTop)).toBe(0);
  await capture(page, "reader-type-and-footer");
  await page.getByRole("tab", { name: "AI 摘要", exact: true }).click();
  await expect(page.locator(".reading-position")).toHaveCount(0);
  await capture(page, "reader-summary");
  await page.getByRole("tab", { name: "正文", exact: true }).click();
  await page.keyboard.press("Escape");
  const id = await first.getAttribute("data-bookmark-id");
  await page.route(`**/bookmark/${id}?body=true`, async route => {
    const response = await route.fetch(); const record = await response.json();
    await route.fulfill({ json: { ...record, body_text: "" } });
  });
  await first.click({ position: { x: 7, y: 7 } });
  await expect(page.locator(".reading-empty")).toContainText("正文还未保存");
  await expect(page.locator(".reading-position")).toHaveCount(0);
  await capture(page, "reader-without-page-text");
});

test("settings fill the workspace; model menus fit edges and hidden tabs release their top-layer menu", async ({ page }) => {
  test.setTimeout(60000);
  await page.route("**/admin/settings/models", route => route.fulfill({ json: { models: Array.from({ length: 30 }, (_, i) => ({
    id: `synthetic/model-${i}`, label: `合成模型 ${i} · Long English and Chinese catalog label`, source: "fixture",
  })), default_model: "synthetic/model-0", warning: "" } }));
  for (const { width, height, language, theme } of [
    { width: 1440, height: 900, language: "zh", theme: "light" },
    { width: 1280, height: 540, language: "en", theme: "dark" },
    { width: 390, height: 844, language: "zh", theme: "light" },
    { width: 320, height: 700, language: "en", theme: "dark" },
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto("/app#settings");
    await page.evaluate(state => { localStorage.setItem("fm-language", state.language); localStorage.setItem("fm-theme", state.theme); }, { language, theme });
    await page.reload();
    await expect(page.locator(".settings-tabs")).toBeVisible();
    const scroll = (await page.locator(".page-scroll").boundingBox())!;
    expect(scroll.width).toBeGreaterThan(width * .8);
    const tabs = page.locator(".settings-tabs [role=tab]");
    await tabs.first().focus();
    for (let i = 0; i < 4; i++) {
      await page.keyboard.press("ArrowRight");
      await settleVisualLayout(page);
      const target = page.locator(".settings-tabs [aria-selected=true]");
      await expect(target).toBeFocused();
      const button = (await target.boundingBox())!, group = (await page.locator(".settings-tabs").boundingBox())!;
      expect(button.x).toBeGreaterThanOrEqual(group.x + 4); expect(button.y).toBeGreaterThanOrEqual(group.y + 4);
      expect(button.x + button.width).toBeLessThanOrEqual(group.x + group.width - 4);
    }
    await page.getByLabel(language === "zh" ? "摘要来源" : "Summary provider", { exact: true }).selectOption("endpoint");
    const draft = page.locator('.model-chat input[name="chat_model"]');
    await draft.fill("synthetic-unsaved-layout-draft");
    const trigger = page.locator(".model-chat .model-picker-trigger");
    await trigger.scrollIntoViewIfNeeded(); await trigger.click();
    const menu = page.locator(".model-picker-menu");
    await expect(menu).toBeVisible(); await expect(menu).toHaveAttribute("popover", "manual");
    await settleVisualLayout(page);
    const bounds = (await menu.boundingBox())!;
    expect(bounds.x).toBeGreaterThanOrEqual(7); expect(bounds.y).toBeGreaterThanOrEqual(7);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width - 7);
    expect(bounds.y + bounds.height).toBeLessThanOrEqual(height - 7);
    await capture(page, `settings-model-menu-${language}-${theme}-${width}`);
    await page.getByRole("combobox", { name: language === "zh" ? "搜索模型" : "Search models", exact: true }).fill("model-12");
    await page.keyboard.press("Enter");
    await expect(draft).toHaveValue("synthetic/model-12");
    await expect(trigger).toBeFocused(); await expect(menu).toHaveCount(0);
    await trigger.click(); await expect(menu).toBeVisible();
    // Changing tabs while a popover is open must not leave an orphan above the new form.
    await page.locator("#settings-tab-sync").evaluate(element => (element as HTMLButtonElement).click());
    await expect(menu).toHaveCount(0);
    await page.locator("#settings-tab-models").click();
    await expect(draft).toHaveValue("synthetic/model-12");
    await page.locator(".page-scroll").evaluate(element => element.scrollTo({ top: 0, behavior: "instant" }));
    await capture(page, `settings-full-width-${language}-${theme}-${width}`);
  }
});

test("folder picker escapes the bookmark dialog scroll area and returns focus without submitting", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto("/app");
  await page.getByRole("button", { name: "新增收藏", exact: true }).click();
  const dialog = page.locator(".library-dialog");
  const trigger = dialog.locator(".folder-picker-trigger");
  await trigger.click();
  const picker = dialog.locator(".folder-picker-panel");
  await expect(picker).toBeVisible();
  await expect(picker).toHaveAttribute("popover", "manual");
  const search = page.getByRole("textbox", { name: "搜索文件夹", exact: true });
  await expect(search).toBeFocused();
  await search.press("Enter"); await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("收藏标题", { exact: true })).toHaveValue("");
  await capture(page, "folder-picker-dialog-390");
  await search.press("Escape"); await expect(picker).toHaveCount(0); await expect(trigger).toBeFocused();
  await trigger.press("Escape"); await expect(dialog).toHaveCount(0);
});
