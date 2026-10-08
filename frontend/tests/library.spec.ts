import { expect, test as base, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdir, readFile } from "node:fs/promises";

type Bookmark = {
  bookmark_id: number;
  url: string;
  title: string;
  folder: string;
  tags: string[];
  body_text?: string;
};
type Library = {
  create: (values?: Partial<Bookmark>) => Promise<Bookmark>;
  read: (id: number) => Promise<Bookmark>;
  remember: (id: number) => void;
  headers: Record<string, string>;
};

// The configured server owns a temporary synthetic library. Each mutation test
// also owns its records so failures cannot alter the corpus used by other suites.
const test = base.extend<{ library: Library }>({
  library: async ({ request }, use) => {
    const boot = await request.get("/app/boot");
    expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` };
    const ids = new Set<number>();
    await use({
      headers,
      remember: (id) => { ids.add(id); },
      create: async (values = {}) => {
        const response = await request.post("/admin/library/bookmarks", {
          headers,
          data: {
            url: `https://library-ui.example/${randomUUID()}`,
            title: "Synthetic library fixture",
            folder: "",
            tags: [],
            ...values,
          },
        });
        expect(response.ok()).toBeTruthy();
        const record = await response.json() as Bookmark;
        ids.add(record.bookmark_id);
        return record;
      },
      read: async (id) => readBookmark(request, headers, id),
    });
    for (const id of ids) {
      const response = await request.delete(`/admin/library/bookmarks/${id}`, { headers });
      expect([200, 404]).toContain(response.status());
    }
  },
});

async function readBookmark(request: APIRequestContext, headers: Record<string, string>, id: number) {
  const response = await request.get(`/bookmark/${id}?body=true`, { headers });
  expect(response.ok()).toBeTruthy();
  return await response.json() as Bookmark;
}

function marker() {
  return `libraryui${randomUUID().replaceAll("-", "")}`;
}

async function search(page: Page, query: string, count: number) {
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill(query);
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".result-row")).toHaveCount(count);
}

function row(page: Page, id: number) {
  return page.locator(`.result-row[data-bookmark-id="${id}"]`);
}

async function addTag(dialog: Locator, value: string) {
  const input = dialog.getByRole("textbox", { name: "输入标签", exact: true });
  await input.fill(value);
  await input.press("Enter");
  await expect(dialog.getByRole("button", { name: `移除标签 ${value}`, exact: true })).toBeVisible();
}

async function save(dialog: Locator) {
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

async function selectAll(page: Page) {
  await page.getByRole("button", { name: "批量管理", exact: true }).click();
  await page.getByRole("button", { name: "选择本页", exact: true }).click();
  await page.getByRole("button", { name: "批量操作", exact: true }).click();
  return page.getByRole("dialog", { name: "批量管理", exact: true });
}

async function download(page: Page, dialog: Locator) {
  const received = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/admin/library/export" && response.request().method() === "POST",
  );
  const downloaded = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "下载导出文件", exact: true }).click();
  const [response, file] = await Promise.all([received, downloaded]);
  expect(response.ok()).toBeTruthy();
  expect(await file.failure()).toBeNull();
  const path = await file.path();
  expect(path).not.toBeNull();
  await expect(dialog).toHaveCount(0);
  return {
    filename: file.suggestedFilename(),
    content: await readFile(path!, "utf8"),
    request: response.request().postDataJSON(),
  };
}

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots", { recursive: true });
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort(),
  );
  await page.addInitScript(() => {
    localStorage.setItem("fm-language", "zh");
    localStorage.setItem("fm-theme", "light");
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 960 });
});

