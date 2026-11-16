import { expect, test as base, type APIRequestContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import { mcpRequest, type McpChange, type McpOperation, type McpStatus } from "../src/mcp-local-state";
import { settleVisualLayout } from "./visual-layout";

type Server = {
  request: APIRequestContext; headers: Record<string, string>;
  read: () => Promise<McpStatus>; change: (values: McpChange) => Promise<McpStatus>;
};
const test = base.extend<{ server: Server }>({
  // This is the same temporary synthetic service used by the workbench tests.
  // A separate cleanup context can restore its enabled state after a timeout.
  server: [async ({ playwright, baseURL }, use) => {
    const request = await playwright.request.newContext({ baseURL, timeout: 5000 });
    const boot = await request.get("/app/boot"); expect(boot.ok()).toBeTruthy();
    const headers = { Authorization: `Bearer ${(await boot.json()).token}` };
    const read = async () => {
      const response = await request.get("/admin/mcp", { headers }); expect(response.ok()).toBeTruthy();
      return response.json() as Promise<McpStatus>;
    };
    const change = async (values: McpChange) => {
      const current = await read();
      const response = await request.post("/admin/mcp", { headers, data: {
        ...values, request_id: `mcp-test-${randomUUID()}`, expected_revision: current.revision,
      } });
      expect(response.ok()).toBeTruthy(); return response.json() as Promise<McpStatus>;
    };
    const initial = await read();
    try { await use({ request, headers, read, change }); }
    finally {
      try { await change({ enabled: initial.enabled }); }
      finally { await request.dispose(); }
    }
  }, { timeout: 30000 }],
});

const errors = new WeakMap<Page, string[]>();
async function prepare(page: Page) {
  const failures: string[] = []; errors.set(page, failures);
  page.on("pageerror", error => failures.push(error.message));
  await page.addInitScript(() => {
    if (!localStorage.getItem("fm-language")) localStorage.setItem("fm-language", "zh");
    if (!localStorage.getItem("fm-theme")) localStorage.setItem("fm-theme", "light");
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
      writeText: async (value: string) => { (window as unknown as { copiedMcp: string }).copiedMcp = value; },
    } });
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
}
test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 850 }); await prepare(page);
});
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" }); expect(errors.get(page)).toEqual([]);
});

const panel = (page: Page) => page.locator(".mcp-settings");
const recovery = (page: Page) => page.locator(".mcp-recovery");
async function pending(page: Page) {
  return page.evaluate(() => Object.keys(localStorage).filter(key => key.startsWith("fm-mcp-operation:"))
    .map(key => JSON.parse(localStorage.getItem(key)!))) as Promise<McpOperation[]>;
}
async function open(page: Page) {
  await page.goto("/app#settings/mcp");
  await expect(panel(page).locator(".mcp-service-status")).not.toHaveText(/正在读取状态|Loading status/);
}
async function reset(page: Page) {
  await panel(page).getByRole("button", { name: /^(重置令牌|Reset token)$/ }).click();
  await panel(page).getByRole("button", { name: /^(确认重置|Confirm reset)$/ }).click();
}
async function intercept(page: Page) {
  const control = {
    writes: [] as Record<string, unknown>[], accepted: [] as McpStatus[], closes: [] as Record<string, unknown>[],
    lost: false, malformed: false, dropBeforeServer: false, failReads: false, malformedReceipt: false, reads: 0,
    holdBefore: null as Promise<void> | null, holdAfter: null as Promise<void> | null,
  };
  await page.route("**/admin/mcp", async route => {
    if (route.request().method() !== "POST") return route.continue();
    const body = route.request().postDataJSON(); control.writes.push(body);
    if (control.dropBeforeServer) { control.dropBeforeServer = false; return route.abort("failed"); }
    if (control.holdBefore) await control.holdBefore;
    const response = await route.fetch();
    if (response.ok()) control.accepted.push(await response.json());
    if (control.holdAfter) await control.holdAfter;
    if (response.ok() && control.lost) { control.lost = false; return route.abort("failed"); }
    if (response.ok() && control.malformed) { control.malformed = false; return route.fulfill({ status: 200, json: {} }); }
    return route.fulfill({ response });
  });
  await page.route(/\/admin\/mcp\/operations\/[^/?]+$/, route => {
    control.reads++;
    if (control.failReads) return route.fulfill({ status: 503, json: { detail: "Synthetic original MCP receipt unavailable" } });
    if (control.malformedReceipt) return route.fulfill({ status: 200, json: {} });
    return route.continue();
  });
  await page.route(/\/admin\/mcp\/operations\/[^/?]+\/close$/, route => {
    control.closes.push(route.request().postDataJSON()); return route.continue();
  });
  return control;
}

