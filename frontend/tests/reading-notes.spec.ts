import { expect, test as base, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import type { Bookmark } from "../src/api";
import { settleVisualLayout } from "./visual-layout";

type Owned = { headers: Record<string, string>; create: () => Promise<Bookmark>; read: (id: number) => Promise<Bookmark> };
const test = base.extend<{ owned: Owned }>({
  owned: async ({ request }, use) => {
    const boot = await request.get("/app/boot"); expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` }, ids = new Set<number>();
    await use({ headers, create: async () => {
      const marker = "notepage" + randomUUID().replaceAll("-", "");
      const response = await request.post("/admin/library/bookmarks", { headers,
        data: { url: `https://reading-notes.example/${marker}`, title: marker } });
      expect(response.ok()).toBeTruthy(); const record = await response.json() as Bookmark; ids.add(record.bookmark_id); return record;
    }, read: async id => {
      const response = await request.get(`/bookmark/${id}?body=true`, { headers }); expect(response.ok()).toBeTruthy(); return response.json();
    } });
    for (const id of ids) {
      const response = await request.delete(`/admin/library/bookmarks/${id}`, { headers }); expect([200, 404]).toContain(response.status());
    }
  },
});
test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); });

const notes = (page: Page) => page.getByRole("region", { name: /^(我的笔记|My note)$/ });
const input = (page: Page) => notes(page).getByRole("textbox", { name: /^(个人阅读笔记|Personal reading note)$/ });
const text = "  记下保存这篇文章的原因。\n\n  A personal note, with exact spacing.\n  ";
async function open(page: Page, record: Bookmark, arrive = true) {
  if (arrive) await page.goto("/app");
  await page.getByRole("textbox", { name: /^(搜索书签|Search bookmarks)$/, exact: true }).fill(record.title);
  const row = page.locator(`.result-row[data-bookmark-id="${record.bookmark_id}"]`); await expect(row).toBeVisible();
  if (!await notes(page).isVisible() || await notes(page).getAttribute("data-bookmark-id") !== String(record.bookmark_id)) await row.locator(".bookmark-preview").click();
  await expect(notes(page)).toBeVisible();
}
async function edit(page: Page) {
  if (!await input(page).count()) await notes(page).getByRole("button", { name: /^(写笔记|编辑笔记|继续编辑笔记|Write a note|Edit note|Continue note draft)$/ }).click();
  await expect(input(page)).toBeEditable();
}
async function intercept(page: Page) {
  const control = { writes: [] as Record<string, unknown>[], lose: false, corrupt: false, reject: false, failReads: false };
  await page.route(/\/admin\/library\/bookmarks\/\d+\/note$/, async route => {
    if (route.request().method() !== "PATCH") return route.continue();
    control.writes.push(route.request().postDataJSON());
    if (control.reject) { control.reject = false; return route.abort("failed"); }
    const lose = control.lose, corrupt = control.corrupt; control.lose = false; control.corrupt = false;
    const response = await route.fetch();
    if (lose) return route.abort("failed");
    if (corrupt) return route.fulfill({ status: 200, json: {} });
    return route.fulfill({ response });
  });
  await page.route(/\/admin\/library\/operations\/[^/?]+$/, route => control.failReads
    ? route.fulfill({ status: 503, json: { detail: "Synthetic note receipt unavailable" } }) : route.continue());
  return control;
}

test("native save preserves rapid multiline input, has one receipt and is searchable", async ({ page, owned }) => {
  const record = await owned.create(), control = await intercept(page);
  await open(page, record); await edit(page); await input(page).fill(text);
  await notes(page).locator("form").evaluate(form => { (form as HTMLFormElement).requestSubmit(); (form as HTMLFormElement).requestSubmit(); });
  await expect(input(page)).toHaveCount(0); expect(control.writes).toHaveLength(1);
  expect(control.writes[0]).toMatchObject({ note: text, base_revision: 0 });
  expect((await owned.read(record.bookmark_id)).note).toBe(text);
  const summary = notes(page).locator(".reader-note-saved > summary"); await summary.press("Enter");
  expect(await notes(page).locator(".reader-note-saved .reader-note-text").textContent()).toBe(text);
  await page.getByRole("button", { name: "返回收藏", exact: true }).click();
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill("personal note");
  await expect(page.locator(`.result-row[data-bookmark-id="${record.bookmark_id}"]`)).toBeVisible();
});