test("create and edit preserve literal folder names and tags after reload", async ({ page, library }) => {
  const token = marker();
  const original = {
    url: `https://library-ui.example/${token}`,
    title: `${token} 收藏标题`,
    folder: "研发 / 阅读 & 资料",
    tags: ["研发 & 阅读", "带,逗号"],
  };
  await page.goto("/app");
  await page.getByRole("button", { name: "新增收藏", exact: true }).click();
  const create = page.getByRole("dialog", { name: "新增收藏", exact: true });
  await create.getByLabel("收藏网址", { exact: true }).fill(original.url);
  await create.getByLabel("收藏标题", { exact: true }).fill(original.title);
  await create.getByLabel("收藏文件夹", { exact: true }).fill(original.folder);
  for (const tag of original.tags) await addTag(create, tag);
  await addTag(create, original.tags[0]);
  await expect(create.locator(".editing-tags button")).toHaveCount(2);
  const created = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/admin/library/bookmarks" && response.request().method() === "POST",
  );
  await create.getByRole("button", { name: "保存", exact: true }).click();
  const response = await created;
  expect(response.ok()).toBeTruthy();
  const record = await response.json() as Bookmark;
  library.remember(record.bookmark_id);
  await expect(create).toHaveCount(0);
  expect(await library.read(record.bookmark_id)).toMatchObject(original);

  await search(page, token, 1);
  await row(page, record.bookmark_id).click();
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  const edit = page.getByRole("dialog", { name: "编辑收藏", exact: true });
  await expect(edit.getByLabel("收藏网址", { exact: true })).toHaveValue(original.url);
  await expect(edit.getByLabel("收藏文件夹", { exact: true })).toHaveValue(original.folder);
  const updated = { ...original, url: `${original.url}/updated`, title: `${token} 修改后的标题`, folder: "", tags: ["带,逗号", "稍后 阅读"] };
  await edit.getByLabel("收藏网址", { exact: true }).fill(updated.url);
  await edit.getByLabel("收藏标题", { exact: true }).fill(updated.title);
  await edit.getByLabel("收藏文件夹", { exact: true }).fill(updated.folder);
  await edit.getByRole("button", { name: `移除标签 ${original.tags[0]}`, exact: true }).click();
  await addTag(edit, updated.tags[1]);
  await page.screenshot({ path: "screenshots/library-edit-zh-1440.png", animations: "disabled" });
  await save(edit);
  expect(await library.read(record.bookmark_id)).toMatchObject(updated);
  await expect(page.locator(".preview-title h1")).toHaveText(updated.title);
  await page.reload();
  await expect(row(page, record.bookmark_id)).toContainText(updated.title);
  await row(page, record.bookmark_id).click();
  await page.locator(".article-details > summary").click();
  for (const tag of updated.tags) await expect(page.locator(".preview-tags").getByRole("button", { name: `# ${tag}`, exact: true })).toBeVisible();
});

test("delete requires fresh consent and cancellation leaves the bookmark intact", async ({ page, request, library }) => {
  const token = marker();
  const first = await library.create({ title: `${token} 删除对象` });
  const second = await library.create({ title: `${token} 保留对象` });
  const deleted: unknown[] = [];
  await page.route("**/admin/library/bulk", async (route) => {
    deleted.push(route.request().postDataJSON());
    await route.continue();
  });
  await page.goto("/app");
  await search(page, token, 2);
  await row(page, first.bookmark_id).click();
  await page.locator(".article-details > summary").click();
  const trigger = page.getByRole("button", { name: "删除收藏", exact: true });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "删除收藏", exact: true });
  await expect(dialog.getByRole("button", { name: "确认删除", exact: true })).toBeDisabled();
  await dialog.getByLabel("我确认删除这些收藏", { exact: true }).check();
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await expect(trigger).toBeFocused();
  expect(deleted).toEqual([]);
  expect((await library.read(first.bookmark_id)).title).toBe(first.title);
  await trigger.click();
  await expect(dialog.getByLabel("我确认删除这些收藏", { exact: true })).not.toBeChecked();
  await expect(dialog.getByRole("button", { name: "确认删除", exact: true })).toBeDisabled();
  await dialog.getByLabel("我确认删除这些收藏", { exact: true }).check();
  await dialog.getByRole("button", { name: "确认删除", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(row(page, first.bookmark_id)).toHaveCount(0);
  await expect(row(page, second.bookmark_id)).toBeVisible();
  await expect(page.locator(".preview-pane")).toHaveCount(0);
  expect(deleted).toEqual([{ ids: [first.bookmark_id], action: "delete" }]);
  expect((await request.get(`/bookmark/${first.bookmark_id}`, { headers: library.headers })).status()).toBe(404);
});

