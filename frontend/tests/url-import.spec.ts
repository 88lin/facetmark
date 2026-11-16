import { expect, test as base, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

type Receipt = { import_id: string; inserted: number; items: { line: number; status: string; bookmark_id?: number }[] };
type Owned = { headers: Record<string, string>; ids: Set<number>; remember: (receipt: Receipt) => void };
const test = base.extend<{ owned: Owned }>({
  owned: async ({ request }, use) => {
    const boot = await request.get("/app/boot");
    expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` }, ids = new Set<number>();
    await use({ headers, ids, remember: receipt => receipt.items.forEach(item => {
      if (item.status === "imported" && item.bookmark_id) ids.add(item.bookmark_id);
    }) });
    for (const id of ids) expect([200, 404]).toContain((await request.delete(`/admin/library/bookmarks/${id}`, { headers })).status());
  },
});

async function open(page: Page, language: "zh" | "en" = "zh") {
  await page.goto("/app");
  await page.getByRole("button", { name: language === "zh" ? "导入书签" : "Import bookmarks", exact: true }).click();
  const panel = page.locator(".url-import");
  await panel.locator("summary").click();
  await expect(panel.getByRole("textbox")).toBeVisible();
  return panel;
}

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await mkdir("screenshots/collection-review", { recursive: true });
});

test("URL preview and keyboard apply use the real API, keep existing content and disable competing imports", async ({ page, request, owned }) => {
  const marker = randomUUID().replaceAll("-", "");
  const existing = await request.post("/admin/library/bookmarks", { headers: owned.headers,
    data: { url: `https://url-import.example/existing-${marker}`, title: "Keep the original title " + marker, folder: "Keep the original folder" } });
  expect(existing.ok()).toBeTruthy();
  const record = await existing.json(); owned.ids.add(record.bookmark_id);
  const panel = await open(page);
  const text = `https://url-import.example/${marker}\t资料检索 ${marker}\nhttps://url-import.example/${marker}?utm_source=duplicate\n${record.url}\tDo not replace\njavascript:alert(1)\nhttps://second.example/${marker}\tSecond synthetic title ${marker}`;
  await panel.getByRole("textbox").fill(text);
  const preview = panel.getByRole("button", { name: "预览网址", exact: true });
  await preview.focus(); await preview.press("Enter");
  await expect(panel.locator(".url-import-preview")).toContainText("将添加 2 条；已存在 1 条；本批重复 1 条；无效 1 条");
  expect((await request.get(`/bookmark/${record.bookmark_id}`, { headers: owned.headers })).ok()).toBeTruthy();
  let submissions = 0, release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/admin/import/urls", async route => {
    submissions++; await gate;
    const response = await route.fetch(); owned.remember(await response.json());
    await route.fulfill({ response });
  });
  const apply = panel.getByRole("button", { name: "导入 2 条新网址", exact: true });
  await apply.focus(); await apply.press("Space");
  await expect.poll(() => submissions).toBe(1);
  await expect(panel.locator(".folder-picker-trigger")).toBeDisabled();
  await expect(page.getByRole("button", { name: "选择文件", exact: true })).toBeDisabled();
  await page.keyboard.press("Space"); expect(submissions).toBe(1);
  release();
  await expect(panel.locator(".url-import-result")).toContainText("已添加 2 条网址");
  const retained = await request.get(`/bookmark/${record.bookmark_id}`, { headers: owned.headers });
  expect((await retained.json()).title).toBe("Keep the original title " + marker);
  await panel.getByRole("button", { name: "查看已导入的收藏", exact: true }).click();
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill(marker);
  await expect(page.locator(".result-row")).toHaveCount(3);
});

