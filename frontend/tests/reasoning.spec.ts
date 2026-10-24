import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const agents = ["codex", "claude", "opencode"].map(id => ({
  id, name: id === "claude" ? "Claude Code" : id === "opencode" ? "OpenCode" : "Codex",
  installed: true, path: "C:\\synthetic\\" + id + ".exe",
}));

async function settings(page: Page, initial: Record<string, unknown>) {
  const saved = { ...initial };
  await page.route("**/admin/settings", async route => {
    if (route.request().method() === "PUT") {
      Object.assign(saved, route.request().postDataJSON().values);
      return route.fulfill({ json: {} });
    }
    const response = await route.fetch();
    const data = await response.json();
    data.channels.chat.configured = true;
    data.settings = data.settings.map((row: { key: string }) => row.key in saved ? { ...row, value: saved[row.key] } : row);
    return route.fulfill({ response, json: data });
  });
  return saved;
}

test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => localStorage.setItem("fm-language", "zh"));
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await page.route("**/admin/agents", route => route.fulfill({ json: { agents } }));
  await page.route("**/admin/settings/models", route => {
    const agent = route.request().postDataJSON().chat_agent || "codex";
    return route.fulfill({ json: {
      agent, default_model: agent + "/summary", default_reasoning_effort: "medium", warning: "",
      models: [{ id: agent + "/summary", label: agent + " summary", source: "cli",
        default_reasoning_effort: "medium", reasoning_levels: (agent === "opencode"
          ? ["balanced", "careful"] : ["low", "medium", "xhigh"]).map(id => ({ id })) }],
    } });
  });
});

