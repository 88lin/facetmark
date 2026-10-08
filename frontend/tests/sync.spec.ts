import { expect, test, type APIRequestContext } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve, sep } from "node:path";

type RecordValue = { url: string; title: string; folder: string; tags: string[]; date_added: number | null };
type Commit = {
  format: string; version: number; id: string; device: string; parents: string[];
  changes: Record<string, RecordValue | null>;
};

async function authenticated(request: APIRequestContext) {
  const boot = await request.get("/app/boot");
  expect(boot.ok()).toBeTruthy();
  const { token } = await boot.json();
  return { Authorization: `Bearer ${token}` };
}

test.beforeEach(async ({ page }) => {
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort(),
  );
});

test.beforeAll(async () => {
  await mkdir("screenshots", { recursive: true });
});

test("shared-folder sync reviews actual changes, rejects a stale preview and resolves concurrent versions", async ({ page, request }) => {
  test.setTimeout(60000);
  const shared = await mkdtemp(join(tmpdir(), "facetmark-ui-sync-"));
  const headers = await authenticated(request);
  let bookmarkId: number | undefined;
  let duplicateId: number | undefined;
  try {
    const saved = await request.post("/admin/library/bookmarks", {
      headers,
      data: { url: `https://sync-ui.example/${randomUUID()}`, title: "SYNC initial title", folder: "同步测试", tags: ["local"] },
    });
    expect(saved.ok()).toBeTruthy();
    const bookmark = await saved.json();
    bookmarkId = bookmark.bookmark_id;

    await page.goto("/app");
    await page.getByRole("button", { name: "设置", exact: true }).click();
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
    await expect(sync.locator(".sync-preview")).toHaveCount(0);
    expect((await readdir(join(shared, ".facetmark-sync"))).filter((name) => name.startsWith("commit-"))).toHaveLength(0);

    await sync.getByRole("button", { name: "预览同步变更", exact: true }).click();
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
    duplicateId = duplicate.bookmark_id;
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
    await page.getByRole("button", { name: "设置", exact: true }).click();
    await expect(page.locator(".sync-settings .sync-state")).toHaveText("未启用");
    await expect(page.getByLabel("共享文件夹完整路径")).toHaveValue(shared);
  } finally {
    await request.post("/admin/library/sync/config", {
      headers, data: { folder: "", enabled: false, auto_sync: false, poll_seconds: 60 },
    });
    if (bookmarkId !== undefined) await request.delete(`/admin/library/bookmarks/${bookmarkId}`, { headers });
    if (duplicateId !== undefined) await request.delete(`/admin/library/bookmarks/${duplicateId}`, { headers });
    const resolved = resolve(shared);
    if (!resolved.startsWith(resolve(tmpdir()) + sep) || !resolved.includes("facetmark-ui-sync-")) {
      throw new Error("Refusing cleanup outside the test-created temporary shared folder");
    }
    await rm(resolved, { recursive: true, force: true });
  }
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
  const sync = page.locator(".sync-settings");
  await expect(sync.getByRole("alert")).toContainText("Synthetic status failure");
  await sync.getByRole("button", { name: "重试读取设置", exact: true }).click();
  await expect(sync.getByRole("alert")).toHaveCount(0);
  await expect(sync.getByLabel("共享文件夹完整路径")).toBeVisible();
});
