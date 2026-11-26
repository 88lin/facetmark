import { expect, test as base, type Locator, type Page } from "@playwright/test";
import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile } from "node:fs/promises";
import type { Bookmark } from "../src/api";
import { settleVisualLayout } from "./visual-layout";

type Owned = { headers: Record<string, string>; remember: (id: number) => void;
  create: (values?: Partial<Bookmark>) => Promise<Bookmark>; read: (id: number) => Promise<Bookmark>;
  edit: (id: number, values: Partial<Bookmark>) => Promise<Bookmark> };
const test = base.extend<{ owned: Owned }>({
  owned: async ({ request }, use) => {
    const boot = await request.get("/app/boot"); expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` }, ids = new Set<number>();
    await use({ headers, remember: id => { ids.add(id); },
      create: async (values = {}) => {
        const response = await request.post("/admin/library/bookmarks", { headers,
          data: { url: `https://library-recovery.example/${randomUUID()}`, title: "Synthetic recovery page", ...values } });
        expect(response.ok()).toBeTruthy();
        const value = await response.json() as Bookmark; ids.add(value.bookmark_id); return value;
      },
      read: async id => {
        const response = await request.get(`/bookmark/${id}?body=true`, { headers });
        expect(response.ok()).toBeTruthy(); return response.json();
      },
      edit: async (id, values) => {
        const response = await request.patch(`/admin/library/bookmarks/${id}`, { headers, data: values });
        expect(response.ok()).toBeTruthy(); return response.json();
      },
    });
    for (const id of ids) {
      const response = await request.delete(`/admin/library/bookmarks/${id}`, { headers });
      expect([200, 404]).toContain(response.status());
    }
  },
});

async function recovery(page: Page, owned: Owned) {
  const control = { writes: [] as { path: string; method: string; body: Record<string, unknown> }[],
    created: [] as number[], receiptReads: 0, loseNext: false, failReceipts: false, rejectNext: 0 };
  await page.route(/\/admin\/library\/operations\/[^/?]+$/, route => {
    control.receiptReads++;
    return control.failReceipts ? route.fulfill({ status: 503, json: { detail: "Synthetic receipt read unavailable" } }) : route.continue();
  });
  await page.route(/\/admin\/library\/(?:bookmarks(?:\/\d+)?|bulk|taxonomy)(?:\?|$)/, async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    if (!["POST", "PATCH", "DELETE"].includes(request.method())) return route.continue();
    const body = request.postDataJSON() || {};
    control.writes.push({ path, method: request.method(), body });
    if (control.rejectNext) {
      const status = control.rejectNext; control.rejectNext = 0;
      return route.fulfill({ status, json: { detail: "Synthetic collection write rejected" } });
    }
    const lost = control.loseNext; control.loseNext = false;
    const response = await route.fetch();
    if (response.ok() && path === "/admin/library/bookmarks" && request.method() === "POST") {
      const value = await response.json() as Bookmark;
      owned.remember(value.bookmark_id); control.created.push(value.bookmark_id);
    }
    return lost ? route.abort("failed") : route.fulfill({ response });
  });
  return control;
}