test("detected model levels, default and selected effort survive testing and saving", async ({ page }) => {
  const saved = await settings(page, { chat_backend: "agent", chat_agent: "codex", chat_agent_model: "", chat_agent_reasoning_effort: "" });
  let tested: Record<string, unknown> = {};
  await page.route("**/admin/settings/test", route => {
    tested = route.request().postDataJSON();
    return route.fulfill({ json: { chat: { ok: true, model: "codex/summary", ms: 1 } } });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat"), thinking = panel.getByRole("combobox", { name: "思考模式", exact: true });
  await expect(thinking.locator('option[value=""]')).toContainText("medium");
  await expect(thinking.locator('option[value="max"]')).toHaveCount(0);
  await thinking.focus(); await thinking.press("ArrowDown"); await thinking.press("Enter");
  await expect(thinking).toHaveValue("low");
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect.poll(() => tested.chat_agent_reasoning_effort).toBe("low");
  await expect.poll(() => saved.chat_agent_reasoning_effort).toBe("low");
  await expect(panel.locator(".tested-model")).toHaveText("codex/summary");
  await thinking.selectOption("xhigh");
  await expect(panel.locator(".tested-model")).toHaveCount(0);
  await expect(panel.locator("header .quiet")).toContainText("需测试");
  for (const size of [{ width: 1024, height: 749 }, { width: 390, height: 844 }, { width: 320, height: 640 }]) {
    await page.setViewportSize(size);
    await expect(thinking).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await page.screenshot({ path: "screenshots/collection-review/reasoning-agent-dark-320.png", animations: "disabled" });
});

test("each agent keeps its own thinking draft and OpenCode passes a model variant", async ({ page }) => {
  await settings(page, { chat_backend: "agent", chat_agent: "codex", chat_agent_model: "", chat_agent_reasoning_effort: "" });
  let tested: Record<string, unknown> = {};
  await page.route("**/admin/settings/test", route => {
    tested = route.request().postDataJSON();
    return route.fulfill({ json: { chat: { ok: true, model: "opencode/summary", ms: 1 } } });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat");
  const thinking = panel.getByRole("combobox", { name: "思考模式", exact: true });
  await expect(thinking.locator('option[value="xhigh"]')).toHaveCount(1);
  await thinking.selectOption("xhigh");
  await page.getByRole("combobox", { name: "选择 Agent", exact: true }).selectOption("opencode");
  await expect(thinking.locator('option[value="careful"]')).toHaveCount(1);
  await expect(thinking).toHaveValue("");
  await thinking.selectOption("careful");
  await page.getByRole("combobox", { name: "选择 Agent", exact: true }).selectOption("codex");
  await expect(thinking).toHaveValue("xhigh");
  await page.getByRole("combobox", { name: "选择 Agent", exact: true }).selectOption("opencode");
  await expect(thinking).toHaveValue("careful");
  await panel.getByRole("button", { name: "测试连接", exact: true }).click();
  await expect.poll(() => tested.chat_agent_reasoning_effort).toBe("careful");
  expect(tested.chat_agent).toBe("opencode");
  await thinking.selectOption("__custom_level__");
  await panel.getByRole("textbox", { name: "自定义思考档位", exact: true }).fill("my-summary-variant");
  await expect(thinking).toHaveValue("my-summary-variant");
});

test("API thinking controls preserve advanced parameters and do not offer unsupported off mode", async ({ page }) => {
  const saved = await settings(page, { chat_backend: "endpoint", chat_model: "gpt-6.1-sol",
    chat_extra_body: '{"max_completion_tokens":4096}', chat_base_url: "https://synthetic.invalid/v1" });
  let tested: Record<string, unknown> = {};
  await page.route("**/admin/settings/test", route => {
    tested = route.request().postDataJSON();
    return route.fulfill({ json: { chat: { ok: true, model: "gpt-6.1-sol", ms: 1 } } });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat"), thinking = panel.getByRole("combobox", { name: "思考模式", exact: true });
  await expect(thinking).toHaveValue("");
  await expect(thinking.locator('option[value="none"]')).toHaveCount(0);
  await thinking.selectOption("high");
  await panel.getByRole("button", { name: "测试并保存", exact: true }).click();
  await expect.poll(() => tested.chat_extra_body).toBeTruthy();
  expect(JSON.parse(String(tested.chat_extra_body))).toEqual({ max_completion_tokens: 4096, reasoning_effort: "high" });
  await expect.poll(() => saved.chat_extra_body).toBe(tested.chat_extra_body);
  await thinking.selectOption("");
  await panel.getByRole("button", { name: "测试连接", exact: true }).click();
  await expect.poll(() => JSON.parse(String(tested.chat_extra_body))).toEqual({ max_completion_tokens: 4096 });
  await page.screenshot({ path: "screenshots/collection-review/reasoning-api-light-1280.png", animations: "disabled" });
});

test("compatible services receive their thinking parameter shape and keep other template fields", async ({ page }) => {
  await settings(page, { chat_backend: "endpoint", chat_model: "custom-summary",
    chat_extra_body: '{"max_tokens":2048,"chat_template_kwargs":{"other_option":"keep"}}' });
  let tested: Record<string, unknown> = {};
  await page.route("**/admin/settings/test", route => {
    tested = route.request().postDataJSON();
    return route.fulfill({ json: { chat: { ok: true, model: "custom-summary", ms: 1 } } });
  });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat");
  await panel.locator(".reasoning-compatibility > summary").click();
  const format = panel.getByRole("combobox", { name: "思考参数格式", exact: true });
  const thinking = panel.getByRole("combobox", { name: "思考模式", exact: true });
  for (const method of ["thinking", "enable_thinking", "chat_template_kwargs"]) {
    await format.selectOption(method); await thinking.selectOption("none");
    tested = {};
    await panel.getByRole("button", { name: "测试连接", exact: true }).click();
    await expect.poll(() => tested.chat_extra_body).toBeTruthy();
    const body = JSON.parse(String(tested.chat_extra_body));
    expect(body.max_tokens).toBe(2048);
    expect(body.chat_template_kwargs.other_option).toBe("keep");
    if (method === "thinking") expect(body.thinking).toEqual({ type: "disabled" });
    if (method === "enable_thinking") expect(body.enable_thinking).toBe(false);
    if (method === "chat_template_kwargs") expect(body.chat_template_kwargs.enable_thinking).toBe(false);
    expect(body.reasoning_effort).toBeUndefined();
  }
});

test("Claude inherits a saved model effort before the client-wide default", async ({ page }) => {
  await settings(page, { chat_backend: "agent", chat_agent: "claude", chat_agent_model: "custom-claude", chat_agent_reasoning_effort: "" });
  await page.route("**/admin/settings/models", route => route.fulfill({ json: {
    agent: "claude", default_model: "custom-claude", configured_reasoning_effort: "low",
    default_reasoning_effort: "high", models: [{ id: "custom-claude", label: "Custom Claude",
      default_reasoning_effort: "high", source: "config" }],
  } }));
  await page.goto("/app#settings");
  const thinking = page.locator(".model-chat").getByRole("combobox", { name: "思考模式", exact: true });
  await expect(thinking.locator('option[value=""]')).toContainText("high");
});

test("invalid advanced JSON remains intact while thinking controls explain the problem", async ({ page }) => {
  await settings(page, { chat_backend: "endpoint", chat_extra_body: "{unfinished" });
  await page.goto("/app#settings");
  const panel = page.locator(".model-chat");
  await expect(panel.getByRole("combobox", { name: "思考模式", exact: true })).toBeDisabled();
  await expect(panel.locator(".reasoning-note").first()).toContainText("有效的 JSON");
  await page.locator(".models > .advanced > summary").click();
  await expect(page.locator('input[name="chat_extra_body"]')).toHaveValue("{unfinished");
});
