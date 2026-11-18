import { expect, test, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import type { SyncWorkspace } from "../src/sync-local-state";
import type { SyncPreview, SyncStatus } from "../src/sync-types";
import { settleVisualLayout } from "./visual-layout";

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
});

async function collection(page: Page) {
  await page.goto("/app");
  await expect(page.locator(".result-row").first()).toBeVisible();
}

async function settings(page: Page) {
  await page.locator(".header-utilities").getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.locator(".settings-workspace")).toBeVisible();
}

function originalSyncPreview() {
  const revision = "a".repeat(64);
  const workspace: SyncWorkspace = { version: 1, configRevision: revision, previewId: "navigation-original-preview",
    draft: { folder: "/synthetic/shared/draft", enabled: true, auto_sync: false, poll_seconds: "90" },
    resolutions: {}, confirmed: false };
  const status: SyncStatus = { folder: "/synthetic/shared/saved", enabled: true, auto_sync: false, poll_seconds: 60,
    configured: true, config_revision: revision, needs_review: true, last_sync_at: null, last_sync_id: null,
    last_error: "", pending_conflicts: 0, pending_operations: [] };
  const preview: SyncPreview = { preview_id: workspace.previewId!, expires_at: Math.floor(Date.now() / 1000) + 3600,
    counts: { upload_new: 0, upload_update: 0, upload_delete: 0, download_new: 0, download_update: 0,
      download_delete: 0, unchanged: 1, conflicts: 0 }, conflicts: [], changes: [],
    excluded_karakeep: 0, excluded_unsupported: 0, stale: false };
  return { workspace, status, preview };
}

test("settings opened from the collection remains the current page after refresh", async ({ page }) => {
  await collection(page);
  await settings(page);
  await expect(page.getByRole("tab", { name: "AI 连接", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.reload();
  await expect(page.locator(".settings-workspace")).toBeVisible();
  await expect(page.getByRole("tab", { name: "AI 连接", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.screenshot({ path: "screenshots/collection-review/quality-settings-refresh.png" });
});

test("task navigation survives refresh and browser Back returns to the preceding page", async ({ page }) => {
  await collection(page);
  await page.locator(".header-utilities").getByRole("button", { name: "任务", exact: true }).click();
  await expect(page.getByRole("heading", { name: "任务与诊断", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "任务与诊断", exact: true })).toBeVisible();
  await settings(page);
  await page.goBack();
  await expect(page.getByRole("heading", { name: "任务与诊断", exact: true })).toBeVisible();
});

test("a local connection draft survives finding a bookmark without a save or a connection test", async ({ page }) => {
  let saves = 0, probes = 0;
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (path === "/admin/settings" && request.method() === "PUT") saves++;
    if (request.method() === "POST" && (path === "/admin/test" || path === "/admin/settings/test"
      || path.startsWith("/admin/model-profiles/") && path.endsWith("/test"))) probes++;
  });
  await collection(page);
  await settings(page);
  const chat = page.locator(".settings-workspace .model-chat");
  await expect(chat.getByRole("combobox", { name: "摘要来源", exact: true })).toBeEnabled();
  await chat.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("endpoint");
  const model = chat.locator('input[name="chat_model"]');
  await expect(model).toBeEnabled();
  await model.fill("manual-navigation-draft-2026");
  const endpoint = chat.locator('input[name="chat_base_url"]');
  await endpoint.fill("https://draft.example.invalid/v1");
  const secret = "synthetic-navigation-secret-kept-in-memory";
  const key = chat.locator('input[name="chat_api_key"]');
  await key.fill(secret);
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("textbox", { name: "搜索书签", exact: true })).toBeFocused();
  await expect(page.locator(".settings-workspace")).toBeHidden();
  await settings(page);
  await expect(model).toHaveValue("manual-navigation-draft-2026");
  await expect(endpoint).toHaveValue("https://draft.example.invalid/v1");
  await expect(key).toHaveValue(secret);
  expect(page.url()).not.toContain(secret);
  expect(await page.evaluate(value => Object.keys(localStorage).some(name => localStorage.getItem(name)?.includes(value)), secret)).toBe(false);
  await page.locator(".app-header .brand").click();
  await expect(page.locator(".settings-workspace")).toBeHidden();
  await settings(page);
  await expect(model).toHaveValue("manual-navigation-draft-2026");
  await expect(key).toHaveValue(secret);
  await settleVisualLayout(page);
  expect(saves).toBe(0);
  expect(probes).toBe(0);
  await page.screenshot({ path: "screenshots/collection-review/quality-settings-draft-retained.png" });
});

test("returning to sync resumes an interrupted original preview without writing settings or losing the draft", async ({ page }) => {
  const { workspace, status, preview } = originalSyncPreview();
  await page.addInitScript(workspace => localStorage.setItem("fm-sync-workspace", JSON.stringify(workspace)), workspace);
  let writes = 0, previewReads = 0;
  let releaseFirstRead!: () => void;
  const firstRead = new Promise<void>(resolve => { releaseFirstRead = resolve; });
  page.on("request", request => {
    if (new URL(request.url()).pathname.startsWith("/admin/library/sync/") && request.method() !== "GET") writes++;
  });
  await page.route("**/admin/library/sync/status", route => route.fulfill({ json: status }));
  await page.route("**/admin/library/sync/previews/navigation-original-preview", async route => {
    const first = ++previewReads === 1;
    if (first) await firstRead;
    try { await route.fulfill({ json: preview }); }
    catch (failure) { if (!first) throw failure; } // The first read was deliberately aborted by navigation.
  });
  try {
    await page.goto("/app#settings/sync");
    const sync = page.locator(".sync-settings");
    await expect.poll(() => previewReads).toBe(1);
    await expect(sync.locator(".sync-state")).toHaveText("等待首次确认");
    await expect(sync.locator(".sync-loading")).toBeVisible();
    await expect(sync.getByLabel("共享文件夹完整路径")).toHaveValue(workspace.draft.folder);
    await page.keyboard.press("Control+k");
    await expect(sync).toBeHidden();
    await expect(page.getByRole("textbox", { name: "搜索书签", exact: true })).toBeFocused();
    releaseFirstRead();
    await settings(page);
    await page.getByRole("tab", { name: "设备同步", exact: true }).click();
    await expect(sync.locator(".sync-preview")).toBeVisible();
    await expect(sync.locator(".sync-loading")).toBeHidden();
    await expect(sync.getByLabel("共享文件夹完整路径")).toHaveValue(workspace.draft.folder);
    await expect(sync.getByLabel("检查间隔（秒）")).toHaveValue("90");
    expect(previewReads).toBeGreaterThanOrEqual(2);
    expect(writes).toBe(0);
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem("fm-sync-workspace")!))).toEqual(workspace);
    await page.screenshot({ path: "screenshots/collection-review/quality-sync-preview-resumed.png" });
  } finally { releaseFirstRead(); }
});

