import { expect, test as base, type APIRequestContext, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import type { Setting } from "../src/api";
import { settleVisualLayout } from "./visual-layout";

type Server = { request: APIRequestContext; headers: Record<string, string>; read: () => Promise<Setting[]> };
const preferenceKeys = ["summary_language", "summary_prompt", "chat_concurrency"];
const test = base.extend<{ server: Server }>({
  server: [async ({ playwright, baseURL }, use) => {
    const request = await playwright.request.newContext({ baseURL, timeout: 5000 });
    const boot = await request.get("/app/boot"); expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` };
    const read = async () => {
      const response = await request.get("/admin/settings", { headers }); expect(response.ok()).toBeTruthy();
      return (await response.json()).settings as Setting[];
    };
    const original = await read();
    try { await use({ request, headers, read }); }
    finally {
      try {
        const values = Object.fromEntries(original.filter(row => preferenceKeys.includes(row.key)).map(row => [row.key, row.value]));
        const response = await request.put("/admin/settings", { headers, data: { values } });
        expect(response.ok()).toBeTruthy();
      } finally { await request.dispose(); }
    }
  }, { timeout: 30000 }],
});

const errors = new WeakMap<Page, string[]>();
const releases = new WeakMap<Page, Set<() => void>>();
function heldResponse(page: Page) {
  let finish!: () => void;
  const wait = new Promise<void>(resolve => { finish = resolve; });
  const release = () => { finish(); releases.get(page)?.delete(release); };
  releases.get(page)!.add(release);
  return { wait, release };
}
async function noHorizontalOverflow(page: Page) {
  await settleVisualLayout(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
}
test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 });
  const failures: string[] = []; errors.set(page, failures); releases.set(page, new Set());
  page.on("pageerror", error => failures.push(error.message));
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
      writeText: async (value: string) => { (window as unknown as { copiedPairing: string }).copiedPairing = value; },
    } });
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});
test.afterEach(async ({ page }) => {
  for (const release of releases.get(page) ?? []) release();
  await page.unrouteAll({ behavior: "wait" });
  expect(errors.get(page)).toEqual([]);
});

const extension = (page: Page) => page.locator(".extension-settings");
async function extensionTransport(page: Page) {
  const control = { reads: 0, completed: 0, failed: false, malformed: false, hold: null as Promise<void> | null, lateDisconnected: false };
  await page.route("**/admin/extension-status", async route => {
    control.reads++;
    if (control.failed) return route.fulfill({ status: 503, json: { detail: "Synthetic extension status unavailable" } });
    if (control.malformed) return route.fulfill({ json: {} });
    const response = await route.fetch();
    const data = await response.json();
    const lateDisconnected = control.lateDisconnected;
    if (control.hold) await control.hold;
    control.completed++;
    return route.fulfill({ response, json: lateDisconnected ? { ...data, recently_connected: false } : data });
  });
  return control;
}
async function confirmExtension(server: Server) {
  const response = await server.request.get("/stats", { headers: { ...server.headers, "X-Facetmark-Client": "extension" } });
  expect(response.ok()).toBeTruthy();
}

test("extension reads only the visible category and one slow initial read remains authoritative", async ({ page, server }) => {
  await confirmExtension(server);
  const control = await extensionTransport(page), held = heldResponse(page);
  control.hold = held.wait;
  await page.clock.install();
  await page.goto("/app#settings/models");
  await expect(page.locator(".summary-preferences")).toBeVisible();
  await page.clock.runFor(11000); expect(control.reads).toBe(0);
  await page.getByRole("tab", { name: "浏览器扩展", exact: true }).focus();
  await page.getByRole("tab", { name: "浏览器扩展", exact: true }).press("Enter");
  await expect(extension(page).locator(".extension-connection-status")).toHaveText("正在读取扩展连接状态…");
  await expect(extension(page).getByText("尚未收到扩展连接。", { exact: false })).toHaveCount(0);
  await page.clock.runFor(11000); expect(control.reads).toBe(1);
  held.release(); control.hold = null;
  await expect(extension(page).locator(".extension-connection-status")).toHaveText("扩展最近已连接此书库");
  await expect(extension(page).getByRole("button", { name: "重新读取扩展状态", exact: true })).toBeEnabled();
});

test("extension read failures retain the confirmed connection and pairing across layouts", async ({ page, server }) => {
  test.setTimeout(90000);
  await confirmExtension(server);
  const control = await extensionTransport(page);
  await page.goto("/app#settings/extension");
  for (const language of ["zh", "en"]) for (const theme of ["light", "dark"]) {
    await page.evaluate(({ language, theme }) => {
      localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme);
    }, { language, theme });
    for (const [width, height] of [[1280, 850], [320, 640], [683, 384]]) {
      control.failed = false;
      await page.setViewportSize({ width, height }); await page.reload();
      const panel = extension(page), state = panel.locator(".extension-connection-status");
      await expect(state).toHaveText(/^(扩展最近已连接此书库|Extension recently connected to this library)$/);
      control.failed = true;
      const reload = panel.getByRole("button", { name: /^(重新读取扩展状态|Reload extension status)$/ });
      await reload.click();
      await expect(panel.locator(".extension-status-error")).toBeVisible();
      await expect(state).toHaveText(/^(上次成功读取：扩展最近已连接此书库。|Last confirmed state: the extension recently connected to this library\.)$/);
      const copy = panel.getByRole("button", { name: /^(复制配对令牌|Copy pairing token)$/ });
      await copy.focus(); await copy.press("Space");
      expect(await page.evaluate(() => (window as unknown as { copiedPairing: string }).copiedPairing)).toBe(server.headers.Authorization.slice(7));
      const reason = panel.locator(".extension-status-error summary");
      await reason.focus(); await reason.press("Enter");
      await expect(panel.locator(".extension-status-error details p")).toContainText("Synthetic extension status unavailable");
      await reload.scrollIntoViewIfNeeded(); await noHorizontalOverflow(page);
      await page.screenshot({ path: `screenshots/collection-review/extension-status-${language}-${theme}-${width}-${height}.png`, animations: "disabled" });
    }
  }
  control.failed = false; control.malformed = true;
  await extension(page).getByRole("button", { name: /^(重新读取扩展状态|Reload extension status)$/ }).click();
  await expect(extension(page).locator(".extension-status-error")).toBeVisible();
  await expect(extension(page).locator(".extension-connection-status")).toContainText("Last confirmed state");
  control.malformed = false;
  await extension(page).getByRole("button", { name: "Reload extension status", exact: true }).click();
  await expect(extension(page).locator(".extension-status-error")).toHaveCount(0);
  await expect(extension(page).locator(".extension-connection-status")).toHaveText("Extension recently connected to this library");
});

test("leaving extension settings cancels its read and a late response cannot replace the confirmed state", async ({ page, server }) => {
  await confirmExtension(server);
  const control = await extensionTransport(page);
  await page.goto("/app#settings/extension");
  const state = extension(page).locator(".extension-connection-status");
  await expect(state).toHaveText("扩展最近已连接此书库");
  const held = heldResponse(page); control.hold = held.wait; control.lateDisconnected = true;
  const priorReads = control.reads;
  await extension(page).getByRole("button", { name: "重新读取扩展状态", exact: true }).click();
  await expect.poll(() => control.reads).toBeGreaterThan(priorReads);
  await page.getByRole("tab", { name: "桌面与更新", exact: true }).click();
  await expect(extension(page)).toBeHidden();
  const priorCompleted = control.completed;
  held.release(); control.hold = null; control.lateDisconnected = false;
  await expect.poll(() => control.completed).toBeGreaterThan(priorCompleted);
  await expect(state).toHaveText("扩展最近已连接此书库");
  const reads = control.reads;
  await page.clock.install(); await page.clock.runFor(11000); expect(control.reads).toBe(reads);
  await page.getByRole("tab", { name: "浏览器扩展", exact: true }).click();
  await expect.poll(() => control.reads).toBe(reads + 1);
  await expect(state).toHaveText("扩展最近已连接此书库");
});

for (const kind of ["summary", "processing"] as const) for (const failedRead of ["settings", "setup"] as const) {
  test(`${kind} saves once and only rereads after a ${failedRead} refresh failure`, async ({ page, server }) => {
    const writes: Record<string, unknown>[] = [];
    let fail = false, probes = 0;
    await page.route("**/admin/settings", async route => {
      if (route.request().method() === "PUT") {
        writes.push(route.request().postDataJSON().values);
        const response = await route.fetch(); expect(response.ok()).toBeTruthy(); return route.fulfill({ response });
      }
      return fail && failedRead === "settings" ? route.fulfill({ status: 503, json: { detail: "Synthetic post-save settings read failure" } }) : route.continue();
    });
    await page.route("**/admin/setup-status", route => fail && failedRead === "setup"
      ? route.fulfill({ status: 503, json: { detail: "Synthetic post-save shared status read failure" } }) : route.continue());
    await page.route("**/admin/settings/test", route => { probes++; return route.abort("failed"); });
    await page.goto("/app#settings/models");
    const panel = page.locator(kind === "summary" ? ".summary-preferences" : ".processing-preferences");
    await expect(panel).toBeVisible();
    const connectionDraft = page.locator(".model-chat input[name=chat_model]");
    await expect(connectionDraft).toBeEnabled(); await connectionDraft.fill("keep-this-unrelated-local-draft");
    const before = await server.read();
    const key = kind === "summary" ? "summary_language" : "chat_concurrency";
    const savedValue = before.find(row => row.key === key)!.value;
    const target = kind === "summary" ? savedValue === "zh" ? "en" : "zh" : Number(savedValue) === 3 ? 1 : 3;
    if (kind === "summary") await panel.getByRole("combobox", { name: "摘要目标语言", exact: true }).selectOption(String(target));
    else await panel.locator("input[name=chat_concurrency]").fill(String(target));
    fail = true;
    const save = panel.getByRole("button", { name: kind === "summary" ? "保存摘要设置" : "保存处理设置", exact: true });
    await expect(save).toBeEnabled();
    await save.focus(); await save.press("Enter");
    await expect(page.locator(".settings-read-recovery")).toBeVisible();
    expect(writes).toEqual([{ [key]: target }]);
    expect((await server.read()).find(row => row.key === key)!.value).toBe(target);
    await expect(panel).not.toContainText("未保存，请重试");
    if (kind === "summary") await expect(page.locator(".models > .notice")).toContainText("摘要设置已保存");
    else await expect(panel.locator(".processing-footer [role=status]")).toContainText("处理设置已保存");
    await expect(connectionDraft).toHaveValue("keep-this-unrelated-local-draft");
    const reload = page.getByRole("button", { name: "重新读取设置状态", exact: true });
    await expect(reload).toBeEnabled();
    await reload.focus(); await reload.press("Space");
    await expect(reload).toBeEnabled();
    await expect(page.locator(".settings-read-recovery")).toBeVisible();
    expect(writes).toHaveLength(1); expect(probes).toBe(0);
    await expect(connectionDraft).toHaveValue("keep-this-unrelated-local-draft");
    if (kind === "summary") await expect(page.locator(".models > .notice")).toContainText("摘要设置已保存");
    else await expect(panel.locator(".processing-footer [role=status]")).toContainText("处理设置已保存");
    await reload.scrollIntoViewIfNeeded(); await noHorizontalOverflow(page);
    await page.screenshot({ path: `screenshots/collection-review/settings-saved-${kind}-${failedRead}-zh-light-1280.png`, animations: "disabled" });
    if (kind === "processing" && failedRead === "setup") {
      await page.getByRole("button", { name: "切换语言", exact: true }).click();
      await page.getByRole("button", { name: "Toggle theme", exact: true }).click();
      await page.setViewportSize({ width: 320, height: 640 });
      await page.getByRole("button", { name: "Reload settings status", exact: true }).scrollIntoViewIfNeeded();
      await noHorizontalOverflow(page);
      await page.screenshot({ path: "screenshots/collection-review/settings-saved-processing-setup-en-dark-320.png", animations: "disabled" });
      await page.setViewportSize({ width: 1280, height: 850 });
      await page.getByRole("button", { name: "Toggle theme", exact: true }).click();
      await page.getByRole("button", { name: "Switch language", exact: true }).click();
    }
    fail = false;
    await reload.focus(); await reload.press("Space");
    await expect(page.locator(".settings-read-recovery")).toHaveCount(0);
    await expect(save).toBeDisabled();
    expect(writes).toHaveLength(1); expect(probes).toBe(0);
    await expect(connectionDraft).toHaveValue("keep-this-unrelated-local-draft");
    await page.reload();
    const input = kind === "summary" ? panel.getByRole("combobox", { name: "摘要目标语言", exact: true }) : panel.locator("input[name=chat_concurrency]");
    await expect(input).toHaveValue(String(target));
    expect(writes).toHaveLength(1);
  });
}

test("update checks show bounded retry details, suppress duplicate activation and keep both download paths reachable", async ({ page }) => {
  const held = heldResponse(page);
  let writes = 0, holding = true;
  let reply: Record<string, unknown> = { current: "2.1.1", latest: null, available: true };
  await page.route("**/admin/updates/check", async route => {
    writes++; if (holding) await held.wait;
    return route.fulfill({ json: reply });
  });
  await page.goto("/app#settings/desktop");
  await page.evaluate(() => { localStorage.setItem("fm-language", "en"); localStorage.setItem("fm-theme", "dark"); });
  await page.setViewportSize({ width: 320, height: 640 }); await page.reload();
  const panel = page.locator(".desktop-note"), check = panel.getByRole("button", { name: "Check for updates", exact: true });
  await check.focus(); await check.press("Enter");
  await expect(panel.getByRole("button", { name: "Checking…", exact: true })).toBeDisabled();
  await page.keyboard.press("Space"); await expect.poll(() => writes).toBe(1);
  holding = false; held.release();
  await expect(panel.locator(".update-status-error")).toBeVisible();
  await expect(panel).not.toContainText("No stable release is available");
  const reason = panel.locator(".update-status-error summary");
  await reason.focus(); await reason.press("Enter");
  await expect(panel.locator(".update-status-error details p")).toContainText("Invalid update check response");
  await expect(panel.getByRole("link", { name: "Release downloads", exact: true })).toHaveAttribute("href", "https://github.com/88lin/facetmark/releases/latest");
  await expect(panel.getByRole("link", { name: "Download preview builds", exact: true })).toHaveAttribute("href", "https://github.com/88lin/facetmark/actions/workflows/ci.yml");
  await noHorizontalOverflow(page);
  await page.screenshot({ path: "screenshots/collection-review/update-retry-en-dark-320.png", animations: "disabled" });
  reply = { current: "2.1.1", latest: "999.0.0", available: true };
  await check.focus(); await check.press("Space");
  await expect(panel.locator(".update-status-error")).toHaveCount(0);
  await expect(panel.getByRole("status")).toContainText("Version 999.0.0 available; current 2.1.1");
  expect(writes).toBe(2);
});