test("unsaved notes survive tab changes, closing and page refresh without a write", async ({ page, owned }) => {
  const record = await owned.create(), control = await intercept(page);
  await open(page, record); await edit(page); await input(page).fill(text);
  await page.getByRole("tab", { name: "相关书签", exact: true }).click(); await page.getByRole("tab", { name: "阅读", exact: true }).click();
  await expect(input(page)).toHaveValue(text);
  await notes(page).getByRole("button", { name: "收起编辑，保留草稿", exact: true }).click();
  await expect(notes(page).getByText("未保存的草稿已保留。", { exact: true })).toBeVisible();
  await page.reload(); await open(page, record); await expect(input(page)).toHaveValue(text);
  expect(control.writes).toHaveLength(0); expect((await owned.read(record.bookmark_id)).note).toBe("");
});

for (const failure of ["lost", "corrupt"] as const) test(`${failure} successful response is recovered by reading the original receipt without another save`, async ({ page, owned }) => {
  const record = await owned.create(), control = await intercept(page);
  control.lose = failure === "lost"; control.corrupt = failure === "corrupt"; control.failReads = true;
  await open(page, record); await edit(page); await input(page).fill(text);
  await notes(page).getByRole("button", { name: "保存笔记", exact: true }).click();
  await expect(notes(page).locator(".reader-note-recovery")).toBeVisible(); await expect(input(page)).toHaveAttribute("readonly", "");
  expect((await owned.read(record.bookmark_id)).note).toBe(text);
  await page.reload(); await open(page, record); await expect(input(page)).toHaveValue(text); expect(control.writes).toHaveLength(1);
  const read = notes(page).getByRole("button", { name: "读取保存回执", exact: true });
  await read.press("Space"); await expect(notes(page).locator(".reader-note-error")).toContainText("Synthetic note receipt unavailable");
  await expect(read).toBeEnabled(); await expect(notes(page).getByRole("button", { name: "返回修改", exact: true })).toHaveCount(0);
  await notes(page).getByRole("button", { name: "重读笔记，保留草稿", exact: true }).click();
  await expect(notes(page).getByRole("button", { name: "返回修改", exact: true })).toHaveCount(0);
  control.failReads = false; await read.press("Enter"); await expect(input(page)).toHaveCount(0);
  expect(control.writes).toHaveLength(1); expect((await owned.read(record.bookmark_id)).note_revision).toBe(1);
});

test("an unaccepted save retries its frozen contents or explicitly returns to editing", async ({ page, owned }) => {
  const record = await owned.create(), control = await intercept(page); control.reject = true;
  await open(page, record); await edit(page); await input(page).fill(text); await notes(page).getByRole("button", { name: "保存笔记", exact: true }).click();
  await expect(notes(page).locator(".reader-note-recovery")).toBeVisible();
  await notes(page).getByRole("button", { name: "读取保存回执", exact: true }).click();
  await notes(page).getByRole("button", { name: "返回修改", exact: true }).click(); await expect(input(page)).toBeEditable();
  await input(page).fill(text + "new draft"); await notes(page).getByRole("button", { name: "保存笔记", exact: true }).press("Space");
  await expect(input(page)).toHaveCount(0); expect(control.writes).toHaveLength(2);
  expect(control.writes[1].request_id).not.toBe(control.writes[0].request_id);
  expect((await owned.read(record.bookmark_id)).note).toBe(text + "new draft");
});