const marker = () => "recovery" + randomUUID().replaceAll("-", "");
const row = (page: Page, id: number) => page.locator(`.result-row[data-bookmark-id="${id}"]`);
async function search(page: Page, query: string, count: number) {
  const received = page.waitForResponse(response => {
    const url = new URL(response.url()); return url.pathname === "/bookmarks" && url.searchParams.get("q") === query;
  });
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill(query);
  expect((await received).ok()).toBeTruthy();
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".result-row")).toHaveCount(count);
  if (count) await expect(page.locator(".result-row").first()).toContainText(query);
}
async function openCreate(page: Page, url: string, title: string) {
  await page.getByRole("button", { name: "新增收藏", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "新增收藏", exact: true });
  await dialog.getByLabel("收藏网址", { exact: true }).fill(url);
  await dialog.getByLabel("收藏标题", { exact: true }).fill(title);
  return dialog;
}
async function openEdit(page: Page, record: Bookmark, query: string) {
  await search(page, query, 1);
  await row(page, record.bookmark_id).locator(".bookmark-preview").click();
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  return page.getByRole("dialog", { name: "编辑收藏", exact: true });
}
async function reopenRecovery(page: Page, language = "zh") {
  await page.reload(); await expect(page.locator(".library-recovery-banner")).toBeVisible();
  await page.locator(".library-recovery-banner").getByRole("button", { name: language === "zh" ? "查看操作" : "Review operation", exact: true }).click();
  return page.getByRole("dialog", { name: language === "zh" ? "恢复收藏操作" : "Recover collection operation", exact: true });
}
async function openExport(page: Page) {
  await page.locator(".library-manage > summary").click();
  await page.getByRole("button", { name: "导出", exact: true }).click();
  return page.getByRole("dialog", { name: "导出收藏", exact: true });
}
async function download(page: Page, dialog: Locator) {
  const received = page.waitForResponse(response => new URL(response.url()).pathname === "/admin/library/export" && response.request().method() === "POST");
  const downloaded = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "下载导出文件", exact: true }).click();
  const [response, file] = await Promise.all([received, downloaded]);
  expect(response.ok()).toBeTruthy(); expect(await file.failure()).toBeNull();
  const path = await file.path(); expect(path).not.toBeNull();
  await expect(dialog).toHaveCount(0);
  return { body: response.request().postDataJSON(), content: JSON.parse(await readFile(path!, "utf8")) };
}

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});
test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); });

test("a lost create response preserves the original content and refresh confirms it without another write", async ({ page, owned }) => {
  const control = await recovery(page, owned), token = marker();
  control.loseNext = true; control.failReceipts = true;
  await page.goto("/app");
  const original = { url: `https://library-recovery.example/${token}`, title: `${token} 原来保存的阅读标题` };
  const create = await openCreate(page, original.url, original.title);
  await create.getByRole("button", { name: "保存", exact: true }).evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click(); });
  await expect(create.locator(".library-write-recovery")).toBeVisible();
  await expect(create.getByLabel("收藏标题", { exact: true })).toHaveValue(original.title);
  expect(control.writes).toHaveLength(1); expect(control.created).toHaveLength(1);
  const dialog = await reopenRecovery(page);
  await expect(dialog.locator(".library-operation-summary")).toContainText(original.title);
  expect(control.writes).toHaveLength(1);
  control.failReceipts = false;
  const read = dialog.getByRole("button", { name: "读取保存结果", exact: true });
  await read.focus(); await read.press("Enter");
  await expect(dialog).toHaveCount(0); await expect(page.locator(".library-recovery-banner")).toHaveCount(0);
  expect(control.writes).toHaveLength(1);
  expect(await owned.read(control.created[0])).toMatchObject(original);
  await search(page, token, 1);
});

