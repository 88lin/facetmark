import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

const endpoint = "http://127.0.0.1:48219/mcp/";
const configuration = (token: string) => ({ mcpServers: { facetmark: {
  type: "http", url: endpoint, headers: { Authorization: "Bearer " + token },
} } });
const codexConfiguration = (token: string) => '[mcp_servers.facetmark]\nurl = "' + endpoint
  + '"\nhttp_headers = { Authorization = "Bearer ' + token + '" }\n';

async function mcpFixture(page: Page, initial: Record<string, unknown> = {}) {
  const status = { revision: "0".repeat(64), enabled: false, configured: false, running: false, transport_ready: true,
    status: "disabled", error: "", endpoint, token: "", client_config: configuration(""),
    codex_config: codexConfiguration(""), locked: { enabled: false, token: false },
    last_request_at: null, probe: null as Record<string, unknown> | null, ...initial };
  const writes: Record<string, unknown>[] = [];
  await page.route("**/admin/mcp", route => {
    let operation: Record<string, unknown> | undefined;
    if (route.request().method() === "POST") {
      const values = route.request().postDataJSON(); writes.push(values);
      if ("enabled" in values || values.rotate_token) {
        expect(values.expected_revision).toBe(status.revision);
        expect(values.request_id).toMatch(/^mcp-[a-f0-9-]+$/);
        status.revision = String(writes.length).padStart(64, "0");
        operation = { request_id: values.request_id, action: "configure", state: "accepted",
          accepted_revision: status.revision, accepted_at: 1794900000, superseded: false };
      }
      if ("enabled" in values) {
        status.enabled = values.enabled;
        if (status.enabled && !status.token) status.token = "synthetic-mcp-only";
        status.running = status.enabled; status.status = status.enabled ? "ready" : "disabled";
        status.probe = null;
      }
      if (values.rotate_token) { status.token = "synthetic-mcp-rotated"; status.probe = null; }
      status.configured = Boolean(status.token);
      status.client_config = configuration(status.token);
      status.codex_config = codexConfiguration(status.token);
      if (values.probe) status.probe = { ok: true, server: "facetmark", tools: 9, resources: 2, templates: 1 };
    }
    return route.fulfill({ json: { ...status, ...(operation ? { operation } : {}) } });
  });
  await page.route("**/karakeep/stats", route => route.fulfill({ json: { documents: 12, users: 1, with_body: 8 } }));
  return { status, writes };
}

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => {
    localStorage.setItem("fm-language", "zh");
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
      writeText: async (text: string) => { (window as unknown as { copiedMcpText: string }).copiedMcpText = text; },
    } });
  });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test("MCP has a separate token, truthful status and current-port client configurations", async ({ page }) => {
  const { status, writes } = await mcpFixture(page);
  await page.goto("/app#settings/mcp");
  const panel = page.locator(".mcp-settings");
  await expect(panel.locator(".mcp-service-status")).toHaveText("MCP 已停用");
  await expect(panel.getByRole("button", { name: "检查接入", exact: true })).toBeDisabled();
  await expect(panel.getByRole("textbox", { name: "MCP 地址", exact: true })).toHaveValue(endpoint);
  await panel.getByRole("button", { name: "开启 MCP", exact: true }).click();
  await expect.poll(() => writes[0]).toEqual({ enabled: true, request_id: expect.stringMatching(/^mcp-[a-f0-9-]+$/),
    expected_revision: "0".repeat(64) });
  await expect(panel.locator(".mcp-service-status")).toHaveText("MCP 服务已启动");
  await expect(panel.locator(".mcp-probe")).toHaveCount(0);
  await panel.getByRole("button", { name: "检查接入", exact: true }).click();
  await expect(panel.locator(".mcp-probe")).toContainText("协议自检通过");
  await expect(panel.locator(".mcp-probe")).toContainText("9 个工具");
  await panel.getByRole("button", { name: "复制客户端配置", exact: true }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { copiedMcpText: string }).copiedMcpText))
    .toBe(JSON.stringify(configuration("synthetic-mcp-only"), null, 2));
  await panel.getByRole("button", { name: "重置令牌", exact: true }).click();
  await expect.poll(() => writes.length).toBe(2);
  await panel.getByRole("button", { name: "确认重置", exact: true }).click();
  await expect.poll(() => status.token).toBe("synthetic-mcp-rotated");
  await expect(panel.getByLabel("MCP 访问令牌", { exact: true })).toHaveValue(status.token);
  await expect(panel.locator(".mcp-probe")).toHaveCount(0);
  await panel.locator(".mcp-codex-config > summary").click();
  await panel.getByRole("button", { name: "复制 Codex 配置", exact: true }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { copiedMcpText: string }).copiedMcpText))
    .toBe(codexConfiguration("synthetic-mcp-rotated"));
  await expect(page.getByRole("textbox", { name: "Karakeep 服务地址", exact: true })).toHaveValue("http://127.0.0.1:48219");
  await expect(page.locator(".mcp-karakeep-stats")).toContainText("12 条收藏");
  await panel.getByRole("button", { name: "停用 MCP", exact: true }).click();
  await expect(panel.locator(".mcp-service-status")).toHaveText("MCP 已停用");
  await expect(panel.getByRole("button", { name: "检查接入", exact: true })).toBeDisabled();
});

