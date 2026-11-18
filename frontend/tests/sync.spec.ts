import { expect, test as base, type APIRequestContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { chmod, mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve, sep } from "node:path";
import type { SyncOperation, SyncWorkspace } from "../src/sync-local-state";
import { settleVisualLayout } from "./visual-layout";

const runtimeErrors = new WeakMap<Page, string[]>();

type RecordValue = { url: string; title: string; folder: string; tags: string[]; date_added: number | null };
type Commit = {
  format: string; version: number; id: string; device: string; parents: string[];
  changes: Record<string, RecordValue | null>;
};
type SyncEnvironment = {
  shared: string;
  headers: Record<string, string>;
  remember: (id: number) => void;
};

// Teardown has its own budget and request context: a timed-out browser action
// must not leave synthetic records or enabled sync in the shared test server.
const test = base.extend<{ syncEnvironment: SyncEnvironment }>({
  syncEnvironment: [async ({ playwright, baseURL }, use) => {
    const shared = await mkdtemp(join(tmpdir(), "facetmark-ui-sync-"));
    const cleanupRequest = await playwright.request.newContext({ baseURL, timeout: 5000 });
    const ids = new Set<number>();
    const headers = await authenticated(cleanupRequest);
    try {
      await use({ shared, headers, remember: (id) => { ids.add(id); } });
    } finally {
      const failures: unknown[] = [];
      const attempt = async (work: () => Promise<void>) => {
        try { await work(); } catch (error) { failures.push(error); }
      };
      await attempt(async () => {
        const response = await cleanupRequest.get("/admin/library/sync/status", { headers });
        expect(response.ok()).toBeTruthy();
        for (const value of (await response.json()).pending_operations ?? []) {
          if (resolve(value.folder) !== resolve(shared)) throw new Error("Pending delivery does not belong to this test's shared folder");
          await chmod(join(shared, ".facetmark-sync"), 0o755);
          const completed = await cleanupRequest.post(`/admin/library/sync/operations/${value.request_id}/retry`, { headers, data: {} });
          expect(completed.status()).toBe(200); expect((await completed.json()).complete).toBe(true);
        }
      });
      await attempt(async () => {
        const response = await cleanupRequest.post("/admin/library/sync/config", {
          headers, data: { folder: "", enabled: false, auto_sync: false, poll_seconds: 60 },
        });
        expect(response.ok()).toBeTruthy();
      });
      for (const id of ids) {
        await attempt(async () => {
          const response = await cleanupRequest.delete(`/admin/library/bookmarks/${id}`, { headers });
          expect([200, 404]).toContain(response.status());
        });
      }
      await attempt(async () => {
        const resolved = resolve(shared);
        if (!resolved.startsWith(resolve(tmpdir()) + sep) || !resolved.includes("facetmark-ui-sync-")) {
          throw new Error("Refusing cleanup outside the test-created temporary shared folder");
        }
        await rm(resolved, { recursive: true, force: true });
      });
      await attempt(async () => { await cleanupRequest.dispose(); });
      if (failures.length) throw new AggregateError(failures, "Failed to clean up the synthetic sync environment");
    }
  }, { timeout: 30000 }],
});

async function authenticated(request: APIRequestContext) {
  const boot = await request.get("/app/boot");
  expect(boot.ok()).toBeTruthy();
  const { token } = await boot.json();
  return { Authorization: `Bearer ${token}` };
}

test.beforeEach(async ({ page }) => {
  const errors: string[] = []; runtimeErrors.set(page, errors);
  page.on("pageerror", error => errors.push(error.message));
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
  });
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort(),
  );
});

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  expect(runtimeErrors.get(page)).toEqual([]);
});

test.beforeAll(async () => {
  await mkdir("screenshots", { recursive: true });
});