test("retry after a lost successful response reuses the original receipt", async ({ page, owned, request }) => {
  const panel = await open(page), marker = randomUUID();
  await panel.getByRole("textbox").fill(`https://url-import.example/lost-${marker}`);
  await panel.getByRole("button", { name: "预览网址", exact: true }).click();
  await expect(panel.locator(".url-import-preview")).toBeVisible();
  const requests: string[] = [];
  let first: Receipt | undefined;
  await page.route("**/admin/import/urls", async route => {
    requests.push(route.request().postDataJSON().request_id);
    const response = await route.fetch(), result = await response.json() as Receipt;
    owned.remember(result);
    if (requests.length === 1) { first = result; await route.abort("failed"); }
    else { expect(result).toEqual(first); await route.fulfill({ response }); }
  });
  await panel.getByRole("button", { name: "导入 1 条新网址", exact: true }).click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await panel.getByRole("button", { name: "重试导入", exact: true }).click();
  await expect(panel.locator(".url-import-result")).toContainText("已添加 1 条网址");
  expect(requests).toHaveLength(2); expect(requests[0]).toBe(requests[1]);
  const history = await request.get(`/admin/import/history/${first!.import_id}`, { headers: owned.headers });
  expect((await history.json()).result).toEqual(first);
});

test("a real library change invalidates preview while retaining the pasted draft", async ({ page, request, owned }) => {
  const panel = await open(page), marker = randomUUID();
  const text = `https://url-import.example/stale-${marker}`;
  await panel.getByRole("textbox").fill(text);
  await panel.getByRole("button", { name: "预览网址", exact: true }).click();
  await expect(panel.locator(".url-import-preview")).toBeVisible();
  const change = await request.post("/admin/library/bookmarks", { headers: owned.headers,
    data: { url: `https://url-import.example/change-${marker}` } });
  expect(change.ok()).toBeTruthy(); owned.ids.add((await change.json()).bookmark_id);
  await panel.getByRole("button", { name: "导入 1 条新网址", exact: true }).click();
  await expect(panel.getByRole("alert")).toContainText("收藏库已变化，请重新预览");
  await expect(panel.getByRole("textbox")).toHaveValue(text);
  await expect(panel.locator(".url-import-preview")).toHaveCount(0);
  await panel.getByRole("button", { name: "预览网址", exact: true }).click();
  await expect(panel.locator(".url-import-preview")).toBeVisible();
  const response = page.waitForResponse(value => new URL(value.url()).pathname === "/admin/import/urls");
  await panel.getByRole("button", { name: "导入 1 条新网址", exact: true }).click();
  owned.remember(await (await response).json());
  await expect(panel.locator(".url-import-result")).toBeVisible();
});

test("successful URL import with a failed collection refresh offers reload without reimporting", async ({ page, owned }) => {
  const panel = await open(page);
  await panel.getByRole("textbox").fill("https://url-import.example/refresh-" + randomUUID());
  await panel.getByRole("button", { name: "预览网址", exact: true }).click();
  await expect(panel.locator(".url-import-preview")).toBeVisible();
  let failRefresh = false, submissions = 0;
  await page.route("**/admin/setup-status", route => failRefresh
    ? route.fulfill({ status: 503, json: { detail: "Synthetic refresh failure" } }) : route.continue());
  await page.route("**/admin/import/urls", async route => {
    submissions++;
    const response = await route.fetch(); owned.remember(await response.json()); failRefresh = true;
    await route.fulfill({ response });
  });
  await panel.getByRole("button", { name: "导入 1 条新网址", exact: true }).click();
  await expect(panel.locator(".url-import-result")).toContainText("已添加 1 条网址");
  await expect(panel.getByRole("alert")).toContainText("网址已导入，但收藏列表未能刷新");
  await expect(panel.getByRole("button", { name: "查看已导入的收藏", exact: true })).toBeDisabled();
  failRefresh = false;
  await panel.getByRole("button", { name: "重新读取收藏", exact: true }).click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await expect(panel.getByRole("button", { name: "查看已导入的收藏", exact: true })).toBeEnabled();
  expect(submissions).toBe(1);
});

test("completed site import retains its result and retries only collection refresh", async ({ page }) => {
  await open(page);
  let failRefresh = true;
  await page.route("**/admin/setup-status", route => failRefresh
    ? route.fulfill({ status: 503, json: { detail: "Synthetic refresh failure" } }) : route.continue());
  await page.route("**/admin/crawl", route => route.fulfill({ json: {
    id: "synthetic_site_complete", state: "done", error: "", report: { pages_attempted: 1, pages_fetched: 1,
      inserted: 1, already_known: 0, bodies_stored: 1, errors: 0, skipped: 0, robots_denied: 0,
      privacy_skipped: 0, off_domain_skipped: 0, notes: [] },
  } }));
  const panel = page.locator(".site-import");
  await panel.locator("summary").click();
  await expect(panel.getByRole("alert")).toContainText("网站导入结果已保存，但收藏列表未能刷新");
  await expect(panel.getByRole("button", { name: "查看已导入的收藏", exact: true })).toBeDisabled();
  failRefresh = false;
  await panel.getByRole("button", { name: "重新读取收藏", exact: true }).click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await expect(panel.getByRole("button", { name: "查看已导入的收藏", exact: true })).toBeEnabled();
});