test("a cleared original sync preview cannot put its late read failure onto the edited draft", async ({ page }) => {
  const { workspace, status } = originalSyncPreview();
  await page.addInitScript(workspace => localStorage.setItem("fm-sync-workspace", JSON.stringify(workspace)), workspace);
  let previewReads = 0, writes = 0;
  let releaseRead!: () => void;
  const heldRead = new Promise<void>(resolve => { releaseRead = resolve; });
  page.on("request", request => {
    if (new URL(request.url()).pathname.startsWith("/admin/library/sync/") && request.method() !== "GET") writes++;
  });
  await page.route("**/admin/library/sync/status", route => route.fulfill({ json: status }));
  await page.route("**/admin/library/sync/previews/navigation-original-preview", async route => {
    previewReads++;
    await heldRead;
    await route.fulfill({ status: 410, json: { detail: "The cleared synthetic preview expired." } });
  });
  try {
    await page.goto("/app#settings/sync");
    const sync = page.locator(".sync-settings");
    await expect.poll(() => previewReads).toBe(1);
    await sync.getByLabel("共享文件夹完整路径").fill("/synthetic/shared/edited");
    await expect(sync.locator(".sync-preview-read")).toHaveCount(0);
    const failure = page.waitForResponse(response => new URL(response.url()).pathname.endsWith("/previews/navigation-original-preview"));
    releaseRead();
    const response = await failure;
    expect(response.status()).toBe(410);
    await response.finished(); await settleVisualLayout(page);
    await expect(sync.locator(".sync-loading")).toBeHidden();
    await expect(sync.getByRole("alert")).toHaveCount(0);
    await expect(sync.locator(".sync-preview")).toHaveCount(0);
    await expect(sync.getByLabel("共享文件夹完整路径")).toHaveValue("/synthetic/shared/edited");
    expect(writes).toBe(0);
    const stored: SyncWorkspace = await page.evaluate(() => JSON.parse(localStorage.getItem("fm-sync-workspace")!));
    expect(stored.previewId).toBeUndefined(); expect(stored.draft.folder).toBe("/synthetic/shared/edited");
  } finally { releaseRead(); }
});

