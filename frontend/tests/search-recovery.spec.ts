import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import type { Bookmark } from "../src/api";
import { settleVisualLayout } from "./visual-layout";

const failures = new WeakMap<Page, string[]>();
test.beforeEach(async ({ page }) => {
  const errors: string[] = []; failures.set(page, errors);
  page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await mkdir("screenshots/collection-review", { recursive: true });
});
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  expect(failures.get(page)).toEqual([]);
});

async function prepare(page: Page, request: APIRequestContext) {
  const boot = await request.get("/app/boot"); expect(boot.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await boot.json()).token}` };
  const saved = await request.get("/bookmarks?limit=60", { headers }); expect(saved.ok()).toBeTruthy();
  const records = (await saved.json()).items as Bookmark[]; expect(records.length).toBe(60);
  // Only response staging is synthetic. Records come from the isolated service;
  // this does not evaluate a real model or semantic relevance.
  await page.route("**/admin/setup-status", async route => {
    const response = await route.fetch(), data = await response.json();
    await route.fulfill({ response, json: { ...data, demo: false, has_vectors: true,
      vector_compatible: true, pending_apply: false,
      channels: { ...data.channels, embed: { configured: true, tested: true }, chat: { configured: true, tested: true } } } });
  });
  return records;
}
const result = (records: Bookmark[], offset = 0) => ({ hits: records.slice(offset, offset + 30),
  total: records.length, offset, limit: 30, depth: 120, has_more: offset + 30 < records.length });
const title = (record: Bookmark) => record.ai_title || record.title;
async function begin(page: Page) {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.getByRole("textbox", { name: /^(搜索书签|Search bookmarks)$/, exact: true }).fill("synthetic staged retrieval");
  await page.getByRole("combobox", { name: /^(检索方式|Search mode)$/, exact: true }).selectOption("semantic");
}

test("keyword first paint remains usable while paging waits for the same ranked result", async ({ page, request }) => {
  const records = await prepare(page, request), ranked = [...records].reverse();
  let release!: () => void, arrived!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; }), received = new Promise<void>(resolve => { arrived = resolve; });
  const requests: Record<string, unknown>[] = [];
  await page.route("**/quick?**", route => route.fulfill({ json: result(records) }));
  await page.route("**/search", async route => {
    requests.push(route.request().postDataJSON()); arrived(); await held;
    await route.fulfill({ json: result(ranked) });
  });
  try {
    await begin(page); await received;
    await expect(page.locator(".result-title").first()).toHaveText(title(records[0]));
    await expect(page.locator(".collection-hint")).toHaveText("正在语义检索，先显示关键词结果");
    await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "true");
    await expect(page.getByRole("button", { name: "下一页", exact: true })).toBeDisabled();
    await expect(page.getByRole("spinbutton", { name: "跳转页码", exact: true })).toBeDisabled();
    const selected = page.locator(`.result-row[data-bookmark-id="${records[0].bookmark_id}"] .bookmark-check`);
    await selected.check();
    release();
    await expect(page.locator(".result-title").first()).toHaveText(title(ranked[0]));
    await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
    await expect(page.locator(".collection-hint")).toHaveText("语义检索结果");
    await expect(page.getByRole("button", { name: "下一页", exact: true })).toBeEnabled();
    await expect(page.locator(".library-selection-count")).toHaveText("已选 1");
    expect(requests).toEqual([{ q: "synthetic staged retrieval ", offset: 0, limit: 30, depth: 120 }]);
  } finally { release(); }
});

test("a failed keyword first paint still runs the full search and shows its result", async ({ page, request }) => {
  const records = await prepare(page, request); let calls = 0;
  await page.route("**/quick?**", route => route.fulfill({ status: 503, json: { detail: "Synthetic quick read unavailable" } }));
  await page.route("**/search", route => { calls++; return route.fulfill({ json: result(records) }); });
  await begin(page);
  await expect(page.locator(".result-title").first()).toHaveText(title(records[0]));
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".search-error, .search-ranking-recovery")).toHaveCount(0);
  expect(calls).toBe(1);
});

test("an empty keyword page never redirects a valid second semantic page back to page one", async ({ page, request }) => {
  const records = await prepare(page, request), offsets: number[] = [];
  await page.route("**/quick?**", route => route.fulfill({ json: { ...result([], Number(new URL(route.request().url()).searchParams.get("offset")) || 0), has_more: false } }));
  await page.route("**/search", route => {
    const offset = route.request().postDataJSON().offset || 0; offsets.push(offset);
    return route.fulfill({ json: result(records, offset) });
  });
  await begin(page); await expect(page.locator(".result-title").first()).toHaveText(title(records[0]));
  await page.getByRole("button", { name: "下一页", exact: true }).click();
  await expect(page.locator(".result-title").first()).toHaveText(title(records[30]));
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.getByRole("spinbutton", { name: "跳转页码", exact: true })).toHaveValue("2");
  expect(offsets).toEqual([0, 30]);
});

test("a failed full search preserves keyword reading and selection until an explicit retry", async ({ page, request }) => {
  const records = await prepare(page, request); let fail = true, calls = 0;
  await page.route("**/quick?**", route => route.fulfill({ json: result(records) }));
  await page.route("**/search", route => {
    calls++;
    return fail ? route.fulfill({ status: 503, json: { detail: "Synthetic ranked read unavailable" } }) : route.fulfill({ json: result(records) });
  });
  await begin(page);
  const recovery = page.locator(".search-ranking-recovery");
  await expect(recovery).toContainText("语义检索未完成，关键词结果仍可使用。");
  await expect(page.locator(".search-error")).toHaveCount(0);
  await expect(page.locator(".result-row")).toHaveCount(30);
  await page.locator(".bookmark-check").first().check();
  await expect(page.locator(".library-selection-count")).toHaveText("已选 1");
  await recovery.locator("summary").press("Enter");
  await expect(recovery).toContainText("Synthetic ranked read unavailable");
  expect(calls).toBe(1);
  fail = false;
  await recovery.getByRole("button", { name: "重试语义检索", exact: true }).press("Enter");
  await expect(recovery).toHaveCount(0);
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".library-selection-count")).toHaveText("已选 1");
  expect(calls).toBe(2);
});

test("both failed reads show a real failure and a late response cannot restore a cleared query", async ({ page, request }) => {
  const records = await prepare(page, request); let fail = true, release!: () => void, arrived!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; }), received = new Promise<void>(resolve => { arrived = resolve; });
  await page.route("**/quick?**", route => fail ? route.fulfill({ status: 503, json: { detail: "Synthetic quick failure" } }) : route.fulfill({ json: result(records) }));
  await page.route("**/search", async route => {
    if (fail) return route.fulfill({ status: 503, json: { detail: "Synthetic ranked failure" } });
    arrived(); await held; return route.fulfill({ json: result([...records].reverse()) });
  });
  try {
    await begin(page);
    await expect(page.locator(".search-error")).toContainText("Synthetic ranked failure");
    await expect(page.locator(".search-ranking-recovery")).toHaveCount(0);
    fail = false;
    await page.locator(".search-error").getByRole("button", { name: "重试", exact: true }).click();
    await received;
    await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill("");
    release();
    await expect(page.locator(".toolbar-location h1")).toHaveText("你的收藏");
    await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
    await expect(page.locator(".result-title").first()).toHaveText(title(records[0]));
    await expect(page.locator(".search-error, .search-ranking-recovery")).toHaveCount(0);
  } finally { release(); }
});

test("localized long search failures retain capsule recovery and can switch to keyword search", async ({ page, request }) => {
  test.setTimeout(120000);
  const records = await prepare(page, request);
  await page.route("**/quick?**", route => route.fulfill({ json: result(records) }));
  await page.route("**/search", route => route.fulfill({ status: 503, json: { detail: "Synthetic model response unavailable: " + "long-error/".repeat(40) } }));
  for (const language of ["zh", "en"] as const) for (const theme of ["light", "dark"] as const) {
    await page.evaluate(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme }).catch(() => {});
    await page.addInitScript(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme });
    await begin(page); const recovery = page.locator(".search-ranking-recovery"); await expect(recovery).toBeVisible();
    await recovery.locator("summary").press("Enter");
    for (const size of [{ width: 1280, height: 850 }, { width: 320, height: 640 }, { width: 683, height: 384 }]) {
      await page.setViewportSize(size); await settleVisualLayout(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(await recovery.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
      const retry = recovery.getByRole("button", { name: language === "zh" ? "重试语义检索" : "Retry semantic search", exact: true });
      await retry.scrollIntoViewIfNeeded(); await expect(retry).toBeInViewport();
      await page.screenshot({ path: `screenshots/collection-review/search-recovery-${language}-${theme}-${size.width}-${size.height}.png`, animations: "disabled" });
    }
  }
  await page.locator(".search-ranking-recovery").getByRole("button", { name: "Use keyword search", exact: true }).press("Space");
  await expect(page.getByRole("combobox", { name: "Search mode", exact: true })).toHaveValue("keyword");
  await expect(page.locator(".search-ranking-recovery")).toHaveCount(0);
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
});