for (const failure of ["lost", "malformed"] as const) test(`${failure} real rotation response recovers read-only and keeps later token and disabled state`, async ({ page, server }) => {
  test.setTimeout(120000);
  const initial = await server.change({ enabled: true });
  const control = await intercept(page); control.lost = failure === "lost"; control.malformed = failure === "malformed"; control.failReads = true;
  let release!: () => void; control.holdAfter = new Promise(resolve => { release = resolve; });
  await open(page); await panel(page).getByRole("button", { name: "重置令牌", exact: true }).click();
  try {
    await panel(page).getByRole("button", { name: "确认重置", exact: true }).evaluate(button => {
      (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click();
    });
    await expect.poll(() => control.accepted.length).toBe(1);
    expect(control.accepted[0].token).not.toBe(initial.token);
    await expect(recovery(page)).toHaveCount(0);
  } finally { release(); control.holdAfter = null; }
  await expect(recovery(page)).toBeVisible();
  const [original] = await pending(page); expect(control.writes).toEqual([mcpRequest(original)]);
  expect(JSON.stringify(original)).not.toContain(initial.token); expect(JSON.stringify(original)).not.toContain(control.accepted[0].token);
  await page.reload(); await expect(recovery(page)).toBeVisible();
  await expect(panel(page).getByRole("button", { name: "复制令牌", exact: true })).toBeDisabled();
  await expect(panel(page).getByRole("button", { name: "复制客户端配置", exact: true })).toBeDisabled();
  expect(control.writes).toHaveLength(1);

  if (failure === "lost") for (const language of ["zh", "en"] as const) for (const theme of ["light", "dark"] as const)
    for (const [width, height] of [[1280, 850], [320, 640], [683, 384]] as const) {
      await page.evaluate(({ language, theme }) => { localStorage.setItem("fm-language", language); localStorage.setItem("fm-theme", theme); }, { language, theme });
      await page.setViewportSize({ width, height }); await page.reload();
      await expect(recovery(page)).toBeVisible();
      const read = recovery(page).getByRole("button", { name: language === "zh" ? "重新读取原修改" : "Read original change", exact: true });
      await expect(read).toBeEnabled(); await read.scrollIntoViewIfNeeded();
      await expect(read).toBeInViewport({ ratio: 1 }); await settleVisualLayout(page);
      expect(await panel(page).evaluate(element => element.scrollWidth <= element.clientWidth)).toBeTruthy();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
      await page.screenshot({ path: `screenshots/collection-review/mcp-recovery-${language}-${theme}-${width}-${height}.png`, animations: "disabled" });
    }

  const later = await server.change({ rotate_token: true }); await server.change({ enabled: false });
  control.failReads = false;
  await recovery(page).getByRole("button", { name: /^(重新读取原修改|Read original change)$/ }).press("Enter");
  await expect(recovery(page)).toHaveCount(0); expect(await pending(page)).toEqual([]);
  await expect(panel(page).getByRole("textbox", { name: /^(MCP 访问令牌|MCP access token)$/ })).toHaveValue(later.token);
  await expect(panel(page).locator(".mcp-service-status")).toHaveText(/^(MCP 已停用|MCP disabled)$/);
  expect(control.writes).toEqual([mcpRequest(original)]); expect((await server.read()).token).toBe(later.token);
  await panel(page).getByRole("button", { name: /^(复制客户端配置|Copy client configuration)$/ }).click();
  expect(await page.evaluate(() => (window as unknown as { copiedMcp: string }).copiedMcp)).toContain(later.token);
});

test("an unaccepted request retries only its original ID and revision after an explicit Space", async ({ page, server }) => {
  const initial = await server.change({ enabled: true }), control = await intercept(page); control.dropBeforeServer = true;
  await open(page); await reset(page); await expect(recovery(page)).toBeVisible();
  await expect(recovery(page).getByRole("button", { name: "继续原修改", exact: true })).toBeEnabled();
  const [original] = await pending(page); expect((await server.read()).token).toBe(initial.token);
  await page.reload(); await expect(recovery(page).getByRole("button", { name: "继续原修改", exact: true })).toBeEnabled();
  expect(control.writes).toEqual([mcpRequest(original)]);
  await recovery(page).getByRole("button", { name: "继续原修改", exact: true }).press("Space");
  await expect(recovery(page)).toHaveCount(0); expect(await pending(page)).toEqual([]);
  expect(control.writes).toEqual([mcpRequest(original), mcpRequest(original)]); expect(control.accepted).toHaveLength(1);
  expect((await server.read()).token).toBe(control.accepted[0].token); expect(control.accepted[0].token).not.toBe(initial.token);
});

for (const acceptedFirst of [false, true]) test(`closing the original request preserves the current token when acceptance ${acceptedFirst ? "wins" : "has not happened"}`, async ({ page, server }) => {
  const initial = await server.change({ enabled: true }), control = await intercept(page); control.dropBeforeServer = true;
  await open(page); await reset(page);
  await expect(recovery(page).getByRole("button", { name: "返回当前配置", exact: true })).toBeEnabled();
  const [original] = await pending(page), body = mcpRequest(original);
  const accepted = acceptedFirst ? await server.request.post("/admin/mcp", { headers: server.headers, data: body }) : null;
  if (accepted) expect(accepted.ok()).toBeTruthy();
  const current = await server.read();
  await recovery(page).getByRole("button", { name: "返回当前配置", exact: true }).click();
  await expect(recovery(page)).toHaveCount(0); expect(await pending(page)).toEqual([]); expect(control.closes).toEqual([body]);
  const late = await server.request.post("/admin/mcp", { headers: server.headers, data: body });
  expect(late.status()).toBe(acceptedFirst ? 200 : 409); expect((await server.read()).token).toBe(current.token);
  if (!acceptedFirst) expect(current.token).toBe(initial.token);
  expect(control.writes).toEqual([body]);
});

test("a delayed stale window cannot rotate a newer configuration and closing retains the newer disabled state", async ({ page, server }) => {
  const initial = await server.change({ enabled: true }), control = await intercept(page);
  let release!: () => void; control.holdBefore = new Promise(resolve => { release = resolve; });
  await open(page); await reset(page);
  try {
    await expect.poll(() => control.writes.length).toBe(1); await server.change({ enabled: false });
  } finally { release(); control.holdBefore = null; }
  await expect(recovery(page)).toBeVisible(); await page.reload();
  await expect(recovery(page).getByRole("button", { name: "继续原修改", exact: true })).toBeDisabled();
  await expect(recovery(page)).toContainText("配置已经变化");
  expect(control.accepted).toEqual([]); expect((await server.read()).token).toBe(initial.token);
  await recovery(page).getByRole("button", { name: "返回当前配置", exact: true }).click();
  await expect(recovery(page)).toHaveCount(0); expect((await server.read()).enabled).toBe(false); expect(control.writes).toHaveLength(1);
});

test("confirmation from a second window clears the same pending operation in both without resending", async ({ page, context, server }) => {
  await server.change({ enabled: true }); const first = await intercept(page); first.lost = true; first.failReads = true;
  await open(page); await reset(page); await expect(recovery(page)).toBeVisible();
  const second = await context.newPage(); await prepare(second); const other = await intercept(second); other.failReads = true;
  try {
    await open(second); await expect(recovery(second)).toBeVisible(); expect(await pending(second)).toEqual(await pending(page));
    await expect(panel(second).getByRole("button", { name: "重置令牌", exact: true })).toBeDisabled();
    other.failReads = false;
    await recovery(second).getByRole("button", { name: "重新读取原修改", exact: true }).click();
    await expect(recovery(second)).toHaveCount(0); await expect(recovery(page)).toHaveCount(0);
    expect(await pending(page)).toEqual([]); expect(first.writes).toHaveLength(1); expect(other.writes).toEqual([]);
    expect(errors.get(second)).toEqual([]);
  } finally { await second.unrouteAll({ behavior: "wait" }); await second.close(); }
});

test("a malformed read receipt keeps the accepted original and never offers an unconfirmed retry", async ({ page, server }) => {
  await server.change({ enabled: true }); const control = await intercept(page); control.lost = true; control.malformedReceipt = true;
  await open(page); await reset(page); await expect(recovery(page)).toBeVisible();
  const originals = await pending(page);
  await recovery(page).getByRole("button", { name: "重新读取原修改", exact: true }).click();
  await expect(panel(page).getByRole("alert")).toContainText("无法确认");
  expect(await pending(page)).toEqual(originals); await expect(recovery(page).getByRole("button", { name: "继续原修改", exact: true })).toHaveCount(0);
  control.malformedReceipt = false;
  await recovery(page).getByRole("button", { name: "重新读取原修改", exact: true }).click();
  await expect(recovery(page)).toHaveCount(0); expect(control.writes).toHaveLength(1);
});

test("failed local persistence sends no token reset and an explicit retry works after storage recovers", async ({ page, server }) => {
  const initial = await server.change({ enabled: true }), control = await intercept(page);
  await page.clock.install();
  let statusReads = 0;
  page.on("response", response => { if (response.url().endsWith("/admin/mcp") && response.request().method() === "GET") statusReads++; });
  await open(page);
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    (window as unknown as { restoreMcpStorage: () => void }).restoreMcpStorage = () => { Storage.prototype.setItem = original; };
    Storage.prototype.setItem = function (key, value) {
      if (key.startsWith("fm-mcp-operation:")) throw new DOMException("Synthetic MCP storage full", "QuotaExceededError");
      return original.call(this, key, value);
    };
  });
  await reset(page); await expect(panel(page).getByRole("alert")).toContainText("Synthetic MCP storage full");
  expect(control.writes).toEqual([]); expect((await server.read()).token).toBe(initial.token);
  const beforeRefresh = statusReads;
  await page.clock.runFor(5_000);
  await expect.poll(() => statusReads).toBeGreaterThan(beforeRefresh);
  await expect(panel(page).getByRole("alert")).toContainText("Synthetic MCP storage full");
  const beforeManualRead = statusReads;
  await panel(page).getByRole("button", { name: "刷新状态", exact: true }).click();
  await expect.poll(() => statusReads).toBeGreaterThan(beforeManualRead);
  await expect(panel(page).getByRole("alert")).toContainText("Synthetic MCP storage full");
  expect(control.writes).toEqual([]);
  await page.evaluate(() => (window as unknown as { restoreMcpStorage: () => void }).restoreMcpStorage());
  await panel(page).getByRole("button", { name: "确认重置", exact: true }).click();
  await expect.poll(() => control.accepted.length).toBe(1); await expect(recovery(page)).toHaveCount(0);
  await expect(panel(page).getByRole("alert")).toHaveCount(0);
});