test("search shortcut closes a narrow reader and focuses the usable collection search", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 640 });
  await collection(page);
  await page.locator(".bookmark-preview").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog")).toBeHidden();
  const search = page.getByRole("textbox", { name: "搜索书签", exact: true });
  await expect(search).toBeFocused();
  await search.fill("navigation-source-query");
  await expect(search).toHaveValue("navigation-source-query");
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/quality-reader-to-search-390.png" });
});

test("search shortcut leaves the navigation drawer and keeps focus in search", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 640 });
  await collection(page);
  await page.getByRole("button", { name: "打开导航", exact: true }).click();
  await expect(page.locator(".sidebar.is-open")).toBeVisible();
  await page.keyboard.press("Control+k");
  await expect(page.locator(".sidebar.is-open")).toHaveCount(0);
  await settleVisualLayout(page);
  await expect(page.getByRole("textbox", { name: "搜索书签", exact: true })).toBeFocused();
});

test("import and setup navigation retain their own pages after refresh and browser Back", async ({ page }) => {
  await collection(page);
  await page.locator(".app-header").getByRole("button", { name: "导入书签", exact: true }).click();
  await expect(page.getByRole("heading", { name: "导入书签", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "导入书签", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "打开完整向导", exact: true }).click();
  await expect(page.locator(".setup-flow")).toBeVisible();
  await page.reload();
  await expect(page.locator(".setup-flow")).toBeVisible();
  await page.locator(".header-navigation").getByRole("button", { name: "全部书签", exact: true }).click();
  await expect(page.locator(".result-row").first()).toBeVisible();
  await page.goBack();
  await expect(page.locator(".setup-flow")).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "导入书签", exact: true })).toBeVisible();
});

