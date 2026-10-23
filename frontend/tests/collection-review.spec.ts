import { expect, test, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

test.skip(process.env.FACETMARK_REVIEW_CORPUS !== "1", "Representative review corpus is a separate isolated cloud run");

type Evidence = { captures: { file: string; state: string; width: number; height: number }[]; actions: string[]; errors: string[]; animationFrames?: unknown[]; failure?: string; recordingError?: string };
const output = "screenshots/collection-review";

async function capture(page: Page, evidence: Evidence, name: string, state: string) {
  await settleVisualLayout(page);
  const viewport = page.viewportSize()!;
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  // Visible text must not share the expansion control's painted or hit area.
  expect(await page.locator(".bookmark-description:has(.summary-expand)").evaluateAll(descriptions => descriptions.every(description => {
    const text = description.querySelector(".result-summary")!.getBoundingClientRect();
    const control = description.querySelector(".summary-expand")!.getBoundingClientRect();
    return !text.width || text.right + 6 <= control.left;
  }))).toBe(true);
  expect(await page.locator(".bookmark-preview > span").evaluateAll(labels => labels.every(label =>
    label.getBoundingClientRect().height <= parseFloat(getComputedStyle(label).lineHeight) + 1))).toBe(true);
  await page.screenshot({ path: `${output}/${name}.png`, fullPage: true, animations: "disabled" });
  evidence.captures.push({ file: `${name}.png`, state, ...viewport });
  console.info(`[collection review] captured ${name}`);
}

test("representative collection, responsive states, exact scopes, save recovery and reading continuity", async ({ browser, baseURL }) => {
  test.setTimeout(180000);
  await mkdir(output, { recursive: true });
  await mkdir("recordings/collection-review", { recursive: true });
  const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 960 },
    locale: "zh-CN", timezoneId: "Asia/Shanghai", reducedMotion: "no-preference",
    recordVideo: { dir: "recordings/collection-review", size: { width: 1440, height: 960 } } });
  await context.addInitScript(() => {
    localStorage.setItem("fm-language", "zh"); localStorage.setItem("fm-theme", "light");
    localStorage.setItem("fm-collection-layout", "grid");
  });
  await context.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const video = page.video();
  const evidence: Evidence = { captures: [], actions: [], errors: [] };
  page.on("pageerror", error => evidence.errors.push(error.message));
  try {
    await page.goto("/app");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await expect(page.locator(".bookmark-status[data-summary-status='failed']").first()).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.fonts.check('32px "Facetmark CJK"') && document.fonts.check('19px "Facetmark Latin"'))).toBe(true);
    await capture(page, evidence, "desktop", "Floating capsule navigation and layered collection, real isolated API, Chinese/mixed titles");
    await page.locator(".result-row").first().hover({ position: { x: 180, y: 100 } });
    await capture(page, evidence, "desktop-hover", "Local pointer light and source badge feedback on the actual record");
    await page.mouse.move(4, 4);
    await page.getByRole("button", { name: "切换主题", exact: true }).first().click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await capture(page, evidence, "desktop-dark", "Dark theme, same content");
    await page.getByRole("button", { name: "切换主题", exact: true }).first().click();

    await page.getByRole("button", { name: "切换语言", exact: true }).first().click();
    await expect(page.locator(".toolbar-location h1")).toHaveText("Your collection");
    await capture(page, evidence, "desktop-english", "English controls and mixed-language collection content");
    const englishSummary = page.locator(".result-row").first().locator(".bookmark-description");
    await englishSummary.getByRole("button", { name: "Show full text", exact: true }).click();
    await expect(englishSummary).toHaveClass(/expanded/);
    await capture(page, evidence, "desktop-english-expanded", "Locale change remeasures summary clipping and retains full-text access");
    await englishSummary.getByRole("button", { name: "Collapse", exact: true }).click();
    await page.getByRole("button", { name: "Switch language", exact: true }).first().click();

    const directory = page.locator(".collection-sidebar");
    const nestedFolder = "设计与体验/中文排版/界面规范/长标题与中英混排";
    const allCount = await page.locator(".result-count").textContent();
    await directory.getByRole("button", { name: "展开「设计与体验」", exact: true }).press("Enter");
    await directory.getByRole("button", { name: "展开「中文排版」", exact: true }).press("Space");
    await directory.getByRole("button", { name: "展开「界面规范」", exact: true }).press("Enter");
    const nestedOption = directory.locator(".facet-options").getByRole("button").and(directory.getByTitle(nestedFolder, { exact: true }));
    await expect(nestedOption).toBeVisible();
    await expect(page.locator(".result-count")).toHaveText(allCount!);
    await capture(page, evidence, "folder-expanded", "Four real directory levels; disclosure leaves the result scope unchanged");
    await nestedOption.press("Enter");
    await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
    await expect(page.locator(".result-row")).toHaveCount(3);
    expect((await page.locator(".result-folder").allTextContents()).every(value => value.trim() === nestedFolder)).toBe(true);
    await directory.locator(".facet-location > summary").click();
    await expect(directory.locator(".facet-location p")).toHaveText(nestedFolder.split("/").join(" / "));
    await capture(page, evidence, "folder-selected", "Exact leaf selection and a readable complete path beside the collection");
    await page.getByRole("button", { name: "切换主题", exact: true }).first().click();
    await capture(page, evidence, "folder-selected-dark", "Selected path and layered folder material in the dark theme");
    await page.getByRole("button", { name: "切换主题", exact: true }).first().click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
    const mobileDirectory = page.locator(".sidebar");
    await expect(mobileDirectory.locator(".facet-options").getByRole("button").and(mobileDirectory.getByTitle(nestedFolder, { exact: true }))).toBeVisible();
    await mobileDirectory.locator(".facet-location > summary").click();
    await mobileDirectory.locator(".facet-options").getByRole("button").and(mobileDirectory.getByTitle(nestedFolder, { exact: true })).scrollIntoViewIfNeeded();
    await capture(page, evidence, "mobile-folder-expanded", "The same exact path and expanded ancestors remain reachable in a narrow window");
    await page.keyboard.press("Escape");
    await page.setViewportSize({ width: 1440, height: 960 });
    await directory.getByRole("button", { name: "全部文件夹", exact: true }).press("Space");
    await expect(page.locator(".result-row")).toHaveCount(30);
    await expect(page.locator(".result-count")).toHaveText(allCount!);
    evidence.actions.push("Four-level folder disclosure preserves scope; exact leaf selection, full-path details and mobile return retain the same object");

    await page.getByRole("button", { name: "列表视图", exact: true }).click();
    await capture(page, evidence, "desktop-list", "Alternate horizontal reading list retains state and metadata");
    await page.getByRole("button", { name: "卡片视图", exact: true }).click();
    await capture(page, evidence, "desktop-cards", "Card layout restored through an interruptible layout transition");
    for (const viewport of [{ width: 1280, height: 600 }, { width: 1024, height: 768 }, { width: 390, height: 844 }, { width: 320, height: 760 }]) {
      await page.setViewportSize(viewport);
      await capture(page, evidence, `collection-${viewport.width}`, "Responsive collection with full operations and long Chinese text");
      await expect(page.locator(".library-tools").getByRole("button", { name: "新增收藏", exact: true })).toBeInViewport();
      await expect(page.locator(".result-title").first()).toBeInViewport();
      await expect(page.locator(".result-row").first()).toBeInViewport({ ratio: 1 });
      if (viewport.width === 320) {
        const rows = await page.locator(".collection-status .fm-button").evaluateAll(buttons =>
          buttons.map(button => Math.round(button.getBoundingClientRect().top)));
        expect(new Set(rows).size).toBe(1);
      }
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
    await expect(page.locator(".sidebar")).toHaveAttribute("aria-modal", "true");
    await expect(page.locator(".sidebar .facet-search input")).toBeVisible();
    await capture(page, evidence, "mobile-directory", "Navigation and searchable directory drawer");
    expect(await page.locator(".sidebar .facet-options").evaluate(directory => {
      const bounds = directory.getBoundingClientRect();
      return [...directory.querySelectorAll(".facet-option:not(.facet-any)")].filter(option => {
        const box = option.getBoundingClientRect();
        return box.top >= bounds.top && box.bottom <= bounds.bottom;
      }).length;
    })).toBeGreaterThanOrEqual(4);
    await page.keyboard.press("Escape");
    await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
    await page.locator(".bookmark-preview").first().click();
    await expect(page.locator(".preview-drawer .body-text")).toBeVisible();
    expect(await page.locator(".preview-drawer").evaluate(reader => {
      const heading = reader.querySelector(".preview-heading")!;
      const box = heading.getBoundingClientRect();
      // Check painting order too: modal pointer suppression can hide an overlap
      // from hit-testing alone while the application header still paints above it.
      const header = document.querySelector(".app-header")!;
      return Number(getComputedStyle(reader).zIndex) > Number(getComputedStyle(header).zIndex) &&
        reader.contains(document.elementFromPoint(box.x + 40, box.y + box.height / 2));
    })).toBe(true);
    await capture(page, evidence, "mobile-reader", "Reading drawer with saved page text and return action");
    await page.keyboard.press("Escape");
    await expect(page.locator(".bookmark-preview").first()).toBeFocused();
    evidence.actions.push("Mobile navigation and reading return restore focus");

    await page.setViewportSize({ width: 1440, height: 960 });
    const search = page.getByRole("textbox", { name: "搜索书签", exact: true });
    await search.fill("qzxvreviewnomatch728461zz");
    // Loading temporarily clears rows; wait for the completed empty result.
    await expect(page.locator(".result-count")).toHaveText("0");
    await expect(page.getByRole("button", { name: "清除条件，查看全部", exact: true })).toBeVisible();
    await expect(page.locator(".result-row")).toHaveCount(0);
    await capture(page, evidence, "empty-search", "Empty search retains query and clear-condition recovery");
    await page.getByRole("button", { name: "清除条件，查看全部", exact: true }).click();
    await expect(page.locator(".result-row")).toHaveCount(30);
    // Record only local finite motion. It is not a target-device FPS certification.
    await page.evaluate(() => {
      const state = window as typeof window & { __reviewFrames: unknown[]; __reviewRAF: number };
      state.__reviewFrames = [];
      const started = performance.now();
      const sample = () => {
        const highlight = document.querySelector('.collection-status .selection-pill');
        const row = document.querySelector('.result-row');
        state.__reviewFrames.push({ ms: performance.now() - started,
          highlight: highlight ? getComputedStyle(highlight).transform : null,
          row: row ? getComputedStyle(row).transform : null,
          running: document.getAnimations().filter(animation => animation.playState === 'running').length });
        state.__reviewRAF = requestAnimationFrame(sample);
      };
      sample();
    });
    await page.getByRole("button", { name: /^待生成/ }).click();
    await page.getByRole("button", { name: /^有摘要/ }).click();
    await page.locator(".collection-status [data-status=all]").click();
    await expect(page.locator(".result-row")).toHaveCount(30);
    await settleVisualLayout(page);
    evidence.animationFrames = await page.evaluate(() => {
      const state = window as typeof window & { __reviewFrames: unknown[]; __reviewRAF: number };
      cancelAnimationFrame(state.__reviewRAF); return state.__reviewFrames;
    });
    evidence.actions.push("Rapid status-tab reversal finishes at all results without blocking controls");

    const firstRow = page.locator(".result-row").first();
    const firstId = Number(await firstRow.getAttribute("data-bookmark-id"));
    const firstTitle = await firstRow.locator(".result-title").innerText();
    await firstRow.locator(".bookmark-check").check();
    await page.getByRole("button", { name: "下一页", exact: true }).click();
    await expect(firstRow).not.toHaveAttribute("data-bookmark-id", String(firstId));
    await firstRow.locator(".bookmark-check").check();
    await expect(page.locator(".selection-total")).toContainText("2");
    await capture(page, evidence, "batch-cross-page", "Two explicit management IDs retained across pages");
    await page.getByRole("button", { name: "生成所选摘要", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("2 条收藏");
    await expect(dialog.getByRole("button", { name: "开始任务", exact: true })).toBeDisabled();
    await capture(page, evidence, "summary-selection", "Selected summary target count and required consent");
    await dialog.getByRole("button", { name: "取消", exact: true }).click();
    await page.getByRole("button", { name: "完成选择", exact: true }).click();
    await page.getByRole("button", { name: "上一页", exact: true }).click();
    await expect(firstRow).toHaveAttribute("data-bookmark-id", String(firstId));
    // Scoped summary selection never becomes management/export's ID selection.
    await firstRow.locator(".bookmark-check").check();
    await page.getByRole("button", { name: /^全选 .* 条用于摘要$/ }).click();
    await expect(page.locator(".collection-selection")).toContainText("跨页生效");
    await capture(page, evidence, "summary-all-matching", "All-matching summary scope is separate from explicit management IDs");
    await page.getByRole("button", { name: "生成所选摘要", exact: true }).click();
    await expect(dialog.getByRole("combobox", { name: "摘要处理范围", exact: true })).toHaveValue("current");
    await capture(page, evidence, "summary-scope", "Server-scoped target review and explicit consent");
    await dialog.getByRole("button", { name: "取消", exact: true }).click();
    await page.getByRole("button", { name: "清空", exact: true }).click();

    await page.locator(".bookmark-status[data-summary-status='failed']").first().getByRole("button", { name: "重试", exact: true }).click();
    await expect(dialog).toContainText("1 条收藏");
    await capture(page, evidence, "summary-retry", "Retry targets one failed bookmark, consent still required");
    await dialog.getByRole("button", { name: "取消", exact: true }).click();
    evidence.actions.push("Selection survives pages; summary review uses selected IDs; individual retry keeps its target");

    await page.getByRole("button", { name: "新增收藏", exact: true }).click();
    await dialog.getByRole("textbox", { name: "收藏网址", exact: true }).fill("https://review.example/new-bookmark");
    const addedTitle = "把一次阅读变成长期线索：中文与 React / TypeScript 混排的新增收藏";
    await dialog.getByRole("textbox", { name: "收藏标题", exact: true }).fill(addedTitle);
    await capture(page, evidence, "add-bookmark", "Actual create form with long mixed-language title");
    let failedSave = false;
    await page.route("**/admin/library/bookmarks", async route => {
      if (route.request().method() === "POST" && !failedSave) {
        failedSave = true; await route.fulfill({ status: 503, json: { detail: "合成网络故障：保存暂未完成，请重试。" } });
      } else await route.continue();
    });
    await dialog.getByRole("button", { name: "保存", exact: true }).click();
    await expect(dialog.getByRole("alert")).toContainText("保存暂未完成");
    await expect(dialog.getByRole("textbox", { name: "收藏标题", exact: true })).toHaveValue(addedTitle);
    await capture(page, evidence, "save-failure", "One injected HTTP failure preserves the form draft");
    await dialog.getByRole("button", { name: "保存", exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await search.fill("url:review.example/new-bookmark");
    await expect(page.locator(".result-row")).toHaveCount(1);
    await expect(page.locator(".result-title")).toHaveText(addedTitle);
    const addedId = Number(await page.locator(".result-row").getAttribute("data-bookmark-id"));
    await page.reload();
    await search.fill("url:review.example/new-bookmark");
    await expect(page.locator(".result-title")).toHaveText(addedTitle);
    await capture(page, evidence, "saved-bookmark", "Actual backend save survives reload and query");
    const cleanup = await context.request.post("/admin/library/bulk", { data: { ids: [addedId], action: "delete" },
      headers: { Authorization: `Bearer ${(await (await context.request.get('/app/boot')).json()).token}` } });
    expect(cleanup.ok()).toBe(true);
    await search.fill("");
    await expect(page.locator(".result-row")).toHaveCount(30);
    evidence.actions.push("Injected save failure preserved draft; retry wrote real isolated API data; reload verified persistence");

    await page.locator(`.result-row[data-bookmark-id='${firstId}'] .bookmark-preview`).click();
    await expect(page.locator(".body-text")).toBeVisible();
    await expect(page.locator(".preview-title h1")).toHaveText(firstTitle);
    await capture(page, evidence, "desktop-reader", "Reader and retained collection index share the selected bookmark");
    await page.getByRole("tab", { name: "AI 摘要", exact: true }).click();
    await expect(page.locator(".preview-scroll")).toHaveAttribute("aria-busy", "false");
    await expect(page.locator(".reading .summary-label")).toBeVisible();
    await capture(page, evidence, "reader-summary", "Saved AI summary in the same reading context");
    await page.getByRole("tab", { name: "正文", exact: true }).click();
    await page.locator(".focus-reading").press("Enter");
    await page.locator(".focus-reading").press("Enter");
    await page.locator(".focus-reading").press("Enter");
    await expect(page.locator(".main-workspace")).toHaveClass(/focus-mode/);
    await capture(page, evidence, "focused-reader", "Focused reading after rapid reversals");
    await page.keyboard.press("Escape");
    await page.keyboard.press("Escape");
    await expect(page.locator(`.result-row[data-bookmark-id='${firstId}'] .bookmark-preview`)).toBeFocused();
    evidence.actions.push("Reader tab changes, focus-mode reversal and Escape return preserve selected object and focus");

    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.getByRole("button", { name: /^待生成/ }).click();
    await page.locator(".collection-status [data-status=all]").click();
    await expect(page.locator(".result-row")).toHaveCount(30);
    await settleVisualLayout(page);
    const active = await page.evaluate(() => document.getAnimations().filter(a => a.playState === "running" &&
      Number(a.effect?.getComputedTiming().duration) > 1).length);
    expect(active).toBe(0);
    await capture(page, evidence, "reduced-motion", "Live reduced-motion preference leaves same usable final state");
    evidence.actions.push("Live reduced-motion change ends finite animation; keyboard and final state remain usable");
    expect(evidence.errors).toEqual([]);
  } catch (error) {
    evidence.failure = error instanceof Error ? error.stack : String(error);
    throw error;
  } finally {
    try {
      await context.close();
      if (video) await video.saveAs("recordings/facetmark-collection-review.webm");
    } catch (error) {
      // Recording cleanup must not replace the original failing action.
      evidence.recordingError = String(error);
    }
    await writeFile(`${output}/review.json`, JSON.stringify(evidence, null, 2));
  }
});
