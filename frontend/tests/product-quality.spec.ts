import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
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

for (const [language, theme, width, height] of [
  ["zh", "light", 320, 760], ["en", "dark", 320, 640], ["zh", "dark", 390, 640],
] as const) test(`narrow collection keeps its direct actions together and leaves space to scan ${language} ${width}`, async ({ page }) => {
  await page.addInitScript(([language, theme]) => {
    localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme);
    localStorage.setItem("fm-collection-layout", "grid");
  }, [language, theme]);
  await page.setViewportSize({ width, height });
  await collection(page); await settleVisualLayout(page);
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
  await expect(page.locator(".result-row").first()).toBeInViewport({ ratio: 1 });
  if (height >= 760) await expect(page.locator(".bookmark-heading").nth(1)).toBeInViewport({ ratio: 1 });
  await page.locator(".library-manage > summary").focus(); await page.keyboard.press("Space");
  await expect(page.locator(".library-manage-menu")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".library-manage > summary")).toBeFocused();
  await page.screenshot({ path: `screenshots/collection-review/quality-collection-${language}-${theme}-${width}-${height}.png` });
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
    await route.fulfill({ json: { ...record, note: "", note_revision: 0, legacy_note_text: "",
      summary: "内容与来源先进入阅读视野。", key_points: ["完整原文可直接抵达。"],
      body_text: "## 保存的阅读上下文\n\n" + "这是一段保留完整来源的合成阅读内容。".repeat(80) } });
  });
  await collection(page); await page.locator(".bookmark-preview").first().click();
  const notes = page.getByRole("region", { name: "我的笔记", exact: true });
  await expect(notes).toBeVisible();
  expect((await notes.boundingBox())!.height).toBeLessThanOrEqual(56);
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/quality-reader-content-first.png" });
  await page.getByRole("button", { name: "跳到保存的原文", exact: true }).focus(); await page.keyboard.press("Enter");
  const source = page.locator(".reader-source h2").first();
  await expect(source).toBeInViewport({ ratio: 1 }); await expect(source).toBeFocused();
  await page.getByRole("button", { name: "回到顶部", exact: true }).click();
  await expect(notes).toBeInViewport({ ratio: 1 });
  await notes.getByRole("button", { name: "写笔记", exact: true }).click();
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
  await page.addInitScript(language => localStorage.setItem("fm-language", language), language);
  await page.setViewportSize({ width: 320, height: 760 });
  await page.route("**/bookmark/*?body=true", async route => {
    const response = await route.fetch(), record = await response.json();
    await route.fulfill({ json: { ...record, summary: "A concise overview of the saved source.",
      key_points: ["Keep the full source reachable."], body_text: "Saved source text.\n\n" + "Readable content. ".repeat(80) } });
  });
  await collection(page); await page.locator(".bookmark-preview").first().click();
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
  await page.screenshot({ path: `screenshots/collection-review/quality-reader-actions-${language}-320.png` });
  await page.getByRole("button", { name: language === "zh" ? "跳到保存的原文" : "Jump to saved source text", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".reader-source h2")).toBeFocused();
  await expect(page.locator(".reader-source h2")).toBeInViewport({ ratio: 1 });
});

for (const tags of [
  ["需要保留完整文字的长标签".repeat(5), "标签二", "标签三", "标签四", "标签五", "标签六"],
  ["宽".repeat(23)],
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
  await page.screenshot({ path: `screenshots/collection-review/quality-collection-long-tags-${tags.length}-390.png` });
  await row.getByRole("button", { name: "展开全部标签", exact: true }).click();
  await expect(items).toHaveCount(tags.length); await expect(items.last()).toHaveText(tags[tags.length - 1]);
  await expect(items.first()).toHaveText(tags[0]);
  await row.getByRole("button", { name: "收起标签", exact: true }).click();
  await expect(items).toHaveCount(Math.min(3, tags.length));
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