for (const [language, theme, width, height, total] of [
  ["zh", "light", 320, 760, null], ["en", "dark", 320, 640, null], ["zh", "dark", 390, 640, null],
  ["en", "dark", 320, 640, 200000], ["en", "light", 320, 640, 200000],
  ["zh", "light", 320, 760, 200000], ["en", "dark", 390, 640, 200000],
] as const) test(`narrow collection keeps its direct actions together and leaves space to scan ${language} ${width}${total === null ? "" : ` ${theme} ${total}`}`, async ({ page }) => {
  await page.addInitScript(([language, theme]) => {
    localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme);
    localStorage.setItem("fm-collection-layout", "grid");
  }, [language, theme]);
  // Keep the service's actual records; override only the count to isolate the
  // layout boundary. Deep paging uses the separate real 200k corpus test.
  if (total !== null) await page.route(url => url.pathname === "/bookmarks", async route => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({ response, json: { ...data, total } });
  });
  await page.setViewportSize({ width, height });
  await collection(page); await settleVisualLayout(page);
  const count = page.locator(".library-selection-count");
  await expect(count).toHaveText((await count.getAttribute("aria-label"))!);
  const bounds = await page.locator(".library-tools").evaluate(element => {
    const controls = [".library-add", ".library-manage > summary", ".library-summary-selection", ".library-summarize"];
    return controls.map(selector => {
      const box = element.querySelector(selector)!.getBoundingClientRect();
      return { left: box.left, right: box.right, top: box.top, height: box.height };
    });
  });
  for (const control of bounds) {
    expect(control.left).toBeGreaterThanOrEqual(0); expect(control.right).toBeLessThanOrEqual(width);
    expect(Math.abs(control.top - bounds[0].top)).toBeLessThan(1);
    expect(control.height).toBeGreaterThanOrEqual(44);
  }
  const footer = page.locator(".results-footer");
  const footerGeometry = await footer.evaluate(element => {
    const box = (node: Element) => {
      const rect = node.getBoundingClientRect();
      return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height };
    };
    const textRects = (selector: string) => {
      const text = document.createRange(); text.selectNodeContents(element.querySelector(selector)!);
      return [...text.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0)
        .map(rect => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }));
    };
    return { footer: box(element), countGroup: box(element.querySelector(".collection-subtitle")!),
      count: element.querySelector(".result-count")!.textContent, countRects: textRects(".result-count"),
      unitRects: textRects(".collection-count-label"), pageCountRects: textRects(".page-jump > span"), paging: box(element.lastElementChild!),
      controls: [...element.querySelectorAll("input, button")].map(box),
      scrollWidth: element.scrollWidth, clientWidth: element.clientWidth };
  });
  if (total !== null) {
    await writeFile(`screenshots/collection-review/quality-pagination-${language}-${theme}-${width}-${total}.json`, JSON.stringify(footerGeometry, null, 2));
    await page.screenshot({ path: `screenshots/collection-review/quality-pagination-${language}-${theme}-${width}-${total}.png` });
    await expect(footer.locator(".result-count")).toHaveText(String(total));
  }
  for (const fragment of [...footerGeometry.countRects, ...footerGeometry.unitRects]) {
    expect(fragment.left).toBeGreaterThanOrEqual(footerGeometry.countGroup.left - 1);
    expect(fragment.right).toBeLessThanOrEqual(footerGeometry.countGroup.right + 1);
    expect(fragment.right).toBeLessThanOrEqual(footerGeometry.paging.left - 1);
  }
  const focusPaints: unknown[] = [];
  for (const control of [
    footer.getByRole("button", { name: /^(上一页|Previous page)$/, exact: true }),
    footer.getByRole("button", { name: /^(下一页|Next page)$/, exact: true }),
    footer.getByRole("button", { name: /^(跳转|Go)$/, exact: true }),
    footer.getByRole("spinbutton", { name: /^(跳转页码|Page to jump to)$/, exact: true }),
  ]) {
    await expect(control).toBeInViewport({ ratio: 1 });
    const box = (await control.boundingBox())!;
    expect(box.width).toBeGreaterThanOrEqual(44); expect(box.height).toBeGreaterThanOrEqual(44);
    if (await control.isEnabled()) {
      await control.focus(); await page.keyboard.press("ArrowRight");
      const outline = await control.evaluate(element => {
        const rect = element.getBoundingClientRect(), style = getComputedStyle(element);
        const extra = Math.max(0, parseFloat(style.outlineWidth) + parseFloat(style.outlineOffset));
        return { focused: element.matches(":focus-visible") || element.getAttribute("data-focus-visible") === "true",
          width: parseFloat(style.outlineWidth), style: style.outlineStyle, extra,
          left: rect.left - extra, right: rect.right + extra, top: rect.top - extra, bottom: rect.bottom + extra };
      });
      focusPaints.push(outline);
      expect(outline.focused).toBe(true); expect(outline.style).toBe("solid"); expect(outline.width).toBeGreaterThanOrEqual(2);
      expect(outline.left).toBeGreaterThanOrEqual(footerGeometry.footer.left - 1); expect(outline.right).toBeLessThanOrEqual(footerGeometry.footer.right + 1);
      expect(outline.top).toBeGreaterThanOrEqual(footerGeometry.footer.top - 1); expect(outline.bottom).toBeLessThanOrEqual(footerGeometry.footer.bottom + 1);
      for (const neighbor of [...footerGeometry.countRects, ...footerGeometry.unitRects, ...footerGeometry.pageCountRects,
        ...footerGeometry.controls.filter(other => Math.abs(other.left - box.x) > .1 || Math.abs(other.top - box.y) > .1)]) {
        const overlapX = Math.min(outline.right, neighbor.right) - Math.max(outline.left, neighbor.left);
        const overlapY = Math.min(outline.bottom, neighbor.bottom) - Math.max(outline.top, neighbor.top);
        expect(overlapX <= 0 || overlapY <= 0).toBe(true);
      }
    }
  }
  if (total !== null) {
    await writeFile(`screenshots/collection-review/quality-pagination-focus-${language}-${theme}-${width}-${total}.json`, JSON.stringify(focusPaints, null, 2));
    await page.screenshot({ path: `screenshots/collection-review/quality-pagination-focus-${language}-${theme}-${width}-${total}.png` });
  }
  expect(await footer.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  expect((await footer.boundingBox())!.height).toBeLessThanOrEqual(52);
  await expect(footer.locator(".result-count")).toBeInViewport({ ratio: 1 });
  await expect(footer.locator(".collection-count-label")).toBeInViewport({ ratio: 1 });
  await expect(page.locator(".result-row").first()).toBeInViewport({ ratio: 1 });
  expect((await page.locator(".result-row").first().boundingBox())!.height).toBeLessThan(300);
  expect((await page.locator(".search-header").boundingBox())!.height).toBeLessThan(130);
  await expect(page.locator(".bookmark-heading").nth(1)).toBeInViewport({ ratio: height >= 760 ? 1 : .4 });
  await page.locator(".library-manage > summary").focus(); await page.keyboard.press("Space");
  await expect(page.locator(".library-manage-menu")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".library-manage > summary")).toBeFocused();
  await page.screenshot({ path: `screenshots/collection-review/quality-collection-${language}-${theme}-${width}-${height}.png` });
});