test("an enabled MCP with an unavailable transport is not shown as running", async ({ page }) => {
  await mcpFixture(page, { enabled: true, configured: true, running: false, transport_ready: false,
    status: "starting", token: "synthetic-mcp-only", client_config: configuration("synthetic-mcp-only"),
    error: "Synthetic MCP transport failure" });
  await page.goto("/app#settings/mcp");
  await expect(page.locator(".mcp-service-status")).toHaveText("服务尚未就绪");
  await expect(page.locator(".mcp-settings [role=alert]")).toContainText("Synthetic MCP transport failure");
  await expect(page.locator(".mcp-settings").getByRole("button", { name: "检查接入", exact: true })).toBeDisabled();
});

test("five settings categories retain keyboard focus, drafts and narrow-window width", async ({ page }) => {
  await mcpFixture(page, { enabled: true, configured: true, running: true, status: "ready",
    token: "synthetic-mcp-only", client_config: configuration("synthetic-mcp-only") });
  await page.goto("/app#settings/mcp");
  const mcp = page.getByRole("tab", { name: "MCP 与接入", exact: true });
  await expect(mcp).toHaveAttribute("aria-selected", "true");
  await mcp.focus(); await mcp.press("Home");
  const ai = page.getByRole("tab", { name: "AI 连接", exact: true });
  await expect(ai).toBeFocused();
  await page.locator("input[name=chat_model]").fill("saved-mcp-navigation-draft");
  await ai.focus(); await ai.press("End");
  await expect(page.getByRole("tab", { name: "桌面与更新", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await expect(mcp).toBeFocused();
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await page.emulateMedia({ colorScheme: width === 320 ? "dark" : "light", reducedMotion: "reduce" });
    await ai.click();
    await expect(page.locator("input[name=chat_model]")).toHaveValue("saved-mcp-navigation-draft");
    await ai.focus(); await ai.press("End"); await page.keyboard.press("ArrowLeft");
    await expect(mcp).toBeFocused();
    await expect(mcp).toBeInViewport({ ratio: 1 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await settleVisualLayout(page);
    await page.screenshot({ path: "screenshots/collection-review/mcp-settings-" + width + ".png", animations: "disabled" });
  }
});

test("link health shows saved and confirmed results without automatically checking URLs", async ({ page }) => {
  const checks: Record<string, unknown>[] = [];
  let healthRun: Record<string, unknown> | null = null;
  const libraryId = "a".repeat(64);
  await page.route("**/link-health/runs/current", route => route.fulfill({ json: { library_id: libraryId, running: false, run: healthRun } }));
  await page.route("**/link-health/summary", route => route.fulfill({ json: { alive: 12, gone: 2, unchecked: 4 } }));
  await page.route("**/graveyard?**", route => route.fulfill({ json: [{ bookmark_id: 1, title: "Saved page",
    ai_title: "保留的旧页面", url: "https://synthetic.invalid/dead", domain: "synthetic.invalid", folder: "",
    health: { status: "gone", checked_at: 1792882800, archive_url: "https://archive.example/saved" } }] }));
  await page.route("**/link-health/check", route => {
    const original = route.request().postDataJSON(); checks.push(original);
    healthRun = { request_id: original.request_id, state: "done", params: { limit: original.limit, ids: null, expected_library: libraryId },
      targets_count: 18, started_at: 1794900000, finished_at: 1794900001, error: "", report: {
        considered: 18, probed: 18, escalated: 2, recovered_bodies: 1,
        by_status: { alive: 16, restricted: 1, gone: 1 }, confirmed_gone: [1], errors: [] } };
    return route.fulfill({ json: healthRun });
  });
  await page.route("**/bookmark/1?body=true", route => route.fulfill({ json: { bookmark_id: 1, title: "Saved page",
    ai_title: "保留的旧页面", url: "https://synthetic.invalid/dead", domain: "synthetic.invalid", folder: "",
    tags: [], summary: "之前保存的内容仍可阅读。", body_text: "## Saved source\n\nThis saved content remains available." } }));
  await page.goto("/app");
  await page.getByRole("button", { name: "任务", exact: true }).click();
  const health = page.locator(".health-tools");
  await health.locator("summary").click();
  await expect(health.locator(".health-counts")).toContainText("待检查");
  await expect(health.locator(".health-bookmarks")).toContainText("保留的旧页面");
  expect(checks).toHaveLength(0);
  await health.getByRole("combobox", { name: "链接检查数量", exact: true }).selectOption("50");
  await health.getByRole("button", { name: "检查链接", exact: true }).click();
  await expect.poll(() => checks).toEqual([{ limit: 50, request_id: expect.stringMatching(/^health-[a-f0-9-]+$/), expected_library: libraryId }]);
  await expect(health.locator(".health-latest")).toContainText("检查了 18 条链接");
  await expect(health.locator(".health-latest")).toContainText("找回 1 条正文");
  await expect(health.locator("pre")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await settleVisualLayout(page);
  await page.screenshot({ path: "screenshots/collection-review/health-results-390.png", animations: "disabled" });
  await health.getByRole("button", { name: "查看保存内容", exact: true }).click();
  await expect(page.locator(".preview-title h1")).toHaveText("保留的旧页面");
  await expect(page.locator(".body-text")).toContainText("This saved content remains available.");
});

for (const [target, expected] of [["auto", "en"], ["zh", "zh"]]) {
  test("new full indexing resolves target language " + target + " in the English interface", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("fm-language", "en"));
    await page.route("**/admin/setup-status", async route => {
      const response = await route.fetch(), setup = await response.json();
      return route.fulfill({ response, json: { ...setup, summary_language: target, demo: true } });
    });
    let started: Record<string, unknown> = {};
    await page.route("**/admin/jobs/start", route => {
      started = route.request().postDataJSON(); return route.fulfill({ json: {
        id: "synthetic-full-index", run_id: "synthetic-full-index-run", state: "done", params: started,
      } });
    });
    await page.goto("/app");
    await page.getByRole("button", { name: "Tasks", exact: true }).click();
    await page.locator(".index-consent > summary").click();
    await page.getByRole("checkbox", { name: "I understand and confirm processing", exact: true }).check();
    await page.getByRole("button", { name: "Start indexing", exact: true }).click();
    await expect.poll(() => started).toEqual({ mode: "index", fetch: true, confirmed: true, summary_language: expected, request_id: expect.any(String) });
  });
}

test("resuming a saved task does not replace its language with the interface language", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("fm-language", "en"));
  let job = { id: "saved-chinese-task", run_id: "saved-chinese-run", state: "paused", resumable: true,
    params: { mode: "summarize", summary_language: "zh" }, items: { done: 1, total: 2, failed: 0 } };
  await page.route("**/admin/job", route => route.fulfill({ json: job }));
  await page.route("**/admin/jobs", route => route.fulfill({ json: { items: [job] } }));
  let resumed: Record<string, unknown> = {};
  await page.route("**/admin/jobs/resume", route => {
    resumed = route.request().postDataJSON();
    job = { ...job, run_id: "resumed-chinese-run", state: "done", resumable: false };
    return route.fulfill({ json: job });
  });
  await page.goto("/app");
  await page.getByRole("button", { name: "Tasks", exact: true }).click();
  await page.getByRole("button", { name: "Resume saved task", exact: true }).click();
  await expect.poll(() => resumed).toEqual({ resume_id: "saved-chinese-task", resume_run_id: "saved-chinese-run", confirmed: true, request_id: expect.any(String) });
});