test("keyboard selection and bulk move and tags affect only the selected results", async ({ page, library }) => {
  const token = marker();
  const first = await library.create({ title: `${token} 第一条`, tags: ["原标签"] });
  const second = await library.create({ title: `${token} 第二条`, tags: ["原标签"] });
  const outside = await library.create({ title: "Not in the selected result set", folder: "保持原样", tags: ["原标签"] });
  await page.goto("/app");
  await search(page, token, 2);
  await page.getByRole("button", { name: "批量管理", exact: true }).click();
  await expect(page.getByRole("button", { name: "批量操作", exact: true })).toBeDisabled();
  await page.locator(".result-row").first().focus();
  await page.keyboard.press("Space");
  await expect(page.locator(".result-row").first()).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("ArrowDown");
  await expect(page.locator(".result-row").nth(1)).toBeFocused();
  await expect(page.locator(".result-row").nth(1)).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator(".preview-pane")).toHaveCount(0);
  await page.getByRole("button", { name: "选择本页", exact: true }).click();
  await expect(page.locator(".selection-total")).toHaveText("已选择 2 条");
  await page.getByRole("button", { name: "批量操作", exact: true }).click();
  let dialog = page.getByRole("dialog", { name: "批量管理", exact: true });
  await dialog.getByLabel("目标文件夹", { exact: true }).fill("同一文件夹 / 完整名称");
  await save(dialog);
  for (const record of [first, second]) expect((await library.read(record.bookmark_id)).folder).toBe("同一文件夹 / 完整名称");
  await expect(page.locator(".selection-total")).toHaveCount(0);
  for (const operation of ["tag-add", "tag-remove"]) {
    dialog = await selectAll(page);
    await dialog.getByLabel("批量操作类型", { exact: true }).selectOption(operation);
    await expect(dialog.getByRole("button", { name: "保存", exact: true })).toBeDisabled();
    await addTag(dialog, "共同,标签");
    await save(dialog);
    for (const record of [first, second]) {
      expect((await library.read(record.bookmark_id)).tags).toEqual(operation === "tag-add" ? ["原标签", "共同,标签"] : ["原标签"]);
    }
  }
  expect(await library.read(outside.bookmark_id)).toMatchObject({ folder: "保持原样", tags: ["原标签"] });
  dialog = await selectAll(page);
  await dialog.getByLabel("批量操作类型", { exact: true }).selectOption("delete");
  await dialog.getByLabel("我确认删除这些收藏", { exact: true }).check();
  await dialog.getByLabel("批量操作类型", { exact: true }).selectOption("move");
  await dialog.getByLabel("批量操作类型", { exact: true }).selectOption("delete");
  await expect(dialog.getByRole("button", { name: "确认删除", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await page.getByRole("button", { name: "完成选择", exact: true }).click();
  await expect(page.locator(".selection-total")).toHaveCount(0);
});

test("export downloads honor search-page, selected and category scopes", async ({ page, library }) => {
  const token = marker();
  const folder = `${token} / 文档`;
  const first = await library.create({ title: `${token} <第一条>`, folder, tags: ["带,逗号"] });
  const second = await library.create({ title: `${token} 第二条`, folder });
  const outside = await library.create({ title: `${token} 文件夹之外`, folder: "导出范围之外" });
  await page.goto("/app");
  await search(page, token, 3);
  await page.getByRole("button", { name: "导出", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "导出收藏", exact: true });
  await expect(dialog.getByRole("combobox", { name: "导出范围", exact: true })).toHaveValue("page");
  await expect(dialog.locator('option[value="filtered"]')).toBeDisabled();
  const wholePage = await download(page, dialog);
  expect(wholePage.filename).toMatch(/^facetmark-.*\.json$/);
  expect([...wholePage.request.ids].sort()).toEqual([first.bookmark_id, second.bookmark_id, outside.bookmark_id].sort());
  const json = JSON.parse(wholePage.content);
  expect(json.facetmark.count).toBe(3);
  expect(json.bookmarks.map((bookmark: Bookmark) => bookmark.url).sort()).toEqual([first.url, second.url, outside.url].sort());
  expect(json.bookmarks.find((bookmark: Bookmark) => bookmark.url === first.url).tags).toEqual(["带,逗号"]);

  await page.getByRole("button", { name: "批量管理", exact: true }).click();
  await row(page, first.bookmark_id).click();
  await page.getByRole("button", { name: "导出所选", exact: true }).click();
  await expect(dialog.getByRole("combobox", { name: "导出范围", exact: true })).toHaveValue("selected");
  await dialog.getByRole("combobox", { name: "文件格式", exact: true }).selectOption("html");
  const selected = await download(page, dialog);
  expect(selected.filename).toMatch(/^facetmark-.*\.html$/);
  expect(selected.request.ids).toEqual([first.bookmark_id]);
  expect(selected.content).toContain("<!DOCTYPE NETSCAPE-Bookmark-file-1>");
  expect(selected.content).toContain(first.url);
  expect(selected.content).toContain("&lt;第一条&gt;");
  expect(selected.content).not.toContain(second.url);
  expect(selected.content).not.toContain(outside.url);
  await page.getByRole("button", { name: "完成选择", exact: true }).click();

  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill("");
  await page.getByRole("button", { name: "筛选收藏", exact: true }).click();
  await page.locator(".facet-nav").getByTitle(folder, { exact: true }).click();
  await expect(page.locator(".result-row")).toHaveCount(2);
  await page.getByRole("button", { name: "导出", exact: true }).click();
  await dialog.getByRole("combobox", { name: "导出范围", exact: true }).selectOption("filtered");
  const filtered = await download(page, dialog);
  expect(filtered.request).toMatchObject({ filters: { folder } });
  expect(filtered.request.ids).toBeUndefined();
  expect(JSON.parse(filtered.content).bookmarks.map((bookmark: Bookmark) => bookmark.url).sort()).toEqual([first.url, second.url].sort());
});

test("taxonomy merges exact names and removes labels without deleting bookmarks", async ({ page, library }) => {
  const token = marker();
  const oldFolder = `${token}/literal/name`;
  const targetFolder = `${token}/destination`;
  const oldTag = `${token} old,tag`;
  const targetTag = `${token} retained tag`;
  const first = await library.create({ folder: oldFolder, tags: [oldTag, targetTag] });
  const second = await library.create({ folder: targetFolder, tags: [oldTag] });
  const outside = await library.create({ folder: `${oldFolder}/child`, tags: [`${oldTag} suffix`] });
  await page.goto("/app");
  await page.getByRole("button", { name: "整理分类", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "整理文件夹与标签", exact: true });
  await dialog.getByLabel("当前名称", { exact: true }).fill(oldFolder);
  await dialog.getByLabel("新名称", { exact: true }).fill(targetFolder);
  await expect(dialog.getByRole("button", { name: "保存", exact: true })).toBeDisabled();
  await dialog.getByLabel("我确认应用到使用该分类的全部收藏", { exact: true }).check();
  await dialog.getByLabel("新名称", { exact: true }).fill(`${targetFolder} draft`);
  await expect(dialog.getByRole("button", { name: "保存", exact: true })).toBeDisabled();
  await dialog.getByLabel("新名称", { exact: true }).fill(targetFolder);
  await dialog.getByLabel("我确认应用到使用该分类的全部收藏", { exact: true }).check();
  await save(dialog);
  for (const record of [first, second]) expect((await library.read(record.bookmark_id)).folder).toBe(targetFolder);
  expect((await library.read(outside.bookmark_id)).folder).toBe(`${oldFolder}/child`);

  for (const action of ["rename", "delete"]) {
    await page.getByRole("button", { name: "整理分类", exact: true }).click();
    await dialog.getByRole("combobox", { name: "整理对象", exact: true }).selectOption("tag");
    await dialog.getByRole("combobox", { name: "操作", exact: true }).selectOption(action);
    await dialog.getByLabel("当前名称", { exact: true }).fill(action === "rename" ? oldTag : targetTag);
    if (action === "rename") await dialog.getByLabel("新名称", { exact: true }).fill(targetTag);
    await dialog.getByLabel("我确认应用到使用该分类的全部收藏", { exact: true }).check();
    await save(dialog);
    for (const record of [first, second]) expect((await library.read(record.bookmark_id)).tags).toEqual(action === "rename" ? [targetTag] : []);
  }
  expect((await library.read(outside.bookmark_id)).tags).toEqual([`${oldTag} suffix`]);
});

test("JSON download retains the saved page text for the selected synthetic bookmark", async ({ page, library }) => {
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const first = page.locator(".result-row").filter({ hasText: "SQLite" }).first();
  const id = Number(await first.getAttribute("data-bookmark-id"));
  const record = await library.read(id);
  expect(record.body_text).toContain("synthetic content");
  await page.getByRole("button", { name: "批量管理", exact: true }).click();
  await first.click();
  await page.getByRole("button", { name: "导出所选", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "导出收藏", exact: true });
  const exported = JSON.parse((await download(page, dialog)).content);
  expect(exported.facetmark).toMatchObject({ full: true, count: 1 });
  expect(exported.bookmarks).toHaveLength(1);
  expect(exported.bookmarks[0]).toMatchObject({
    url: record.url,
    title: record.title,
    folder: record.folder,
    tags: record.tags,
    content: { body_text: record.body_text },
  });
});

test("fetch needs no model while summarization requires chat and explicit consent", async ({ page, library }) => {
  const token = marker();
  const record = await library.create({ title: token });
  let chatReady = false;
  let job: object = { state: "idle", done: [], log: [] };
  const starts: Record<string, unknown>[] = [];
  await page.route("**/admin/setup-status", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.demo = false;
    data.channels.chat.tested = chatReady;
    data.channels.embed.tested = false;
    data.channels.embed.configured = false;
    await route.fulfill({ json: data });
  });
  await page.route("**/admin/job", (route) => route.fulfill({ json: job }));
  // Exercise job creation and subsequent navigation without fetching fixture
  // URLs or contacting any configured model from the CI server.
  await page.route("**/admin/jobs/start", async (route) => {
    const body = route.request().postDataJSON();
    starts.push(body);
    job = { state: "done", params: body, planned: [body.mode === "fetch" ? "fetch" : "enrich"], done: [body.mode === "fetch" ? "fetch" : "enrich"], items: { done: 1, total: 1 }, log: [] };
    await route.fulfill({ json: job });
  });
  await page.goto("/app");
  await page.getByRole("button", { name: "任务", exact: true }).click();
  await page.getByRole("button", { name: "生成阅读摘要", exact: true }).click();
  let dialog = page.getByRole("dialog", { name: "生成 AI 摘要", exact: true });
  await expect(dialog.getByRole("alert")).toContainText("配置并测试聊天模型");
  await dialog.getByLabel("我同意将上述内容发送给聊天模型", { exact: true }).check();
  await expect(dialog.getByRole("button", { name: "开始任务", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await page.getByRole("button", { name: "抓取网页正文", exact: true }).click();
  dialog = page.getByRole("dialog", { name: "提取网页正文", exact: true });
  await expect(dialog.getByText("不调用 AI 模型", { exact: false })).toBeVisible();
  await expect(dialog.locator(".consent")).toHaveCount(0);
  await expect(dialog.getByRole("button", { name: "开始任务", exact: true })).toBeEnabled();
  await dialog.getByRole("button", { name: "开始任务", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(starts).toEqual([{ mode: "fetch", confirmed: false, force: false }]);
  await expect(page.locator(".tasks h2")).toHaveText("正文抓取已完成");

  chatReady = true;
  await page.reload();
  await search(page, token, 1);
  await row(page, record.bookmark_id).click();
  await page.getByRole("tab", { name: "AI 摘要", exact: true }).click();
  await page.getByRole("button", { name: "生成这篇摘要", exact: true }).click();
  dialog = page.getByRole("dialog", { name: "生成 AI 摘要", exact: true });
  await expect(dialog.getByRole("alert")).toHaveCount(0);
  await expect(dialog.getByRole("button", { name: "开始任务", exact: true })).toBeDisabled();
  await dialog.getByLabel("我同意将上述内容发送给聊天模型", { exact: true }).check();
  await dialog.getByLabel("重新处理已完成的内容", { exact: true }).check();
  await dialog.getByRole("button", { name: "开始任务", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(starts[1]).toEqual({ mode: "summarize", bookmark_ids: [record.bookmark_id], confirmed: true, force: true });
  await expect(page.locator(".tasks h2")).toHaveText("摘要生成已完成");
  await expect(page.locator(".tasks")).toContainText("范围：1 条所选书签");
});

test("mobile action dialogs trap focus, fit the screen and restore the underlying reader", async ({ page, library }) => {
  const token = marker();
  const record = await library.create({ title: token });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app");
  const add = page.getByRole("button", { name: "新增收藏", exact: true });
  await add.click();
  let dialog = page.getByRole("dialog", { name: "新增收藏", exact: true });
  for (let index = 0; index < 12; index++) {
    await page.keyboard.press(index < 6 ? "Tab" : "Shift+Tab");
    expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBeTruthy();
  }
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(add).toBeFocused();
  await search(page, token, 1);
  await row(page, record.bookmark_id).click();
  const preview = page.getByRole("dialog", { name: "书签预览", exact: true });
  await expect(preview).toBeVisible();
  const edit = preview.getByRole("button", { name: "编辑", exact: true });
  await edit.click();
  dialog = page.getByRole("dialog", { name: "编辑收藏", exact: true });
  await dialog.getByLabel("收藏标题", { exact: true }).fill("Unsaved draft that must not leak");
  const box = await dialog.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  expect(await dialog.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
  await page.screenshot({ path: "screenshots/library-edit-zh-390.png", animations: "disabled" });
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(preview).toBeVisible();
  await expect(edit).toBeFocused();
  expect((await library.read(record.bookmark_id)).title).toBe(token);
  await page.keyboard.press("Escape");
  await expect(preview).toHaveCount(0);
  await expect(row(page, record.bookmark_id)).toBeFocused();
});

test("failed saves retain the draft and allow a successful retry", async ({ page, library }) => {
  const record = await library.create({ title: marker() });
  let failed = false;
  await page.route(`**/admin/library/bookmarks/${record.bookmark_id}`, async (route) => {
    if (route.request().method() === "PATCH" && !failed) {
      failed = true;
      await route.fulfill({ status: 503, json: { detail: "Synthetic save failure" } });
    } else await route.continue();
  });
  await page.goto("/app");
  await search(page, record.title, 1);
  await row(page, record.bookmark_id).click();
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "编辑收藏", exact: true });
  await dialog.getByLabel("收藏标题", { exact: true }).fill(`${record.title} retry`);
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("Synthetic save failure");
  await expect(dialog.getByLabel("收藏标题", { exact: true })).toHaveValue(`${record.title} retry`);
  expect((await library.read(record.bookmark_id)).title).toBe(record.title);
  await save(dialog);
  expect((await library.read(record.bookmark_id)).title).toBe(`${record.title} retry`);
});

test("opening during a running task refreshes the cached reader when that task completes", async ({ page, library }) => {
  const record = await library.create({ title: marker() });
  let completed = false;
  await page.route("**/admin/setup-status", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ json: { ...await response.json(), library_revision: completed ? "task-after" : "task-before" } });
  });
  await page.route("**/admin/job", (route) => route.fulfill({ json: {
    state: completed ? "done" : "running", params: { mode: "fetch" }, planned: ["fetch"], done: completed ? ["fetch"] : [],
  } }));
  await page.route(`**/bookmark/${record.bookmark_id}?body=true`, async (route) => {
    const response = await route.fetch();
    await route.fulfill({ json: { ...await response.json(), body_text: completed ? "New saved text from the completed reading task." : "Old text shown while the reading task is running." } });
  });
  await page.goto("/app");
  await search(page, record.title, 1);
  await row(page, record.bookmark_id).click();
  await expect(page.locator(".reading")).toContainText("Old text shown while");
  completed = true;
  await expect(page.locator(".reading")).toContainText("New saved text from", { timeout: 10000 });
});