test("another window's saved note requires review before replacing it with the preserved draft", async ({ page, request, owned }) => {
  const record = await owned.create(), control = await intercept(page); await open(page, record); await edit(page); await input(page).fill(text);
  const other = await request.patch(`/admin/library/bookmarks/${record.bookmark_id}/note`, { headers: owned.headers,
    data: { request_id: randomUUID(), note: "Another window's saved note", base_revision: 0 } }); expect(other.ok()).toBeTruthy();
  await notes(page).getByRole("button", { name: "保存笔记", exact: true }).click();
  const conflict = notes(page).locator(".reader-note-conflict"); await expect(conflict).toBeVisible(); await expect(input(page)).toHaveValue(text);
  await expect(notes(page).getByRole("button", { name: "保存笔记", exact: true })).toBeDisabled();
  await conflict.locator("summary").press("Enter"); await expect(conflict.locator(".reader-note-text")).toHaveText("Another window's saved note");
  expect((await owned.read(record.bookmark_id)).note).toBe("Another window's saved note");
  await conflict.getByRole("button", { name: "保留草稿继续修改", exact: true }).press("Space"); await expect(input(page)).toHaveValue(text);
  await notes(page).getByRole("button", { name: "保存笔记", exact: true }).click(); await expect(input(page)).toHaveCount(0);
  expect((await owned.read(record.bookmark_id)).note).toBe(text); expect(control.writes).toHaveLength(2);
});

test("late confirmation for the previous page never clears the next page's draft", async ({ page, owned }) => {
  const first = await owned.create(), second = await owned.create(); let release!: () => void, received!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; }), contacted = new Promise<void>(resolve => { received = resolve; });
  let completed!: () => void;
  const replied = new Promise<void>(resolve => { completed = resolve; });
  await page.route(`/admin/library/bookmarks/${first.bookmark_id}/note`, async route => {
    if (route.request().method() !== "PATCH") return route.continue();
    const response = await route.fetch(); received(); await held; await route.fulfill({ response }); completed();
  });
  try {
    await open(page, first); await edit(page); await input(page).fill(text); await notes(page).getByRole("button", { name: "保存笔记", exact: true }).click(); await contacted;
    await page.getByRole("button", { name: "返回收藏", exact: true }).click(); await open(page, second, false); await edit(page); await input(page).fill("Next page's draft");
    release(); await replied; await expect(input(page)).toHaveValue("Next page's draft"); await page.reload(); await open(page, second); await expect(input(page)).toHaveValue("Next page's draft");
    expect((await owned.read(first.bookmark_id)).note).toBe(text); expect((await owned.read(second.bookmark_id)).note).toBe("");
  } finally { release(); }
});

test("long conflict notes and editing controls remain usable in both themes, languages and short windows", async ({ page, request, owned }) => {
  test.setTimeout(120_000);
  const record = await owned.create(), draft = text.repeat(30); await open(page, record); await edit(page); await input(page).fill(draft);
  const other = await request.patch(`/admin/library/bookmarks/${record.bookmark_id}/note`, { headers: owned.headers,
    data: { request_id: randomUUID(), note: ("另一个窗口保存的完整笔记。 A complete saved note.\n  ").repeat(40), base_revision: 0 } }); expect(other.ok()).toBeTruthy();
  await notes(page).getByRole("button", { name: "保存笔记", exact: true }).click(); await expect(notes(page).locator(".reader-note-conflict")).toBeVisible();
  for (const language of ["zh", "en"] as const) for (const theme of ["light", "dark"] as const) {
    await page.evaluate(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme });
    await page.reload(); await open(page, record); await expect(input(page)).toHaveValue(draft);
    for (const size of [{ width: 1280, height: 850 }, { width: 390, height: 844 }, { width: 320, height: 640 }, { width: 683, height: 384 }]) {
      await page.setViewportSize(size); await settleVisualLayout(page);
      await notes(page).locator(".reader-note-conflict").scrollIntoViewIfNeeded();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(await notes(page).evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
      const keep = notes(page).getByRole("button", { name: language === "zh" ? "保留草稿继续修改" : "Keep draft and continue", exact: true });
      await keep.scrollIntoViewIfNeeded(); await expect(keep).toBeInViewport();
      const bounds = await keep.boundingBox(); expect(bounds!.height).toBeGreaterThanOrEqual(size.width < 421 ? 44 : 40);
      await page.screenshot({ path: `screenshots/collection-review/notes-${language}-${theme}-${size.width}-${size.height}.png`, animations: "disabled" });
    }
  }
});
