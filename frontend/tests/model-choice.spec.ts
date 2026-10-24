import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const agents = ["codex", "claude", "opencode"].map(id => ({ id, name: id === "claude" ? "Claude Code" : id === "codex" ? "Codex" : "OpenCode", installed: true, path: `/fixture/${id}` }));
test.beforeEach(async ({ page }) => {
  await mkdir("screenshots", { recursive: true });
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents } }));
  await page.route("**/admin/settings/models", route => {
    const agent = route.request().postDataJSON().chat_agent || "codex";
    return route.fulfill({ json: { agent, default_model: `${agent}/default`, warning: "", models: [
      { id: `${agent}/fast`, label: "快速摘要", source: "cli" }, { id: `${agent}/careful`, label: "详细阅读", source: "cli" },
    ] } });
  });
});

test("model choice survives test, save and reopen and reaches summary generation", async ({ page }) => {
  let saved: Record<string, unknown> = {};
  let tested: Record<string, unknown> = {};
  let generated: Record<string, unknown> = {};
  await page.route("**/admin/jobs/preview", route => route.fulfill({ json: { total: 1, revision: "synthetic-model-preview" } }));
  await page.route("**/admin/jobs/start", route => {
    generated = route.request().postDataJSON();
    return route.fulfill({ json: { id: "synthetic-summary", state: "done", params: generated } });
  });
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      saved = { ...saved, ...route.request().postDataJSON().values };
      return route.fulfill({ json: {} });
    }
    const response = await route.fetch();
    const data = await response.json();
    data.settings = data.settings.map((row: { key: string }) => row.key in saved ? { ...row, value: saved[row.key] } : row);
    return route.fulfill({ response, json: data });
  });
  await page.route("**/admin/settings/test", route => {
    tested = route.request().postDataJSON();
    return route.fulfill({ json: { chat: { ok: true, model: tested.chat_agent_model, ms: 17 } } });
  });
  await page.goto("/app#settings");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("agent");
  await page.getByRole("combobox", { name: "选择 Agent", exact: true }).selectOption("opencode");
  const panel = page.locator(".model-chat");
  await expect(panel.locator(".model-picker-trigger")).toContainText("opencode/default");
  await panel.locator(".model-picker-trigger").click();
  await page.getByRole("combobox", { name: "搜索模型", exact: true }).fill("careful");
  await expect(page.getByRole("listbox").getByRole("option")).toHaveCount(1);
  await page.screenshot({ path: "screenshots/models-search-desktop.png", animations: "disabled" });
  await page.keyboard.press("Enter");
  await expect(panel.locator(".model-picker-trigger")).toContainText("详细阅读");
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect(panel.locator(".connection-feedback")).toContainText("连接已验证并保存");
  expect(tested.chat_agent_model).toBe("opencode/careful");
  expect(saved.chat_agent_model).toBe("opencode/careful");
  await expect(panel.getByRole("button", { name: "刷新模型", exact: true })).toBeEnabled();
  await panel.locator(".model-picker-trigger").click();
  await expect(page.getByRole("option", { name: /快速摘要/ })).toBeVisible();
  await page.keyboard.press("Escape");
  await panel.getByRole("button", { name: "前往生成摘要", exact: true }).click();
  await expect.poll(() => generated).toEqual(expect.objectContaining({ mode: "summarize", confirmed: true, summary_language: "zh" }));
  await expect(page.getByRole("dialog", { name: "生成 AI 摘要", exact: true })).toHaveCount(0);
  await page.reload();
  await expect(panel.locator(".model-picker-trigger")).toContainText(/详细阅读|opencode\/careful/);
  await page.setViewportSize({ width: 390, height: 844 });
  await panel.getByRole("button", { name: "测试并保存", exact: true }).scrollIntoViewIfNeeded();
  await expect(panel.getByRole("button", { name: "测试并保存", exact: true })).toBeInViewport({ ratio: 1 });
  await page.screenshot({ path: "screenshots/models-selected-mobile.png", animations: "disabled" });
});

test("switching agents keeps independent model drafts and ignores stale catalogs", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/admin/settings/models", async route => {
    const agent = route.request().postDataJSON().chat_agent;
    if (agent === "claude") await gate;
    return route.fulfill({ json: { models: [{ id: `${agent}/only`, label: `${agent} model`, source: "cli" }], default_model: `${agent}/default`, warning: "" } });
  });
  try {
    await page.goto("/app#settings");
    await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("agent");
    const panel = page.locator(".model-chat");
    const agent = page.getByRole("combobox", { name: "选择 Agent", exact: true });
    await agent.selectOption("opencode");
    await panel.getByRole("button", { name: "手动输入", exact: true }).click();
    await panel.locator('input[name="chat_agent_model"]').fill("custom/keep");
    await agent.selectOption("claude");
    await expect(panel.locator('input[name="chat_agent_model"]')).toHaveValue("");
    await agent.selectOption("opencode");
    release();
    await expect(panel.locator('input[name="chat_agent_model"]')).toHaveValue("custom/keep");
    await expect(panel.getByRole("button", { name: "刷新模型", exact: true })).toBeEnabled();
    await panel.locator(".model-picker-trigger").click();
    await expect(page.getByRole("option", { name: /opencode model/ })).toBeVisible();
    await expect(page.getByRole("option", { name: /claude model/ })).toHaveCount(0);
  } finally { release(); }
});