test("retrying a lost edit receipt preserves a later edit made in another window", async ({ page, owned }) => {
  const token = marker(), record = await owned.create({ title: `${token} Original`, folder: "Keep this folder", tags: ["Keep this tag"] });
  const control = await recovery(page, owned); control.loseNext = true; control.failReceipts = true;
  await page.goto("/app"); const edit = await openEdit(page, record, token);
  await edit.getByLabel("收藏标题", { exact: true }).fill(`${token} First saved edit`);
  await edit.getByRole("button", { name: "保存", exact: true }).click();
  await expect(edit.locator(".library-write-recovery")).toBeVisible();
  await owned.edit(record.bookmark_id, { title: `${token} Later edit from another window` });
  const dialog = await reopenRecovery(page); control.failReceipts = false;
  await dialog.getByRole("button", { name: "重试同一次操作", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(control.writes).toHaveLength(2); expect(control.writes[1]).toEqual(control.writes[0]);
  expect(await owned.read(record.bookmark_id)).toMatchObject({ title: `${token} Later edit from another window`, folder: record.folder, tags: record.tags });
});

test("a saved change with a failed collection refresh remains confirmed through reload and only rereads", async ({ page, owned }) => {
  const control = await recovery(page, owned), token = marker(); let failFacets = false;
  await page.route("**/bookmarks/facets", route => failFacets ? route.fulfill({ status: 503, json: { detail: "Synthetic facets read unavailable" } }) : route.continue());
  await page.goto("/app"); const dialog = await openCreate(page, `https://library-recovery.example/${token}`, `${token} 已保存的内容`);
  failFacets = true;
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  await expect(dialog.locator(".library-write-recovery")).toContainText("这次操作已经保存");
  await expect(dialog.getByRole("button", { name: "重试同一次操作", exact: true })).toHaveCount(0);
  expect(control.writes).toHaveLength(1);
  const reopened = await reopenRecovery(page);
  await expect(reopened.locator(".library-write-recovery")).toContainText("这次操作已经保存");
  await page.setViewportSize({ width: 320, height: 640 }); await settleVisualLayout(page);
  await expect(reopened.locator(".library-write-recovery")).toBeInViewport({ ratio: 1 });
  failFacets = false;
  await reopened.getByRole("button", { name: "重新读取收藏", exact: true }).click();
  await expect(reopened).toHaveCount(0);
  expect(control.writes).toHaveLength(1); expect((await owned.read(control.created[0])).title).toBe(`${token} 已保存的内容`);
});

test("retrying a lost delete confirms the old selection and retains a newly created bookmark", async ({ page, owned, request }) => {
  const token = marker(), original = await owned.create({ title: `${token} Delete this page` });
  const control = await recovery(page, owned); control.loseNext = true; control.failReceipts = true;
  await page.goto("/app"); await search(page, token, 1);
  await page.locator(".library-manage > summary").click();
  await page.getByRole("button", { name: "批量管理", exact: true }).click();
  await page.getByRole("button", { name: "选择本页", exact: true }).click();
  await page.getByRole("button", { name: "批量操作", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "批量管理", exact: true });
  await dialog.getByRole("combobox", { name: "批量操作类型", exact: true }).selectOption("delete");
  await dialog.getByRole("checkbox", { name: "我确认删除这些收藏", exact: true }).check();
  await dialog.getByRole("button", { name: "确认删除", exact: true }).click();
  await expect(dialog.locator(".library-write-recovery")).toBeVisible();
  const later = await owned.create({ title: `${token} Keep the new page` }); expect(later.bookmark_id).toBeGreaterThan(original.bookmark_id);
  const reopened = await reopenRecovery(page); control.failReceipts = false;
  await reopened.getByRole("button", { name: "重试同一次操作", exact: true }).click();
  await expect(reopened).toHaveCount(0); expect(control.writes).toHaveLength(2);
  expect(control.writes[1]).toEqual(control.writes[0]); expect(control.writes[0].body.ids).toEqual([original.bookmark_id]);
  expect((await request.get(`/bookmark/${original.bookmark_id}`, { headers: owned.headers })).status()).toBe(404);
  expect((await owned.read(later.bookmark_id)).title).toBe(later.title);
});

for (const kind of ["create", "edit"] as const) test(`a rejected recovered ${kind} returns to its original editable content and uses a new explicit save`, async ({ page, owned }) => {
  const token = marker(), originalUrl = `https://library-recovery.example/${token}`;
  const record = kind === "edit" ? await owned.create({ url: originalUrl, title: `${token} Before editing`, folder: "Original folder", tags: ["Original tag"] }) : null;
  const control = await recovery(page, owned); control.rejectNext = 503; control.failReceipts = true;
  await page.goto("/app");
  const originalTitle = `${token} Unconfirmed draft`;
  const first = record ? await openEdit(page, record, token) : await openCreate(page, originalUrl, originalTitle);
  if (record) await first.getByLabel("收藏标题", { exact: true }).fill(originalTitle);
  await first.getByRole("button", { name: "保存", exact: true }).click();
  await expect(first.locator(".library-write-recovery")).toBeVisible();
  const reopened = await reopenRecovery(page); control.rejectNext = 409; control.failReceipts = false;
  await reopened.getByRole("button", { name: "重试同一次操作", exact: true }).click();
  await expect(reopened.locator(".library-write-recovery")).toContainText("这次操作未保存");
  await page.setViewportSize({ width: 320, height: 640 }); await settleVisualLayout(page);
  await expect(reopened.locator(".library-write-recovery")).toBeInViewport({ ratio: 1 });
  await reopened.getByRole("button", { name: "修改原操作", exact: true }).click();
  const editable = page.getByRole("dialog", { name: record ? "编辑收藏" : "新增收藏", exact: true });
  await expect(editable.getByLabel("收藏标题", { exact: true })).toHaveValue(originalTitle);
  await expect(editable.getByLabel("收藏网址", { exact: true })).toHaveValue(originalUrl);
  await expect(editable.getByLabel("收藏标题", { exact: true })).toBeEnabled();
  const revised = `${token} Explicitly revised`;
  await editable.getByLabel("收藏标题", { exact: true }).fill(revised);
  await editable.getByRole("button", { name: "保存", exact: true }).click();
  await expect(editable).toHaveCount(0); expect(control.writes).toHaveLength(3);
  expect(control.writes[1].body.request_id).toBe(control.writes[0].body.request_id);
  expect(control.writes[2].body.request_id).not.toBe(control.writes[0].body.request_id);
  const saved = await owned.read(record ? record.bookmark_id : control.created[0]);
  expect(saved).toMatchObject({ url: originalUrl, title: revised });
  if (record) expect(saved).toMatchObject({ folder: record.folder, tags: record.tags });
});

test("duplicate URLs open the existing bookmark without overwriting its saved content", async ({ page, owned }) => {
  const token = marker(), original = await owned.create({ title: `${token} Saved title`, tags: ["Saved tag"] });
  const control = await recovery(page, owned);
  await page.goto("/app"); const dialog = await openCreate(page, original.url, `${token} Unsaved replacement`);
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  const existing = dialog.getByRole("button", { name: "打开已有收藏", exact: true });
  await expect(existing).toBeEnabled(); await existing.focus(); await existing.press("Enter");
  await expect(dialog).toHaveCount(0); await expect(page.locator(".preview-title h1")).toHaveText(original.title);
  expect(await owned.read(original.bookmark_id)).toMatchObject({ title: original.title, tags: original.tags });
  expect(control.writes).toHaveLength(1); expect(control.created).toHaveLength(0);
});

test("a rejected edit of a removed page retains the full draft for an explicit new bookmark", async ({ page, owned, request }) => {
  const token = marker(), original = await owned.create({ title: `${token} Original`, folder: "Retained folder", tags: ["Retained tag"] });
  const control = await recovery(page, owned); control.rejectNext = 503; control.failReceipts = true;
  await page.goto("/app"); const edit = await openEdit(page, original, token);
  const title = `${token} Retained editing draft`;
  await edit.getByLabel("收藏标题", { exact: true }).fill(title);
  await edit.getByRole("button", { name: "保存", exact: true }).click(); await expect(edit.locator(".library-write-recovery")).toBeVisible();
  expect((await request.delete(`/admin/library/bookmarks/${original.bookmark_id}`, { headers: owned.headers })).ok()).toBeTruthy();
  const recovered = await reopenRecovery(page); control.rejectNext = 404; control.failReceipts = false;
  await recovered.getByRole("button", { name: "重试同一次操作", exact: true }).click();
  await recovered.getByRole("button", { name: "修改原操作", exact: true }).click();
  const create = page.getByRole("dialog", { name: "新增收藏", exact: true });
  await expect(create.getByLabel("收藏网址", { exact: true })).toHaveValue(original.url);
  await expect(create.getByLabel("收藏标题", { exact: true })).toHaveValue(title);
  await expect(create.locator(".folder-picker-trigger")).toContainText(original.folder);
  await expect(create.getByRole("button", { name: "移除标签 Retained tag", exact: true })).toBeVisible();
  await expect(create.locator(".notice").filter({ hasText: "原来的收藏已移除" })).toBeVisible();
  expect(control.writes).toHaveLength(2); expect(control.created).toHaveLength(0);
  await create.getByRole("button", { name: "保存", exact: true }).click(); await expect(create).toHaveCount(0);
  const replacement = await owned.read(control.created[0]); expect(replacement.bookmark_id).toBeGreaterThan(original.bookmark_id);
  expect(replacement).toMatchObject({ url: original.url, title, folder: original.folder, tags: original.tags });
  expect(control.writes).toHaveLength(3);
});

test("keyword selection exports every matching pending page across pagination and honors exclusions", async ({ page, owned, request }) => {
  test.setTimeout(90_000);
  const token = marker(), pending: Bookmark[] = [];
  for (let index = 0; index < 35; index++) pending.push(await owned.create({ title: `${token} Pending ${index}` }));
  const doneUrl = `https://library-recovery.example/${token}/summarized`;
  const doneTitle = `${token} Already summarized`;
  const sourceHash = "t:" + createHash("sha256").update(`${doneTitle}\0${doneUrl}`).digest("hex");
  const imported = await request.post("/admin/import", { headers: { ...owned.headers, "Content-Type": "application/json" },
    data: JSON.stringify({ facetmark: { version: 2, full: true, restorable: true }, bookmarks: [{ url: doneUrl,
      title: doneTitle, folder: "", tags: [], date_added: 1792886400,
      derived: { summary: "Saved synthetic summary", basis: "title", model: "synthetic", source_hash: sourceHash } }] }) });
  expect(imported.ok()).toBeTruthy();
  const importResult = await imported.json();
  const done = await request.get(`/bookmarks?q=${token}&limit=100`, { headers: owned.headers }); expect(done.ok()).toBeTruthy();
  const doneRow = (await done.json()).items.find((item: Bookmark) => item.url === doneUrl) as Bookmark; expect(doneRow).toBeTruthy(); owned.remember(doneRow.bookmark_id);
  expect(importResult.restored_summaries).toBe(1);
  expect(importResult.warnings).toEqual([]);
  await page.goto("/app"); await search(page, token, 30);
  const changed = page.waitForResponse(response => { const url = new URL(response.url()); return url.pathname === "/bookmarks" && url.searchParams.get("q") === token && url.searchParams.get("status") === "pending"; });
  await page.locator('.collection-status button[data-status="pending"]').click();
  expect((await changed).ok()).toBeTruthy(); await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await page.getByRole("checkbox", { name: "全选当前结果", exact: true }).check();
  await expect(page.locator(".library-selection-count")).toHaveText("已选 35");
  const excluded = Number(await page.locator(".result-row").first().getAttribute("data-bookmark-id"));
  await row(page, excluded).getByRole("checkbox").uncheck();
  await expect(page.locator(".library-selection-count")).toHaveText("已选 34");
  const dialog = await openExport(page); await expect(dialog.getByRole("combobox", { name: "导出范围", exact: true })).toHaveValue("selected");
  const exported = await download(page, dialog);
  expect(exported.body).toEqual({ format: "json", scope: { q: token, status: "pending", exclude_ids: [excluded] } });
  expect(exported.content.bookmarks.map((item: Bookmark) => item.url).sort()).toEqual(pending.filter(item => item.bookmark_id !== excluded).map(item => item.url).sort());
});

test("page export keeps the page shown when opened even after a background collection refresh", async ({ page, owned }) => {
  test.setTimeout(90_000);
  const token = marker(); for (let index = 0; index < 31; index++) await owned.create({ title: `${token} Original ${index}` });
  await page.goto("/app"); await search(page, token, 30);
  const originalIds = await page.locator(".result-row").evaluateAll(elements => elements.map(element => Number(element.getAttribute("data-bookmark-id"))));
  const dialog = await openExport(page); await dialog.getByRole("combobox", { name: "导出范围", exact: true }).selectOption("page");
  const later = await owned.create({ title: `${token} Later page` });
  await expect(row(page, later.bookmark_id)).toHaveCount(1);
  const updatedIds = await page.locator(".result-row").evaluateAll(elements => elements.map(element => Number(element.getAttribute("data-bookmark-id"))));
  expect(updatedIds).not.toEqual(originalIds);
  const exported = await download(page, dialog); expect(exported.body).toEqual({ format: "json", ids: originalIds });
  expect(exported.content.bookmarks).toHaveLength(30); expect(exported.content.bookmarks.some((item: Bookmark) => item.url === later.url)).toBe(false);
  const originals = await Promise.all(originalIds.map(id => owned.read(id)));
  expect(exported.content.bookmarks.map((item: Bookmark) => item.url).sort()).toEqual(originals.map(item => item.url).sort());
});

test("long recovered content stays complete while keyboard controls remain reachable in both themes and languages", async ({ page, owned }) => {
  test.setTimeout(120_000);
  const control = await recovery(page, owned), token = marker(); control.loseNext = true; control.failReceipts = true;
  const title = (`${token} ` + "保存完整的阅读线索和原来的修改内容。 Keep the full original draft and saved reading context. ".repeat(20)).trim();
  const url = `https://library-recovery.example/${token}?note=` + "long-original-reading-context-".repeat(30);
  await page.goto("/app"); const create = await openCreate(page, url, title);
  await create.getByRole("button", { name: "保存", exact: true }).click(); await expect(create.locator(".library-write-recovery")).toBeVisible();
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const language of ["zh", "en"] as const) for (const theme of ["light", "dark"] as const) {
    await page.evaluate(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme });
    const dialog = await reopenRecovery(page, language);
    const fullTitleName = language === "zh" ? "查看完整标题" : "View full Title";
    const summary = dialog.locator(`.library-operation-detail > summary[aria-label="${fullTitleName}"]`);
    const detail = summary.locator("..");
    await expect(summary).toHaveCount(1);
    await summary.focus(); await summary.press("Enter"); await expect(detail).toHaveAttribute("open", "");
    expect(await detail.locator(":scope > div").textContent()).toBe(title);
    for (const size of [{ width: 1280, height: 850 }, { width: 390, height: 844 }, { width: 320, height: 640 }, { width: 683, height: 384 }]) {
      await page.setViewportSize(size); await settleVisualLayout(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const bounds = await dialog.evaluate(element => {
        const body = element.querySelector(".library-dialog-body")!, footer = element.querySelector(".library-dialog-footer")!;
        const bodyBounds = body.getBoundingClientRect(), footerBounds = footer.getBoundingClientRect();
        return { bodyHeight: bodyBounds.height, bodyBottom: bodyBounds.bottom, footerTop: footerBounds.top,
          footerBottom: footerBounds.bottom, viewport: innerHeight, scrolls: body.scrollHeight > body.clientHeight,
          horizontal: element.scrollWidth > element.clientWidth,
          buttons: [...footer.querySelectorAll("button")].map(button => ({ height: button.getBoundingClientRect().height, bottom: button.getBoundingClientRect().bottom })) };
      });
      expect(bounds.bodyHeight).toBeGreaterThan(size.width === 320 ? 136 : 24);
      expect(bounds.bodyBottom).toBeLessThanOrEqual(bounds.footerTop);
      const state = dialog.locator(".library-write-recovery");
      await expect(state).toBeInViewport({ ratio: 1 });
      await expect(dialog).toHaveAttribute("aria-describedby", (await state.getAttribute("id"))!);
      expect(await state.evaluate(element => Boolean(element.closest(".library-dialog-body")))).toBe(false);
      const stateBox = (await state.boundingBox())!;
      expect(stateBox.y + stateBox.height).toBeLessThanOrEqual((await dialog.locator(".library-dialog-body").boundingBox())!.y);
      expect(bounds.footerBottom).toBeLessThanOrEqual(bounds.viewport); expect(bounds.horizontal).toBe(false); expect(bounds.scrolls).toBe(true);
      for (const button of bounds.buttons) { expect(button.height).toBeGreaterThanOrEqual(44); expect(button.bottom).toBeLessThanOrEqual(bounds.viewport); }
      await page.screenshot({ path: `screenshots/collection-review/library-recovery-${language}-${theme}-${size.width}-${size.height}.png`, animations: "disabled" });
    }
    const read = dialog.getByRole("button", { name: language === "zh" ? "读取保存结果" : "Read saved result", exact: true });
    const previousReads = control.receiptReads;
    await read.focus(); await read.press("Space"); await expect.poll(() => control.receiptReads).toBe(previousReads + 1); await expect(read).toBeEnabled();
    expect(control.writes).toHaveLength(1);
    await dialog.getByRole("button", { name: language === "zh" ? "稍后处理" : "Continue later", exact: true }).click(); await expect(dialog).toHaveCount(0);
  }
  const dialog = await reopenRecovery(page, "en"); control.failReceipts = false;
  await dialog.getByRole("button", { name: "Read saved result", exact: true }).click(); await expect(dialog).toHaveCount(0);
  expect(control.writes).toHaveLength(1); expect(await owned.read(control.created[0])).toMatchObject({ title, url });
});
