import { expect, test as base, type APIRequestContext, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { healthRequest, type HealthOperation, type HealthRun } from "../src/health-local-state";
import { settleVisualLayout } from "./visual-layout";

type Owned = { request: APIRequestContext; headers: Record<string, string>; ids: Set<string>; fixture: (hold: boolean, reset?: boolean) => Promise<void>; calls: () => Promise<number> };
const test = base.extend<{ owned: Owned }>({
  owned: [async ({ playwright, baseURL }, use) => {
    const request = await playwright.request.newContext({ baseURL, timeout: 5000 });
    const boot = await request.get("/app/boot"); expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` }, ids = new Set<string>();
    const fixture = async (hold: boolean, reset = false) => {
      const response = await request.post("/__fixture/health", { headers, data: { hold, reset } }); expect(response.ok()).toBeTruthy();
    };
    const calls = async () => {
      const response = await request.get("/__fixture/health", { headers }); expect(response.ok()).toBeTruthy(); return (await response.json()).requests.length as number;
    };
    try {
      await fixture(false, true); await use({ request, headers, ids, fixture, calls });
    } finally {
      try {
        const response = await request.get("/link-health/runs/current", { headers }); expect(response.ok()).toBeTruthy();
        const current = (await response.json()).run as HealthRun | null;
        if (current && ["running", "stopping"].includes(current.state)) {
          if (!ids.has(current.request_id)) throw new Error("Refusing to stop another test's link check");
          expect((await request.post(`/link-health/runs/${current.request_id}/stop`, { headers })).ok()).toBeTruthy();
          await expect.poll(async () => (await (await request.get(`/link-health/runs/${current.request_id}`, { headers })).json()).state)
            .not.toMatch(/^(running|stopping)$/);
        }
        await fixture(false);
      } finally { await request.dispose(); }
    }
  }, { timeout: 30000 }],
});
const failures = new WeakMap<Page, string[]>();
test.beforeEach(async ({ page }) => {
  const errors: string[] = []; failures.set(page, errors); page.on("pageerror", error => errors.push(error.message));
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});
test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); expect(failures.get(page)).toEqual([]); });
const health = (page: Page) => page.locator(".health-tools");
const recovery = (page: Page) => page.locator(".health-recovery");
async function pending(page: Page) {
  return page.evaluate(() => Object.keys(localStorage).filter(key => key.startsWith("fm-health-operation:"))
    .map(key => JSON.parse(localStorage.getItem(key)!))) as Promise<HealthOperation[]>;
}
async function open(page: Page, waitForResults = true) {
  await page.goto("/app");
  const navigation = page.getByRole("button", { name: /^(打开导航|Open navigation)$/, exact: true });
  if (await navigation.isVisible()) {
    await navigation.press("Enter");
    await expect(page.getByRole("dialog", { name: /^(导航|Navigation)$/, exact: true })).toBeVisible();
  }
  await page.getByRole("button", { name: /^(任务|Tasks)$/, exact: true }).click();
  const details = health(page);
  if (!await details.getAttribute("open")) {
    // The open attribute is an empty string when present.
    if (!(await details.evaluate(element => (element as HTMLDetailsElement).open))) await details.locator(":scope > summary").press("Enter");
  }
  if (waitForResults) await expect(details.locator(".health-saved-summary")).toBeVisible();
}
async function stableCalls(owned: Owned) {
  let prior = -1;
  await expect.poll(async () => { const count = await owned.calls(); const result = count === prior ? count : -1; prior = count; return result; }, { intervals: [50, 100, 150] }).toBeGreaterThan(0);
  return prior;
}
async function intercept(page: Page, owned: Owned) {
  const control = { writes: [] as Record<string, unknown>[], stops: [] as string[], closes: [] as Record<string, unknown>[], lost: false,
    malformed: false, dropBeforeServer: false, failCurrent: false, malformedCurrent: false, failReceipt: false, rejectStop: false, lostStop: false };
  await page.route("**/link-health/check", async route => {
    const body = route.request().postDataJSON(); control.writes.push(body); owned.ids.add(body.request_id);
    if (control.dropBeforeServer) { control.dropBeforeServer = false; return route.abort("failed"); }
    const response = await route.fetch();
    if (response.ok() && control.lost) { control.lost = false; return route.abort("failed"); }
    if (response.ok() && control.malformed) { control.malformed = false; return route.fulfill({ status: 200, json: {} }); }
    return route.fulfill({ response });
  });
  await page.route("**/link-health/runs/current", route => control.failCurrent
    ? route.fulfill({ status: 503, json: { detail: "Synthetic link check status unavailable" } })
    : control.malformedCurrent ? route.fulfill({ status: 200, json: {} }) : route.continue());
  await page.route(/\/link-health\/runs\/(?!current$)[^/?]+$/, route => control.failReceipt
    ? route.fulfill({ status: 503, json: { detail: "Synthetic original link receipt unavailable" } }) : route.continue());
  await page.route(/\/link-health\/runs\/[^/?]+\/stop$/, async route => {
    control.stops.push(new URL(route.request().url()).pathname);
    if (control.rejectStop) return route.fulfill({ status: 503, json: { detail: "Synthetic stop not accepted" } });
    const response = await route.fetch();
    if (response.ok() && control.lostStop) { control.lostStop = false; return route.abort("failed"); }
    return route.fulfill({ response });
  });
  await page.route(/\/link-health\/runs\/[^/?]+\/close$/, route => { control.closes.push(route.request().postDataJSON()); return route.continue(); });
  return control;
}

for (const failure of ["lost", "malformed"] as const) test(`a ${failure} real check response survives navigation and refresh, then stops that same run`, async ({ page, owned }) => {
  test.setTimeout(120000);
  await owned.fixture(true); const control = await intercept(page, owned); await open(page);
  expect(await owned.calls()).toBe(0);
  await health(page).getByRole("combobox", { name: "链接检查数量", exact: true }).selectOption("50");
  control.failCurrent = true; control.failReceipt = true; control.lost = failure === "lost"; control.malformed = failure === "malformed";
  await health(page).getByRole("button", { name: "检查链接", exact: true }).evaluate(button => {
    (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click();
  });
  await expect(recovery(page)).toBeVisible(); const [original] = await pending(page);
  expect(original.limit).toBe(50); expect(control.writes).toEqual([healthRequest(original)]);
  const count = await stableCalls(owned);
  await page.getByRole("button", { name: "返回收藏", exact: true }).click(); await open(page);
  await expect(recovery(page)).toBeVisible(); await page.reload(); await open(page);
  await expect(recovery(page)).toBeVisible(); expect(control.writes).toEqual([healthRequest(original)]); expect(await owned.calls()).toBe(count);
  await expect(recovery(page).getByRole("button", { name: "继续原检查", exact: true })).toHaveCount(0);

  if (failure === "lost") for (const language of ["zh", "en"] as const) for (const theme of ["light", "dark"] as const)
    for (const [width, height] of [[1280, 850], [320, 640], [683, 384]] as const) {
      await page.evaluate(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme });
      await page.setViewportSize({ width, height }); await open(page);
      await expect(recovery(page)).toBeVisible();
      const read = recovery(page).getByRole("button", { name: language === "zh" ? "读取原检查" : "Read original check", exact: true });
      await read.scrollIntoViewIfNeeded(); await expect(read).toBeInViewport({ ratio: 1 }); await settleVisualLayout(page);
      expect(await health(page).evaluate(element => element.scrollWidth <= element.clientWidth)).toBeTruthy();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
      await page.screenshot({ path: `screenshots/collection-review/health-recovery-${language}-${theme}-${width}-${height}.png`, animations: "disabled" });
    }

  control.failCurrent = control.failReceipt = false;
  await recovery(page).getByRole("button", { name: /^(读取原检查|Read original check)$/ }).press("Enter");
  await expect(recovery(page)).toHaveCount(0); await expect(health(page).locator(".health-running")).toBeVisible();
  await expect(health(page).getByRole("combobox", { name: /^(链接检查数量|Link check limit)$/ })).toHaveValue("50");
  expect(control.writes).toEqual([healthRequest(original)]); expect(await owned.calls()).toBe(count);
  await health(page).getByRole("button", { name: /^(停止检查|Stop check)$/ }).press("Space");
  await expect(health(page).locator(".health-run-notice")).toContainText(/检查已停止|The check stopped/);
  expect(control.stops).toEqual([`/link-health/runs/${original.requestId}/stop`]); expect(await pending(page)).toEqual([]);
});

test("an unaccepted original retries its frozen limit only after a click and its completed result survives reopening", async ({ page, owned }) => {
  test.setTimeout(60000); const control = await intercept(page, owned); await owned.fixture(true); await open(page);
  await health(page).getByRole("combobox", { name: "链接检查数量", exact: true }).selectOption("50");
  control.dropBeforeServer = true;
  await health(page).getByRole("button", { name: "检查链接", exact: true }).click();
  await expect(recovery(page).getByRole("button", { name: "继续原检查", exact: true })).toBeEnabled();
  const [original] = await pending(page); expect(await owned.calls()).toBe(0);
  await open(page); await expect(recovery(page).getByRole("button", { name: "继续原检查", exact: true })).toBeEnabled();
  expect(control.writes).toEqual([healthRequest(original)]); expect(await owned.calls()).toBe(0);
  await recovery(page).getByRole("button", { name: "继续原检查", exact: true }).press("Space");
  await expect(health(page).locator(".health-running")).toBeVisible(); expect(control.writes).toEqual([healthRequest(original), healthRequest(original)]);
  await stableCalls(owned); await owned.fixture(false);
  await expect(health(page).locator(".health-latest")).toContainText("检查了 50 条链接", { timeout: 20000 });
  expect(await pending(page)).toEqual([]);
  const count = await owned.calls(); await open(page);
  await expect(health(page).locator(".health-latest")).toContainText("检查了 50 条链接");
  expect(control.writes).toHaveLength(2); expect(await owned.calls()).toBe(count);
});

test("returning from an absent original closes its ID and a late direct request visits no URLs", async ({ page, owned }) => {
  const control = await intercept(page, owned); await open(page); control.dropBeforeServer = true;
  await health(page).getByRole("button", { name: "检查链接", exact: true }).click();
  await expect(recovery(page).getByRole("button", { name: "返回已保存结果", exact: true })).toBeEnabled();
  const [original] = await pending(page), body = healthRequest(original), count = await owned.calls();
  let releaseClose!: () => void;
  const closeGate = new Promise<void>(resolve => { releaseClose = resolve; });
  await page.route(/\/link-health\/runs\/[^/?]+\/close$/, async route => {
    control.closes.push(route.request().postDataJSON());
    const response = await route.fetch();
    await closeGate;
    await route.fulfill({ response });
  });
  try {
    await recovery(page).getByRole("button", { name: "返回已保存结果", exact: true }).click();
    await expect.poll(() => control.closes).toEqual([body]);
    await expect(recovery(page)).toBeVisible();
    await expect(recovery(page)).toHaveAttribute("aria-busy", "true");
    await expect(recovery(page).getByRole("status")).toContainText("正在关闭原检查请求");
    expect(await pending(page)).toEqual([original]);
    for (const name of ["读取原检查", "继续原检查", "返回已保存结果"]) {
      const button = recovery(page).getByRole("button", { name, exact: true });
      await expect(button).toBeDisabled();
      await button.evaluate(element => (element as HTMLButtonElement).click());
    }
    expect(control.closes).toEqual([body]); expect(control.writes).toEqual([body]);
    await page.screenshot({ path: "screenshots/collection-review/health-closing-original.png", animations: "disabled" });
    releaseClose();
    await expect(recovery(page)).toHaveCount(0); expect(await pending(page)).toEqual([]); expect(control.closes).toEqual([body]);
    const late = await owned.request.post("/link-health/check", { headers: owned.headers, data: body });
    expect(late.status()).toBe(409); expect(await owned.calls()).toBe(count); expect(control.writes).toEqual([body]);
  } finally { releaseClose(); }
});

test("another local library's unresolved original stays stored and is not sent to this collection", async ({ page, owned }) => {
  const control = await intercept(page, owned); await open(page);
  const other = { version: 1, requestId: "health-other-local-library", createdAt: 10, limit: 500, libraryId: "0".repeat(64) };
  await page.evaluate(original => localStorage.setItem("fm-health-operation:" + original.requestId, JSON.stringify(original)), other);
  await open(page); await expect(health(page).getByRole("button", { name: "检查链接", exact: true })).toBeEnabled();
  expect(control.writes).toEqual([]); expect(await pending(page)).toEqual([other]); expect(await owned.calls()).toBe(0);
});

test("an active link check blocks new processing while collection selection, reading and local editing remain usable", async ({ page, owned }) => {
  await owned.fixture(true); const control = await intercept(page, owned); await open(page);
  await health(page).getByRole("button", { name: "检查链接", exact: true }).click();
  await expect(health(page).locator(".health-running")).toBeVisible(); await stableCalls(owned);
  await page.getByRole("button", { name: "返回收藏", exact: true }).click();
  await expect(page.locator(".library-summarize")).toBeDisabled();
  await expect(page.locator(".library-add")).toBeEnabled();
  const row = page.locator(".result-row").first();
  await expect(row.locator(".bookmark-check")).toBeEnabled();
  await row.locator(".bookmark-check").check();
  await row.locator(".bookmark-preview").click();
  await expect(page.locator(".reader-edit")).toBeEnabled();
  await expect(page.locator(".reader-manage-actions .secondary").first()).toBeDisabled();
  await open(page);
  await health(page).getByRole("button", { name: "停止检查", exact: true }).click();
  await expect(health(page).locator(".health-run-notice")).toContainText("检查已停止");
  expect(control.writes).toHaveLength(1);
});

test("malformed current state retains the original and cannot trigger another check", async ({ page, owned }) => {
  await owned.fixture(true); const control = await intercept(page, owned); await open(page);
  control.lost = true; control.malformedCurrent = true;
  await health(page).getByRole("button", { name: "检查链接", exact: true }).click();
  await expect(recovery(page)).toBeVisible(); const originals = await pending(page);
  await recovery(page).getByRole("button", { name: "读取原检查", exact: true }).click();
  await expect(health(page).getByRole("alert")).toContainText("无法确认");
  expect(await pending(page)).toEqual(originals); expect(control.writes).toHaveLength(1);
  control.malformedCurrent = false;
  await recovery(page).getByRole("button", { name: "读取原检查", exact: true }).click();
  await expect(health(page).locator(".health-running")).toBeVisible();
  await health(page).getByRole("button", { name: "停止检查", exact: true }).click();
  await expect(health(page).locator(".health-run-notice")).toContainText("检查已停止");
});

test("a slow status read is not repeatedly cancelled by polling and visits no URLs", async ({ page, owned }) => {
  const control = await intercept(page, owned); await page.clock.install();
  let release!: () => void, reads = 0;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/link-health/runs/current", async route => {
    reads++; await held;
    const response = await route.fetch(); return route.fulfill({ response });
  });
  try {
    await open(page, false); await expect.poll(() => reads).toBe(1);
    await expect(health(page).locator(".health-saved-summary")).toHaveCount(0);
    await page.clock.runFor(7_000);
    expect(reads).toBe(1);
    await expect(health(page).getByRole("button", { name: "检查链接", exact: true })).toBeDisabled();
    release();
    await expect(health(page).getByRole("button", { name: "检查链接", exact: true })).toBeEnabled();
    await expect(health(page).locator(".health-saved-summary")).toBeVisible();
    expect(control.writes).toEqual([]); expect(await owned.calls()).toBe(0);
  } finally { release(); }
});

test("a failed local original save keeps its error through refresh and requires an explicit retry", async ({ page, owned }) => {
  const control = await intercept(page, owned); await page.clock.install(); await open(page);
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    (window as unknown as { restoreHealthStorage: () => void }).restoreHealthStorage = () => { Storage.prototype.setItem = original; };
    Storage.prototype.setItem = function (key, value) {
      if (key.startsWith("fm-health-operation:")) throw new DOMException("Synthetic health storage full", "QuotaExceededError");
      return original.call(this, key, value);
    };
  });
  await health(page).getByRole("button", { name: "检查链接", exact: true }).click();
  await expect(health(page).getByRole("alert")).toContainText("Synthetic health storage full");
  await page.clock.runFor(7_000);
  await health(page).getByRole("button", { name: "刷新已保存结果", exact: true }).click();
  await expect(health(page).getByRole("alert")).toContainText("Synthetic health storage full");
  expect(control.writes).toEqual([]); expect(await owned.calls()).toBe(0);
  await page.evaluate(() => (window as unknown as { restoreHealthStorage: () => void }).restoreHealthStorage());
  await health(page).getByRole("button", { name: "检查链接", exact: true }).press("Enter");
  await expect(health(page).locator(".health-latest")).toContainText("检查了 20 条链接", { timeout: 20000 });
  expect(control.writes).toHaveLength(1); expect(await pending(page)).toEqual([]);
  await expect(health(page).getByRole("alert")).toHaveCount(0);
});

for (const failure of ["rejected", "lost"] as const) test(`a ${failure} stop keeps the original run and never starts a replacement check`, async ({ page, owned }) => {
  await owned.fixture(true); const control = await intercept(page, owned); await open(page);
  await health(page).getByRole("button", { name: "检查链接", exact: true }).click();
  await expect(health(page).locator(".health-running")).toBeVisible();
  const [original] = await pending(page), count = await stableCalls(owned);
  control.rejectStop = failure === "rejected"; control.lostStop = failure === "lost";
  await health(page).getByRole("button", { name: "停止检查", exact: true }).click();
  if (failure === "rejected") {
    await expect(health(page).getByRole("alert")).toContainText("Synthetic stop not accepted");
    await health(page).getByRole("button", { name: "刷新已保存结果", exact: true }).click();
    await expect(health(page).getByRole("alert")).toContainText("Synthetic stop not accepted");
    await expect(health(page).locator(".health-running")).toBeVisible();
    control.rejectStop = false;
    await health(page).getByRole("button", { name: "停止检查", exact: true }).click();
  }
  await expect(health(page).locator(".health-run-notice")).toContainText("检查已停止");
  await expect(health(page).getByRole("alert")).toHaveCount(0);
  expect(control.stops).toEqual(Array(failure === "rejected" ? 2 : 1).fill(`/link-health/runs/${original.requestId}/stop`));
  expect(control.writes).toEqual([healthRequest(original)]); expect(await owned.calls()).toBe(count); expect(await pending(page)).toEqual([]);
});