test("compact collection menus retain status, sorting and layout across the breakpoint without writes", async ({ page }) => {
  const queries: { status: string | null; sort: string | null }[] = []; let writes = 0;
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.pathname === "/bookmarks" && request.method() === "GET") queries.push({ status: url.searchParams.get("status"), sort: url.searchParams.get("sort") });
    if (url.pathname.startsWith("/admin/bookmarks") && request.method() !== "GET") writes++;
  });
  await page.setViewportSize({ width: 320, height: 640 }); await collection(page);
  const status = page.locator(".collection-status-menu"), display = page.locator(".collection-options-menu");
  await status.locator(":scope > summary").focus(); await page.keyboard.press("Space");
  await expect(status.locator(".collection-status .fm-button")).toHaveCount(4);
  await status.locator('[data-status="pending"]').press("Enter");
  await expect(status).toHaveJSProperty("open", false);
  await expect(status.locator(":scope > summary")).toBeFocused();
  await expect(status.locator(":scope > summary")).toHaveAttribute("aria-label", /待生成/);
  await display.locator(":scope > summary").press("Enter");
  await display.getByRole("combobox", { name: "排序", exact: true }).selectOption("oldest");
  await expect.poll(() => queries.some(value => value.status === "pending" && value.sort === "oldest")).toBe(true);
  await display.getByRole("button", { name: "原文摘录", exact: true }).click();
  await expect(display.getByRole("button", { name: "原文摘录", exact: true })).toHaveAttribute("aria-pressed", "true");
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/quality-collection-browse-menu-320.png" });
  await display.getByRole("button", { name: "列表视图", exact: true }).press("Space");
  await expect(display).toHaveJSProperty("open", false); await expect(display.locator(":scope > summary")).toBeFocused();
  await expect(page.locator(".main-workspace")).toHaveClass(/list-mode/);
  await page.setViewportSize({ width: 720, height: 850 });
  await expect(status).toHaveCount(0);
  await expect(page.locator('.collection-status [data-status="pending"]')).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("combobox", { name: "排序", exact: true })).toHaveValue("oldest");
  await expect(page.locator(".collection-view-switch").getByRole("button", { name: "列表视图", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.setViewportSize({ width: 719, height: 640 });
  await expect(status.locator(":scope > summary")).toHaveAttribute("aria-label", /待生成/);
  await display.locator(":scope > summary").press("Enter");
  await expect(display.getByRole("combobox", { name: "排序", exact: true })).toHaveValue("oldest");
  await expect(display.getByRole("button", { name: "原文摘录", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(display.getByRole("button", { name: "列表视图", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Escape"); await expect(display.locator(":scope > summary")).toBeFocused();
  expect(writes).toBe(0);
});

for (const [language, theme] of [["zh", "light"], ["en", "dark"]] as const)
test(`all five settings categories are visible and retain keyboard history ${language}`, async ({ page }) => {
  await page.addInitScript(([language, theme]) => {
    localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme);
  }, [language, theme]);
  await page.setViewportSize({ width: 320, height: 640 });
  await page.goto("/app#settings/models");
  await expect(page.locator(".settings-workspace")).toBeVisible();
  for (const id of ["models", "sync", "extension", "mcp", "desktop"])
    await expect(page.locator("#settings-tab-" + id)).toBeInViewport({ ratio: 1 });
  await page.locator("#settings-tab-models").focus(); await page.keyboard.press("End");
  await expect(page.locator("#settings-tab-desktop")).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator("#settings-tab-mcp")).toHaveAttribute("aria-selected", "true");
  await page.goBack();
  await expect(page.locator("#settings-tab-desktop")).toHaveAttribute("aria-selected", "true");
  await page.goForward();
  await expect(page.locator("#settings-tab-mcp")).toHaveAttribute("aria-selected", "true");
  await page.reload();
  await expect(page.locator("#settings-panel-mcp")).toBeVisible();
  await settleVisualLayout(page);
  await page.screenshot({ path: `screenshots/collection-review/quality-settings-categories-${language}-${theme}-320.png` });
});

test("entering desktop settings does not initialize the unvisited connection form", async ({ page }) => {
  let settingReads = 0, detections = 0;
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (path === "/admin/settings" && request.method() === "GET") settingReads++;
    if (path === "/admin/agents" && request.method() === "GET") detections++;
  });
  await page.goto("/app#settings/desktop");
  await expect(page.locator("#settings-panel-desktop")).toBeVisible(); await settleVisualLayout(page);
  expect(settingReads).toBe(0); expect(detections).toBe(0);
  await page.getByRole("tab", { name: "AI 连接", exact: true }).click();
  await expect(page.locator('.model-chat input[name="chat_model"]')).toBeEnabled();
  expect(settingReads).toBe(1); expect(detections).toBe(1);
});

test("an empty note stays compact while source navigation and retained drafts remain usable", async ({ page }) => {
  let saves = 0;
  page.on("request", request => { if (request.method() === "PATCH" && new URL(request.url()).pathname.endsWith("/note")) saves++; });
  await page.route("**/bookmark/*?body=true", async route => {
    const response = await route.fetch(), record = await response.json();
    await route.fulfill({ json: { ...record, date_added: 0, note: "", note_revision: 0, legacy_note_text: "",
      summary: "内容与来源先进入阅读视野。", key_points: ["完整原文可直接抵达。"],
      body_text: "## 保存的阅读上下文\n\n" + "这是一段保留完整来源的合成阅读内容。".repeat(80) } });
  });
  await collection(page); await page.locator(".bookmark-preview").first().click();
  await expect(page.locator(".article-source .source-rule")).toHaveCount(0);
  const notes = page.getByRole("region", { name: "我的笔记", exact: true });
  await expect(notes).toBeVisible();
  expect((await notes.boundingBox())!.height).toBeLessThanOrEqual(56);
  expect(await notes.evaluate(element => Boolean(element.closest(".article-options")))).toBe(true);
  const noteBox = (await notes.boundingBox())!, sizeBox = (await page.locator(".reader-type-controls").boundingBox())!;
  expect(Math.abs(noteBox.y - sizeBox.y)).toBeLessThanOrEqual(4);
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/quality-reader-content-first.png" });
  await page.getByRole("button", { name: "跳到保存的原文", exact: true }).focus(); await page.keyboard.press("Enter");
  const source = page.locator(".reader-source h2").first();
  await expect(source).toBeInViewport({ ratio: 1 }); await expect(source).toBeFocused();
  await page.getByRole("button", { name: "回到顶部", exact: true }).click();
  await expect(notes).toBeInViewport({ ratio: 1 });
  await notes.getByRole("button", { name: "写笔记", exact: true }).focus(); await page.keyboard.press("Space");
  expect(await notes.evaluate(element => Boolean(element.closest(".reading")))).toBe(true);
  const editor = notes.getByRole("textbox", { name: "个人阅读笔记", exact: true });
  await expect(editor).toBeFocused(); await editor.fill("继续浏览后仍保留的本机阅读草稿。");
  await notes.getByRole("button", { name: "收起编辑，保留草稿", exact: true }).click();
  await expect(notes).toContainText("未保存的草稿已保留");
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("textbox", { name: "搜索书签", exact: true })).toBeFocused();
  await page.locator(".bookmark-preview").first().click();
  await expect(editor).toHaveValue("继续浏览后仍保留的本机阅读草稿。");
  expect(saves).toBe(0);
});

for (const language of ["zh", "en"] as const)
test(`overview actions and saved source remain reachable in a narrow reader ${language}`, async ({ page }) => {
  const previews: Record<string, unknown>[] = []; let readingId = 0;
  await page.route("**/admin/jobs/preview", async route => {
    previews.push(route.request().postDataJSON());
    await route.fulfill({ status: 503, json: { detail: "Synthetic reading menu refusal" } });
  });
  await page.addInitScript(language => localStorage.setItem("fm-language", language), language);
  await page.setViewportSize({ width: 320, height: 760 });
  await page.route("**/bookmark/*?body=true", async route => {
    const response = await route.fetch(), record = await response.json();
    readingId = record.bookmark_id;
    await route.fulfill({ json: { ...record, date_added: 1_700_000_000, summary: "A concise overview of the saved source.",
      key_points: ["Keep the full source reachable."], body_text: "Saved source text.\n\n" + "Readable content. ".repeat(80) } });
  });
  await collection(page); await page.locator(".bookmark-preview").first().click();
  await expect(page.locator(".article-source .source-rule")).toHaveCount(1);
  await expect(page.locator(".article-source")).toContainText("2023");
  for (const control of await page.locator(".reader-actions > .icon-button:not(.focus-reading), .preview-tabs > button").all()) {
    await expect(control).toBeInViewport({ ratio: 1 });
    const box = (await control.boundingBox())!;
    expect(box.width).toBeGreaterThanOrEqual(44); expect(box.height).toBeGreaterThanOrEqual(44);
  }
  const header = page.locator(".reader-summary > .reader-section-heading");
  await expect(header).toBeVisible(); await settleVisualLayout(page);
  const bounds = await header.evaluate(element => {
    const parent = element.getBoundingClientRect();
    return Array.from(element.querySelectorAll("h2, button"), child => {
      const box = child.getBoundingClientRect();
      return { left: box.left, right: box.right, parentLeft: parent.left, parentRight: parent.right };
    });
  });
  for (const control of bounds) {
    expect(control.left).toBeGreaterThanOrEqual(control.parentLeft - 1);
    expect(control.right).toBeLessThanOrEqual(control.parentRight + 1);
  }
  expect((await page.locator(".reader-summary-text").boundingBox())!.y).toBeLessThan(530);
  const tools = page.locator(".reader-options-menu"), trigger = tools.locator(":scope > summary");
  await page.screenshot({ path: `screenshots/collection-review/quality-reader-actions-${language}-320.png` });
  await trigger.focus(); await page.keyboard.press("Space");
  await expect(tools).toHaveJSProperty("open", true);
  await tools.getByRole("button", { name: language === "zh" ? "增大阅读字号" : "Increase reading text size", exact: true }).press("Enter");
  await expect(tools.locator(".reader-type-reset")).toHaveText("112%");
  await tools.getByRole("button", { name: language === "zh" ? "恢复默认阅读字号" : "Reset reading text size", exact: true }).press("Space");
  await expect(tools.locator(".reader-type-reset")).toHaveText("100%");
  await page.keyboard.press("Escape"); await expect(trigger).toBeFocused();
  await expect(tools).toHaveJSProperty("open", false);
  await trigger.press("Enter"); await tools.locator(".reader-edit").press("Space");
  const edit = page.getByRole("dialog", { name: language === "zh" ? "编辑收藏" : "Edit bookmark", exact: true });
  await expect(edit).toBeVisible(); await edit.getByRole("button", { name: language === "zh" ? "取消" : "Cancel", exact: true }).click();
  await expect(edit).toHaveCount(0); await settleVisualLayout(page); await expect(trigger).toBeFocused();
  await page.getByRole("button", { name: language === "zh" ? "跳到保存的原文" : "Jump to saved source text", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".reader-source h2")).toBeFocused();
  await expect(page.locator(".reader-source h2")).toBeInViewport({ ratio: 1 });
  await trigger.focus(); await trigger.press("Enter");
  await tools.getByRole("button", { name: language === "zh" ? "重新生成这篇摘要" : "Regenerate this summary", exact: true }).press("Space");
  await expect.poll(() => previews.length).toBe(1);
  expect(previews[0]).toEqual(expect.objectContaining({ mode: "summarize", bookmark_ids: [readingId], force: true }));
  await expect(page.locator(".summary-generation-feedback")).toContainText("Synthetic reading menu refusal");
  await page.keyboard.press("Escape");
  await expect(page.locator(".preview-drawer")).toHaveCount(0);
  await expect(page.locator(".bookmark-preview").first()).toBeFocused();
});

for (const tags of [
  ["需要保留完整文字的长标签".repeat(5), "标签二", "标签三", "标签四", "标签五", "标签六"],
  ["宽".repeat(23)],
  ["第一个完整长标签".repeat(5), "第二个完整长标签".repeat(5)],
]) test(`many or clipped tags can be inspected without expanding the initial card (${tags.length} tags)`, async ({ page }) => {
  await page.route("**/bookmarks?**", async route => {
    const response = await route.fetch(), data = await response.json();
    data.items[0].tags = tags;
    await route.fulfill({ response, json: data });
  });
  await page.setViewportSize({ width: 390, height: 640 });
  await collection(page); await settleVisualLayout(page);
  const row = page.locator(".result-row").first(), items = row.locator(".bookmark-tags li:not(.bookmark-tags-more)");
  await expect(items).toHaveCount(Math.min(3, tags.length));
  if (tags.length > 2) await expect(items.nth(2)).toBeHidden();
  await expect(row.getByRole("button", { name: "展开全部标签", exact: true })).not.toContainText("+0");
  await page.screenshot({ path: `screenshots/collection-review/quality-collection-long-tags-${tags.length}-390.png` });
  await row.getByRole("button", { name: "展开全部标签", exact: true }).focus(); await page.keyboard.press("Enter");
  await expect(items).toHaveCount(tags.length); await expect(items.last()).toHaveText(tags[tags.length - 1]);
  await expect(items.first()).toHaveText(tags[0]);
  await expect(items.last()).toBeVisible();
  await row.getByRole("button", { name: "收起标签", exact: true }).focus(); await page.keyboard.press("Space");
  await expect(items).toHaveCount(Math.min(3, tags.length));
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("three short tags keep full text and keyboard disclosure across narrow and desktop layouts", async ({ page }) => {
  const tags = ["设计", "阅读", "笔记"];
  await page.route("**/bookmarks?**", async route => {
    const response = await route.fetch(), data = await response.json();
    data.items[0].tags = tags;
    await route.fulfill({ response, json: data });
  });
  await collection(page); await settleVisualLayout(page);
  const row = page.locator(".result-row").first(), list = row.getByRole("list", { name: "标签", exact: true });
  const items = list.locator("li:not(.bookmark-tags-more)"), disclosure = list.locator(".bookmark-tags-more button");
  await expect(items).toHaveText(tags); await expect(items.nth(2)).toBeVisible();
  await expect(disclosure).toBeHidden();
  expect(await items.evaluateAll(elements => elements.some(element => element.scrollWidth > element.clientWidth + 1))).toBe(false);
  await page.screenshot({ path: "screenshots/collection-review/quality-collection-three-tags-1280.png" });

  for (const width of [719, 720, 390]) {
    await page.setViewportSize({ width, height: 760 }); await settleVisualLayout(page);
    if (width > 719) {
      await expect(items.nth(2)).toBeVisible(); await expect(disclosure).toBeHidden();
    } else {
      await expect(items.nth(2)).toBeHidden(); await expect(disclosure).toBeVisible();
      await expect(disclosure.locator(".bookmark-tags-label-short")).toHaveText("+1");
    }
  }
  const firstTag = (await items.first().boundingBox())!, button = (await disclosure.boundingBox())!;
  expect(await items.evaluateAll(elements => elements.slice(0, 2).some(element => element.scrollWidth > element.clientWidth + 1))).toBe(false);
  expect(button.width).toBeGreaterThanOrEqual(44); expect(button.height).toBeGreaterThanOrEqual(44);
  expect(firstTag.height).toBeLessThan(button.height - 4);
  expect(Math.abs(firstTag.y + firstTag.height / 2 - button.y - button.height / 2)).toBeLessThanOrEqual(1);
  await page.screenshot({ path: "screenshots/collection-review/quality-collection-three-tags-390.png" });
  await disclosure.focus(); await page.keyboard.press("Enter");
  await expect(disclosure).toHaveAttribute("aria-expanded", "true");
  await expect(items).toHaveText(tags); await expect(items.nth(2)).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 850 }); await settleVisualLayout(page);
  await expect(items.nth(2)).toBeVisible(); await expect(disclosure).toBeVisible();
  await expect(disclosure).toHaveAccessibleName("收起标签");
  await disclosure.focus(); await page.keyboard.press("Space");
  await expect(disclosure).toHaveAttribute("aria-expanded", "false");
  await expect(disclosure).toBeHidden(); await expect(items).toHaveText(tags); await expect(items.nth(2)).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
