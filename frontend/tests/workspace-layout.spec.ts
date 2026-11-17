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

async function savedTextFixture(page: Page, sourceText?: string) {
  const paragraph = "收藏需要把问题、来源与当时的想法放在一起。A saved page keeps its reading context and native source link. ";
  const body = ["## 阅读与上下文", ...Array.from({ length: 16 }, () => paragraph.repeat(4)),
    "## 文章末尾", "最后一段仍然完整可见，阅读进度和返回顶部不会遮挡正文。"].join("\n\n");
  await page.route("**/bookmark/*?body=true", async route => {
    const response = await route.fetch();
    const record = await response.json();
    await route.fulfill({ json: { ...record, body_text: sourceText ?? body,
      summary: "收藏保存来源与阅读上下文，回到内容时仍能找到原文。", key_points: ["保留原始来源。"],
      indexed: { ...record.indexed, summary_basis: "body", enriched_by: "synthetic-summary" } } });
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
  await expect(first.locator(".bookmark-check")).not.toBeChecked();
  await expect(page.getByRole("button", { name: "完成选择", exact: true })).toHaveCount(0);
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

test("reader index reveals the whole selection after layout motion and restores collection scroll on close", async ({ page }) => {
  await savedTextFixture(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const opener = page.locator(".result-row").nth(12);
  await opener.scrollIntoViewIfNeeded();
  const before = await page.locator(".result-list").evaluate(element => element.scrollTop);
  expect(before).toBeGreaterThan(0);
  await opener.click({ position: { x: 7, y: 7 } });
  await expect(page.locator(".body-text")).toBeVisible();
  const measurements = [];
  for (const action of [null, "下一条收藏", "下一条收藏", "上一条收藏"] as const) {
    if (action) await page.getByRole("button", { name: action, exact: true }).press("Enter");
    await settleVisualLayout(page);
    await expect(page.locator(".result-row.selected .result-title")).toBeInViewport({ ratio: 1 });
    const bounds = await page.locator(".result-list").evaluate(element => {
      const list = element.getBoundingClientRect(), card = element.querySelector(".result-row.selected")!.getBoundingClientRect();
      return { top: card.top, bottom: card.bottom, listTop: list.top, listBottom: list.bottom };
    });
    expect(bounds.top).toBeGreaterThanOrEqual(bounds.listTop - 1);
    expect(bounds.bottom).toBeLessThanOrEqual(bounds.listBottom + 1);
    measurements.push(bounds);
  }
  await capture(page, "reader-index-full-selection");
  await page.keyboard.press("Escape");
  await settleVisualLayout(page);
  expect(Math.abs(await page.locator(".result-list").evaluate(element => element.scrollTop) - before)).toBeLessThanOrEqual(1);
  await expect(page.locator(".result-row").nth(13).locator(".bookmark-preview")).toBeFocused();
  await writeFile(`${output}/reader-index-continuity.json`, JSON.stringify({ measurements, restoredScroll: before }, null, 2));
});

test("narrow reading leaves the collection layout and scroll in place through consecutive previews", async ({ page }) => {
  test.setTimeout(60_000);
  await savedTextFixture(page);
  const measurements = [];
  for (const { width, height } of [{ width: 390, height: 900 }, { width: 1024, height: 900 },
    { width: 320, height: 640 }, { width: 320, height: 384 }]) {
    await page.setViewportSize({ width, height });
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    const opener = page.locator(".result-row").nth(12);
    const trigger = opener.locator(".bookmark-preview");
    await settleVisualLayout(page);
    // The short workspace has nested scroll regions. Center the real control
    // rather than leaving a fractional edge clipped by the outer viewport.
    await trigger.evaluate(element => element.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" }));
    await settleVisualLayout(page);
    await test.info().attach(`reader-trigger-${width}-${height}`, {
      body: JSON.stringify(await trigger.evaluate(element => {
        const ancestors = [];
        for (let parent = element.parentElement; parent; parent = parent.parentElement) {
          const style = getComputedStyle(parent);
          if (/(auto|scroll|hidden|clip)/.test(`${style.overflowX} ${style.overflowY}`)) {
            ancestors.push({ className: parent.className, rect: parent.getBoundingClientRect().toJSON(),
              scroll: parent.scrollTop, extent: parent.scrollHeight, clientHeight: parent.clientHeight });
          }
        }
        return { viewport: { width: innerWidth, height: innerHeight }, rect: element.getBoundingClientRect().toJSON(), ancestors };
      })), contentType: "application/json",
    });
    await expect(trigger).toBeInViewport({ ratio: 1 });
    const before = await page.locator(".result-list").evaluate(element => ({
      scroll: element.scrollTop,
      extent: element.scrollHeight,
      columns: getComputedStyle(element).gridTemplateColumns,
      workspaceScroll: element.closest<HTMLElement>(".main-workspace")!.scrollTop,
      workspaceExtent: element.closest<HTMLElement>(".main-workspace")!.scrollHeight,
      workspaceClientHeight: element.closest<HTMLElement>(".main-workspace")!.clientHeight,
    }));
    expect(before.scroll).toBeGreaterThan(0);
    await trigger.click();
    await expect(page.locator(".body-text")).toBeVisible();
    await expect(page.locator(".collection-view-switch")).toHaveCount(1);
    await expect(page.getByRole("group", { name: "收藏显示方式", exact: true })).toHaveCount(0);
    const toolbars = [];
    for (const action of [null, "下一条收藏", "上一条收藏"] as const) {
      if (action) await page.getByRole("button", { name: action, exact: true }).press("Enter");
      await settleVisualLayout(page);
      const current = await page.locator(".result-list").evaluate(element => ({
        scroll: element.scrollTop,
        extent: element.scrollHeight,
        columns: getComputedStyle(element).gridTemplateColumns,
        workspaceScroll: element.closest<HTMLElement>(".main-workspace")!.scrollTop,
        workspaceExtent: element.closest<HTMLElement>(".main-workspace")!.scrollHeight,
        workspaceClientHeight: element.closest<HTMLElement>(".main-workspace")!.clientHeight,
      }));
      const toolbar = await page.locator(".preview-drawer .preview-heading").evaluate(element => {
        const header = element.getBoundingClientRect();
        const count = element.querySelector(".reader-count")!;
        const text = document.createRange(); text.selectNodeContents(count);
        const countRects = [...text.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0)
          .map(rect => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }));
        // React renders the two numbers and separator as separate text nodes.
        // Count their actual vertical lines, retaining every measured fragment.
        const lineTops: number[] = [];
        for (const rect of countRects) if (!lineTops.some(top => Math.abs(top - rect.top) <= 1)) lineTops.push(rect.top);
        return { countRects, countLines: lineTops.length, buttons: [...element.querySelectorAll("button")].map(button => {
          const box = button.getBoundingClientRect();
          const style = getComputedStyle(button);
          const focusOutset = style.outlineStyle === "none" ? 0
            : Math.max(0, parseFloat(style.outlineWidth) + parseFloat(style.outlineOffset));
          return { left: box.left, right: box.right, top: box.top, bottom: box.bottom, focusOutset };
        }), left: header.left, right: header.right, top: header.top, bottom: header.bottom };
      });
      await test.info().attach(`reader-context-${width}-${height}-${action ?? "open"}`, {
        body: JSON.stringify({ viewport: { width, height }, before, current, toolbar }),
        contentType: "application/json",
      });
      expect(current).toEqual(before);
      expect(toolbar.countLines).toBe(1);
      for (const rect of toolbar.countRects) {
        expect(rect.left).toBeGreaterThanOrEqual(toolbar.left);
        expect(rect.right).toBeLessThanOrEqual(toolbar.right);
        expect(rect.top).toBeGreaterThanOrEqual(toolbar.top);
        expect(rect.bottom).toBeLessThanOrEqual(toolbar.bottom);
      }
      for (const button of toolbar.buttons) {
        expect(button.left).toBeGreaterThanOrEqual(toolbar.left);
        expect(button.right).toBeLessThanOrEqual(toolbar.right);
        expect(button.top).toBeGreaterThanOrEqual(toolbar.top);
        expect(button.bottom).toBeLessThanOrEqual(toolbar.bottom);
        if (button.focusOutset > 0) {
          const focus = { left: button.left - button.focusOutset, right: button.right + button.focusOutset,
            top: button.top - button.focusOutset, bottom: button.bottom + button.focusOutset };
          expect(focus.left).toBeGreaterThanOrEqual(toolbar.left);
          expect(focus.right).toBeLessThanOrEqual(toolbar.right);
          expect(focus.top).toBeGreaterThanOrEqual(toolbar.top);
          expect(focus.bottom).toBeLessThanOrEqual(toolbar.bottom);
          for (const neighbor of [...toolbar.countRects, ...toolbar.buttons.filter(other => other !== button)]) {
            const overlaps = Math.min(focus.right, neighbor.right) > Math.max(focus.left, neighbor.left)
              && Math.min(focus.bottom, neighbor.bottom) > Math.max(focus.top, neighbor.top);
            expect(overlaps).toBe(false);
          }
        }
      }
      if (action) expect(toolbar.buttons.some(button => button.focusOutset > 0)).toBe(true);
      toolbars.push({ action: action ?? "open", ...toolbar });
    }
    await expect(page.getByRole("button", { name: "返回收藏", exact: true })).toBeVisible();
    await capture(page, `reader-background-context-${width}-${height}`);
    await page.keyboard.press("Escape");
    await settleVisualLayout(page);
    const restored = await page.locator(".result-list").evaluate(element => ({
      scroll: element.scrollTop,
      extent: element.scrollHeight,
      columns: getComputedStyle(element).gridTemplateColumns,
      workspaceScroll: element.closest<HTMLElement>(".main-workspace")!.scrollTop,
      workspaceExtent: element.closest<HTMLElement>(".main-workspace")!.scrollHeight,
      workspaceClientHeight: element.closest<HTMLElement>(".main-workspace")!.clientHeight,
    }));
    await test.info().attach(`reader-return-${width}-${height}`, {
      body: JSON.stringify({ viewport: { width, height }, before, current: restored }), contentType: "application/json",
    });
    expect(restored).toEqual(before);
    await expect(opener.locator(".bookmark-preview")).toBeFocused();
    measurements.push({ width, height, ...before, toolbars });
  }
  await writeFile(`${output}/reader-background-context.json`, JSON.stringify(measurements, null, 2));
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
  await expect(page.locator(".reader-summary")).toBeVisible();
  await expect(page.locator(".preview-tabs [role=tab]")).toHaveCount(2);
  await expect(page.getByRole("tab", { name: "AI 摘要", exact: true })).toHaveCount(0);
  await expect(page.locator(".reading-position")).toBeVisible();
  await capture(page, "reader-summary");
  await page.keyboard.press("Escape");
  await savedTextFixture(page, "");
  await first.click({ position: { x: 7, y: 7 } });
  await expect(page.locator(".reader-summary")).toBeVisible();
  await expect(page.locator(".reader-source-missing")).toContainText("正文尚未保存");
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
    for (let i = 0; i < await tabs.count(); i++) {
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
