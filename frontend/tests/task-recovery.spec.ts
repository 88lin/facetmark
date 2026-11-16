import { expect, test as base, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import type { Bookmark, Job } from "../src/api";
import type { TaskOperation, TaskReceipt } from "../src/task-local-state";
import { settleVisualLayout } from "./visual-layout";

const prefix = "fm-task-operation:";
const runtimeErrors = new WeakMap<Page, string[]>();
type Owned = { headers: Record<string, string>; create: (title: string) => Promise<Bookmark>; jobs: Set<string> };
const test = base.extend<{ owned: Owned }>({
  owned: async ({ request }, use) => {
    const boot = await request.get("/app/boot"); expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` }, ids = new Set<number>(), jobs = new Set<string>();
    await use({ headers, jobs, create: async title => {
      const response = await request.post("/admin/library/bookmarks", { headers,
        data: { url: `https://task-recovery.example/${randomUUID()}`, title } });
      expect(response.ok()).toBeTruthy(); const value = await response.json() as Bookmark; ids.add(value.bookmark_id); return value;
    } });
    const current = await request.get("/admin/job", { headers }); expect(current.ok()).toBeTruthy();
    const job = await current.json() as Job;
    if (job.state === "running" && job.id && job.run_id && jobs.has(job.id)) {
      expect((await request.post("/admin/jobs/cancel", { headers,
        data: { job_id: job.id, run_id: job.run_id, request_id: randomUUID() } })).ok()).toBeTruthy();
      await expect.poll(async () => (await (await request.get("/admin/job", { headers })).json()).state).not.toBe("running");
    }
    for (const id of ids) expect([200, 404]).toContain((await request.delete(`/admin/library/bookmarks/${id}`, { headers })).status());
  },
});

test.beforeEach(async ({ page }) => {
  const errors: string[] = []; runtimeErrors.set(page, errors);
  page.on("pageerror", error => errors.push(error.message));
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
  expect(runtimeErrors.get(page)).toEqual([]);
});