test("history detail failure and interrupted loading recover without losing the list", async ({ page }) => {
  const item = { id: "synthetic_history_0001", source: "urls", label: "Pasted URLs", created_at: 1700000000,
    state: "partial", error: "", result: { inserted: 1, skipped: 1 } };
  await page.route("**/admin/import/history?*", route => route.fulfill({ json: { items: [item], offset: 0, limit: 20, has_more: false } }));
  let calls = 0, release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/admin/import/history/synthetic_history_0001", async route => {
    calls++;
    if (calls === 1) return route.fulfill({ status: 503, json: { detail: "Synthetic detail read failure" } });
    if (calls === 2) await gate;
    await route.fulfill({ json: { ...item, result: { ...item.result,
      items: [{ line: 1, url: "https://synthetic.example/", title: "Synthetic saved URL", status: "imported" }] } } }).catch(() => {});
  });
  await open(page);
  const history = page.locator(".import-history"), summary = history.locator("summary");
  await summary.click();
  await history.getByRole("button", { name: "查看逐项结果", exact: true }).click();
  await expect(history.getByRole("alert")).toContainText("Synthetic detail read failure");
  await history.getByRole("button", { name: "重试读取逐项结果", exact: true }).click();
  await expect.poll(() => calls).toBe(2);
  await summary.click();
  await expect(history).toHaveAttribute("aria-busy", "false"); release();
  await summary.click();
  const detail = history.getByRole("button", { name: "查看逐项结果", exact: true });
  await expect(detail).toBeEnabled(); await detail.click();
  await expect(history.locator(".url-import-items")).toContainText("Synthetic saved URL");
  expect(calls).toBe(3);
  await history.getByRole("button", { name: "收起逐项结果", exact: true }).click();
  await expect(history.locator(".url-import-items")).toHaveCount(0);
  await expect(history.locator(".import-history-list > li")).toHaveCount(1);
});

for (const [language, theme, width, height] of [
  ["zh", "light", 1280, 850], ["en", "dark", 1024, 600], ["zh", "dark", 390, 700], ["en", "light", 320, 640],
] as const) test(`URL import long text, keyboard focus and reduced motion fit ${language} ${theme} ${width}`, async ({ page }) => {
  await page.addInitScript(([lang, color]) => { localStorage.setItem("fm-language", lang); localStorage.setItem("fm-theme", color); }, [language, theme]);
  await page.setViewportSize({ width, height }); await page.emulateMedia({ reducedMotion: "reduce" });
  const items = [
    { line: 1, url: "https://synthetic.example/" + "long-address-".repeat(35), title: "用于检索的长标题与资料说明 Long bookmark title ".repeat(8), status: "new" },
    { line: 2, url: "https://synthetic.example/existing", title: "已有收藏 Existing bookmark", status: "existing" },
    { line: 3, url: "javascript:alert(1)", title: "", status: "invalid" },
  ];
  await page.route("**/admin/import/urls/preview", route => route.fulfill({ json: {
    revision: "synthetic-revision", items, counts: { new: 1, existing: 1, duplicate: 0, invalid: 1 },
  } }));
  const panel = await open(page, language);
  await panel.getByRole("textbox").fill("https://synthetic.example/long-address");
  await panel.getByRole("button", { name: language === "zh" ? "预览网址" : "Preview URLs", exact: true }).click();
  await expect(panel.locator(".url-import-preview")).toBeVisible();
  await panel.locator(".url-import-preview").scrollIntoViewIfNeeded(); await settleVisualLayout(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await panel.locator('.url-import-items [data-status="invalid"] a').count()).toBe(0);
  await page.screenshot({ path: `screenshots/collection-review/url-import-${language}-${theme}-${width}.png`, animations: "disabled" });
});