test("catalog failures support retry and manual input without claiming a connection", async ({ page }) => {
  let failed = true;
  await page.route("**/admin/settings/models", route => failed
    ? route.fulfill({ status: 503, json: { detail: "Synthetic catalog unavailable" } })
    : route.fulfill({ json: { models: [{ id: "available/model", label: "Available", source: "cli" }], default_model: "", warning: "" } }));
  await page.goto("/app#settings");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("agent");
  const panel = page.locator(".model-chat");
  await expect(panel.locator(".model-picker .error")).toContainText("catalog unavailable");
  await panel.getByRole("button", { name: "手动输入", exact: true }).click();
  await panel.locator('input[name="chat_agent_model"]').fill("manual/model");
  failed = false;
  await panel.getByRole("button", { name: "刷新模型", exact: true }).click();
  await expect(panel.locator(".model-picker .error")).toHaveCount(0);
  await expect(panel.locator('input[name="chat_agent_model"]')).toHaveValue("manual/model");
  await expect(panel.locator("header")).toContainText("需测试");
});

test("test transport errors and save failures replace stale success beside the action", async ({ page }) => {
  let connectionFails = false;
  let saveFails = true;
  await page.route("**/admin/settings/test", route => connectionFails
    ? route.fulfill({ status: 503, json: { detail: "Synthetic connection interrupted" } })
    : route.fulfill({ json: { chat: { ok: true, model: "fixture/model", ms: 10 } } }));
  await page.route("**/admin/settings", route => route.request().method() === "PUT"
    ? route.fulfill(saveFails ? { status: 409, json: { detail: "Synthetic save conflict" } } : { json: {} }) : route.continue());
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("endpoint");
  await panel.locator('input[name="chat_model"]').fill("my-draft");
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect(panel.locator(".connection-feedback")).toContainText("配置未保存");
  await expect(panel.locator('input[name="chat_model"]')).toHaveValue("my-draft");
  await page.setViewportSize({ width: 390, height: 844 });
  await panel.locator(".connection-feedback").scrollIntoViewIfNeeded();
  await page.screenshot({ path: "screenshots/models-save-error-mobile.png", animations: "disabled" });
  connectionFails = true;
  await panel.getByRole("button", { name: "测试连接", exact: true }).click();
  await expect(panel.locator("header")).toContainText("测试未通过");
  await expect(panel.locator(".test-result")).toHaveCount(0);
  await expect(panel.locator(".model-test .error")).toContainText("connection interrupted");
  saveFails = false;
});

test("settings load failure can recover without editing a blank configuration", async ({ page }) => {
  let failed = true;
  await page.route("**/admin/settings", route => failed ? route.fulfill({ status: 503, json: { detail: "unavailable" } }) : route.continue());
  await page.goto("/app#settings");
  await expect(page.locator(".settings-loading")).toContainText("未能读取");
  await expect(page.locator('.models input[name="chat_model"]')).toHaveCount(0);
  failed = false;
  await page.getByRole("button", { name: "重新读取设置", exact: true }).click();
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("endpoint");
  await expect(page.locator('.models input[name="chat_model"]')).toBeVisible();
});

test("automatic detection changes agent without reusing its old model or success", async ({ page }) => {
  let installed = agents;
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents: installed } }));
  await page.route("**/admin/settings/test", route => route.fulfill({ json: { chat: { ok: true, model: "codex/custom", ms: 10 } } }));
  await page.goto("/app#settings");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("agent");
  const panel = page.locator(".model-chat");
  await panel.getByRole("button", { name: "手动输入", exact: true }).click();
  await panel.locator('input[name="chat_agent_model"]').fill("codex/custom");
  await panel.getByRole("button", { name: "测试连接", exact: true }).click();
  await expect(panel.locator(".test-result")).toBeVisible();
  installed = agents.map(agent => ({ ...agent, installed: agent.id === "opencode" }));
  await panel.getByRole("button", { name: "重新检测", exact: true }).click();
  await expect(panel.locator(".agent-detection")).toContainText("OpenCode");
  await expect(panel.locator('input[name="chat_agent_model"]')).toHaveValue("");
  await expect(panel.locator(".test-result")).toHaveCount(0);
  await expect(panel.locator(".connection-feedback")).toHaveCount(0);
  await expect(panel.locator(".model-picker-trigger")).toContainText("opencode/default");
});

test("successful save keeps the acknowledged model visible when reload fails", async ({ page }) => {
  let saved: Record<string, unknown> = {};
  let reloadFails = false;
  await page.route("**/admin/settings/test", route => route.fulfill({ json: { chat: { ok: true, model: "new-model", ms: 10 } } }));
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      saved = route.request().postDataJSON().values;
      reloadFails = true;
      return route.fulfill({ json: {} });
    }
    if (reloadFails) return route.fulfill({ status: 503, json: { detail: "Synthetic reload failed" } });
    const response = await route.fetch();
    const data = await response.json();
    data.settings = data.settings.map((row: { key: string }) => row.key in saved ? { ...row, value: saved[row.key] } : row);
    return route.fulfill({ response, json: data });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat");
  await page.getByRole("combobox", { name: "摘要来源", exact: true }).selectOption("endpoint");
  await panel.locator('input[name="chat_model"]').fill("new-model");
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect(panel.locator(".connection-feedback")).toContainText("连接已验证并保存");
  await expect(page.locator(".models > .error")).toContainText("未能读取");
  await expect(panel.locator('input[name="chat_model"]')).toHaveValue("new-model");
  reloadFails = false;
  await page.getByRole("button", { name: "重新读取设置", exact: true }).click();
  await expect(page.locator(".models > .error")).toHaveCount(0);
  await expect(panel.locator('input[name="chat_model"]')).toHaveValue("new-model");
});