async function pending(page: Page) {
  return page.evaluate(storagePrefix => Object.keys(localStorage).filter(key => key.startsWith(storagePrefix))
    .map(key => JSON.parse(localStorage.getItem(key)!)), prefix) as Promise<TaskOperation[]>;
}
async function openTasks(page: Page) {
  await page.goto("/app");
  await page.getByRole("button", { name: "任务", exact: true }).click();
}
async function openSetupTasks(page: Page) {
  await page.goto("/app");
  await page.getByRole("button", { name: "导入", exact: true }).click();
  await page.getByRole("button", { name: "打开完整向导", exact: true }).click();
  const steps = page.getByRole("navigation", { name: "设置步骤", exact: true });
  await steps.getByRole("button", { name: /连接模型/ }).click();
  await steps.getByRole("button", { name: /建立索引/ }).click();
}
async function generate(page: Page, title: string, id: number) {
  await page.goto("/app");
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill(title);
  const row = page.locator(`.result-row[data-bookmark-id="${id}"]`); await expect(row).toBeVisible();
  await row.getByRole("checkbox").check();
  await expect(page.getByRole("button", { name: "生成摘要", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "生成摘要", exact: true }).click();
}
async function realTasks(page: Page, owned: Owned) {
  const control = { starts: [] as Record<string, unknown>[], lostResponse: false, dropBeforeServer: false,
    failReceipts: false, failCurrent: false, reads: 0, hold: null as Promise<void> | null };
  await page.route("**/admin/job", route => control.failCurrent
    ? route.fulfill({ status: 503, json: { detail: "Synthetic task status unavailable" } }) : route.continue());
  await page.route(/\/admin\/jobs\/operations\/[^/?]+$/, route => {
    control.reads++;
    return control.failReceipts ? route.fulfill({ status: 503, json: { detail: "Synthetic task acceptance unavailable" } }) : route.continue();
  });
  await page.route("**/admin/jobs/start", async route => {
    control.starts.push(route.request().postDataJSON());
    if (control.dropBeforeServer) { control.dropBeforeServer = false; return route.abort("failed"); }
    const response = await route.fetch(); expect(response.ok()).toBeTruthy();
    const value = await response.json() as Job; expect(value.id).toBeTruthy(); owned.jobs.add(value.id!);
    if (control.hold) await control.hold;
    if (control.lostResponse) { control.lostResponse = false; return route.abort("failed"); }
    return route.fulfill({ response });
  });
  return control;
}

test("a lost real summary start survives refresh and an accepted task only rereads after a status failure", async ({ page, request, owned }) => {
  const title = "task" + randomUUID().replaceAll("-", ""), record = await owned.create(title);
  const control = await realTasks(page, owned); control.lostResponse = true; control.failReceipts = true;
  let release!: () => void; control.hold = new Promise(resolve => { release = resolve; });
  try {
    await generate(page, title, record.bookmark_id);
    await expect.poll(() => control.starts.length).toBe(1);
    await expect.poll(() => owned.jobs.size).toBe(1);
    await expect(page.locator(".task-recovery")).toHaveCount(0);
    await expect(page.locator(".app-shell")).not.toHaveClass(/has-task-recovery/);
  } finally { release(); control.hold = null; }
  const recovery = page.locator(".task-recovery"); await expect(recovery).toBeVisible();
  await expect(recovery.getByRole("button", { name: "读取任务结果", exact: true })).toBeEnabled();
  const original = structuredClone(control.starts[0]); expect(original.bookmark_ids).toEqual([record.bookmark_id]);
  await expect.poll(async () => (await pending(page))[0]?.requestId).toBe(original.request_id);
  const previousReads = control.reads; await page.reload();
  await expect(recovery).toBeVisible(); await expect.poll(() => control.reads).toBeGreaterThan(previousReads);
  await expect(recovery.getByRole("button", { name: "读取任务结果", exact: true })).toBeEnabled();
  expect(control.starts).toEqual([original]);
  control.failReceipts = false; control.failCurrent = true;
  await recovery.getByRole("button", { name: "读取任务结果", exact: true }).click();
  await expect(recovery).toContainText("操作已接受");
  await expect(recovery.getByRole("button", { name: "继续原任务请求", exact: true })).toHaveCount(0);
  await expect.poll(async () => (await pending(page))[0]?.confirmed).toBe(true);
  await expect.poll(async () => {
    const saved = await request.get(`/bookmark/${record.bookmark_id}?body=true`, { headers: owned.headers });
    expect(saved.ok()).toBeTruthy(); return (await saved.json()).summary;
  }).toBeTruthy();
  control.failCurrent = false;
  await expect(recovery.getByRole("button", { name: "读取任务结果", exact: true })).toBeEnabled();
  await recovery.getByRole("button", { name: "读取任务结果", exact: true }).click();
  await expect(recovery).toHaveCount(0); expect(await pending(page)).toEqual([]); expect(control.starts).toEqual([original]);
  const accepted = await request.get(`/admin/jobs/operations/${original.request_id}`, { headers: owned.headers });
  expect(accepted.ok()).toBeTruthy(); expect((await accepted.json()).result.params.bookmark_ids).toEqual([record.bookmark_id]);
});

test("an unaccepted network failure retries the original selection and request ID after changing the visible query", async ({ page, owned }) => {
  const title = "task" + randomUUID().replaceAll("-", ""), record = await owned.create(title);
  const control = await realTasks(page, owned); control.dropBeforeServer = true;
  await generate(page, title, record.bookmark_id);
  const recovery = page.locator(".task-recovery"); await expect(recovery).toBeVisible();
  const original = structuredClone(control.starts[0]);
  await expect(recovery.getByRole("button", { name: "继续原任务请求", exact: true })).toBeEnabled();
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill("a different visible query");
  await recovery.getByRole("button", { name: "继续原任务请求", exact: true }).click();
  await expect(recovery).toHaveCount(0); expect(control.starts).toEqual([original, original]);
  expect(original.bookmark_ids).toEqual([record.bookmark_id]); expect(owned.jobs.size).toBe(1); expect(await pending(page)).toEqual([]);
});

async function controlled(page: Page) {
  const control = { job: { id: "abcdef123456", run_id: "original-run", state: "running", params: { mode: "summarize" },
    items: { total: 4, done: 1, failed: 0 }, log: [], pause_requested: false, cancel_requested: false } as Job,
    writes: [] as { action: string; body: Record<string, unknown> }[], receipts: new Map<string, TaskReceipt>(),
    reads: 0, failReceipts: false, lostResponse: false, rejectNext: false, hold: null as Promise<void> | null };
  await page.route("**/admin/job", route => route.fulfill({ json: control.job }));
  await page.route("**/admin/jobs", route => route.fulfill({ json: { items: [] } }));
  await page.route(/\/admin\/jobs\/operations\/[^/?]+$/, route => {
    control.reads++; const id = new URL(route.request().url()).pathname.split("/").at(-1)!;
    if (control.failReceipts) return route.fulfill({ status: 503, json: { detail: "Synthetic control receipt unavailable" } });
    return control.receipts.has(id) ? route.fulfill({ json: control.receipts.get(id) })
      : route.fulfill({ status: 404, json: { detail: "No accepted synthetic task request" } });
  });
  await page.route(/\/admin\/jobs\/(pause|cancel)$/, async route => {
    const body = route.request().postDataJSON(), action = new URL(route.request().url()).pathname.split("/").at(-1)!;
    control.writes.push({ action, body });
    if (control.rejectNext) { control.rejectNext = false; return route.fulfill({ status: 409, json: { detail: "Synthetic original run stopped" } }); }
    expect(body.job_id).toBe(control.job.id); expect(body.run_id).toBe(control.job.run_id);
    control.job = { ...control.job, pause_requested: action === "pause", cancel_requested: action === "cancel" };
    const job = structuredClone(control.job), result = action === "cancel" ? { cancel_requested: true, job } : job;
    control.receipts.set(body.request_id, { request_id: body.request_id, action, job_id: job.id!, run_id: job.run_id!, result, job });
    if (control.hold) await control.hold;
    if (control.lostResponse) { control.lostResponse = false; return route.abort("failed"); }
    return route.fulfill({ json: result });
  });
  return control;
}

for (const action of ["pause", "cancel"] as const) test("rapid " + action + " sends one control bound to the original run", async ({ page }) => {
  const control = await controlled(page);
  let release!: () => void; control.hold = new Promise(resolve => { release = resolve; });
  await openTasks(page); const button = page.getByRole("button", { name: action === "pause" ? "暂停任务" : "取消任务", exact: true });
  try {
    await expect(button).toBeEnabled();
    await button.evaluate(element => { (element as HTMLButtonElement).click(); (element as HTMLButtonElement).click(); });
    await expect.poll(() => control.writes.length).toBe(1);
    expect(control.writes[0]).toEqual({ action, body: { job_id: "abcdef123456", run_id: "original-run", request_id: expect.any(String) } });
    await expect(page.locator(".task-recovery")).toHaveCount(0);
    control.job = { ...control.job, run_id: "newer-run", pause_requested: false, cancel_requested: false };
  } finally { release(); control.hold = null; }
  await expect(page.getByRole("button", { name: "取消任务", exact: true })).toBeEnabled();
  expect(control.writes).toHaveLength(1); expect(await pending(page)).toEqual([]);
  expect(control.job.pause_requested).toBe(false); expect(control.job.cancel_requested).toBe(false);
});

test("refresh settles an accepted original control without sending it to a newer run", async ({ page }) => {
  const control = await controlled(page); control.lostResponse = true; control.failReceipts = true;
  await openTasks(page); await page.getByRole("button", { name: "暂停任务", exact: true }).click();
  const recovery = page.locator(".task-recovery"); await expect(recovery).toBeVisible();
  control.job = { ...control.job, run_id: "newer-run", pause_requested: false, cancel_requested: false };
  await page.reload(); await expect(recovery).toBeVisible();
  await expect(recovery.getByRole("button", { name: "继续原任务请求", exact: true })).toBeEnabled();
  expect(control.writes).toHaveLength(1); control.failReceipts = false;
  await recovery.getByRole("button", { name: "继续原任务请求", exact: true }).click();
  await expect(recovery).toHaveCount(0); expect(control.writes).toHaveLength(1);
  expect(control.job.run_id).toBe("newer-run"); expect(control.job.pause_requested).toBe(false);
});

test("a refusal survives receipt failure and revising rechecks whether another window accepted it", async ({ page }) => {
  const control = await controlled(page); control.rejectNext = true; control.failReceipts = true;
  await openTasks(page); await page.getByRole("button", { name: "暂停任务", exact: true }).click();
  const recovery = page.locator(".task-recovery"); await expect(recovery).toBeVisible();
  await expect.poll(async () => (await pending(page))[0]?.refused).toBe(true);
  await page.reload(); await expect(recovery).toBeVisible();
  await expect(recovery.getByRole("button", { name: "返回修改任务", exact: true })).toHaveCount(0);
  control.failReceipts = false;
  await expect(recovery.getByRole("button", { name: "读取任务结果", exact: true })).toBeEnabled();
  await recovery.getByRole("button", { name: "读取任务结果", exact: true }).click();
  await expect(recovery.getByRole("button", { name: "返回修改任务", exact: true })).toBeEnabled();
  const requestId = (await pending(page))[0].requestId, oldJob = { ...control.job, pause_requested: true };
  control.receipts.set(requestId, { request_id: requestId, action: "pause", job_id: oldJob.id!, run_id: oldJob.run_id!, result: oldJob, job: oldJob });
  control.job = { ...control.job, run_id: "newer-run", pause_requested: false };
  const reads = control.reads;
  await recovery.getByRole("button", { name: "返回修改任务", exact: true }).click();
  await expect(recovery).toHaveCount(0); expect(control.reads).toBe(reads + 1); expect(control.writes).toHaveLength(1);
  expect(await pending(page)).toEqual([]); expect(control.job.pause_requested).toBe(false);
});

for (const entry of ["tasks", "setup"] as const) test("an unresolved original start still allows cancelling the visible current run from " + entry, async ({ page }) => {
  const original: TaskOperation = { version: 1, requestId: "unconfirmed-original-start", createdAt: Date.now(), confirmed: false,
    change: { kind: "start", values: { mode: "summarize", confirmed: true, bookmark_ids: [17], force: true } } };
  await page.addInitScript(({ original, prefix }) => localStorage.setItem(prefix + original.requestId, JSON.stringify(original)), { original, prefix });
  const control = await controlled(page); control.failReceipts = true;
  await (entry === "setup" ? openSetupTasks(page) : openTasks(page));
  const recovery = page.locator(".task-recovery"); await expect(recovery).toBeVisible();
  await expect(recovery.getByRole("button", { name: "读取任务结果", exact: true })).toBeEnabled();
  await expect(page.getByRole("button", { name: "暂停任务", exact: true })).toBeDisabled();
  const cancel = page.getByRole("button", { name: "取消任务", exact: true }); await expect(cancel).toBeEnabled();
  await cancel.click(); await expect(cancel).toBeDisabled();
  await expect.poll(() => control.writes.length).toBe(1);
  expect(control.writes[0]).toEqual({ action: "cancel", body: { job_id: "abcdef123456", run_id: "original-run", request_id: expect.any(String) } });
  await expect.poll(async () => (await pending(page)).map(value => value.requestId)).toEqual([original.requestId]);
  expect((await pending(page))[0].change).toEqual(original.change);
  expect(control.job.cancel_requested).toBe(true); await expect(recovery).toBeVisible();
});

test("revising a refused selected fetch preserves its explicit choice to retain completed content", async ({ page, owned }) => {
  const title = "task" + randomUUID().replaceAll("-", ""), record = await owned.create(title);
  const original: TaskOperation = { version: 1, requestId: "refused-fetch-request", createdAt: Date.now(), confirmed: false, refused: true,
    change: { kind: "start", values: { mode: "fetch", confirmed: false, bookmark_ids: [record.bookmark_id], scope: { q: title }, force: false } } };
  await page.addInitScript(({ original, prefix }) => localStorage.setItem(prefix + original.requestId, JSON.stringify(original)), { original, prefix });
  const starts: Record<string, unknown>[] = [];
  await page.route("**/admin/jobs/start", route => {
    starts.push(route.request().postDataJSON());
    return route.fulfill({ json: { id: "synthetic-revised-fetch", run_id: "synthetic-revised-run", state: "done", params: starts[0] } });
  });
  await page.goto("/app"); const recovery = page.locator(".task-recovery");
  await expect(recovery.getByRole("button", { name: "返回修改任务", exact: true })).toBeEnabled();
  await recovery.getByRole("button", { name: "返回修改任务", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "提取网页正文", exact: true });
  await expect(dialog).toBeVisible(); await expect(dialog).toContainText("已完成且未变化的内容会跳过");
  await expect(dialog.getByRole("button", { name: "开始任务", exact: true })).toBeEnabled();
  expect(starts).toHaveLength(0);
  await dialog.getByRole("button", { name: "开始任务", exact: true }).click();
  await expect(dialog).toHaveCount(0); await expect.poll(() => starts.length).toBe(1);
  expect(starts[0]).toMatchObject({ mode: "fetch", force: false, confirmed: false, bookmark_ids: [record.bookmark_id], scope: { q: title } });
  expect(starts[0].request_id).not.toBe(original.requestId); expect(await pending(page)).toEqual([]);
});

test("long original scopes remain complete and all recovery controls stay reachable in narrow and short windows", async ({ page }) => {
  test.setTimeout(120_000);
  const query = "保留原来的完整关键词和阅读问题。 Keep the original reading query and context. ".repeat(25);
  const original: TaskOperation = { version: 1, requestId: "long-original-task", createdAt: Date.now(), confirmed: false, refused: true,
    change: { kind: "start", values: { mode: "summarize", confirmed: true, force: false,
      scope: { folder: "原来的文件夹 / Original folder", q: query, status: "pending", session: 17, exclude_ids: [23, 24] } } } };
  let writes = 0;
  await page.route(/\/admin\/jobs\/(start|resume|pause|cancel)$/, route => { writes++; return route.fulfill({ status: 409, json: { detail: "No model work is allowed in this layout scenario" } }); });
  await page.addInitScript(({ original, prefix }) => { if (!localStorage.getItem(prefix + original.requestId)) localStorage.setItem(prefix + original.requestId, JSON.stringify(original)); }, { original, prefix });
  await page.goto("/app"); await page.emulateMedia({ reducedMotion: "reduce" });
  for (const language of ["zh", "en"] as const) for (const theme of ["light", "dark"] as const) {
    await page.evaluate(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme });
    await page.reload(); const recovery = page.locator(".task-recovery"); await expect(recovery).toBeVisible();
    const reviseName = language === "zh" ? "返回修改任务" : "Revise task";
    await expect(recovery.getByRole("button", { name: reviseName, exact: true })).toBeEnabled();
    const detail = recovery.locator("details.task-recovery-scope"), summary = detail.locator("summary");
    await summary.focus(); await summary.press("Enter"); await expect(detail).toHaveAttribute("open", "");
    await expect(detail.locator("p")).toContainText(query);
    await expect(detail.locator("p")).toContainText(language === "zh" ? "排除 2 条收藏" : "2 bookmarks excluded");
    for (const size of [{ width: 1280, height: 850 }, { width: 390, height: 844 }, { width: 320, height: 640 }, { width: 683, height: 384 }]) {
      await page.setViewportSize(size); await settleVisualLayout(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const bounds = await recovery.boundingBox(); expect(bounds).not.toBeNull();
      expect(bounds!.y).toBeGreaterThanOrEqual(0); expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(size.height);
      expect((await page.locator(".main-workspace").boundingBox())!.height).toBeGreaterThan(48);
      for (const button of await recovery.locator(".task-recovery-actions button").all()) {
        await button.focus(); const box = await button.boundingBox(); expect(box).not.toBeNull();
        expect(box!.height).toBeGreaterThanOrEqual(44); expect(box!.y).toBeGreaterThanOrEqual(0);
        expect(box!.y + box!.height).toBeLessThanOrEqual(size.height);
      }
      await page.screenshot({ path: `screenshots/collection-review/task-recovery-${language}-${theme}-${size.width}-${size.height}.png`, animations: "disabled" });
    }
    const read = recovery.getByRole("button", { name: language === "zh" ? "读取任务结果" : "Read task result", exact: true });
    await read.focus(); await read.press("Space"); await expect(read).toBeEnabled();
    expect(writes).toBe(0); expect((await pending(page))[0].change).toEqual(original.change);
  }
});