test("shared-folder sync reviews actual changes, rejects a stale preview and resolves concurrent versions", async ({ page, request, syncEnvironment }) => {
  test.setTimeout(60000);
  const { shared, headers, remember } = syncEnvironment;
  await test.step("Review, apply and persist shared-folder sync", async () => {
    const saved = await request.post("/admin/library/bookmarks", {
      headers,
      data: { url: `https://sync-ui.example/${randomUUID()}`, title: "SYNC initial title", folder: "同步测试", tags: ["local"] },
    });
    expect(saved.ok()).toBeTruthy();
    const bookmark = await saved.json();
    const bookmarkId: number = bookmark.bookmark_id;
    remember(bookmarkId);

    await page.goto("/app");
    await page.getByRole("button", { name: "设置", exact: true }).click();
    await page.getByRole("tab", { name: "设备同步", exact: true }).click();
    const sync = page.locator(".sync-settings");
    await expect(sync.getByRole("heading", { name: "在设备之间同步书签" })).toBeVisible();
    await sync.getByLabel("共享文件夹完整路径").fill(shared);
    await sync.getByLabel("启用共享文件夹同步", { exact: true }).check();
    await sync.getByLabel("首次确认后自动同步", { exact: true }).uncheck();
    await sync.getByRole("button", { name: "保存同步设置", exact: true }).click();
    await expect(sync.locator(".sync-state")).toHaveText("等待首次确认");

    await sync.getByRole("button", { name: "预览同步变更", exact: true }).click();
    await expect(sync.locator(".sync-preview")).toBeVisible();
    await sync.locator(".sync-change-list > summary").click();
    const initial = sync.locator(".sync-change").filter({ hasText: "SYNC initial title" });
    await initial.locator(":scope > summary").click();
    await expect(initial.locator(".sync-comparison")).toContainText(bookmark.url);
    const apply = sync.getByRole("button", { name: "应用本次同步", exact: true });
    await expect(apply).toBeDisabled();

    // Change the real local DB after preview. Applying it must require a fresh
    // review and must not publish an outdated snapshot to the shared folder.
    const updated = await request.patch(`/admin/library/bookmarks/${bookmarkId}`, {
      headers, data: { title: "SYNC refreshed baseline" },
    });
    expect(updated.ok()).toBeTruthy();
    await sync.getByLabel("我已核对以上变更，并确认应用", { exact: true }).check();
    await apply.click();
    await expect(sync.getByRole("alert")).toContainText("preview again");
    await expect(sync.locator(".sync-preview")).toBeVisible();
    await expect(initial.locator(".sync-comparison")).toContainText("SYNC initial title");
    const recovery = sync.getByRole("complementary", { name: "同步操作恢复" });
    await expect(recovery).toContainText("原请求未被接受");
    expect((await readdir(join(shared, ".facetmark-sync"))).filter((name) => name.startsWith("commit-"))).toHaveLength(0);

    await recovery.getByRole("button", { name: "返回修改同步", exact: true }).click();
    await expect(recovery).toHaveCount(0);
    await sync.getByRole("button", { name: "重新预览", exact: true }).click();
    await sync.getByLabel("我已核对以上变更，并确认应用", { exact: true }).check();
    await sync.getByRole("button", { name: "应用本次同步", exact: true }).click();
    await expect(sync.locator(".notice")).toContainText("同步完成");
    const directory = join(shared, ".facetmark-sync");
    const files = (await readdir(directory)).filter((name) => name.startsWith("commit-"));
    expect(files).toHaveLength(1);
    const baseline = JSON.parse(await readFile(join(directory, files[0]), "utf8")) as Commit;
    const [syncId, base] = Object.entries(baseline.changes).find(([, value]) => value?.url === bookmark.url)!;
    expect(base?.title).toBe("SYNC refreshed baseline");
    for (const record of Object.values(baseline.changes)) {
      if (record) expect(Object.keys(record).sort()).toEqual(["date_added", "folder", "tags", "title", "url"]);
    }

    // Two independent devices edit from the same parent. Both versions must
    // remain visible; the user selects a concrete remote version, not whichever
    // file happened to arrive last.
    expect((await request.patch(`/admin/library/bookmarks/${bookmarkId}`, {
      headers, data: { title: "SYNC local choice", tags: ["local", "待决定"] },
    })).ok()).toBeTruthy();
    for (const [title, tag] of [["SYNC remote first", "remote-one"], ["SYNC remote second", "remote-two"]]) {
      const id = randomUUID();
      const commit: Commit = {
        format: "facetmark-library-sync", version: 1, id, device: randomUUID(), parents: [baseline.id],
        changes: { [syncId]: { ...base!, title, folder: "完整展示的共享文件夹/子目录", tags: [tag, "研发 & 阅读"] } },
      };
      await writeFile(join(directory, `commit-${id}.json`), JSON.stringify(commit), { flag: "wx" });
    }
    await sync.getByRole("button", { name: "预览同步变更", exact: true }).click();
    const conflict = sync.locator(".sync-conflict");
    await expect(conflict).toHaveCount(1);
    await expect(conflict.getByRole("radio")).toHaveCount(3);
    for (const title of ["SYNC local choice", "SYNC remote first", "SYNC remote second"]) {
      await expect(conflict.locator(".sync-metadata")).toContainText([title].map(() => title));
    }
    await expect(sync.getByLabel("我已核对以上变更，并确认应用", { exact: true })).toBeDisabled();
    const selectedVersion = conflict.locator(".sync-version").filter({ hasText: "SYNC remote second" });
    await selectedVersion.getByRole("radio").check();
    await expect(sync.getByRole("button", { name: "应用本次同步", exact: true })).toBeDisabled();

    await page.setViewportSize({ width: 1440, height: 960 });
    await conflict.scrollIntoViewIfNeeded();
    await page.screenshot({ path: "screenshots/sync-conflicts-zh-1440.png", animations: "disabled" });
    await page.setViewportSize({ width: 390, height: 844 });
    await conflict.scrollIntoViewIfNeeded();
    expect(await sync.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
    await expect(selectedVersion.getByRole("radio")).toBeChecked();
    await page.screenshot({ path: "screenshots/sync-conflicts-zh-390.png", animations: "disabled" });
    await sync.getByLabel("我已核对以上变更，并确认应用", { exact: true }).check();
    await sync.getByRole("button", { name: "应用本次同步", exact: true }).click();
    await expect(sync.locator(".notice")).toContainText("同步完成");
    await expect(sync.locator(".sync-backup code")).toContainText("library-sync-");
    const received = await (await request.get(`/bookmark/${bookmarkId}`, { headers })).json();
    expect(received.title).toBe("SYNC remote second");
    expect(received.tags).toEqual(["remote-two", "研发 & 阅读"]);

    // A remote URL edit can make two already-attached records collide. Neither
    // local version is absent, so the explicit duplicate deletion must work.
    const duplicateResponse = await request.post("/admin/library/bookmarks", {
      headers,
      data: { url: `https://sync-ui.example/${randomUUID()}`, title: "SYNC duplicate to remove", folder: "同步测试", tags: [] },
    });
    expect(duplicateResponse.ok()).toBeTruthy();
    const duplicate = await duplicateResponse.json();
    const duplicateId: number = duplicate.bookmark_id;
    remember(duplicateId);
    await sync.getByRole("button", { name: "预览同步变更", exact: true }).click();
    await sync.getByLabel("我已核对以上变更，并确认应用", { exact: true }).check();
    await sync.getByRole("button", { name: "应用本次同步", exact: true }).click();
    await expect(sync.locator(".notice")).toContainText("同步完成");
    const history: Commit[] = await Promise.all((await readdir(directory))
      .filter((name) => name.startsWith("commit-"))
      .map(async (name) => JSON.parse(await readFile(join(directory, name), "utf8")) as Commit));
    const parents = new Set(history.flatMap((commit) => commit.parents));
    const [duplicateSyncId, duplicateRecord] = history.flatMap((commit) => Object.entries(commit.changes))
      .find(([, value]) => value?.url === duplicate.url)!;
    const collisionId = randomUUID();
    await writeFile(join(directory, `commit-${collisionId}.json`), JSON.stringify({
      format: "facetmark-library-sync", version: 1, id: collisionId, device: randomUUID(),
      parents: history.filter((commit) => !parents.has(commit.id)).map((commit) => commit.id),
      changes: { [duplicateSyncId]: { ...duplicateRecord!, url: bookmark.url } },
    } satisfies Commit), { flag: "wx" });
    await sync.getByRole("button", { name: "预览同步变更", exact: true }).click();
    await expect(sync.locator(".sync-conflict")).toHaveCount(2);
    const keep = sync.locator(".sync-conflict").filter({ has: page.locator("legend", { hasText: "SYNC remote second" }) });
    const remove = sync.locator(".sync-conflict").filter({ has: page.locator("legend", { hasText: "SYNC duplicate to remove" }) });
    await keep.getByRole("radio", { name: "保留本机状态", exact: true }).check();
    await remove.getByRole("radio", { name: "删除重复书签 · 无此书签", exact: true }).check();
    await expect(sync.getByRole("button", { name: "应用本次同步", exact: true })).toBeDisabled();
    await remove.getByRole("radio", { name: "删除重复书签 · 无此书签", exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: "screenshots/sync-duplicate-zh-390.png", animations: "disabled" });
    await sync.getByLabel("我已核对以上变更，并确认应用", { exact: true }).check();
    await sync.getByRole("button", { name: "应用本次同步", exact: true }).click();
    await expect(sync.locator(".notice")).toContainText("同步完成");
    expect((await request.get(`/bookmark/${duplicateId}`, { headers })).status()).toBe(404);
    expect((await (await request.get(`/bookmark/${bookmarkId}`, { headers })).json()).title).toBe("SYNC remote second");

    await sync.getByLabel("首次确认后自动同步", { exact: true }).check();
    await sync.getByLabel("检查间隔（秒）", { exact: true }).fill("30");
    await sync.getByRole("button", { name: "保存同步设置", exact: true }).click();
    await expect(sync.locator(".sync-state")).toHaveText("自动同步已启用");
    await sync.getByRole("button", { name: "停用同步", exact: true }).click();
    await expect(sync.locator(".sync-state")).toHaveText("未启用");
    const status = await (await request.get("/admin/library/sync/status", { headers })).json();
    expect(status).toMatchObject({ enabled: false, auto_sync: false, poll_seconds: 30, needs_review: false });
    await page.reload();
    await expect(page).toHaveURL(/#settings\/sync$/);
    await expect(page.getByRole("tab", { name: "设备同步", exact: true })).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#settings-panel-sync")).toBeVisible();
    await expect(page.locator(".sync-settings .sync-state")).toHaveText("未启用");
    await expect(page.getByLabel("共享文件夹完整路径")).toHaveValue(shared);
    await expect(page.getByLabel("启用共享文件夹同步", { exact: true })).not.toBeChecked();
    await expect(page.getByLabel("检查间隔（秒）", { exact: true })).toHaveValue("30");
  });
});

test("sync settings distinguish loading failure and recover through retry", async ({ page }) => {
  let failed = false;
  await page.route("**/admin/library/sync/status", async (route) => {
    if (!failed) {
      failed = true;
      await route.fulfill({ status: 503, json: { detail: "Synthetic status failure" } });
    } else await route.continue();
  });
  await page.goto("/app");
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await page.getByRole("tab", { name: "设备同步", exact: true }).click();
  const sync = page.locator(".sync-settings");
  await expect(sync.getByRole("alert")).toContainText("Synthetic status failure");
  await sync.getByRole("button", { name: "重试读取设置", exact: true }).click();
  await expect(sync.getByRole("alert")).toHaveCount(0);
  await expect(sync.getByLabel("共享文件夹完整路径")).toBeVisible();
});

async function openSync(page: Page) {
  await page.goto("/app#settings/sync");
  await expect(page.locator("#settings-panel-sync")).toBeVisible();
  await expect(page.locator(".sync-state")).toBeVisible();
  return page.locator(".sync-settings");
}
async function configureSync(page: Page, shared: string, wait = true) {
  const sync = await openSync(page);
  await expect(sync.getByLabel("共享文件夹完整路径")).toBeEnabled();
  await sync.getByLabel("共享文件夹完整路径").fill(shared);
  await sync.getByLabel("启用共享文件夹同步", { exact: true }).check();
  await sync.getByLabel("首次确认后自动同步", { exact: true }).uncheck();
  await sync.getByRole("button", { name: "保存同步设置", exact: true }).click();
  if (wait) {
    await expect(sync.locator(".sync-state")).toHaveText("等待首次确认");
    await expect(sync.getByRole("button", { name: "预览同步变更", exact: true })).toBeEnabled();
  }
  return sync;
}
async function createSyncBookmark(request: APIRequestContext, environment: SyncEnvironment, title: string) {
  const response = await request.post("/admin/library/bookmarks", { headers: environment.headers,
    data: { url: `https://sync-recovery.example/${randomUUID()}`, title, folder: "Sync recovery", tags: ["sync"] } });
  expect(response.ok()).toBeTruthy(); const record = await response.json(); environment.remember(record.bookmark_id); return record;
}
async function syncOperations(page: Page) {
  return page.evaluate(() => Object.keys(localStorage).filter(key => key.startsWith("fm-sync-operation:"))
    .map(key => JSON.parse(localStorage.getItem(key)!))) as Promise<SyncOperation[]>;
}
async function syncWorkspace(page: Page) {
  return page.evaluate(() => JSON.parse(localStorage.getItem("fm-sync-workspace") ?? "null")) as Promise<SyncWorkspace | null>;
}
async function interceptSync(page: Page) {
  const control = { writes: [] as { action: "config" | "apply"; body: Record<string, unknown> }[], reads: 0,
    failReads: false, failRefresh: false, lose: "" as "" | "config" | "apply", malformed: false,
    dropBeforeServer: false, hold: null as Promise<void> | null };
  await page.route(/\/admin\/library\/sync\/operations\/[^/?]+$/, async route => {
    control.reads++;
    if (control.failReads) await route.fulfill({ status: 503, json: { detail: "Synthetic sync receipt unavailable" } });
    else await route.continue();
  });
  await page.route("**/bookmarks/facets", route => control.failRefresh
    ? route.fulfill({ status: 503, json: { detail: "Synthetic library refresh unavailable" } }) : route.continue());
  await page.route(/\/admin\/library\/sync\/(?:config|apply)$/, async route => {
    const action = new URL(route.request().url()).pathname.endsWith("config") ? "config" : "apply";
    control.writes.push({ action, body: route.request().postDataJSON() });
    if (control.dropBeforeServer && action === "apply") { control.dropBeforeServer = false; return route.abort("failed"); }
    const response = await route.fetch();
    if (control.hold) await control.hold;
    if (response.ok() && control.lose === action) { control.lose = ""; return route.abort("failed"); }
    if (response.ok() && action === "apply" && control.malformed) {
      control.malformed = false;
      return route.fulfill({ status: response.status(), json: { ...await response.json(), counts: {} } });
    }
    return route.fulfill({ response });
  });
  return control;
}
async function reviewSync(page: Page) {
  const sync = page.locator(".sync-settings");
  await sync.getByRole("button", { name: "预览同步变更", exact: true }).click();
  await expect(sync.locator(".sync-preview")).toBeVisible();
  await sync.getByLabel("我已核对以上变更，并确认应用", { exact: true }).check();
  await expect(sync.getByRole("button", { name: "应用本次同步", exact: true })).toBeEnabled();
}

test("a lost real configuration save keeps its full draft and refresh only reads the original receipt", async ({ page, request, syncEnvironment }) => {
  await createSyncBookmark(request, syncEnvironment, "Configuration recovery page");
  const control = await interceptSync(page); control.lose = "config"; control.failReads = true;
  let release!: () => void; control.hold = new Promise(resolve => { release = resolve; });
  const longFolder = join(syncEnvironment.shared, ...Array.from({ length: 8 }, (_, index) => `saved-${index}-${"shared-folder-".repeat(7)}`));
  await mkdir(longFolder, { recursive: true });
  try {
    await configureSync(page, longFolder, false);
    await expect.poll(() => control.writes.length).toBe(1);
    await expect.poll(async () => (await request.get("/admin/library/sync/status", { headers: syncEnvironment.headers })).json().then(value => value.folder)).toBe(longFolder);
    await expect(page.locator(".sync-recovery")).toHaveCount(0);
  } finally { release(); control.hold = null; }
  const recovery = page.getByRole("complementary", { name: "同步操作恢复" });
  await expect(recovery).toBeVisible(); await expect(recovery.getByRole("button", { name: "读取原操作结果", exact: true })).toBeEnabled();
  const original = structuredClone(control.writes[0]); expect(original.body.expected_revision).toMatch(/^[0-9a-f]{64}$/);
  await page.reload();
  await expect(recovery).toBeVisible(); await expect(recovery.getByRole("button", { name: "读取原操作结果", exact: true })).toBeEnabled();
  expect(control.writes).toEqual([original]);
  await expect(page.getByLabel("共享文件夹完整路径")).toHaveValue(longFolder);
  await recovery.getByText("查看原设置内容", { exact: true }).press("Enter");
  await expect(recovery.locator(".sync-metadata dd").first()).toHaveText(longFolder);
  await page.setViewportSize({ width: 320, height: 568 }); await recovery.scrollIntoViewIfNeeded(); await settleVisualLayout(page);
  expect(await page.locator(".sync-settings").evaluate(element => element.scrollWidth <= element.clientWidth)).toBeTruthy();
  await page.screenshot({ path: "screenshots/sync-original-long-path-zh-320.png", animations: "disabled" });
  control.failReads = false;
  await recovery.getByRole("button", { name: "读取原操作结果", exact: true }).press("Space");
  await expect(recovery).toHaveCount(0); expect(await syncOperations(page)).toEqual([]); expect(control.writes).toEqual([original]);
});

for (const failure of ["lost", "malformed"] as const) test(`a ${failure} real apply response survives refresh without replacing a newer local edit`, async ({ page, request, syncEnvironment }) => {
  test.setTimeout(60000);
  const record = await createSyncBookmark(request, syncEnvironment, "Frozen synchronization title");
  const control = await interceptSync(page); await configureSync(page, syncEnvironment.shared); await reviewSync(page);
  control.failReads = true; control.lose = failure === "lost" ? "apply" : ""; control.malformed = failure === "malformed";
  await page.getByRole("button", { name: "应用本次同步", exact: true }).click();
  const recovery = page.getByRole("complementary", { name: "同步操作恢复" });
  await expect(recovery).toBeVisible(); await expect(recovery.getByRole("button", { name: "读取原操作结果", exact: true })).toBeEnabled();
  const original = structuredClone(control.writes.find(value => value.action === "apply")!);
  expect((await syncOperations(page))[0].confirmed).toBe(false);
  const directory = join(syncEnvironment.shared, ".facetmark-sync"), before = (await readdir(directory)).filter(name => name.startsWith("commit-"));
  expect(before).toHaveLength(1);
  expect((await request.patch(`/admin/library/bookmarks/${record.bookmark_id}`, { headers: syncEnvironment.headers, data: { title: "Newer local title remains" } })).ok()).toBeTruthy();
  const previousReads = control.reads; await page.reload();
  await expect(recovery).toBeVisible(); await expect.poll(() => control.reads).toBeGreaterThan(previousReads);
  await expect(recovery.getByRole("button", { name: "读取原操作结果", exact: true })).toBeEnabled();
  expect(control.writes.filter(value => value.action === "apply")).toEqual([original]);
  control.failReads = false; control.failRefresh = true;
  await recovery.getByRole("button", { name: "读取原操作结果", exact: true }).click();
  await expect(recovery).toContainText("操作已接受");
  await expect.poll(async () => (await syncOperations(page))[0]?.confirmed).toBe(true);
  await expect(recovery.getByRole("button", { name: "读取原操作结果", exact: true })).toBeEnabled();
  control.failRefresh = false; control.failReads = true;
  if (failure === "lost") for (const [language, theme, width, height] of [["zh", "light", 1280, 850], ["en", "dark", 683, 384], ["zh", "dark", 320, 568], ["en", "light", 390, 844]] as const) {
    await page.evaluate(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme });
    await page.setViewportSize({ width, height }); await page.reload();
    const panel = page.locator(".sync-recovery"); await expect(panel).toBeVisible();
    await expect(panel.getByRole("button", { name: language === "zh" ? "读取原操作结果" : "Read original result", exact: true })).toBeEnabled();
    await panel.scrollIntoViewIfNeeded(); await settleVisualLayout(page);
    expect(await page.locator(".sync-settings").evaluate(element => element.scrollWidth <= element.clientWidth)).toBeTruthy();
    expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBeTruthy();
    await page.screenshot({ path: `screenshots/sync-accepted-${language}-${theme}-${width}.png`, animations: "disabled" });
  }
  control.failReads = false;
  await page.locator(".sync-recovery").getByRole("button", { name: /^(读取原操作结果|Read original result)$/ }).click();
  await expect(page.locator(".sync-recovery")).toHaveCount(0);
  expect(await syncOperations(page)).toEqual([]); expect(control.writes.filter(value => value.action === "apply")).toEqual([original]);
  expect((await readdir(directory)).filter(name => name.startsWith("commit-"))).toEqual(before);
  expect((await (await request.get(`/bookmark/${record.bookmark_id}`, { headers: syncEnvironment.headers })).json()).title).toBe("Newer local title remains");
});

test("an unaccepted lost apply only retries its frozen request after an explicit click", async ({ page, request, syncEnvironment }) => {
  await createSyncBookmark(request, syncEnvironment, "Retry synchronization once");
  const control = await interceptSync(page); await configureSync(page, syncEnvironment.shared); await reviewSync(page);
  control.dropBeforeServer = true;
  await page.getByRole("button", { name: "应用本次同步", exact: true }).click();
  await expect(page.locator(".sync-recovery")).toBeVisible();
  await expect(page.getByRole("button", { name: "重试原请求", exact: true })).toBeEnabled();
  const original = structuredClone(control.writes.find(value => value.action === "apply")!);
  expect((await readdir(join(syncEnvironment.shared, ".facetmark-sync"))).filter(name => name.startsWith("commit-"))).toEqual([]);
  await page.reload(); await expect(page.getByRole("button", { name: "重试原请求", exact: true })).toBeEnabled();
  expect(control.writes.filter(value => value.action === "apply")).toEqual([original]);
  await page.getByRole("button", { name: "重试原请求", exact: true }).press("Enter");
  await expect(page.locator(".sync-recovery")).toHaveCount(0);
  expect(control.writes.filter(value => value.action === "apply")).toEqual([original, original]);
  expect((await readdir(join(syncEnvironment.shared, ".facetmark-sync"))).filter(name => name.startsWith("commit-"))).toHaveLength(1);
});

test("a real write-denied shared delivery survives disabling and server-only recovery without rewriting newer local metadata", async ({ page, request, syncEnvironment }) => {
  test.skip(process.platform === "win32", "POSIX write denial is covered here; Windows filesystem failure recovery is covered by isolated backend tests.");
  test.setTimeout(60000);
  const record = await createSyncBookmark(request, syncEnvironment, "Frozen original shared title");
  const control = await interceptSync(page); await configureSync(page, syncEnvironment.shared); await reviewSync(page);
  const directory = join(syncEnvironment.shared, ".facetmark-sync");
  let retries = 0;
  page.on("request", value => { if (value.method() === "POST" && /\/sync\/operations\/[^/]+\/retry$/.test(new URL(value.url()).pathname)) retries++; });
  await chmod(directory, 0o555);
  try {
    await page.getByRole("button", { name: "应用本次同步", exact: true }).click();
    await expect(page.locator(".sync-recovery")).toBeVisible();
    await expect(page.locator(".sync-recovery")).toContainText("操作已接受");
    await expect.poll(async () => (await syncOperations(page))[0]?.confirmed).toBe(true);
    const pending = (await (await request.get("/admin/library/sync/status", { headers: syncEnvironment.headers })).json()).pending_operations;
    expect(pending).toHaveLength(1);
    const originalId = pending[0].request_id;
    await page.getByRole("button", { name: "继续原同步", exact: true }).click();
    await expect(page.getByRole("button", { name: "继续原同步", exact: true })).toBeEnabled();
    expect(retries).toBe(1);
    expect((await readdir(directory)).filter(name => name.startsWith("commit-"))).toEqual([]);
    await page.getByRole("button", { name: "停用同步", exact: true }).click();
    await expect(page.locator(".sync-state")).toHaveText("未启用");
    expect((await (await request.get("/admin/library/sync/status", { headers: syncEnvironment.headers })).json()).pending_operations[0].request_id).toBe(originalId);
    expect((await request.patch(`/admin/library/bookmarks/${record.bookmark_id}`, { headers: syncEnvironment.headers, data: { title: "Newer local title after failed delivery" } })).ok()).toBeTruthy();
    await page.evaluate(() => { for (const key of Object.keys(localStorage)) if (key.startsWith("fm-sync-operation:")) localStorage.removeItem(key); });
    await page.reload();
    await expect(page.getByRole("complementary", { name: "未完成的共享发送" })).toBeVisible();
    expect(retries).toBe(1);
    await chmod(directory, 0o755);
    control.failRefresh = true;
    await page.getByRole("button", { name: "继续原同步", exact: true }).click();
    await expect(page.getByRole("complementary", { name: "同步操作恢复" })).toContainText("操作已接受");
    await expect(page.getByRole("button", { name: "读取原操作结果", exact: true })).toBeEnabled();
    expect((await syncOperations(page))[0]).toMatchObject({ requestId: originalId, confirmed: true, change: { kind: "receipt", action: "apply" } });
    expect(retries).toBe(2);
    const receipt = await (await request.get(`/admin/library/sync/operations/${originalId}`, { headers: syncEnvironment.headers })).json();
    expect(receipt.state).toBe("done");
    const files = (await readdir(directory)).filter(name => name.startsWith("commit-")); expect(files).toHaveLength(1);
    const commit = JSON.parse(await readFile(join(directory, files[0]), "utf8")) as Commit;
    expect(Object.values(commit.changes).find(value => value?.url === record.url)?.title).toBe("Frozen original shared title");
    expect((await (await request.get(`/bookmark/${record.bookmark_id}`, { headers: syncEnvironment.headers })).json()).title).toBe("Newer local title after failed delivery");
    control.failRefresh = false;
    await page.getByRole("button", { name: "读取原操作结果", exact: true }).click();
    await expect(page.locator(".sync-recovery")).toHaveCount(0); expect(await syncOperations(page)).toEqual([]); expect(retries).toBe(2);
    expect(control.writes.filter(value => value.action === "apply")).toHaveLength(1);
  } finally { await chmod(directory, 0o755); }
});

test("reopening a reviewed conflict keeps its exact preview and choice without applying and a changed version requires review again", async ({ page, request, syncEnvironment }) => {
  test.setTimeout(60000);
  const record = await createSyncBookmark(request, syncEnvironment, "Preview baseline title");
  await configureSync(page, syncEnvironment.shared); await reviewSync(page);
  await page.getByRole("button", { name: "应用本次同步", exact: true }).click();
  await expect(page.locator(".sync-preview")).toHaveCount(0);
  const directory = join(syncEnvironment.shared, ".facetmark-sync"), file = (await readdir(directory)).find(name => name.startsWith("commit-"))!;
  const baseline = JSON.parse(await readFile(join(directory, file), "utf8")) as Commit;
  const [sid, baseRecord] = Object.entries(baseline.changes).find(([, value]) => value?.url === record.url)!;
  const cid = randomUUID();
  await writeFile(join(directory, `commit-${cid}.json`), JSON.stringify({ format: "facetmark-library-sync", version: 1,
    id: cid, device: randomUUID(), parents: [baseline.id], changes: { [sid]: { ...baseRecord!, title: "Remote reviewed title" } } } satisfies Commit), { flag: "wx" });
  expect((await request.patch(`/admin/library/bookmarks/${record.bookmark_id}`, { headers: syncEnvironment.headers, data: { title: "Local reviewed title" } })).ok()).toBeTruthy();
  let previews = 0, applies = 0;
  page.on("request", value => {
    if (value.method() !== "POST") return;
    const path = new URL(value.url()).pathname;
    if (path === "/admin/library/sync/preview") previews++;
    if (path === "/admin/library/sync/apply") applies++;
  });
  const sync = page.locator(".sync-settings");
  await sync.getByRole("button", { name: "预览同步变更", exact: true }).click();
  const selected = sync.locator(".sync-version").filter({ hasText: "Remote reviewed title" }).getByRole("radio");
  await selected.check(); await sync.getByLabel("我已核对以上变更，并确认应用", { exact: true }).check();
  const original = (await syncWorkspace(page))!; expect(original.resolutions[sid]).toBe(`remote:${cid}`); expect(original.confirmed).toBe(true);
  await page.reload(); await expect(selected).toBeChecked();
  await expect(sync.getByLabel("我已核对以上变更，并确认应用", { exact: true })).toBeChecked();
  expect((await syncWorkspace(page))!.previewId).toBe(original.previewId); expect(previews).toBe(1); expect(applies).toBe(0);
  expect((await (await request.get(`/bookmark/${record.bookmark_id}`, { headers: syncEnvironment.headers })).json()).title).toBe("Local reviewed title");
  expect((await request.patch(`/admin/library/bookmarks/${record.bookmark_id}`, { headers: syncEnvironment.headers, data: { title: "A different local version" } })).ok()).toBeTruthy();
  await page.reload(); await expect(selected).toBeChecked(); await expect(selected).toBeDisabled();
  await expect(sync.locator(".sync-preview")).toContainText("原预览与选择保留"); expect(previews).toBe(1); expect(applies).toBe(0);
  await sync.getByRole("button", { name: "重新预览", exact: true }).click();
  await expect(selected).not.toBeChecked(); await expect(selected).toBeEnabled();
  await expect(sync.getByLabel("我已核对以上变更，并确认应用", { exact: true })).not.toBeChecked();
  expect((await syncWorkspace(page))!.previewId).not.toBe(original.previewId);
  await selected.check(); await sync.getByLabel("我已核对以上变更，并确认应用", { exact: true }).check();
  await sync.getByRole("button", { name: "应用本次同步", exact: true }).click();
  await expect(sync.locator(".sync-preview")).toHaveCount(0);
  expect(previews).toBe(2); expect(applies).toBe(1);
  expect((await (await request.get(`/bookmark/${record.bookmark_id}`, { headers: syncEnvironment.headers })).json()).title).toBe("Remote reviewed title");
});

test("a configuration changed in another window rejects the old revision and retains the original draft for explicit editing", async ({ page, request, syncEnvironment }) => {
  await createSyncBookmark(request, syncEnvironment, "Configuration comparison page");
  const control = await interceptSync(page), sync = await openSync(page);
  await sync.getByLabel("共享文件夹完整路径").fill(syncEnvironment.shared);
  await sync.getByLabel("启用共享文件夹同步", { exact: true }).check();
  const originalWorkspace = (await syncWorkspace(page))!;
  expect((await request.post("/admin/library/sync/config", { headers: syncEnvironment.headers,
    data: { folder: syncEnvironment.shared, enabled: true, auto_sync: false, poll_seconds: 45, request_id: randomUUID() } })).ok()).toBeTruthy();
  await sync.getByRole("button", { name: "保存同步设置", exact: true }).click();
  await expect(page.locator(".sync-recovery")).toContainText("原请求未被接受");
  await expect(page.getByRole("button", { name: "返回修改同步", exact: true })).toBeEnabled();
  const original = structuredClone(control.writes[0]); expect(original.body.expected_revision).toBe(originalWorkspace.configRevision);
  const other = await (await request.get("/admin/library/sync/status", { headers: syncEnvironment.headers })).json(); expect(other.poll_seconds).toBe(45);
  await page.getByRole("button", { name: "返回修改同步", exact: true }).click();
  await expect(page.locator(".sync-recovery")).toHaveCount(0);
  await expect(sync.getByLabel("共享文件夹完整路径")).toHaveValue(syncEnvironment.shared);
  await expect(sync.getByLabel("检查间隔（秒）", { exact: true })).toHaveValue("60");
  await expect(sync.locator(".sync-current")).toContainText("同步设置已在另一窗口修改");
  await expect(sync.getByRole("button", { name: "保存同步设置", exact: true })).toBeDisabled();
  await sync.getByRole("button", { name: "保留草稿并继续", exact: true }).click();
  await sync.getByLabel("检查间隔（秒）", { exact: true }).fill("90");
  await sync.getByRole("button", { name: "保存同步设置", exact: true }).click();
  await expect.poll(() => control.writes.length).toBe(2);
  await expect(sync.getByRole("button", { name: "预览同步变更", exact: true })).toBeEnabled();
  expect(control.writes[1].body.request_id).not.toBe(original.body.request_id); expect(control.writes[1].body.expected_revision).toBe(other.config_revision);
  expect((await (await request.get("/admin/library/sync/status", { headers: syncEnvironment.headers })).json()).poll_seconds).toBe(90);
  expect(await syncOperations(page)).toEqual([]);
});
